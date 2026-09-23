import base64,json
from lab.scale_pipeline import process_record,worker
from ulpf.schema import digest
import pytest

def record():
    raw=b'unknown raw message'
    return {'topic':'test','partition':0,'offset':0,'value':{'raw_base64':base64.b64encode(raw).decode(),'raw_hash':digest(raw),'source':'lab','received_at':'2026-01-01T00:00:00Z'}}
def test_scale_preserves_unknown_and_rejects_corrupt_envelope():
    rec=record();row=process_record(rec,'run',0)
    assert row['status']=='unparsed' and row['normalized']=='null'
    assert base64.b64decode(row['raw_base64'])==b'unknown raw message'
    rec['value']['raw_hash']='0'*64
    with pytest.raises(ValueError,match='hash mismatch'):process_record(rec,'run',0)

def test_scale_sink_failure_never_advances_checkpoint(tmp_path,monkeypatch):
    class Response:
        def raise_for_status(self):pass
        def json(self):return [record()]
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,*a,**kw):return Response()
    monkeypatch.setattr('lab.scale_pipeline.httpx.Client',Client)
    def fail(*a):raise RuntimeError('sink unavailable')
    monkeypatch.setattr('lab.scale_pipeline.clickhouse',fail)
    with pytest.raises(RuntimeError,match='sink unavailable'):worker(('test','run',0,[0],[1],str(tmp_path)))
    assert list(tmp_path.iterdir())==[]
