#!/usr/bin/env python3
"""Reproducible single-node durable-ingestion benchmark, never a scale claim."""
import argparse,json,platform,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ulpf.store import Store
from ulpf.demo import scenario
p=argparse.ArgumentParser();p.add_argument('--events',type=int,default=2000);p.add_argument('--output');args=p.parse_args()
if not 100<=args.events<=100000: p.error('--events must be 100..100000')
with tempfile.TemporaryDirectory(prefix='aegis-benchmark-') as d:
    store=Store(d);sources={};start=time.perf_counter()
    for item in scenario(args.events):
        if item['source'] not in sources:sources[item['source']]=store.register_source(item['source'],mode='replay')
        store.ingest(item['raw'],sources[item['source']]['id'],'benchmark')
    elapsed=time.perf_counter()-start;seal_start=time.perf_counter()
    while store.stats()['sealed']<args.events:store.seal()
    seal_seconds=time.perf_counter()-seal_start
    proof=store.proof(store.events(limit=1)['items'][0]['id'])
    stats=store.stats()
    report={'system':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'events':stats['total'],'seconds':round(elapsed,3),'events_per_second':round(args.events/elapsed,1),'p95_processing_ms':stats['p95_ms'],'normalized':stats['normalized'],'unparsed':stats['statuses'].get('unparsed',0),'seal_seconds':round(seal_seconds,3),'proof_verified':proof['verified'],'scope':'Sequential local Store.ingest; SQLite WAL/FULL; 5 synthetic formats; includes raw+revision writes; excludes network, LLM and concurrent dashboard. Not a production load or billion/day test.'}
    store.close()
text=json.dumps(report,indent=2);print(text)
if args.output:Path(args.output).write_text(text+'\n')
