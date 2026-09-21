"""LOGFLUX local API and dashboard. No cloud services or CDN assets required."""
import asyncio
import base64
import csv
from contextlib import asynccontextmanager
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import time
import uuid
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .store import Store, MAX_EVENT
from .receivers import Receivers
from .schema import SCHEMA, SCHEMA_HASH, ecs_export, utcnow
from . import discovery
from .demo import scenario, drift_sample

STATIC=Path(__file__).parent/"static"

class SourceInput(BaseModel):
    name: str=Field(min_length=1,max_length=100)
    peer: str=""
    kind: str="network"
    mode: str="live"
class EventInput(BaseModel):
    source_id: str
    raw: str|None=Field(default=None,max_length=MAX_EVENT)
    raw_base64: str|None=Field(default=None,max_length=MAX_EVENT*2)
class MappingInput(BaseModel):
    mapping: dict[str,str]
class ApprovalInput(BaseModel):
    reviewer: str=Field(min_length=1,max_length=100)
    acknowledge: bool=False
class CaseInput(BaseModel):
    title: str=Field(min_length=1,max_length=200)
    event_ids: list[str]=Field(max_length=1000)
    notes: str=Field(default="",max_length=10000)
class SinkInput(BaseModel):
    name: str=Field(min_length=1,max_length=100)
    url: str=Field(max_length=2000)

