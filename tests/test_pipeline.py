import base64
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from ulpf.parsers import decode, built_in_mapping
from ulpf.schema import normalize
from ulpf.store import Store, MAX_EVENT
from ulpf.demo import scenario, drift_sample

FORTI=b'devname="FGT" devid="FG1" logid="1" timestamp="2026-09-17T10:00:00+05:30" srcip=10.0.0.1 dstip=192.0.2.1 srcport=5000 dstport=443 action=accept proto=6 level=information'
UNKNOWN=b'{"source_ip":"10.0.0.1","destination_ip":"192.0.2.1","action":"deny","protocol":"tcp"}'

def test_raw_exact_bytes_unique_event_identity(store,source):
    raw=FORTI+b'\r\n'
    a=store.ingest(raw,source['id']); b=store.ingest(raw,source['id'])
    assert a!=b
    assert store.event(a,raw=True)['raw']==raw
    assert store.event(a)['raw_hash']==store.event(b)['raw_hash']
    assert store.event(a)['normalized']['action']=='allow'
    assert store.event(a)['normalized']['time']=='2026-09-17T04:30:00+00:00'

def test_raw_sql_immutable(store,source):
    eid=store.ingest(FORTI,source['id'])
    with pytest.raises(sqlite3.IntegrityError): store.db.execute('UPDATE raw_events SET raw=? WHERE id=?',(b'changed',eid))
    store.db.rollback()
    with pytest.raises(sqlite3.IntegrityError): store.db.execute('DELETE FROM raw_events WHERE id=?',(eid,))
    store.db.rollback()

@pytest.mark.parametrize('raw',[b'\xff\xfe\x00',b'{"src":',b'{"x":1,"x":2}',b'<log><!ENTITY a "x"></log>',b'{"x":NaN}'])
def test_malformed_is_preserved_with_explicit_failure(store,source,raw):
    eid=store.ingest(raw,source['id'])
    assert store.event(eid)['status']=='failed'
    assert store.event(eid,raw=True)['raw']==raw
    assert store.event(eid)['error']

