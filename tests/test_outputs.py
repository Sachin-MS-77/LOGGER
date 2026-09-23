import asyncio
import json
import httpx
import pytest
from ulpf.outputs import send,validate_index
from test_pipeline import FORTI

def test_elastic_bulk_checks_item_errors_and_stable_document_id(store,source):
    eid=store.ingest(FORTI,source['id']);n=store.event(eid)['normalized'];bodies=[]
    row={'id':'delivery','event_id':eid,'revision':1,'kind':'elasticsearch','index_name':'logs-test','url':'http://localhost:9200','payload':json.dumps({'event':n})}
    def response(request):
        bodies.append(request.content)
        assert request.url.path=='/_bulk'
        return httpx.Response(200,json={'errors':len(bodies)==1,'items':[{'index':{'status':429 if len(bodies)==1 else 201,'error':{'type':'rejected'}}}]})
    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as c:
            with pytest.raises(ValueError,match='rejected'):await send(c,row)
            await send(c,row)
    asyncio.run(execute())
    assert bodies[0]==bodies[1] and bodies[0].endswith(b'\n')
    action,document=map(json.loads,bodies[0].splitlines())
    assert action['index']['_id']==eid+':1'
    assert document['source']['ip']=='10.0.0.1'

@pytest.mark.parametrize('name',['Bad Index','../events','_hidden','logs\nfoo',''])
def test_elastic_rejects_invalid_index(name):
    with pytest.raises(ValueError):validate_index(name)
