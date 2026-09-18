import base64
import json
from fastapi.testclient import TestClient
from ulpf.app import create_app
from test_pipeline import FORTI

def test_api_auth_ingest_evidence_export_and_case(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_ADMIN_TOKEN','test-token-not-for-production')
    with TestClient(create_app(tmp_path,start_receivers=False)) as client:
        assert client.get('/health').status_code==200
        assert client.get('/api/stats').status_code==401
        client.headers['Authorization']='Bearer test-token-not-for-production'
        source=client.post('/api/sources',json={'name':'API test','mode':'replay'}).json()
        response=client.post('/api/ingest',json={'source_id':source['id'],'raw_base64':base64.b64encode(FORTI).decode()})
        assert response.status_code==200
        event=response.json()['event'];eid=event['id']
        assert event['status']=='normalized'
        assert client.get(f'/api/events/{eid}/raw').content==FORTI
        assert client.post('/api/integrity/seal').status_code==200
        assert client.get(f'/api/events/{eid}/proof').json()['verified']
        export=client.get('/api/export?format=ecs')
        assert json.loads(export.text)['source']['ip']=='10.0.0.1'
        case=client.post('/api/cases',json={'title':'Test case','event_ids':[eid],'notes':'verified'})
        assert case.status_code==200
        assert client.get(f'/api/events/{eid}/provenance').json()['cases'][0]['title']=='Test case'
        assert client.get('/api/events?q=%27%20OR%201=1').json()['total']==0
        assert client.get('/api/stats').json()['total']==1

def test_file_upload_keeps_line_terminators(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_ADMIN_TOKEN','test-token-not-for-production')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        c.headers['Authorization']='Bearer test-token-not-for-production'
        source=c.post('/api/sources',json={'name':'file','mode':'replay'}).json()
        content=FORTI+b'\r\n'+FORTI+b'\n'
        result=c.post('/api/upload?source_id='+source['id'],content=content,headers={'Content-Type':'application/octet-stream'}).json()
        assert result['accepted']==2
        assert c.get('/api/events/'+result['event_ids'][0]+'/raw').content==FORTI+b'\r\n'
        assert c.get('/api/events/'+result['event_ids'][1]+'/raw').content==FORTI+b'\n'

def test_static_assets_are_local_and_csp_present(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_ADMIN_TOKEN','test-token-not-for-production')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        response=c.get('/')
        assert response.status_code==200
        assert 'frame-ancestors' in response.headers['content-security-policy']
        assert c.get('/static/app.js').status_code==200
        assert c.get('/static/style.css').status_code==200

def test_source_edit_preserves_original_evidence_metadata(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_ADMIN_TOKEN','test-token-not-for-production')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        c.headers['Authorization']='Bearer test-token-not-for-production'
        source=c.post('/api/sources',json={'name':'Original source','mode':'replay'}).json()
        eid=c.post('/api/ingest',json={'source_id':source['id'],'raw':FORTI.decode()}).json()['event']['id']
        c.post('/api/integrity/seal')
        assert c.patch('/api/sources/'+source['id'],json={'name':'Updated source','peer':'192.0.2.8','mode':'lab','kind':'firewall'}).status_code==200
        original=c.get('/api/events/'+eid).json()
        assert original['source']=='Original source' and original['mode']=='replay'
        assert c.get('/api/events/'+eid+'/proof').json()['verified']
        new=c.post('/api/ingest',json={'source_id':source['id'],'raw':FORTI.decode()}).json()['event']
        assert new['source']=='Updated source' and new['mode']=='lab'
