#!/usr/bin/env python3
"""Real loopback witness processes: signed aggregate, outage, catch-up and conflict."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import httpx
from ulpf.integrity import SigningKey
from ulpf.remote_ledger import anchor
from ulpf.schema import digest,canonical,utcnow
from ulpf.store import Store
from ulpf.demo import scenario

def run(aggregate_root):
    token=secrets.token_urlsafe(32);processes=[];logs=[]
    with tempfile.TemporaryDirectory(prefix='logflux-witness-test-') as tmp:
        directory=Path(tmp);token_file=directory/'token';token_file.write_text(token);token_file.chmod(0o600)
        witnesses=[]
        for i in range(3):
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            name=f'witness-{i+1}';key=SigningKey(directory/name/(name+'.key'))
            witnesses.append({'name':name,'url':f'http://127.0.0.1:{port}','public_key':key.public})
        def start(i):
            w=witnesses[i];log=(directory/(w['name']+'.log')).open('a');logs.append(log)
            p=subprocess.Popen([sys.executable,'-m','ulpf.witness_service','--directory',str(directory/w['name']),
              '--name',w['name'],'--token-file',str(token_file),'--port',w['url'].rsplit(':',1)[1]],cwd=ROOT,stdout=log,stderr=log)
            processes.append(p)
            for _ in range(100):
                try:
                    if httpx.get(w['url']+'/health',timeout=.3,trust_env=False).status_code==200:return p
                except httpx.HTTPError: pass
                if p.poll() is not None:raise RuntimeError('witness failed to start')
                time.sleep(.05)
            raise TimeoutError('witness start timeout')
        try:
            active=[start(i) for i in range(3)]
            config=directory/'witnesses.json';config.write_text(json.dumps({'token_file':str(token_file),'witnesses':witnesses}))
            previous=os.environ.get('LOGFLUX_WITNESS_CONFIG');os.environ['LOGFLUX_WITNESS_CONFIG']=str(config)
            try:
                store=Store(directory/'collector')
                source=store.register_source('Witness test',mode='lab')
                eid=store.ingest(next(scenario(1))['raw'],source['id']);store.seal()
                assert store.proof(eid)['verified']
                cp1=json.loads(store.one('SELECT checkpoint FROM batches')['checkpoint']);store.close()
            finally:
                if previous is None:os.environ.pop('LOGFLUX_WITNESS_CONFIG',None)
                else:os.environ['LOGFLUX_WITNESS_CONFIG']=previous
            cp2={'sequence':2,'previous':digest(canonical(cp1)),'root':aggregate_root,'event_count':0,'created_at':utcnow()}
            active[2].terminate();active[2].wait(timeout=10)
            two=anchor(cp2,witnesses,token,[cp1]);assert two['anchored'] and len(two['votes'])==2
            active[1].terminate();active[1].wait(timeout=10)
            cp3={**cp2,'sequence':3,'previous':digest(canonical(cp2)),'created_at':utcnow()}
            one=anchor(cp3,witnesses,token,[cp1,cp2]);assert not one['anchored']
            start(1);start(2)
            caught=anchor(cp3,witnesses,token,[cp1,cp2]);assert caught['anchored'] and len(caught['votes'])==3
            conflict=anchor({**cp3,'root':'f'*64},witnesses,token,[cp1,cp2]);assert not conflict['anchored']
            return {'main_store_remote_proof_verified':True,'aggregate_root':aggregate_root,'two_of_three_available':two['anchored'],
              'one_of_three_rejected':not one['anchored'],'restart_catchup_votes':len(caught['votes']),
              'conflicting_checkpoint_rejected':not conflict['anchored'],'checkpoint':cp3,'votes':caught['votes'],
              'scope':'Three separate HTTP processes, separate databases/keys, same physical host; independent machine/administrator custody NOT verified.'}
        finally:
            for p in processes:
                if p.poll() is None:p.terminate();p.wait(timeout=10)
            for log in logs:log.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--aggregate-root',default=digest(b'network-witness-test'));p.add_argument('--output',default='docs/witness-verification.json');a=p.parse_args()
    result=run(a.aggregate_root);Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
