#!/usr/bin/env python3
"""Send an existing file over TCP / UDP / verified TLS without modifying bytes."""
import argparse,socket,ssl,time
p=argparse.ArgumentParser();p.add_argument('file');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=5514);p.add_argument('--transport',choices=['tcp','udp','tls'],default='tcp');p.add_argument('--ca');p.add_argument('--single',action='store_true');p.add_argument('--rate',type=float,default=100,help='maximum offered records/second');a=p.parse_args()
if a.rate<=0:p.error('--rate must be positive')
def frames():
    start=time.perf_counter()
    with open(a.file,'rb') as f:
        source=[f.read()] if a.single else f
        for i,raw in enumerate(source):
            delay=start+i/a.rate-time.perf_counter()
            if delay>0:time.sleep(delay)
            yield raw
count=0
if a.transport=='udp':
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        for raw in frames():
            if raw:s.sendto(raw,(a.host,a.port));count+=1
else:
    s=socket.create_connection((a.host,a.port),timeout=10)
    if a.transport=='tls':s=ssl.create_default_context(cafile=a.ca).wrap_socket(s,server_hostname=a.host)
    with s:
        for raw in frames():
            if raw:s.sendall(str(len(raw)).encode()+b' '+raw);count+=1
print(f'Sent {count} frames over {a.transport}. Check the event stream to confirm durable receipt.')
