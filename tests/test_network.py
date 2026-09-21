"""End-to-end network tests with real localhost TCP, UDP, TLS and HTTP sockets."""
import asyncio
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import socket
import ssl
import threading
import time
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from ulpf.app import deliver_outbox
from ulpf.receivers import Receivers
from test_pipeline import FORTI


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]


def certificate(tmp_path):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc)-timedelta(minutes=1))
          .not_valid_after(datetime.now(timezone.utc)+timedelta(days=1))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False)
          .sign(key,hashes.SHA256()))
    cp=tmp_path/'server.pem'; kp=tmp_path/'server.key'
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    return str(cp),str(kp)


def test_real_tcp_udp_tls_octet_and_newline_frames(store,tmp_path):
    cert,key=certificate(tmp_path)
    async def exercise():
        receiver=Receivers(store,port=free_port(),tls_port=free_port(),cert=cert,key=key)
        await receiver.start()
        try:
            assert all(v['listening'] for v in receiver.status.values())
            _,writer=await asyncio.open_connection('127.0.0.1',receiver.port)
            frames=[FORTI+b'\r\n',FORTI+b'\n']
            # Both supported TCP framing schemes over a single stream, fragmented writes.
            wire=frames[0]+str(len(frames[1])).encode()+b' '+frames[1]
            for at in range(0,len(wire),17):
                writer.write(wire[at:at+17]);await writer.drain()
            writer.close(); await writer.wait_closed()
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                s.sendto(FORTI,('127.0.0.1',receiver.port))
            context=ssl.create_default_context(cafile=cert)
            _,writer=await asyncio.open_connection('127.0.0.1',receiver.tls_port,ssl=context,server_hostname='localhost')
            writer.write(str(len(FORTI)).encode()+b' '+FORTI);await writer.drain()
            writer.close(); await writer.wait_closed()
            for _ in range(100):
                if store.stats()['total']==4: break
                await asyncio.sleep(.02)
            events=store.events()['items']
            assert len(events)==4
            assert sorted(e['transport'] for e in events)==['tcp','tcp','tls','udp']
            assert all(e['status']=='normalized' for e in events)
            raw=[store.event(e['id'],raw=True)['raw'] for e in events]
            assert sorted(raw)==sorted([*frames,FORTI,FORTI])
            store.seal()
            assert all(store.proof(e['id'])['verified'] for e in events)
            assert store.metrics['receiver_errors']==0
        finally: await receiver.close()
    asyncio.run(exercise())


def test_outbox_retry_preserves_delivery_key(store,source):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.headers['Idempotency-Key'],json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(503 if len(requests)==1 else 204);self.end_headers()
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        store.db.execute("INSERT INTO sinks VALUES('test','Local test',?,1,'now')",(f'http://127.0.0.1:{server.server_port}',));store.db.commit()
        store.ingest(FORTI,source['id'])
        asyncio.run(deliver_outbox(store))
        row=store.one('SELECT * FROM outbox')
        assert row['status']=='pending' and row['attempts']==1
        store.db.execute('UPDATE outbox SET next_attempt=0');store.db.commit()
        asyncio.run(deliver_outbox(store))
        assert store.one('SELECT * FROM outbox')['status']=='delivered'
        assert requests[0]==requests[1]
        asyncio.run(deliver_outbox(store));assert len(requests)==2
    finally: server.shutdown();server.server_close();worker.join()


def test_semantic_assertions_cannot_reference_unrelated_events(store,source):
    store.ingest(b'{"origin":"192.0.2.1","target":"192.0.2.2"}',source['id'])
    c=store.candidates()[0];store.save_mapping(c['id'],{'source_ip':'origin','destination_ip':'target'})
    with pytest.raises(ValueError,match='reference a sample'):
        store.validate_candidate(c['id'],[{'event_id':'not-a-sample','fields':{'source_ip':'192.0.2.1'}}])


def test_parser_revision_keeps_original_approval_and_allows_rollback(store,source):
    eid=store.ingest(b'{"origin":"192.0.2.1","target":"192.0.2.2"}',source['id'])
    c=store.candidates()[0]
    store.save_mapping(c['id'],{'source_ip':'origin','destination_ip':'target'})
    store.validate_candidate(c['id']);p1=store.approve(c['id'],'Automated test',True)['plugin']
    revised=store.revise_candidate(c['id'])
    assert revised['id']!=c['id'] and store.candidate(c['id'])['status']=='approved'
    store.validate_candidate(revised['id']);p2=store.approve(revised['id'],'Automated test',True)['plugin']
    assert p2.endswith('-v2')
    store.activate_plugin(p1);store.replay(c['fingerprint'])
    assert store.event(eid)['parser']==p1+'@1'
    assert store.event(eid,raw=True)['raw']==b'{"origin":"192.0.2.1","target":"192.0.2.2"}'
