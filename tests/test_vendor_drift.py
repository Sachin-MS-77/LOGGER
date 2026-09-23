from pathlib import Path
from ulpf.parsers import decode

def test_documented_epoch_unit_drift_needs_approval_and_preserves_bytes(store,source):
    samples=Path(__file__).resolve().parents[1]/'samples'
    old=(samples/'fortigate-epoch-seconds.log').read_bytes();new=(samples/'fortigate-epoch-nanoseconds.log').read_bytes()
    first=store.ingest(old,source['id']);a=store.event(first)
    assert a['status']=='normalized' and a['normalized']['time']=='2019-05-07T01:10:42+00:00'
    eid=store.ingest(new,source['id']);before=store.event(eid)
    assert before['status']=='drifted' and before['normalized'] is None
    candidate=next(x for x in store.candidates() if x['fingerprint']==decode(new)['fingerprint'])
    check=store.validate_candidate(candidate['id'],[{'event_id':eid,'fields':{'source_ip':'192.0.2.10','time':'2019-05-07T01:10:42.762142+00:00'}}])
    assert check['passed'];store.approve(candidate['id'],'Automated test reviewer',True);store.replay(candidate['fingerprint'])
    after=store.event(eid,raw=True)
    assert after['status']=='normalized' and after['revision']==2
    assert after['raw']==new and after['raw_hash']==before['raw_hash']
    assert len(store.provenance(eid)['revisions'])==2
    store.seal();assert store.proof(eid)['verified']
