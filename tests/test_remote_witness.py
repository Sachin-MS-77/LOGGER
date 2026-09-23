from fastapi.testclient import TestClient
from ulpf.witness_service import create_witness_app
from ulpf.integrity import verify_signature
from ulpf.schema import digest,canonical
from ulpf.remote_ledger import anchor
import pytest

def test_network_witness_auth_idempotency_conflicts_and_gap(tmp_path):
    token='test-witness-token-at-least-24-characters'
    with TestClient(create_witness_app(tmp_path,'test',token)) as c:
        assert c.get('/state').status_code==401
        c.headers['Authorization']='Bearer '+token
        key=c.get('/state').json()['public_key']
        cp={'sequence':1,'previous':'0'*64,'root':'a'*64,'event_count':100,'created_at':'2026-09-23T00:00:00Z'}
        signature=c.post('/vote',json=cp).json()
        assert verify_signature(cp,signature,[key])
        assert c.post('/vote',json=cp).json()==signature
        assert c.post('/vote',json={**cp,'root':'b'*64}).status_code==409
        assert c.post('/vote',json={**cp,'sequence':3}).status_code==409
        assert c.get('/state').json()['hash']==digest(canonical(cp))

def test_remote_quorum_rejects_duplicate_pins():
    with pytest.raises(ValueError,match='distinct'):
        anchor({},[{'public_key':'same'}]*3,'token')

def test_remote_witness_requires_tls():
    with pytest.raises(ValueError,match='HTTPS'):
        anchor({},[{'public_key':str(i),'url':'http://192.0.2.1','name':str(i)} for i in range(3)],'token')

def test_any_single_witness_verifies_inclusion_and_rejects_tampering(tmp_path):
    from scripts.verify_witness_proof import verify
    from ulpf.integrity import SigningKey,merkle,leaf_hash
    manifest={'raw_hash':'a'*64};root,paths=merkle([leaf_hash(manifest)])
    key=SigningKey(tmp_path/'one.key');cp={'root':root,'sequence':1}
    doc={'manifest':manifest,'proof':paths[0],'checkpoint':cp,'votes':[key.sign(cp)]}
    assert verify(doc,key.public)['verified']
    assert not verify(doc,key.public)['quorum_verified']
    with pytest.raises(ValueError,match='inclusion'):verify({**doc,'manifest':{'raw_hash':'b'*64}},key.public)
