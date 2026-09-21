import json
import pytest
import wasmtime
from ulpf.integrity import merkle, leaf_hash, verify_proof, SigningKey, Witness, verify_signature, unb64
from ulpf.sandbox import Sandbox
from test_pipeline import FORTI, UNKNOWN

@pytest.mark.parametrize('count',[1,2,3,7,16,35])
def test_merkle_all_leaves_and_tamper(count):
    leaves=[leaf_hash({'id':i}) for i in range(count)]
    root,proofs=merkle(leaves)
    assert all(verify_proof(l,p,root) for l,p in zip(leaves,proofs))
    assert not verify_proof(leaf_hash({'id':'changed'}),proofs[0],root)

def test_quorum_outage_and_catch_up(store,source):
    store.ledger.witnesses[0].enabled=False
    first=store.ingest(FORTI,source['id']); store.seal()
    assert store.proof(first)['verified']
    store.ledger.witnesses[1].enabled=False
    second=store.ingest(FORTI,source['id']); store.seal()
    assert not store.proof(second)['ledger_valid']
    store.ledger.witnesses[0].enabled=True; store.ledger.witnesses[1].enabled=True
    store.seal()
    assert store.proof(second)['verified']
    assert len(store.proof(second)['anchor']['votes'])==3

def test_witness_refuses_conflict(tmp_path):
    w=Witness(tmp_path,'test'); checkpoint={'sequence':1,'previous':'0'*64,'root':'a'*64}
    assert w.vote(checkpoint)==w.vote(checkpoint)
    with pytest.raises(ValueError): w.vote({**checkpoint,'root':'b'*64})
    w.close()

def test_manifest_tampering_detected(store,source):
    eid=store.ingest(FORTI,source['id']); store.seal()
    row=store.one('SELECT manifest FROM members WHERE event_id=?',(eid,))
    manifest=json.loads(row['manifest']); manifest['source']='forged'
    store.db.execute('UPDATE members SET manifest=? WHERE event_id=?',(json.dumps(manifest),eid));store.db.commit()
    assert not store.proof(eid)['verified']

def test_plugin_tamper_signature_and_trust(store,source,tmp_path):
    store.ingest(UNKNOWN,source['id']);c=store.candidates()[0]
    store.validate_candidate(c['id']);p=store.approve(c['id'],'Reviewer',True)
    bundle=json.loads(store.one('SELECT bundle FROM plugins WHERE id=?',(p['plugin'],))['bundle'])
    assert verify_signature(bundle['payload'],bundle['signature'],[store.signer.public])
    bundle['payload']['reviewer']='attacker'
    with pytest.raises(Exception): verify_signature(bundle['payload'],bundle['signature'],[store.signer.public])
    with pytest.raises(ValueError): verify_signature({},SigningKey(tmp_path/'other.key').sign({}),[store.signer.public])

def test_wasm_fuel_stops_infinite_loop():
    sandbox=Sandbox()
    binary=wasmtime.wat2wasm('(module (func (export "select") (param i32) (result i32) (loop $forever (br $forever)) (i32.const -1)))')
    with pytest.raises(wasmtime.Trap): sandbox.project(binary,[],{})

def test_wasm_host_access_forbidden():
    sandbox=Sandbox()
    binary=wasmtime.wat2wasm('(module (import "env" "write" (func)) (func (export "select") (param i32) (result i32) (i32.const -1)))')
    with pytest.raises(ValueError,match='imports'): sandbox.project(binary,[],{})

def test_wasm_memory_limit():
    sandbox=Sandbox()
    binary=wasmtime.wat2wasm('(module (memory 2) (func (export "select") (param i32) (result i32) (i32.const -1)))')
    with pytest.raises(Exception): sandbox.project(binary,[],{})

def test_projection_consistency():
    sandbox=Sandbox();keys=['src','dst'];mapping={'source_ip':'src','destination_ip':'dst'}
    wasm=sandbox.compile(mapping,keys)
    assert sandbox.project(wasm,keys,{'src':'10.0.0.1','dst':'192.0.2.1'})==mapping