def create_app(data_dir=None, start_receivers=True):
    directory=Path(data_dir or os.getenv("LOGFLUX_DATA_DIR", os.getenv("AEGIS_DATA_DIR","data")))
    directory.mkdir(parents=True,exist_ok=True)
    token_path=directory/"admin-token"
    token=os.getenv("LOGFLUX_ADMIN_TOKEN", os.getenv("AEGIS_ADMIN_TOKEN"))
    if not token:
        if token_path.exists(): token=token_path.read_text().strip()
        else:
            token=secrets.token_urlsafe(32)
            fd=os.open(token_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"w") as f: f.write(token+"\n")
    if len(token)<16: raise ValueError("LOGFLUX_ADMIN_TOKEN must contain at least 16 characters")

    async def maintenance(app):
        while not app.state.stop.is_set():
            try:
                await asyncio.to_thread(app.state.store.seal)
                await deliver_outbox(app.state.store)
            except Exception as exc:
                app.state.background_error=str(exc)
            try: await asyncio.wait_for(app.state.stop.wait(),timeout=5)
            except asyncio.TimeoutError: pass

    @asynccontextmanager
    async def lifespan(app):
        store=Store(directory); app.state.store=store; app.state.stop=asyncio.Event(); app.state.background_error=None
        app.state.demo={"running":False,"processed":0,"total":0}; app.state.demo_task=None
        receiver=Receivers(store,os.getenv("LOGFLUX_SYSLOG_HOST", os.getenv("AEGIS_SYSLOG_HOST","127.0.0.1")),int(os.getenv("LOGFLUX_SYSLOG_PORT", os.getenv("AEGIS_SYSLOG_PORT","5514"))),
                           int(os.getenv("LOGFLUX_TLS_PORT", os.getenv("AEGIS_TLS_PORT","6514"))),os.getenv("LOGFLUX_TLS_CERT", os.getenv("AEGIS_TLS_CERT")),os.getenv("LOGFLUX_TLS_KEY", os.getenv("AEGIS_TLS_KEY")),os.getenv("LOGFLUX_TLS_CA", os.getenv("AEGIS_TLS_CA")))
        app.state.receivers=receiver
        lab_receiver=Receivers(store,"127.0.0.1",int(os.getenv("LOGFLUX_LAB_PORT", os.getenv("AEGIS_LAB_PORT","5515"))),mode="lab")
        app.state.lab_receivers=lab_receiver
        store.recover()
        if start_receivers:
            await receiver.start(); await lab_receiver.start()
        task=asyncio.create_task(maintenance(app))
        print(f"LOGFLUX ready. Admin access token: {token_path.resolve()} (or LOGFLUX_ADMIN_TOKEN).",flush=True)
        yield
        app.state.stop.set()
        if app.state.demo_task: await app.state.demo_task
        if start_receivers:
            await receiver.close(); await lab_receiver.close()
        await task
        store.close()

    app=FastAPI(title="LOGFLUX Universal Log Intelligence",version="1.0.0",lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    async def auth(request:Request):
        provided=request.headers.get("authorization","")
        if not hmac.compare_digest(provided,"Bearer "+token):
            raise HTTPException(401,"Enter the local admin access token to connect.")

    @app.middleware("http")
    async def limits(request,call_next):
        length=request.headers.get("content-length")
        if length:
            try:
                if int(length)>8*1024*1024: return JSONResponse({"detail":"request exceeds 8 MiB"},status_code=413)
            except ValueError: return JSONResponse({"detail":"invalid content length"},status_code=400)
        response=await call_next(request)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["X-Frame-Options"]="DENY"
        response.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        if request.url.path.startswith("/api/"): response.headers["Cache-Control"]="no-store"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request,exc): return JSONResponse({"detail":str(exc)},status_code=400)
    @app.get("/health")
    def health(): return {"service":"logflux","status":"ok"}
    api=APIRouter(prefix="/api",dependencies=[Depends(auth)])
    def store(): return app.state.store

    @api.get("/status")
    def system_status():
        return {"version":"1.0.0","schema":SCHEMA,"schema_hash":SCHEMA_HASH,"listeners":app.state.receivers.status,
                "lab_listeners":app.state.lab_receivers.status,"demo":app.state.demo,"background_error":app.state.background_error,"registry_public_key":store().signer.public,
                "witnesses":[{"name":w.name,"enabled":w.enabled,"key_id":w.key.id} for w in store().ledger.witnesses],
                "ledger_mode":"2-of-3 signed checkpoints; local witnesses share a host", "storage":"SQLite WAL + FULL synchronous durability",
                "limits":{"event_bytes":MAX_EVENT,"single_node":True},"offline_assets":True}
    @app.exception_handler(httpx.HTTPError)
    async def upstream_error(request,exc):
        return JSONResponse({"detail":"Local model service could not complete the request. Check System & outputs; manual mapping remains available."},status_code=503)
    @api.get("/metrics")
    def metrics():
        s=store().stats()
        values={"events_total":s["total"],"normalized_total":s["normalized"],"evidence_sealed_total":s["sealed"],"pending_formats":s["pending_review"],"receiver_errors_total":s["metrics"]["receiver_errors"],"uptime_seconds":s["uptime_seconds"]}
        return Response("".join(f"# TYPE logflux_{k} gauge\nlogflux_{k} {v}\n" for k,v in values.items()),media_type="text/plain")
    @api.get("/stats")
    def stats(): return store().stats()
    @api.get("/schema")
    def schema(): return {"schema":SCHEMA,"hash":SCHEMA_HASH,"conformance":"LOGFLUX schema using OCSF concepts; not full OCSF certification"}
    @api.get("/sources")
    def sources(): return store().stats()["sources"]
    @api.post("/sources")
    def add_source(body:SourceInput): return store().register_source(**body.model_dump())
    @api.patch("/sources/{sid}")
    def update_source(sid:str,body:SourceInput):
        import ipaddress
        if not store().one("SELECT id FROM sources WHERE id=?",(sid,)): raise ValueError("source not found")
        if body.peer: ipaddress.ip_address(body.peer)
        if body.mode not in ("live","lab","replay"): raise ValueError("invalid source mode")
        if not body.name.strip(): raise ValueError("source name required")
        with store().lock:
            store().db.execute("UPDATE sources SET name=?,peer=?,kind=?,mode=? WHERE id=?",(body.name.strip(),body.peer,body.kind,body.mode,sid));store().db.commit()
        store().audit("source.updated",{"id":sid,**body.model_dump(),"scope":"future receipts only; original evidence metadata unchanged"})
        return store().one("SELECT * FROM sources WHERE id=?",(sid,))
    @api.post("/ingest")
    def ingest(body:EventInput):
        if (body.raw is None)==(body.raw_base64 is None): raise ValueError("supply exactly one of raw or raw_base64")
        raw=base64.b64decode(body.raw_base64,validate=True) if body.raw_base64 is not None else body.raw.encode()
        eid=store().ingest(raw,body.source_id,"http")
        return {"accepted":True,"event":store().event(eid)}
    @api.post("/upload")
    async def upload(request:Request,source_id:str,framing:str="lines"):
        data=bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data)>8*1024*1024: raise HTTPException(413,"upload exceeds 8 MiB")
        if framing not in ("lines","single"): raise ValueError("framing must be lines or single")
        frames=bytes(data).splitlines(keepends=True) if framing=="lines" else [bytes(data)]
        if len(frames)>10000: raise ValueError("upload limited to 10,000 events")
        ids=[]; rejected=[]
        for i,raw in enumerate(frames):
            if not raw: continue
            try: ids.append(await asyncio.to_thread(store().ingest,raw,source_id,"file","",framing))
            except ValueError as exc: rejected.append({"frame":i+1,"reason":str(exc)})
        return {"accepted":len(ids),"rejected":rejected,"event_ids":ids[:100],"ids_truncated":len(ids)>100}
    @api.get("/events")
    def events(limit:int=50,offset:int=0,status:str="",source:str="",q:str="",fingerprint:str="",mode:str=""):
        return store().events(limit,offset,status,source,q,fingerprint,mode)
    @api.get("/events/{eid}")
    def event(eid:str): return store().event(eid)
    @api.get("/events/{eid}/raw")
    def raw_event(eid:str):
        return Response(store().event(eid,raw=True)["raw"],media_type="application/octet-stream",headers={"Content-Disposition":f'attachment; filename="{uuid.UUID(eid)}.raw"'})
    @api.get("/events/{eid}/proof")
    def proof(eid:str): return store().proof(eid)
    @api.get("/events/{eid}/provenance")
    def provenance(eid:str): return store().provenance(eid)
    @api.get("/export")
    def export(format:str="jsonl",q:str="",status:str="",source:str="",mode:str="",offset:int=0):
        if format not in ("jsonl","ecs","csv"): raise ValueError("format must be jsonl, ecs or csv")
        events=store().events(limit=1000,q=q,status=status,source=source,mode=mode,offset=offset)["items"]
        if format=="csv":
            output=io.StringIO(); fields=["id","source","mode","status"]+SCHEMA["fields"]
            writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader()
            for row in events:
                values={**{k:row[k] for k in fields[:4]},**{k:(row["normalized"] or {}).get(k) for k in SCHEMA["fields"]}}
                # Protect spreadsheet consumers from formula injection.
                writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(("=","+","-","@")) else v) for k,v in values.items()})
            content=output.getvalue(); media="text/csv"; ext="csv"
        else:
            content="\n".join(json.dumps(ecs_export(r) if format=="ecs" else r,ensure_ascii=False) for r in events)+("\n" if events else "")
            media="application/x-ndjson"; ext="jsonl"
        return Response(content,media_type=media,headers={"Content-Disposition":f'attachment; filename="logflux-{format}.{ext}"',"X-Export-Limit":"1000"})
    @api.get("/candidates")
    def candidates(): return store().candidates()
    @api.get("/candidates/{cid}")
    def candidate(cid:str): return store().candidate(cid)
    @api.put("/candidates/{cid}/mapping")
    def mapping(cid:str,body:MappingInput): store().save_mapping(cid,body.mapping); return store().candidate(cid)
    @api.post("/candidates/{cid}/revise")
    def revise(cid:str): return store().revise_candidate(cid)
    @api.post("/candidates/{cid}/validate")
    def validate(cid:str,body:dict|None=None): return store().validate_candidate(cid,(body or {}).get("expectations",[]))
    @api.post("/candidates/{cid}/approve")
    def approve(cid:str,body:ApprovalInput): return store().approve(cid,body.reviewer,body.acknowledge)
    @api.post("/candidates/{cid}/replay")
    def replay(cid:str): return store().replay(store().candidate(cid)["fingerprint"])
    @api.post("/candidates/{cid}/llm")
    def llm(cid:str):
        proposal=discovery.propose(store().candidate(cid)); store().save_mapping(cid,proposal["mapping"],"local-llm:"+proposal["model"])
        store().audit("candidate.llm_proposal",{"candidate":cid,"model":proposal["model"]})
        return proposal
    @api.get("/llm/status")
    def llm_status(): return discovery.status()
    @api.get("/plugins")
    def plugins():
        result=[]
        for row in store().rows("SELECT * FROM plugins ORDER BY created_at DESC"):
            bundle=json.loads(row.pop("bundle")); row.update({"reviewer":bundle["payload"]["reviewer"],"signature":bundle["signature"],"mapping":bundle["payload"]["mapping"]}); result.append(row)
        return result
    @api.get("/plugins/{pid}/bundle")
    def bundle(pid:str):
        row=store().one("SELECT bundle FROM plugins WHERE id=?",(pid,))
        if not row: raise ValueError("plugin not found")
        return Response(row["bundle"],media_type="application/json",headers={"Content-Disposition":'attachment; filename="parser.logflux.json"'})
    @api.post("/plugins/import")
    def import_plugin(body:dict): return store().import_plugin(body)
    @api.post("/plugins/{pid}/activate")
    def activate(pid:str): return store().activate_plugin(pid)
    @api.post("/integrity/seal")
    def seal(): return store().seal()
    @api.get("/integrity/batches")
    def batches():
        rows=store().rows("SELECT * FROM batches ORDER BY seq DESC LIMIT 100")
        for row in rows:
            row["checkpoint"]=json.loads(row["checkpoint"]); row["anchoring"]=json.loads(row["anchoring"])
        return rows
    @api.get("/integrity/audit")
    def audit(): return store().rows("SELECT * FROM audit ORDER BY seq DESC LIMIT 100")
    @api.post("/integrity/witness/{name}")
    def witness(name:str,body:dict):
        for w in store().ledger.witnesses:
            if w.name==name:
                w.enabled=bool(body.get("enabled",True)); store().audit("witness.availability",{"name":name,"enabled":w.enabled}); return {"name":name,"enabled":w.enabled}
        raise ValueError("witness not found")
    @api.get("/graph")
    def graph(ip:str="", source:str="", minutes:int=Query(default=0,ge=0,le=43200)): return store().relationships(ip,source,minutes)
    @api.get("/alerts")
    def alerts(): return store().rows("SELECT a.*,r.source,r.mode FROM alerts a JOIN raw_events r ON r.id=a.event_id ORDER BY created_at DESC LIMIT 100")
    @api.get("/cases")
    def cases():
        rows=store().rows("SELECT * FROM cases ORDER BY created_at DESC")
        for row in rows: row["event_ids"]=json.loads(row["event_ids"])
        return rows
    @api.post("/cases")
    def create_case(body:CaseInput):
        if not body.event_ids: raise ValueError("select at least one event")
        for eid in body.event_ids: store().event(eid)
        cid=str(uuid.uuid4())
        with store().lock:
            store().db.execute("INSERT INTO cases VALUES(?,?,?,?,?)",(cid,body.title,json.dumps(body.event_ids),body.notes,utcnow())); store().db.commit()
        store().audit("case.created",{"case":cid,"events":body.event_ids})
        return {"id":cid}
    @api.get("/sinks")
    def sinks(): return store().rows("SELECT s.*,(SELECT COUNT(*) FROM outbox o WHERE o.sink_id=s.id AND status='delivered') delivered,(SELECT COUNT(*) FROM outbox o WHERE o.sink_id=s.id AND status='pending') pending FROM sinks s")
    @api.post("/sinks")
    def add_sink(body:SinkInput):
        parsed=urlparse(body.url)
        if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.password: raise ValueError("provide an HTTP(S) endpoint without credentials in its URL")
        sid=str(uuid.uuid4())
        with store().lock:
            store().db.execute("INSERT INTO sinks VALUES(?,?,?,1,?)",(sid,body.name,body.url,utcnow())); store().db.commit()
        store().audit("sink.created",{"id":sid,"name":body.name})
        return {"id":sid}
    @api.post("/sinks/{sid}/toggle")
    def toggle_sink(sid:str,body:dict):
        with store().lock:
            if not store().one("SELECT id FROM sinks WHERE id=?",(sid,)): raise ValueError("sink not found")
            store().db.execute("UPDATE sinks SET enabled=? WHERE id=?",(bool(body.get("enabled")),sid)); store().db.commit()
        return {"updated":True}
    @api.get("/outbox")
    def outbox(): return store().rows("SELECT id,sink_id,event_id,status,attempts,error FROM outbox ORDER BY rowid DESC LIMIT 100")
    @api.post("/demo/start")
    async def demo_start(body:dict|None=None):
        if app.state.demo["running"]: raise ValueError("replay already running")
        count=min(max(int((body or {}).get("count",120)),5),1000)
        app.state.demo={"running":True,"processed":0,"total":count,"label":"Synthetic replay"}
        async def run():
            try:
                sources={}
                for item in scenario(count):
                    if app.state.stop.is_set(): break
                    if item["source"] not in sources: sources[item["source"]]=await asyncio.to_thread(store().register_source,item["source"],"",item["kind"],"replay")
                    await asyncio.to_thread(store().ingest,item["raw"],sources[item["source"]]["id"],"scenario-replay")
                    app.state.demo["processed"]+=1
                    await asyncio.sleep(.075)
                await asyncio.to_thread(store().seal)
            except Exception as exc: app.state.demo["error"]=str(exc)
            finally: app.state.demo["running"]=False
        app.state.demo_task=asyncio.create_task(run()); return app.state.demo
    @api.post("/demo/drift")
    def demo_drift():
        source=store().register_source("FortiGate · perimeter","","firewall","replay")
        eid=store().ingest(drift_sample(),source["id"],"scenario-replay")
        return store().event(eid)

    app.include_router(api)
    app.mount("/static",StaticFiles(directory=STATIC),name="static")
    @app.get("/")
    def index(): return FileResponse(STATIC/"index.html")
    return app

