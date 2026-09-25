#!/usr/bin/env python3
"""Experimental Redpanda -> independent processes -> ClickHouse pipeline.

Static partition ownership, durable local offsets, at-least-once writes and
ReplacingMergeTree logical deduplication. This is not the dashboard's SQLite
store, a replicated cluster, or automatic worker rebalancing.
"""
import argparse
import base64
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import httpx
from ulpf.demo import scenario
from ulpf.parsers import decode,built_in_mapping
from ulpf.schema import normalize,canonical,digest,utcnow
from ulpf.integrity import leaf_hash,merkle,verify_proof

def write_atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    with temp.open('w') as f:
        json.dump(value,f);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def clickhouse(client,sql,body=None):
    r=client.post('http://127.0.0.1:18123/',params={'query':sql},content=body,
                  auth=('logflux',os.environ['LOGFLUX_LAB_PASSWORD']))
    r.raise_for_status();return r

def stream_clickhouse(client,sql):
    credential=base64.b64encode(f"logflux:{os.environ['LOGFLUX_LAB_PASSWORD']}".encode()).decode()
    request=client.build_request('POST','http://127.0.0.1:18123/',params={'query':sql},headers={'Authorization':f'Basic {credential}'})
    response=client.send(request,stream=True)
    try:
        response.raise_for_status()
        for line in response.iter_lines():
            if line: yield json.loads(line)
    finally:
        response.close()

def process_record(record,run_id,worker):
    envelope=record['value'];raw=base64.b64decode(envelope['raw_base64'],validate=True)
    if digest(raw)!=envelope['raw_hash']: raise ValueError('broker envelope raw hash mismatch')
    eid=f"{record['topic']}:{record['partition']}:{record['offset']}"
    n=None;status='unparsed';error=''
    try:
        parsed=decode(raw);mapping=built_in_mapping(parsed)
        if mapping:
            n=normalize(parsed['attributes'],mapping,{'event_id':eid,'raw_hash':digest(raw),
              'source':envelope['source'],'source_id':envelope['source'],'received_at':envelope['received_at'],
              'parser':'builtin:'+str(parsed['vendor']),'revision':1,'mode':'lab'})
            status='partial' if n['quality']['issues'] else 'normalized'
    except Exception as exc: status='failed';error=type(exc).__name__
    norm=json.dumps(n,separators=(',',':'))
    manifest={'id':eid,'run_id':run_id,'source':envelope['source'],'received_at':envelope['received_at'],
              'raw_hash':digest(raw),'normalized_hash':digest(norm.encode())}
    return {'run_id':run_id,'event_id':eid,'worker':worker,'raw_base64':envelope['raw_base64'],
            'raw_hash':digest(raw),'normalized':norm,'status':status,'error':error,'manifest':json.dumps(manifest)}

def worker(config):
    topic,run_id,number,partitions,expected,directory=config
    count=0;started=time.perf_counter()
    with httpx.Client(timeout=30,trust_env=False) as client:
        for partition in partitions:
            checkpoint=Path(directory)/f'{run_id}-p{partition}.json'
            offset=json.loads(checkpoint.read_text())['next_offset'] if checkpoint.exists() else 0
            deadline=time.monotonic()+120
            while offset<expected[partition]:
                if time.monotonic()>deadline: raise TimeoutError('partition did not reach its expected end offset')
                r=client.get(f'http://127.0.0.1:18082/topics/{topic}/partitions/{partition}/records',
                    params={'offset':offset,'timeout':1000,'max_bytes':512000},
                    headers={'Accept':'application/vnd.kafka.json.v2+json'})
                r.raise_for_status();records=r.json()
                if isinstance(records,dict): records=records['records']
                records=[x for x in records if x['offset']<expected[partition]]
                if not records: continue
                rows=[process_record(x,run_id,number) for x in records]
                root,proofs=merkle([leaf_hash(json.loads(x['manifest'])) for x in rows])
                for row,proof in zip(rows,proofs):row.update(batch_root=root,proof=json.dumps(proof))
                body='\n'.join(json.dumps(x) for x in rows)+'\n'
                clickhouse(client,'INSERT INTO logflux_scale FORMAT JSONEachRow',body)
                # Never advance durable offsets until ClickHouse acknowledges the write.
                offset=records[-1]['offset']+1
                write_atomic(checkpoint,{'next_offset':offset,'topic':topic,'partition':partition})
                count+=len(rows)
    return {'worker':number,'partitions':partitions,'processed':count,'seconds':round(time.perf_counter()-started,4)}

