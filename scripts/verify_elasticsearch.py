#!/usr/bin/env python3
"""Live native Bulk acceptance against a disposable loopback Elasticsearch node."""
import argparse,asyncio,json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from ulpf.store import Store
from ulpf.demo import scenario
from ulpf.outputs import send
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:19200');p.add_argument('--output',default='docs/elasticsearch-verification.json');a=p.parse_args()
if not a.url.startswith(('http://127.0.0.1:','http://localhost:')):p.error('acceptance script is for a disposable loopback node')
async def main():
    with tempfile.TemporaryDirectory() as directory:
        store=Store(directory);source=store.register_source('Elastic acceptance',mode='replay');eid=store.ingest(next(scenario(5))['raw'],source['id']);event=store.event(eid)['normalized']
        index='logflux-acceptance-'+str(int(time.time()))
        row={'id':'test-delivery','event_id':eid,'revision':1,'kind':'elasticsearch','index_name':index,'url':a.url,'payload':json.dumps({'event':event})}
        async with httpx.AsyncClient(timeout=30,trust_env=False) as client:
            for _ in range(90):
                try:
                    r=await client.get(a.url);r.raise_for_status();version=r.json()['version']['number'];break
                except Exception:await asyncio.sleep(1)
            else:raise RuntimeError('Elasticsearch did not become ready')
            await send(client,row);await send(client,row)
            r=await client.post(a.url+'/'+index+'/_refresh');r.raise_for_status()
            count=(await client.get(a.url+'/'+index+'/_count')).json()['count'];assert count==1
            doc=(await client.get(a.url+'/'+index+'/_doc/'+eid+':1')).json()['_source']
            assert doc['event']['hash']==event['provenance']['raw_hash'] and doc['source']['ip']==event['source_ip']
            report={'elasticsearch_version':version,'native_bulk_accepted':True,'retry_document_count':count,'raw_hash_reference_preserved':True,'ecs_source_ip_verified':True,'scope':'Disposable loopback Elasticsearch node; live native connector and stable-ID retry. Item failure handling separately unit-tested. No authenticated remote-cluster acceptance claim.'}
            r=await client.delete(a.url+'/'+index);r.raise_for_status()
        store.close();Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
asyncio.run(main())