@given(st.binary(min_size=1,max_size=2048))
@settings(max_examples=100,deadline=None,suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_arbitrary_received_bytes_are_never_lost(store,source,raw):
    eid=store.ingest(raw,source['id'])
    event=store.event(eid,raw=True)
    assert event['raw']==raw
    assert event['status'] in ('normalized','partial','unparsed','drifted','failed')
    assert event['revision']==1

def test_oversize_rejected_before_acceptance(store,source):
    with pytest.raises(ValueError): store.ingest(b'x'*(MAX_EVENT+1),source['id'])
    assert store.stats()['total']==0
    assert store.metrics['rejected']==1

def test_unknown_approval_replay_and_provenance(store,source):
    eid=store.ingest(UNKNOWN,source['id'])
    assert store.event(eid)['status']=='unparsed'
    candidate=store.candidates()[0]
    with pytest.raises(ValueError): store.approve(candidate['id'],'Reviewer',True)
    report=store.validate_candidate(candidate['id'],[{'event_id':eid,'fields':{'source_ip':'10.0.0.1','destination_ip':'192.0.2.1','action':'deny'}}])
    assert report['passed'] and report['semantic_assertions']==3
    with pytest.raises(ValueError): store.approve(candidate['id'],'Reviewer',False)
    result=store.approve(candidate['id'],'Reviewer',True)
    assert result['version']==1
    assert store.replay(candidate['fingerprint'])['statuses']=={'normalized':1}
    assert store.event(eid,raw=True)['raw']==UNKNOWN
    provenance=store.provenance(eid)
    assert len(provenance['revisions'])==2
    assert provenance['revisions'][0]['status']=='unparsed'
    assert provenance['revisions'][1]['status']=='normalized'

def test_semantics_catch_swapped_ips(store,source):
    eid=store.ingest(UNKNOWN,source['id']); c=store.candidates()[0]
    store.save_mapping(c['id'],{'source_ip':'destination_ip','destination_ip':'source_ip'})
    report=store.validate_candidate(c['id'],[{'event_id':eid,'fields':{'source_ip':'10.0.0.1','destination_ip':'192.0.2.1'}}])
    assert not report['passed']
    with pytest.raises(ValueError): store.approve(c['id'],'Reviewer',True)

def test_edit_invalidates_validation(store,source):
    store.ingest(UNKNOWN,source['id']); c=store.candidates()[0]
    store.validate_candidate(c['id'])
    store.save_mapping(c['id'],{'source_ip':'source_ip','action':'action'})
    assert store.candidate(c['id'])['report'] is None
    with pytest.raises(ValueError): store.approve(c['id'],'Reviewer',True)

def test_drift_is_quarantined_not_silently_mapped(store,source):
    store.ingest(FORTI,source['id'])
    eid=store.ingest(drift_sample(),source['id'])
    assert store.event(eid)['status']=='drifted'
    assert store.event(eid)['normalized'] is None
    assert store.candidates()

def test_recovery_after_crash_between_commit_and_parse(tmp_path):
    s=Store(tmp_path); src=s.register_source('crash-test',mode='replay')
    def crash(eid): raise RuntimeError('simulated process exit')
    s.process=crash
    with pytest.raises(RuntimeError): s.ingest(FORTI,src['id'])
    eid=s.events()['items'][0]['id']; assert s.event(eid)['status']=='queued'; s.close()
    recovered=Store(tmp_path); recovered.recover()
    assert recovered.event(eid)['status']=='normalized'
    assert recovered.event(eid,raw=True)['raw']==FORTI
    recovered.close()

def test_concurrent_ingestion_accounted(store,source):
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids=list(pool.map(lambda _:store.ingest(FORTI,source['id']),range(80)))
    assert len(set(ids))==80 and store.stats()['total']==80
    assert store.stats()['normalized']==80

@pytest.mark.parametrize('raw,fmt',[
    (b'CEF:0|Vendor|Device|1|10|Connection blocked|8|src=10.0.0.1 dst=192.0.2.1 spt=42 dpt=443 proto=TCP act=deny msg=two words here','cef'),
    (b'LEEF:1.0|Vendor|Device|1|10|src=10.0.0.1\tdst=192.0.2.1\taction=deny','leef'),
    (b'LEEF:2.0|Vendor|Device|1|10|0x09|src=10.0.0.1\tdst=192.0.2.1\taction=deny','leef'),
    (b'<event><srcip>10.0.0.1</srcip><dstip>192.0.2.1</dstip><action>deny</action></event>','xml'),
    (b'srcip,dstip,action\n10.0.0.1,192.0.2.1,deny\n','csv'),
    (b'<134>Sep 17 10:00:00 pfSense filterlog: 5,,,1000000103,em0,match,block,in,4,0x0,,64,1,0,none,6,tcp,60,10.0.0.1,192.0.2.1,5000,443,0,S,1,,65535,,mss','pfsense'),
    (b'<134>1 2026-09-17T10:00:00Z host app - ID1 [example@123 k="v"] {"src_ip":"10.0.0.1"}','json'),
])
def test_format_adapters(raw,fmt): assert decode(raw)['format']==fmt

def test_cef_unquoted_spaces_and_escaped_header():
    p=decode(b'CEF:0|Vendor|Device|1|10|Connection \\| blocked|8|src=10.0.0.1 dst=192.0.2.1 msg=two words here act=deny')
    assert p['attributes']['cef.name']=='Connection | blocked'
    assert p['attributes']['msg']=='two words here'

def test_invalid_ip_and_port_are_reported_not_coerced():
    n=normalize({'src':'999.1.1.1','dpt':'99999'},{'source_ip':'src','destination_port':'dpt'},{'source':'x','received_at':'2026-01-01T00:00:00Z'})
    assert n['source_ip'] is None and n['destination_port'] is None
    assert len(n['quality']['issues'])==2

def test_unknown_vendor_fields_survive(store,source):
    eid=store.ingest(FORTI+b' proprietary_sensor=abc',source['id'])
    assert store.event(eid)['normalized']['unmapped']['proprietary_sensor']=='abc'

def test_fixture_scenario_routes_all_events(store):
    for entry in scenario(50):
        src=store.register_source(entry['source'],kind=entry['kind'],mode='replay')
        store.ingest(entry['raw'],src['id'])
    assert store.stats()['total']==50
    assert store.stats()['normalized']==40
    assert store.stats()['statuses']['unparsed']==10
    assert all(e['mode']=='replay' for e in store.events(limit=100)['items'])

def test_iptables_repeated_inner_packet_preserved_without_overwriting_outer(store,source):
    raw=b'Feb  1 00:00:02 bridge kernel: INBOUND ICMP: IN=br0 OUT=br0 SRC=192.0.2.1 DST=198.51.100.2 LEN=96 PROTO=ICMP TYPE=3 CODE=3 SRC=198.51.100.2 DST=192.0.2.1 LEN=60 PROTO=TCP SPT=5000 DPT=80'
    eid=store.ingest(raw,source['id']);e=store.event(eid)
    assert e['normalized']['source_ip']=='192.0.2.1'
    assert e['normalized']['protocol']=='icmp'
    assert e['normalized']['source_port'] is None and e['normalized']['destination_port'] is None
    assert e['normalized']['action']=='unknown'
    assert e['normalized']['unmapped']['repeated.SRC.2']=='198.51.100.2'
    assert store.event(eid,raw=True)['raw']==raw