def run(count,workers,directory,partitions=4):
    if partitions < 1 or workers < 1 or workers > partitions: raise ValueError('workers must be between 1 and partitions')
    run_id=uuid.uuid4().hex;topic='logflux-'+run_id;directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    compose=['docker','compose','-p','logflux-scale','-f',str(ROOT/'lab/compose.scale.yml')]
    subprocess.run(compose+['exec','-T','redpanda','rpk','topic','create',topic,'--partitions',str(partitions)],check=True,capture_output=True)
    with httpx.Client(timeout=30,trust_env=False) as client:
        clickhouse(client,'''CREATE TABLE IF NOT EXISTS logflux_scale (
          run_id String,event_id String,worker UInt32,raw_base64 String,raw_hash String,
          normalized String,status String,error String,manifest String,batch_root String,proof String)
          ENGINE=ReplacingMergeTree ORDER BY (run_id,event_id)''')
        expected=[0]*partitions;records=[];start=time.perf_counter()
        for i,item in enumerate(scenario(count)):
            p=i%partitions;expected[p]+=1
            records.append({'partition':p,'key':str(i),'value':{'raw_base64':base64.b64encode(item['raw']).decode(),
              'raw_hash':digest(item['raw']),'source':item['source'],'received_at':utcnow()}})
        for i in range(0,len(records),250):
            r=client.post(f'http://127.0.0.1:18082/topics/{topic}',json={'records':records[i:i+250]},
                          headers={'Content-Type':'application/vnd.kafka.json.v2+json'})
            r.raise_for_status()
            if any(x.get('error_code',0) for x in r.json()['offsets']):raise ValueError('broker rejected record')
        producer_seconds=time.perf_counter()-start
        started=time.perf_counter()
        configs=[(topic,run_id,w,list(range(w,partitions,workers)),expected,str(directory)) for w in range(workers)]
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            results=list(pool.map(worker,configs))
        seconds=time.perf_counter()-started
        stored=0; roots=set(); statuses={}
        for row in stream_clickhouse(client,f"SELECT * FROM logflux_scale FINAL WHERE run_id='{run_id}' ORDER BY event_id FORMAT JSONEachRow"):
            stored+=1; statuses[row['status']]=statuses.get(row['status'],0)+1
            if digest(base64.b64decode(row['raw_base64']))!=row['raw_hash']: raise AssertionError('stored bytes changed')
            manifest=json.loads(row['manifest'])
            if digest(row['normalized'].encode())!=manifest['normalized_hash']:raise AssertionError('normalized bytes changed')
            if not verify_proof(leaf_hash(manifest),json.loads(row['proof']),row['batch_root']):raise AssertionError('shard proof failed')
            roots.add(row['batch_root'])
        if stored!=count:raise AssertionError(f'expected {count}, stored {stored}')
        roots=sorted(roots)
        manifests=[{'run_id':run_id,'batch_root':root} for root in roots]
        root,proofs=merkle([leaf_hash(x) for x in manifests])
        # Resume all workers with their committed offsets. No new records are written.
        resumed=[worker(c) for c in configs]
        assert sum(x['processed'] for x in resumed)==0
        result={'run_id':run_id,'events':count,'workers':workers,'partitions':partitions,'seconds':round(seconds,4),
          'events_per_second':round(count/seconds,2),'producer_seconds':round(producer_seconds,4),
          'end_to_end_seconds':round(seconds+producer_seconds,4),'worker_results':results,'all_raw_hashes_verified':True,
          'all_shard_proofs_verified':True,'resume_no_duplicates':True,'aggregate_root':root,
          'batch_count':len(roots),'status_counts':statuses,
          'platform':platform.platform(),'python':platform.python_version(),
          'scope':f'Local {partitions}-partition broker, separate Python workers, one ClickHouse node. Timed worker startup + broker read + normalization + Merkle creation + columnar insertion + durable offset commits. Producer separately timed. Verification and root aggregation excluded. No HA, dynamic rebalancing or dashboard integration.'}
        write_atomic(directory/(run_id+'-aggregate.json'),{'root':root,'manifests':manifests,'proofs':proofs})
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--events',type=int,default=2000);p.add_argument('--workers',type=int,default=4);p.add_argument('--partitions',type=int,default=4)
    p.add_argument('--directory',default='data/scale-lab');p.add_argument('--output',default='docs/scale-benchmark.json');a=p.parse_args()
    if not 4<=a.events<=100000:p.error('events must be between 4 and 100000')
    if a.partitions < 1 or a.workers < 1 or a.workers > a.partitions:p.error('--workers must be between 1 and --partitions')
    result=run(a.events,a.workers,a.directory,a.partitions);write_atomic(a.output,result);print(json.dumps(result,indent=2))
