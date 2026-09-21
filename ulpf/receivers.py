"""TCP, UDP and optional TLS Syslog listeners with bounded message framing."""
import asyncio
import ssl
from .store import MAX_EVENT

class Receivers:
    def __init__(self, store, host="127.0.0.1", port=5514, tls_port=6514, cert=None, key=None, ca=None, mode="live"):
        self.store=store; self.mode=mode; self.host=host; self.port=port; self.tls_port=tls_port
        self.cert=cert; self.key=key; self.ca=ca; self.tcp=None; self.udp=None; self.tls=None
        self.queue=asyncio.Queue(maxsize=4096); self.tasks=[]
        self.status={"tcp":{"listening":False},"udp":{"listening":False},"tls":{"listening":False,"reason":"certificate not configured"}}

    def source_for(self,peer):
        if self.mode == "lab": return self.store.register_source("Socket cyber range · synthetic",peer,"lab","lab")
        return self.store.resolve_peer(peer)

    async def start(self):
        try:
            self.tcp=await asyncio.start_server(self.handle,self.host,self.port,limit=MAX_EVENT+32)
            self.status["tcp"]={"listening":True,"host":self.host,"port":self.port}
        except OSError as exc: self.status["tcp"]={"listening":False,"error":str(exc)}
        outer=self
        class Protocol(asyncio.DatagramProtocol):
            def datagram_received(self,data,addr):
                try: outer.queue.put_nowait((data,addr[0]))
                except asyncio.QueueFull:
                    outer.store.metrics["receiver_errors"]+=1
                    outer.store.metrics["last_receiver_error"]="UDP queue full: datagram dropped before durable acceptance"
            def error_received(self,exc):
                outer.store.metrics["receiver_errors"]+=1; outer.store.metrics["last_receiver_error"]=str(exc)
        try:
            self.udp,_=await asyncio.get_running_loop().create_datagram_endpoint(Protocol,local_addr=(self.host,self.port))
            self.status["udp"]={"listening":True,"host":self.host,"port":self.port,"delivery":"best effort; UDP cannot guarantee source delivery"}
        except OSError as exc: self.status["udp"]={"listening":False,"error":str(exc)}
        if self.cert and self.key:
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.minimum_version=ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(self.cert,self.key)
            if self.ca: context.load_verify_locations(self.ca); context.verify_mode=ssl.CERT_REQUIRED
            try:
                self.tls=await asyncio.start_server(self.handle,self.host,self.tls_port,ssl=context,limit=MAX_EVENT+32)
                self.status["tls"]={"listening":True,"host":self.host,"port":self.tls_port,"mutual_tls":bool(self.ca)}
            except OSError as exc: self.status["tls"]={"listening":False,"error":str(exc)}
        self.tasks=[asyncio.create_task(self.consume())]

    async def consume(self):
        while True:
            raw,peer=await self.queue.get()
            try:
                source=await asyncio.to_thread(self.source_for,peer)
                await asyncio.to_thread(self.store.ingest,raw,source["id"],"udp",peer,"datagram")
            except Exception as exc:
                self.store.metrics["receiver_errors"]+=1; self.store.metrics["last_receiver_error"]=str(exc)
            finally: self.queue.task_done()

    async def handle(self,reader,writer):
        peer=writer.get_extra_info("peername")[0]
        transport="tls" if writer.get_extra_info("ssl_object") else "tcp"
        try:
            source=await asyncio.to_thread(self.source_for,peer)
            while True:
                first=await reader.read(1)
                if not first: break
                if first.isdigit():
                    prefix=first
                    while True:
                        char=await reader.readexactly(1)
                        if char==b" ": break
                        if not char.isdigit() or len(prefix)>=7: raise ValueError("invalid RFC6587 length prefix")
                        prefix+=char
                    size=int(prefix)
                    if not 0<size<=MAX_EVENT: raise ValueError("Syslog frame exceeds configured limit")
                    raw=await reader.readexactly(size); framing=f"octet-counted:{prefix.decode()}"
                else:
                    try: raw=first+await reader.readuntil(b"\n")
                    except asyncio.IncompleteReadError as exc: raw=first+exc.partial
                    if len(raw)>MAX_EVENT: raise ValueError("Syslog frame exceeds configured limit")
                    framing="newline-delimited; terminator preserved when received"
                await asyncio.to_thread(self.store.ingest,raw,source["id"],transport,peer,framing)
        except (Exception,) as exc:
            self.store.metrics["receiver_errors"]+=1; self.store.metrics["last_receiver_error"]=str(exc)
        finally:
            writer.close()
            try: await writer.wait_closed()
            except Exception: pass

    async def close(self):
        for server in (self.tcp,self.tls):
            if server: server.close(); await server.wait_closed()
        if self.udp: self.udp.close()
        await self.queue.join()
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
