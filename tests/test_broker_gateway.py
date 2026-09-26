import base64, hashlib
from scripts.broker_gateway import Gateway

def test_gateway_envelope_preserves_exact_bytes_and_hash():
    raw=b'\xffdevice=fw action=deny\r\n'
    item=Gateway('http://127.0.0.1:18082','test','127.0.0.1',5516).envelope(raw,'192.0.2.5',7)
    value=item['value']
    assert base64.b64decode(value['raw_base64'])==raw
    assert value['raw_hash']==hashlib.sha256(raw).hexdigest()
    assert value['source_peer']=='192.0.2.5'
    assert item['key']=='7'
