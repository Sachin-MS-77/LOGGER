from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from ulpf.app import create_app
from test_pipeline import FORTI

def test_graph_filters_keep_receipt_time_separate_from_source_time(store, source):
    other=store.register_source('Second source',mode='lab')
    first=store.ingest(FORTI,source['id'])
    store.ingest(FORTI,other['id'])
    result=store.relationships(source=source['id'],minutes=30)
    assert [t['id'] for t in result['timeline']]==[first]
    assert result['timeline'][0]['received_at']!=result['timeline'][0]['time']
    assert result['behavior']['observing_sources']==1
    assert store.relationships(ip='203.0.113.200')['timeline']==[]
    assert len(store.relationships()['timeline'])==2

def test_graph_excludes_old_receipts_and_validates_range(tmp_path,monkeypatch):
    monkeypatch.setenv('LOGFLUX_ADMIN_TOKEN','logflux-test-token-not-for-production')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        c.headers['Authorization']='Bearer logflux-test-token-not-for-production'
        assert c.get('/api/graph?minutes=-1').status_code==422
        assert c.get('/api/graph?minutes=43201').status_code==422
        assert c.get('/api/graph?minutes=30').json()['timeline']==[]
        assert c.get('/health').json()['service']=='logflux'

def test_graph_time_filter_rejects_old_receipt(store,source,monkeypatch):
    old=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    monkeypatch.setattr('ulpf.store.utcnow',lambda:old)
    store.ingest(FORTI,source['id'])
    assert len(store.relationships()['timeline'])==1
    assert store.relationships(minutes=30)['timeline']==[]
