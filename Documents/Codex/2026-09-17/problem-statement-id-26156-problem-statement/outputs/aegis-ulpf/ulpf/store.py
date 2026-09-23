"""Single-node durable event store and preprocessing control plane.

SQLite WAL is deliberately a demonstrator implementation, not a billion/day claim.
Raw evidence and normalized revisions are separate, append-only records.
"""
import base64
from collections import Counter
import ipaddress
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig
from .schema import canonical, digest, utcnow, normalize, SCHEMA_HASH, COMPATIBLE_SCHEMA_HASHES
from .parsers import decode, suggest_mapping, built_in_mapping
from .integrity import SigningKey, WitnessLedger, merkle, leaf_hash, verify_proof, verify_signature, b64, unb64
from .sandbox import Sandbox

MAX_EVENT = 256 * 1024

class Store:
    def __init__(self, directory):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock(); self.seal_lock = threading.Lock()
        self.db = sqlite3.connect(self.directory/"events.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, name TEXT NOT NULL, peer TEXT, kind TEXT, mode TEXT, created_at TEXT, last_seen TEXT, baseline TEXT, enabled INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS raw_events(id TEXT PRIMARY KEY, raw BLOB NOT NULL, raw_hash TEXT NOT NULL, source_id TEXT NOT NULL, source TEXT NOT NULL, mode TEXT NOT NULL, transport TEXT, peer TEXT, received_at TEXT NOT NULL, framing TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY REFERENCES raw_events(id), status TEXT, format TEXT, fingerprint TEXT, parser TEXT, normalized TEXT, attributes TEXT, error TEXT, revision INTEGER DEFAULT 0, duration_ms REAL);
        CREATE INDEX IF NOT EXISTS ix_events_fingerprint ON events(fingerprint,status);
        CREATE INDEX IF NOT EXISTS ix_raw_time ON raw_events(received_at);
        CREATE INDEX IF NOT EXISTS ix_raw_source ON raw_events(source_id);
        CREATE TABLE IF NOT EXISTS revisions(id TEXT PRIMARY KEY, event_id TEXT REFERENCES raw_events(id), version INTEGER, parser TEXT, normalized TEXT, status TEXT, created_at TEXT, UNIQUE(event_id,version));
        CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, fingerprint TEXT, format TEXT, source TEXT, mapping TEXT, keys TEXT, template TEXT, status TEXT, report TEXT, created_at TEXT, proposal_source TEXT DEFAULT 'deterministic');
        CREATE UNIQUE INDEX IF NOT EXISTS ix_candidate_active ON candidates(fingerprint) WHERE status IN ('draft','validated');
        CREATE TABLE IF NOT EXISTS plugins(id TEXT PRIMARY KEY, fingerprint TEXT, version INTEGER, bundle TEXT, active INTEGER, created_at TEXT, UNIQUE(fingerprint,version));
        CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY, seq INTEGER UNIQUE, root TEXT, checkpoint TEXT, anchoring TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS members(event_id TEXT PRIMARY KEY REFERENCES raw_events(id), batch_id TEXT REFERENCES batches(id), manifest TEXT, leaf TEXT, proof TEXT);
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, action TEXT, detail TEXT, previous TEXT, hash TEXT, signature TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY, event_id TEXT REFERENCES raw_events(id), rule TEXT, severity TEXT, title TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, title TEXT, event_ids TEXT, notes TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS sinks(id TEXT PRIMARY KEY, name TEXT, url TEXT, enabled INTEGER, created_at TEXT);
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, sink_id TEXT REFERENCES sinks(id), event_id TEXT, revision INTEGER, payload TEXT, status TEXT, attempts INTEGER DEFAULT 0, error TEXT, next_attempt REAL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS ix_outbox_status ON outbox(status,next_attempt);
        CREATE TRIGGER IF NOT EXISTS immutable_raw_update BEFORE UPDATE ON raw_events BEGIN SELECT RAISE(ABORT,'raw evidence is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_raw_delete BEFORE DELETE ON raw_events BEGIN SELECT RAISE(ABORT,'raw evidence is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'revisions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'revisions are immutable'); END;
        ''')
        self.db.commit()
        self.signer = SigningKey(self.directory/"keys"/"registry.key")
        self.ledger = WitnessLedger(self.directory/"keys")
        self.sandbox = Sandbox()
        config = TemplateMinerConfig(); config.drain_max_clusters = 1000
        self.miner = TemplateMiner(config=config)
        self.started = time.time()
        self.metrics = {"rejected":0,"receiver_errors":0,"last_receiver_error":None}

    def rows(self, sql, args=()):
        with self.lock: return [dict(r) for r in self.db.execute(sql,args).fetchall()]
    def one(self, sql, args=()):
        rows = self.rows(sql,args); return rows[0] if rows else None
    def audit(self, action, detail):
        with self.lock:
            last = self.db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            entry = {"time":utcnow(),"action":action,"detail":detail,"previous":last[0] if last else "0"*64}
            h = digest(canonical(entry)); sig = self.signer.sign(entry)
            self.db.execute("INSERT INTO audit(time,action,detail,previous,hash,signature) VALUES(?,?,?,?,?,?)",
                            (entry["time"],action,json.dumps(detail),entry["previous"],h,json.dumps(sig)))
            self.db.commit()

    def register_source(self, name, peer="", kind="network", mode="live"):
        name = str(name).strip()
        if not name or len(name)>100: raise ValueError("source name must contain 1–100 characters")
        if mode not in ("live","replay","lab"): raise ValueError("invalid source mode")
        if peer:
            try: ipaddress.ip_address(peer)
            except ValueError: raise ValueError("peer must be a literal IPv4 or IPv6 address")
        with self.lock:
            existing = self.one("SELECT * FROM sources WHERE name=? AND mode=?",(name,mode))
            if existing: return existing
            sid = str(uuid.uuid4())
            self.db.execute("INSERT INTO sources(id,name,peer,kind,mode,created_at,enabled) VALUES(?,?,?,?,?,?,1)",(sid,name,peer,kind,mode,utcnow()))
            self.db.commit(); self.audit("source.registered",{"id":sid,"name":name,"mode":mode})
            return self.one("SELECT * FROM sources WHERE id=?",(sid,))

    def resolve_peer(self, peer):
        row = self.one("SELECT * FROM sources WHERE peer=? AND enabled=1 AND mode IN ('live','lab') ORDER BY created_at LIMIT 1",(peer,))
        if row: return row
        return self.register_source(f"Device {peer}",peer,"unclassified","live")

    def ingest(self, raw, source_id, transport="http", peer="", framing="message"):
        if not isinstance(raw, bytes): raise ValueError("raw input must be bytes")
        if not raw or len(raw)>MAX_EVENT:
            self.metrics["rejected"] += 1
            raise ValueError(f"event must contain 1–{MAX_EVENT} bytes")
        source = self.one("SELECT * FROM sources WHERE id=? AND enabled=1",(source_id,))
        if not source: raise ValueError("source does not exist or is disabled")
        eid, now = str(uuid.uuid4()), utcnow()
        with self.lock:
            try:
                self.db.execute("INSERT INTO raw_events VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,raw,digest(raw),source_id,source["name"],source["mode"],transport,peer,now,framing))
                self.db.execute("INSERT INTO events(id,status) VALUES(?,'queued')",(eid,))
                self.db.execute("UPDATE sources SET last_seen=? WHERE id=?",(now,source_id))
                self.db.commit()
            except Exception:
                self.db.rollback(); raise
        # Durable raw commit precedes all parsing and downstream work.
        self.process(eid)
        return eid

    def process(self, eid):
        start = time.perf_counter()
        with self.lock:
            row = self.one("SELECT r.*,e.revision FROM raw_events r JOIN events e USING(id) WHERE id=?",(eid,))
            if not row: raise ValueError("event not found")
            revision = row["revision"]+1
            normalized, attributes, error, fmt, fp, parser = None, {}, None, "unknown", None, None
            status = "unparsed"
            try:
                parsed = decode(row["raw"])
                fmt, fp, attributes = parsed["format"],parsed["fingerprint"],parsed["attributes"]
                plugin = self.one("SELECT * FROM plugins WHERE fingerprint=? AND active=1 ORDER BY version DESC LIMIT 1",(fp,))
                mapping = None
                if plugin:
                    bundle = json.loads(plugin["bundle"])
                    verify_signature(bundle["payload"],bundle["signature"],[self.signer.public]+self.extra_trusted_keys())
                    payload = bundle["payload"]
                    mapping = self.sandbox.project(unb64(payload["wasm"]),payload["keys"],attributes)
                    parser = f"{plugin['id']}@{plugin['version']}"
                else:
                    mapping = built_in_mapping(parsed)
                    if mapping: parser = f"builtin:{parsed['vendor']}@1"
                source = self.one("SELECT * FROM sources WHERE id=?",(row["source_id"],))
                baseline = json.loads(source["baseline"] or "[]")
                drift = bool(baseline and fp not in baseline)
                # New fingerprints are staged even if a broad built-in adapter accepts them.
                if drift and not plugin:
                    mapping = None; status = "drifted"
                if mapping:
                    context = {"event_id":eid,"raw_hash":row["raw_hash"],"source":row["source"],"source_id":row["source_id"],"received_at":row["received_at"],"parser":parser,"revision":revision,"mode":row["mode"]}
                    normalized = normalize(attributes,mapping,context)
                    status = "partial" if normalized["quality"]["issues"] else "normalized"
                    if status == "partial": self.ensure_candidate(parsed,row["source"])
                    if fp not in baseline:
                        baseline.append(fp)
                        self.db.execute("UPDATE sources SET baseline=? WHERE id=?",(json.dumps(baseline),row["source_id"]))
                else:
                    status = "drifted" if drift else "unparsed"
                    self.ensure_candidate(parsed,row["source"])
            except Exception as exc:
                status, error = "failed", f"{type(exc).__name__}: {str(exc)[:500]}"
            norm_json = json.dumps(normalized,ensure_ascii=False) if normalized else None
            self.db.execute("UPDATE events SET status=?,format=?,fingerprint=?,parser=?,normalized=?,attributes=?,error=?,revision=?,duration_ms=? WHERE id=?",
                            (status,fmt,fp,parser,norm_json,json.dumps(attributes,ensure_ascii=False),error,revision,(time.perf_counter()-start)*1000,eid))
            self.db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?,?)",(str(uuid.uuid4()),eid,revision,parser,norm_json,status,utcnow()))
            if normalized:
                self.detect(eid,normalized)
                for sink in self.rows("SELECT * FROM sinks WHERE enabled=1"):
                    delivery_id = str(uuid.uuid4())
                    self.db.execute("INSERT INTO outbox(id,sink_id,event_id,revision,payload,status) VALUES(?,?,?,?,?,'pending')",
                                    (delivery_id,sink["id"],eid,revision,json.dumps({"delivery_id":delivery_id,"event":normalized})))
            self.db.commit()
            return status

    def ensure_candidate(self, parsed, source):
        found = self.one("SELECT id FROM candidates WHERE fingerprint=? AND status IN ('draft','validated')",(parsed["fingerprint"],))
        if found: return found["id"]
        template = parsed["template"]
        if parsed["body"]:
            mined = self.miner.add_log_message(parsed["body"][:8000]); template = mined["template_mined"]
        cid = str(uuid.uuid4())
        self.db.execute("INSERT INTO candidates(id,fingerprint,format,source,mapping,keys,template,status,created_at) VALUES(?,?,?,?,?,?,?,'draft',?)",
                        (cid,parsed["fingerprint"],parsed["format"],source,json.dumps(suggest_mapping(parsed["attributes"])),json.dumps(sorted(parsed["attributes"])),template,utcnow()))
        return cid

    def extra_trusted_keys(self):
        path = self.directory/"trusted-plugin-keys.json"
        return json.loads(path.read_text()) if path.exists() else []

    def candidate(self, cid):
        row = self.one("SELECT * FROM candidates WHERE id=?",(cid,))
        if not row: raise ValueError("candidate not found")
        for key in ("mapping","keys","report"):
            row[key] = json.loads(row[key]) if row[key] else None
        row["samples"] = self.events(fingerprint=row["fingerprint"],limit=8)["items"]
        return row

    def save_mapping(self, cid, mapping, proposal_source="reviewer"):
        candidate = self.candidate(cid)
        if candidate["status"] == "approved": raise ValueError("approved candidates are immutable; create a new version")
        if not isinstance(mapping,dict) or not mapping: raise ValueError("mapping must be a nonempty object")
        from .schema import SCHEMA
        if any(k not in SCHEMA["fields"] or v not in candidate["keys"] for k,v in mapping.items()): raise ValueError("mapping contains an unknown target or source field")
        with self.lock:
            self.db.execute("UPDATE candidates SET mapping=?,report=NULL,status='draft',proposal_source=? WHERE id=?",(json.dumps(mapping),proposal_source,cid)); self.db.commit()
        self.audit("candidate.mapping",{"candidate":cid,"mapping":mapping,"proposal_source":proposal_source})

    def revise_candidate(self, cid):
        with self.lock:
            c = self.candidate(cid)
            if c["status"] != "approved": raise ValueError("only approved candidates can be revised")
            existing = self.one("SELECT id FROM candidates WHERE fingerprint=? AND status IN ('draft','validated')",(c["fingerprint"],))
            if existing: return self.candidate(existing["id"])
            new_id = str(uuid.uuid4())
            self.db.execute("INSERT INTO candidates(id,fingerprint,format,source,mapping,keys,template,status,created_at,proposal_source) VALUES(?,?,?,?,?,?,?,'draft',?,?)",
                (new_id,c["fingerprint"],c["format"],c["source"],json.dumps(c["mapping"]),json.dumps(c["keys"]),c["template"],utcnow(),"revision:"+cid))
            self.db.commit()
            self.audit("candidate.revised",{"previous":cid,"candidate":new_id})
            return self.candidate(new_id)

    def validate_candidate(self, cid, expectations=None):
        c = self.candidate(cid); mapping, keys = c["mapping"], c["keys"]
        if c["status"] == "approved": raise ValueError("candidate already approved")
        wasm = self.sandbox.compile(mapping,keys)
        samples = self.rows("SELECT r.*,e.attributes FROM raw_events r JOIN events e USING(id) WHERE e.fingerprint=? ORDER BY r.received_at DESC LIMIT 100",(c["fingerprint"],))
        results, vectors, mutation_count, failed = [], [], 0, 0
        expectations = expectations or []
        from .schema import SCHEMA
        if not isinstance(expectations,list) or len(expectations)>100: raise ValueError("expectations must be an array of at most 100 samples")
        sample_ids={sample["id"] for sample in samples}
        for e in expectations:
            if not isinstance(e,dict) or e.get("event_id") not in sample_ids: raise ValueError("semantic assertion must reference a sample in this validation batch")
            if not isinstance(e.get("fields"),dict) or not e["fields"] or any(k not in SCHEMA["fields"] for k in e["fields"]): raise ValueError("semantic assertion requires known normalized fields")
        for sample in samples:
            attrs = json.loads(sample["attributes"])
            selected = self.sandbox.project(wasm,keys,attrs)
            n = normalize(attrs,selected,{"source":sample["source"],"received_at":sample["received_at"]})
            errors = list(n["quality"]["issues"])
            for expectation in expectations:
                if expectation.get("event_id") == sample["id"]:
                    for field, value in expectation.get("fields",{}).items():
                        if n.get(field) != value: errors.append({"field":field,"reason":"semantic expectation failed","expected":value,"actual":n.get(field)})
            failed += bool(errors)
            results.append({"event_id":sample["id"],"passed":not errors,"issues":errors,"preview":n})
            vectors.append({"raw_base64":b64(sample["raw"]),"attributes":attrs,"expected_projection":selected})
            # Mutation tests check deterministic decoder containment. Rejecting input is acceptable.
            for mutated in (sample["raw"][:3],b"\xff"+sample["raw"],sample["raw"]+b"\x00",b'{"src":',b'<x><!ENTITY a "x"></x>'):
                try: decode(mutated)
                except Exception: pass
                mutation_count += 1
        if len(mapping)<2: failed += 1
        known_pairs = {}
        for old in self.rows("SELECT r.source_id,e.normalized FROM events e JOIN raw_events r USING(id) WHERE e.normalized IS NOT NULL ORDER BY r.received_at DESC LIMIT 2000"):
            n=json.loads(old["normalized"])
            pair=(n.get("source_ip"),n.get("destination_ip"))
            if all(pair): known_pairs.setdefault(pair,set()).add(old["source_id"])
        corroborated=0
        for result,sample in zip(results,samples):
            n=result["preview"]; pair=(n.get("source_ip"),n.get("destination_ip"))
            if known_pairs.get(pair,set())-{sample["source_id"]}: corroborated+=1
        semantic_assertions=sum(len(e.get("fields",{})) for e in expectations)
        signals={"syntax_replay":bool(samples),"type_conformity":failed==0,"semantic_assertions":semantic_assertions,
                 "cross_source_pairs":corroborated,"cross_source_scope":"pair co-occurrence in latest 2,000 normalized events; no identity or causality guarantee"}
        confidence=(25 if samples else 0)+(25 if failed==0 else 0)+(30 if semantic_assertions and failed==0 else 0)+(20 if corroborated else 0)
        report = {"passed":bool(samples) and failed==0,"samples":len(samples),"failed_samples":failed,
                  "mutations":mutation_count,"mutation_scope":"decoder exception containment; Hypothesis suite separately tests preservation",
                  "sandbox":{"runtime":"Wasmtime","host_imports":0,"memory_bytes":65536,"fuel":10000},
                  "semantic_assertions":semantic_assertions,"signals":signals,
                  "mapping_hash":digest(canonical(mapping)),"results":results,"tested_at":utcnow(),"vectors":vectors,
                  "confidence":confidence,
                  "confidence_note":"heuristic review priority, not calibrated probability of correctness"}
        with self.lock:
            self.db.execute("UPDATE candidates SET report=?,status=? WHERE id=?",(json.dumps(report),"validated" if report["passed"] else "draft",cid)); self.db.commit()
        self.audit("candidate.validated",{"candidate":cid,"passed":report["passed"],"samples":len(samples)})
        return report

    def approve(self, cid, reviewer, acknowledge):
        with self.lock:
            c = self.candidate(cid); report = c["report"]
            if not acknowledge: raise ValueError("reviewer must confirm semantic mapping review")
            if not reviewer.strip(): raise ValueError("reviewer name required")
            if c["status"] != "validated" or not report or not report["passed"] or report["mapping_hash"] != digest(canonical(c["mapping"])):
                raise ValueError("a successful validation of the current mapping is required")
            version = self.one("SELECT COALESCE(MAX(version),0)+1 n FROM plugins WHERE fingerprint=?",(c["fingerprint"],))["n"]
            pid = f"parser-{c['fingerprint'][:10]}-v{version}"
            binary = self.sandbox.compile(c["mapping"],c["keys"])
            payload = {"id":pid,"version":version,"fingerprint":c["fingerprint"],"schema_hash":SCHEMA_HASH,"mapping":c["mapping"],"keys":c["keys"],"wasm":b64(binary),"wasm_sha256":digest(binary),
                       "sbom":{"bomFormat":"CycloneDX","specVersion":"1.5","version":1,"components":[{"type":"application","name":pid,"version":str(version),"hashes":[{"alg":"SHA-256","content":digest(binary)}]}]},
                       "test_vectors":report["vectors"],"reviewer":reviewer,"approved_at":utcnow(),"format":c["format"]}
            bundle = {"payload":payload,"signature":self.signer.sign(payload)}
            self.db.execute("UPDATE plugins SET active=0 WHERE fingerprint=?",(c["fingerprint"],))
            self.db.execute("INSERT INTO plugins VALUES(?,?,?,?,1,?)",(pid,c["fingerprint"],version,json.dumps(bundle),utcnow()))
            self.db.execute("UPDATE candidates SET status='approved' WHERE id=?",(cid,)); self.db.commit()
            self.audit("plugin.approved",{"plugin":pid,"reviewer":reviewer,"candidate":cid})
            return {"plugin":pid,"version":version,"signature":bundle["signature"]}

    def replay(self, fingerprint):
        ids = self.rows("SELECT id FROM events WHERE fingerprint=? ORDER BY id",(fingerprint,))
        result = Counter(self.process(row["id"]) for row in ids)
        self.audit("events.replayed",{"fingerprint":fingerprint,"count":len(ids),"statuses":dict(result)})
        return {"count":len(ids),"statuses":dict(result)}

    def activate_plugin(self, pid):
        with self.lock:
            plugin = self.one("SELECT * FROM plugins WHERE id=?",(pid,))
            if not plugin: raise ValueError("plugin not found")
            self.db.execute("UPDATE plugins SET active=0 WHERE fingerprint=?",(plugin["fingerprint"],))
            self.db.execute("UPDATE plugins SET active=1 WHERE id=?",(pid,)); self.db.commit()
            self.audit("plugin.activated",{"plugin":pid})
        return {"active":pid}

    def import_plugin(self, bundle):
        payload = bundle["payload"]
        verify_signature(payload,bundle["signature"],[self.signer.public]+self.extra_trusted_keys())
        if payload["schema_hash"] not in COMPATIBLE_SCHEMA_HASHES: raise ValueError("plugin schema differs from this runtime")
        binary = unb64(payload["wasm"])
        if digest(binary) != payload["wasm_sha256"]: raise ValueError("binary hash mismatch")
        if not payload.get("test_vectors"): raise ValueError("bundle has no test vectors")
        for vector in payload["test_vectors"]:
            result = self.sandbox.project(binary,payload["keys"],vector["attributes"])
            if result != vector["expected_projection"]: raise ValueError("bundle test vector failed")
        with self.lock:
            if self.one("SELECT id FROM plugins WHERE id=?",(payload["id"],)): raise ValueError("plugin already exists")
            self.db.execute("INSERT INTO plugins VALUES(?,?,?,?,0,?)",(payload["id"],payload["fingerprint"],payload["version"],json.dumps(bundle),utcnow())); self.db.commit()
        self.audit("plugin.imported",{"plugin":payload["id"],"active":False})
        return {"plugin":payload["id"],"active":False}

    def event(self, eid, raw=False):
        row = self.one("SELECT r.*,e.status,e.format,e.fingerprint,e.parser,e.normalized,e.attributes,e.error,e.revision,e.duration_ms FROM raw_events r JOIN events e USING(id) WHERE id=?",(eid,))
        if not row: raise ValueError("event not found")
        if not raw:
            value = row.pop("raw")
            row["raw_text"] = value.decode("utf-8",errors="replace")
            row["raw_base64"] = b64(value)
            row["raw_size"] = len(value)
        row["normalized"] = json.loads(row["normalized"]) if row["normalized"] else None
        row["attributes"] = json.loads(row["attributes"] or "{}")
        return row

    def events(self, limit=50, offset=0, status="", source="", q="", fingerprint="", mode=""):
        where, args = [], []
        for col,val in (("e.status",status),("r.source_id",source),("e.fingerprint",fingerprint),("r.mode",mode)):
            if val: where.append(f"{col}=?"); args.append(val)
        if q:
            where.append("(r.source LIKE ? OR e.normalized LIKE ? OR CAST(r.raw AS TEXT) LIKE ?)"); args.extend([f"%{q[:200]}%"]*3)
        clause = " WHERE "+" AND ".join(where) if where else ""
        total = self.one("SELECT COUNT(*) n FROM raw_events r JOIN events e USING(id)"+clause,args)["n"]
        ids = self.rows("SELECT r.id FROM raw_events r JOIN events e USING(id)"+clause+" ORDER BY r.received_at DESC,r.rowid DESC LIMIT ? OFFSET ?",args+[min(max(limit,1),1000),max(offset,0)])
        return {"items":[self.event(r["id"]) for r in ids],"total":total,"offset":offset}

    def seal(self):
        with self.seal_lock:
            with self.lock:
                rows = self.rows("SELECT r.id,r.raw_hash,r.source_id,r.source,r.mode,r.transport,r.peer,r.received_at,r.framing FROM raw_events r LEFT JOIN members m ON m.event_id=r.id WHERE m.event_id IS NULL ORDER BY r.received_at,r.rowid LIMIT 1000")
                if rows:
                    root, proofs = merkle([leaf_hash(r) for r in rows])
                    last = self.one("SELECT checkpoint,seq FROM batches ORDER BY seq DESC LIMIT 1")
                    sequence = last["seq"]+1 if last else 1
                    checkpoint = {"sequence":sequence,"previous":digest(canonical(json.loads(last["checkpoint"]))) if last else "0"*64,"root":root,"event_count":len(rows),"created_at":utcnow()}
                    bid = str(uuid.uuid4())
                    self.db.execute("INSERT INTO batches VALUES(?,?,?,?,?,?)",(bid,sequence,root,json.dumps(checkpoint),json.dumps({"anchored":False,"votes":[],"errors":[],"quorum":2}),utcnow()))
                    for manifest,proof in zip(rows,proofs):
                        self.db.execute("INSERT INTO members VALUES(?,?,?,?,?)",(manifest["id"],bid,json.dumps(manifest),leaf_hash(manifest),json.dumps(proof)))
                    self.db.commit()
            history = []
            for batch in self.rows("SELECT * FROM batches ORDER BY seq"):
                checkpoint = json.loads(batch["checkpoint"])
                current = json.loads(batch["anchoring"])
                if len(current.get("votes",[])) < len(self.ledger.witnesses):
                    result = self.ledger.anchor(checkpoint,history)
                    with self.lock:
                        self.db.execute("UPDATE batches SET anchoring=? WHERE id=?",(json.dumps(result),batch["id"])); self.db.commit()
                history.append(checkpoint)
            return {"sealed_events":len(rows),"batches":len(history)}

    def proof(self, eid):
        event = self.event(eid,raw=True)
        member = self.one("SELECT m.*,b.root,b.checkpoint,b.anchoring FROM members m JOIN batches b ON b.id=m.batch_id WHERE event_id=?",(eid,))
        raw_ok = digest(event["raw"]) == event["raw_hash"]
        if not member: return {"event_id":eid,"raw_hash_valid":raw_ok,"sealed":False,"verified":False}
        manifest = json.loads(member["manifest"]); proof = json.loads(member["proof"])
        manifest_ok = all(event.get(k) == v for k,v in manifest.items())
        merkle_ok = verify_proof(leaf_hash(manifest),proof,member["root"])
        checkpoint, anchor = json.loads(member["checkpoint"]),json.loads(member["anchoring"])
        valid_keys = set()
        for vote in anchor["votes"]:
            try:
                verify_signature(checkpoint,vote,self.ledger.trusted); valid_keys.add(vote["public_key"])
            except Exception: pass
        chain_ok = True; previous = "0"*64
        for batch in self.rows("SELECT checkpoint FROM batches WHERE seq<=? ORDER BY seq",(checkpoint["sequence"],)):
            payload = json.loads(batch["checkpoint"])
            if payload["previous"] != previous: chain_ok=False
            previous = digest(canonical(payload))
        quorum_ok = len(valid_keys)>=self.ledger.quorum and checkpoint["root"]==member["root"] and chain_ok
        return {"event_id":eid,"sealed":True,"raw_hash_valid":raw_ok,"manifest_valid":manifest_ok,"merkle_valid":merkle_ok,
                "ledger_valid":quorum_ok,"chain_valid":chain_ok,"verified":raw_ok and manifest_ok and merkle_ok and quorum_ok,
                "manifest":manifest,"leaf":leaf_hash(manifest),"proof":proof,"root":member["root"],"checkpoint":checkpoint,"anchor":anchor,
                "trusted_witness_keys":self.ledger.trusted,"trust_note":"Local witnesses share one host. Verification detects inconsistency; it does not prove source truth or independent custody."}

    def detect(self, eid, n):
        alerts = []
        if n["event_type"] == "intrusion_detection" or n["action"]=="alert": alerts.append(("ids-signal",n["severity"] if n["severity"]!="unknown" else "medium",n["message"] or "IDS signal observed"))
        if n["action"]=="deny" and n["destination_port"] in (22,23,3389,445): alerts.append(("blocked-admin","medium",f"Blocked connection to management port {n['destination_port']}"))
        for rule,severity,title in alerts:
            aid = digest(f"{eid}:{rule}".encode())[:32]
            self.db.execute("INSERT OR IGNORE INTO alerts VALUES(?,?,?,?,?,?)",(aid,eid,rule,severity,title,utcnow()))

    def stats(self):
        statuses = {r["status"]:r["n"] for r in self.rows("SELECT status,COUNT(*) n FROM events GROUP BY status")}
        total = sum(statuses.values()); normalized = statuses.get("normalized",0)+statuses.get("partial",0)
        sources = self.rows("SELECT s.*,COUNT(r.id) events FROM sources s LEFT JOIN raw_events r ON r.source_id=s.id GROUP BY s.id ORDER BY s.last_seen DESC")
        now = datetime.now(timezone.utc).replace(second=0,microsecond=0)
        cutoff = (now-timedelta(minutes=29)).isoformat()
        counts = {r["minute"]:r["count"] for r in self.rows("SELECT substr(received_at,1,16) minute,COUNT(*) count FROM raw_events WHERE received_at>=? GROUP BY minute",(cutoff,))}
        minute_counts = [{"minute":(now-timedelta(minutes=i)).isoformat()[:16],"count":counts.get((now-timedelta(minutes=i)).isoformat()[:16],0)} for i in reversed(range(30))]
        times = self.rows("SELECT duration_ms FROM events WHERE duration_ms IS NOT NULL ORDER BY duration_ms")
        byte_count = self.one("SELECT COALESCE(SUM(length(raw)),0) n FROM raw_events")["n"]
        formats = self.rows("SELECT format,COUNT(*) count FROM events GROUP BY format ORDER BY count DESC")
        return {"total":total,"normalized":normalized,"coverage":round(100*normalized/total,1) if total else 0,"statuses":statuses,
                "sources":sources,"source_count":len(sources),"formats":formats,"timeline":minute_counts,"raw_bytes":byte_count,
                "sealed":self.one("SELECT COUNT(*) n FROM members")["n"],"pending_review":self.one("SELECT COUNT(*) n FROM candidates WHERE status!='approved'")["n"],
                "alerts":self.one("SELECT COUNT(*) n FROM alerts")["n"],"plugins":self.one("SELECT COUNT(*) n FROM plugins WHERE active=1")["n"],
                "p95_ms":round(times[min(len(times)-1,int(len(times)*.95))]["duration_ms"],2) if times else None,
                "modes":self.rows("SELECT mode,COUNT(*) count FROM raw_events GROUP BY mode"),"uptime_seconds":int(time.time()-self.started),
                "metrics":self.metrics,"outbox":self.rows("SELECT status,COUNT(*) count FROM outbox GROUP BY status")}

    def candidates(self):
        result = []
        for row in self.rows("SELECT c.*,COUNT(e.id) affected FROM candidates c LEFT JOIN events e ON e.fingerprint=c.fingerprint GROUP BY c.id ORDER BY CASE WHEN c.status='approved' THEN 1 ELSE 0 END,affected DESC,c.created_at DESC"):
            row["mapping"] = json.loads(row["mapping"]); row["keys"] = json.loads(row["keys"])
            report = json.loads(row["report"]) if row["report"] else None
            row["report"] = {k:v for k,v in report.items() if k not in ("results","vectors")} if report else None
            result.append(row)
        return result

    def relationships(self, ip="", source="", minutes=0):
        rows = self.events(limit=1000,q=ip,source=source)["items"]
        cutoff = (datetime.now(timezone.utc)-timedelta(minutes=minutes)).isoformat() if minutes else ""
        nodes, edges, timeline = {}, [], []
        peers = {}; actions=Counter(); destinations=set(); seen_sources=set()
        for row in reversed(rows):
            if cutoff and row["received_at"] < cutoff: continue
            n = row["normalized"]
            if not n: continue
            source, dest = n.get("source_ip"),n.get("destination_ip")
            if ip and ip not in (source,dest): continue
            if not source or not dest: continue
            seen_sources.add(row["source"]); actions[n["action"]]+=1; destinations.add(dest)
            for addr in (source,dest):
                nodes.setdefault(addr,{"id":addr,"type":"address","events":0}); nodes[addr]["events"]+=1
            edges.append({"source":source,"target":dest,"action":n["action"],"event_id":row["id"],"device":row["source"]})
            peers.setdefault((source,dest),set()).add(row["source"])
            timeline.append({"id":row["id"],"received_at":row["received_at"],"time":n["time"],"time_basis":n["time_basis"],"source":row["source"],"mode":row["mode"],"source_ip":source,"destination_ip":dest,"port":n.get("destination_port"),"action":n["action"],"message":n["message"],"severity":n["severity"]})
        return {"nodes":list(nodes.values()),"edges":edges,"timeline":sorted(timeline,key=lambda x:x["time"]),
                "corroborated_pairs":[{"source":s,"destination":d,"devices":sorted(v)} for (s,d),v in peers.items() if len(v)>1],
                "behavior":{"actions":dict(actions),"unique_destinations":len(destinations),"observing_sources":len(seen_sources)},
                "scope":"Latest 1,000 matching events, filtered by receipt time; address co-occurrence is not proof of attack or identity."}

    def provenance(self, eid):
        row = self.event(eid)
        revisions = self.rows("SELECT id,version,parser,status,created_at FROM revisions WHERE event_id=? ORDER BY version",(eid,))
        alerts = self.rows("SELECT * FROM alerts WHERE event_id=?",(eid,))
        cases = [c for c in self.rows("SELECT * FROM cases") if eid in json.loads(c["event_ids"])]
        return {"raw":{"id":eid,"hash":row["raw_hash"],"received_at":row["received_at"]},"source":row["source"],"schema_hash":(row["normalized"] or {}).get("schema_hash"),"runtime_schema_hash":SCHEMA_HASH,"revisions":revisions,"alerts":alerts,"cases":cases}

    def recover(self):
        for row in self.rows("SELECT id FROM events WHERE status='queued'"): self.process(row["id"])
    def close(self):
        self.ledger.close(); self.db.close()
