#!/usr/bin/env python3
"""TCP Syslog -> Redpanda REST gateway.

The gateway is an opt-in ingestion boundary for the scalable deployment. It
hashes the exact received bytes before publishing an envelope and does not
ack/clear its bounded queue until Redpanda accepts the batch. Downstream
workers can then normalize and seal those envelopes without SQLite write
contention in the socket process.
"""
import argparse, asyncio, base64, hashlib, json, os, time
from urllib.parse import quote
import urllib.request

MAX_EVENT = 64 * 1024

class Gateway:
    def __init__(self, broker, topic, host, port, batch_size=500, queue_size=20000):
        self.broker=broker.rstrip('/'); self.topic=topic; self.host=host; self.port=port
        self.batch_size=batch_size; self.queue=asyncio.Queue(maxsize=queue_size)
        self.accepted=0; self.published=0; self.rejected=0

    def envelope(self, raw, peer, sequence):
        return {'key':str(sequence),'value':{'raw_base64':base64.b64encode(raw).decode(),
          'raw_hash':hashlib.sha256(raw).hexdigest(),'source_peer':peer,
          'received_ns':time.time_ns(),'transport':'tcp','framing':'rfc6587-octet-counted'}}

    async def publish(self, rows):
        body=json.dumps({'records':rows}).encode()
        url=f'{self.broker}/topics/{quote(self.topic,safe="")}'; req=urllib.request.Request(url,body,{'Content-Type':'application/vnd.kafka.json.v2+json'})
        def send():
            with urllib.request.urlopen(req,timeout=30) as response:return json.loads(response.read())
        result=await asyncio.to_thread(send)
        if any(x.get('error_code',0) for x in result.get('offsets',[])): raise RuntimeError('Redpanda rejected a record')
        self.published+=len(rows)

    async def publisher(self):
        batch=[]
        while True:
            item=await self.queue.get()
            if item is None:
                if batch: await self.publish(batch)
                self.queue.task_done(); return
            batch.append(item); self.queue.task_done()
            if len(batch)>=self.batch_size:
                await self.publish(batch); batch=[]

    async def handle(self, reader, writer):
        peer=writer.get_extra_info('peername')[0]; sequence=0
        try:
            while True:
                first=await reader.read(1)
                if not first: break
                if not first.isdigit(): raise ValueError('gateway requires RFC6587 octet-counted framing')
                prefix=first
                while True:
                    char=await reader.readexactly(1)
                    if char==b' ': break
                    if not char.isdigit() or len(prefix)>=7: raise ValueError('invalid frame length')
                    prefix+=char
                size=int(prefix)
                if not 0<size<=MAX_EVENT: raise ValueError('event exceeds 64 KiB')
                raw=await reader.readexactly(size); sequence+=1
                await self.queue.put(self.envelope(raw,peer,sequence)); self.accepted+=1
        except (asyncio.IncompleteReadError, ValueError): self.rejected+=1
        finally:
            writer.close(); await writer.wait_closed()

    async def run(self):
        worker=asyncio.create_task(self.publisher())
        server=await asyncio.start_server(self.handle,self.host,self.port,limit=MAX_EVENT+32)
        async with server:
            try: await server.serve_forever()
            finally:
                await self.queue.put(None); await self.queue.join(); await worker

def main():
    p=argparse.ArgumentParser(); p.add_argument('--broker',default='http://127.0.0.1:18082'); p.add_argument('--topic',default='logflux-live'); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=5516); p.add_argument('--batch-size',type=int,default=500); p.add_argument('--queue-size',type=int,default=20000); a=p.parse_args()
    if not 1<=a.batch_size<=5000 or not 100<=a.queue_size<=1000000:p.error('invalid batch or queue size')
    try: asyncio.run(Gateway(a.broker,a.topic,a.host,a.port,a.batch_size,a.queue_size).run())
    except KeyboardInterrupt: pass
if __name__=='__main__': main()
