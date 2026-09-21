import json
import pytest
from fastapi.testclient import TestClient
from ulpf.app import create_app
from ulpf import discovery, schema
from test_pipeline import UNKNOWN, FORTI

def test_legacy_settings_and_new_setting_precedence(tmp_path,monkeypatch):
    monkeypatch.setenv('AEGIS_ADMIN_TOKEN','legacy-test-token-long-enough')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        assert c.get('/api/stats',headers={'Authorization':'Bearer legacy-test-token-long-enough'}).status_code==200
    monkeypatch.setenv('LOGFLUX_ADMIN_TOKEN','new-test-token-long-enough')
    with TestClient(create_app(tmp_path,start_receivers=False)) as c:
        assert c.get('/api/stats',headers={'Authorization':'Bearer legacy-test-token-long-enough'}).status_code==401
        assert c.get('/api/stats',headers={'Authorization':'Bearer new-test-token-long-enough'}).status_code==200
    monkeypatch.setenv('AEGIS_LLM_MODEL','legacy-model')
    assert discovery.settings()[1]=='legacy-model'
    monkeypatch.setenv('LOGFLUX_LLM_MODEL','new-model')
    assert discovery.settings()[1]=='new-model'

def test_signed_legacy_mapping_import_and_unknown_schema_rejection(store,source):
    store.ingest(UNKNOWN,source['id'])
    c=store.candidates()[0]
    store.validate_candidate(c['id'])
    p=store.approve(c['id'],'Migration test',True)
    bundle=json.loads(store.one('SELECT bundle FROM plugins WHERE id=?',(p['plugin'],))['bundle'])
    bundle['payload'].update(id='legacy-migration-test',version=2,schema_hash=schema.LEGACY_SCHEMA_HASH)
    bundle['signature']=store.signer.sign(bundle['payload'])
    store.import_plugin(bundle)
    assert store.one('SELECT active FROM plugins WHERE id=?',('legacy-migration-test',))['active']==0
    bundle['payload'].update(id='unknown-schema-test',schema_hash='f'*64)
    bundle['signature']=store.signer.sign(bundle['payload'])
    with pytest.raises(ValueError,match='schema differs'): store.import_plugin(bundle)

def test_provenance_keeps_historical_schema_hash(store,source,monkeypatch):
    current=schema.SCHEMA_HASH
    monkeypatch.setattr(schema,'SCHEMA_HASH',schema.LEGACY_SCHEMA_HASH)
    eid=store.ingest(FORTI,source['id'])
    store.seal()
    monkeypatch.setattr(schema,'SCHEMA_HASH',current)
    assert store.provenance(eid)['schema_hash']==schema.LEGACY_SCHEMA_HASH
    assert store.provenance(eid)['runtime_schema_hash']==current
    assert store.proof(eid)['verified']
