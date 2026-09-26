#!/usr/bin/env python3
"""60-second broker-gateway acceptance benchmark.

Requires the local scale Redpanda REST endpoint and creates a disposable topic.
It verifies exact raw hashes, seals a Merkle root, and anchors a checkpoint with
the existing local witness ledger. This is a broker/evidence-path benchmark,
not a claim that the SQLite dashboard has become distributed.
"""
import argparse, asyncio, base64, hashlib, json, os, socket, subprocess, tempfile, time, urllib.request, uuid
from pathlib import Path
from ulpf.integrity import WitnessLedger, leaf_hash, merkle
from ulpf.schema import canonical, digest, utcnow

def request(url, method='GET', payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url,data=data,method=method,headers={'Content-Type':'application/vnd.kafka.json.v2+json','Accept':'application/vnd.kafka.json.v2+json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read() or b'{}')

def frame(raw): return str(len(raw)).encode()+b' '+raw

def run(args):
    topic='logflux-e2e-'+uuid.uuid4().hex[:12]; base=args.broker.rstrip('/')
    subprocess.run(['docker','exec',args.redpanda,'rpk','topic','create',topic,'--partitions',str(args.partitions)],check=True,capture_output=True)
    gateway=subprocess.Popen([os.environ.get('PYTHON','python3'),str(Path(__file__).with_name('broker_gateway.py')),'--broker',base,'--topic',topic,'--host',args.host,'--port',str(args.port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(1)
    sent=0; begin=time.monotonic(); deadline=begin+args.seconds
    try:
      with socket.create_connection((args.host,args.port),timeout=10) as sock:
        sock.settimeout(2)
        while time.monotonic()<deadline:
            raw=f'devname="E2E" devid="LAB" srcip=10.0.0.1 dstip=192.0.2.1 action=accept seq={sent}'.encode()
            try: sock.sendall(frame(raw)); sent+=1
            except (TimeoutError,OSError): break
            target=begin+sent/args.rate
            delay=target-time.monotonic()
            if delay>0: time.sleep(min(delay,.01))
      # Read every partition after the gateway has drained its bounded queue.
      records=[]; offsets=[0]*args.partitions; idle=0
      while idle<20:
        before=len(records)
        for partition in range(args.partitions):
            rows=request(f'{base}/topics/{topic}/partitions/{partition}/records?offset={offsets[partition]}&timeout=1000&max_bytes=512000')
            if isinstance(rows,dict): rows=rows.get('records',[])
            if rows:
                records.extend(rows); offsets[partition]=rows[-1]['offset']+1
        if len(records)==before: idle+=1; time.sleep(.5)
        else: idle=0
        if len(records)>=sent: break
    finally:
      gateway.terminate(); gateway.wait(timeout=10)
    manifests=[]; verified=0
    for item in records:
        value=item.get('value',item); raw=base64.b64decode(value['raw_base64'],validate=True)
        if hashlib.sha256(raw).hexdigest()!=value['raw_hash']: raise AssertionError('raw hash mismatch')
        manifest={'id':f'{topic}:{item.get("partition",0)}:{item.get("offset",0)}','raw_hash':value['raw_hash'],'received_ns':value['received_ns']}
        manifests.append(manifest); verified+=1
    root,proofs=merkle([leaf_hash(x) for x in manifests]) if manifests else ('',[])
    with tempfile.TemporaryDirectory(prefix='logflux-e2e-witness-') as directory:
        ledger=WitnessLedger(Path(directory)/'keys'); checkpoint={'sequence':1,'previous':'0'*64,'root':root,'event_count':verified,'created_at':utcnow()}; anchor=ledger.anchor(checkpoint,[]); ledger.close()
    report={'topic':topic,'offered_rate':args.rate,'duration_seconds':args.seconds,'sent_to_gateway':sent,'broker_observed':len(records),'durably_verified':verified,'loss_percent':round(100*max(0,sent-verified)/sent,4) if sent else None,'raw_hashes_verified':verified==len(records),'merkle_root':root,'witness_quorum':anchor.get('anchored',False),'witness_votes':len(anchor.get('votes',[])),'scope':'TCP gateway to Redpanda REST, streamed raw-hash verification, Merkle batch and local three-witness checkpoint. Single broker and same-host witnesses; not the SQLite dashboard or an HA deployment.'}
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2)); return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--broker',default='http://127.0.0.1:18082');p.add_argument('--redpanda',default='logflux-scale-redpanda-1');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=5516);p.add_argument('--rate',type=int,default=15000);p.add_argument('--seconds',type=int,default=60);p.add_argument('--partitions',type=int,default=4);p.add_argument('--output',default='docs/benchmark-15k.json');a=p.parse_args();run(a)