async def deliver_outbox(store):
    rows=store.rows("SELECT o.*,s.url FROM outbox o JOIN sinks s ON s.id=o.sink_id WHERE o.status='pending' AND o.next_attempt<=? AND s.enabled=1 ORDER BY o.rowid LIMIT 20",(time.time(),))
    if not rows: return
    async with httpx.AsyncClient(timeout=3,trust_env=False,follow_redirects=False) as client:
        for row in rows:
            error=None; delivered=False
            try:
                response=await client.post(row["url"],content=row["payload"],headers={"Content-Type":"application/json","Idempotency-Key":row["id"]})
                response.raise_for_status(); delivered=True
            except Exception as exc: error=str(exc)[:500]
            with store.lock:
                store.db.execute("UPDATE outbox SET status=?,attempts=attempts+1,error=?,next_attempt=? WHERE id=?",
                                 ("delivered" if delivered else "pending",error,time.time()+min(300,2**min(row["attempts"]+1,8)),row["id"])); store.db.commit()

if __name__=="__main__":
    import uvicorn
    uvicorn.run(create_app(),host=os.getenv("LOGFLUX_HOST", os.getenv("AEGIS_HOST","127.0.0.1")),port=int(os.getenv("LOGFLUX_PORT", os.getenv("AEGIS_PORT","8765"))),log_level="info")
