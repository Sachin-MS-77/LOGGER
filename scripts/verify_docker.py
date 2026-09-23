#!/usr/bin/env python3
"""Acceptance check for an already running LOGFLUX container; token never printed."""
import argparse,base64,json,socket,subprocess,time,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--container',default='logflux-review');p.add_argument('--api',default='http://127.0.0.1:18765');p.add_argument('--port',type=int,default=15514);p.add_argument('--output',default='docs/docker-verification.json');a=p.parse_args()
token=subprocess.check_output(['docker','exec',a.container,'cat','/var/lib/logflux/admin-token']).decode().strip()
def call(path,data=None):
    req=urllib.request.Request(a.api+path,json.dumps(data).encode() if data is not None else None,{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
assert call('/health')['status']=='ok'
source=call('/api/sources',{'name':'Container acceptance','mode':'replay'})
raw=b'devname="Docker" devid="TEST" logid="1" srcip=10.0.0.1 dstip=192.0.2.1 srcport=5000 dstport=443 action=accept proto=6 level=information'
e=call('/api/ingest',{'source_id':source['id'],'raw_base64':base64.b64encode(raw).decode()})['event'];eid=e['id']
assert e['status']=='normalized'
req=urllib.request.Request(a.api+'/api/events/'+eid+'/raw',headers={'Authorization':'Bearer '+token})
with urllib.request.urlopen(req) as r:assert r.read()==raw
before=call('/api/stats')['total']
with socket.create_connection(('127.0.0.1',a.port),timeout=10) as s:s.sendall(str(len(raw)).encode()+b' '+raw)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.sendto(raw,('127.0.0.1',a.port))
for _ in range(100):
    if call('/api/stats')['total']>=before+2:break
    time.sleep(.1)
assert call('/api/stats')['total']>=before+2
call('/api/integrity/seal',{});assert call('/api/events/'+eid+'/proof')['verified']
subprocess.run(['docker','restart',a.container],check=True,capture_output=True)
for _ in range(100):
    try:
        if call('/health')['status']=='ok':break
    except Exception:pass
    time.sleep(.2)
assert call('/api/events/'+eid+'/proof')['verified']
inspection=json.loads(subprocess.check_output(['docker','inspect',a.container]))[0]
report={'health':True,'authenticated_ingestion':True,'exact_raw_bytes':True,'tcp_udp_received':True,'proof_verified_after_restart':True,'user':inspection['Config']['User'],'read_only_root':inspection['HostConfig']['ReadonlyRootfs'],'scope':'Local Docker engine; fresh synthetic test data. Not a physical firewall test, Linux host test or CI result.'}
Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
