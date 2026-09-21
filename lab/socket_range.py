#!/usr/bin/env python3
"""Controlled traffic generator: synthetic firewall/router/IDS records over real sockets.
No scans, exploitation, or external targets. Run on the collector host.
"""
import argparse,json,socket,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ulpf.demo import scenario
p=argparse.ArgumentParser();p.add_argument('--token-file',required=True);p.add_argument('--api',default='http://127.0.0.1:8765');p.add_argument('--port',type=int,default=5515);p.add_argument('--count',type=int,default=100);a=p.parse_args()
from urllib.parse import urlparse
if urlparse(a.api).hostname not in ('localhost','127.0.0.1'):p.error('This controlled lab runs only against localhost')
token=Path(a.token_file).read_text().strip()
source={'name':'Socket cyber range · synthetic','peer':'127.0.0.1','kind':'lab','mode':'lab'}
req=urllib.request.Request(a.api+'/api/sources',json.dumps(source).encode(),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
with urllib.request.urlopen(req) as r:r.read()
with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
    s.connect(('127.0.0.1',a.port))
    for event in scenario(a.count):
        raw=event['raw'];s.sendall(str(len(raw)).encode()+b' '+raw);time.sleep(.05)
print('Sent',a.count,'synthetic records over real TCP; inspect traffic mode “lab”.')
