#!/usr/bin/env python3
"""Isolated real-listener benchmark; offers load for a fixed wall-clock duration.
A requested rate is not achieved throughput. Records received after the offered
window are drain receipts and are reported separately. No 24-hour run is implied.
"""
import argparse,concurrent.futures,json,os,platform,secrets,socket,sqlite3,ssl,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def run(rate,seconds,connections,transport,cert=None,key=None,ca=None,drain=15):
    with tempfile.TemporaryDirectory(prefix='logflux-load-') as directory:
        api,tcp,tls,lab=port(),port(),port(),port();token=secrets.token_urlsafe(32)
        env={**os.environ,'LOGFLUX_DATA_DIR':directory,'LOGFLUX_ADMIN_TOKEN':token,'LOGFLUX_PORT':str(api),'LOGFLUX_SYSLOG_PORT':str(tcp),'LOGFLUX_TLS_PORT':str(tls),'LOGFLUX_LAB_PORT':str(lab),'LOGFLUX_HOST':'127.0.0.1','LOGFLUX_SYSLOG_HOST':'127.0.0.1'}
        env.pop('LOGFLUX_WITNESS_CONFIG',None)
        if transport=='tls':env.update(LOGFLUX_TLS_CERT=cert,LOGFLUX_TLS_KEY=key)
        log=open(Path(directory)/'server.log','w');server=subprocess.Popen([sys.executable,str(ROOT/'scripts/run.py')],env=env,stdout=log,stderr=log)
        try:
            for _ in range(200):
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{api}/health',timeout=1) as r:
                        if json.load(r)['status']=='ok':break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('isolated collector did not start')
            db=sqlite3.connect(f'file:{directory}/events.sqlite3?mode=ro',uri=True,timeout=30)
            begin=time.perf_counter()+.25;end=begin+seconds
            def sender(number):
                sent=0;errors=0;uncertain=0
                if transport=='udp':s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                else:
                    s=socket.create_connection(('127.0.0.1',tls if transport=='tls' else tcp),timeout=2)
                    if transport=='tls':s=ssl.create_default_context(cafile=ca).wrap_socket(s,server_hostname='localhost')
                s.settimeout(seconds+1)
                with s:
                    while time.perf_counter()<end:
                        due=begin+sent*connections/rate
                        delay=due-time.perf_counter()
                        if delay>0:time.sleep(min(delay,max(0,end-time.perf_counter())))
                        if time.perf_counter()>=end:break
                        raw=f'devname="BENCH" devid="LAB" logid="1" srcip=10.0.0.1 dstip=192.0.2.1 srcport=5000 dstport=443 action=accept proto=6 level=information bench_worker={number} bench_seq={sent}'.encode()
                        try:
                            s.settimeout(max(.01,end-time.perf_counter()))
                            if transport=='udp':s.sendto(raw,('127.0.0.1',tcp))
                            else:s.sendall(str(len(raw)).encode()+b' '+raw)
                            sent+=1
                        except OSError:errors+=1;uncertain+=1;break
                return {'connection':number,'sent':sent,'send_errors':errors,'uncertain_last_frame':uncertain,'active_seconds':round(time.perf_counter()-begin,3)}
            with concurrent.futures.ThreadPoolExecutor(max_workers=connections) as pool:
                futures=[pool.submit(sender,i) for i in range(connections)]
                while time.perf_counter()<end:time.sleep(min(.1,max(0,end-time.perf_counter())))
                received_window=db.execute('SELECT COUNT(*) FROM raw_events').fetchone()[0]
                results=[f.result() for f in futures];sent=sum(x['sent'] for x in results)
                deadline=time.perf_counter()+drain
                while time.perf_counter()<deadline:
                    received=db.execute('SELECT COUNT(*) FROM raw_events').fetchone()[0]
                    if received>=sent:break
                    time.sleep(.25)
                received=db.execute('SELECT COUNT(*) FROM raw_events').fetchone()[0]
                statuses=dict(db.execute('SELECT status,COUNT(*) FROM events GROUP BY status'));db.close()
            return {'transport':transport,'offered_eps':rate,'duration_seconds':seconds,'connections':connections,'sent':sent,'actual_sent_eps':round(sent/seconds,2),'durably_received_in_window':received_window,'live_socket_eps':round(received_window/seconds,2),'received_after_drain':received,'drain_seconds_limit':drain,'not_received_after_drain':max(0,sent-received),'unreceived_percent':round(100*max(0,sent-received)/sent,4) if sent else None,'senders':results,'statuses':statuses,'arithmetic_events_per_day':round(received_window/seconds*86400),'day_projection_note':'Arithmetic only from this short run; no 24-hour measurement.'}
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()
            log.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rates',type=int,nargs='+',default=[2000,4000,8000,16000]);p.add_argument('--seconds',type=int,default=120);p.add_argument('--connections',type=int,default=4);p.add_argument('--transport',choices=['tcp','udp','tls'],default='tcp');p.add_argument('--cert');p.add_argument('--key');p.add_argument('--ca');p.add_argument('--output',default='docs/benchmark-sustained.json');a=p.parse_args()
    if a.seconds<1 or a.connections<1 or min(a.rates)<1:p.error('rates, seconds, connections must be positive')
    if a.transport=='tls' and not all((a.cert,a.key,a.ca)):p.error('TLS requires --cert --key --ca')
    report={'platform':platform.platform(),'python':platform.python_version(),'scope':'Actual isolated application + SQLite FULL + real loopback sockets, concurrent senders and background sealing; synthetic fixed-format events. Same machine sender and receiver. Offered rate may be throttled by TCP backpressure. No real-device or distributed capacity claim.','runs':[]}
    for rate in a.rates:
        row=run(rate,a.seconds,a.connections,a.transport,a.cert,a.key,a.ca);report['runs'].append(row);Path(a.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
