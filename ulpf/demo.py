"""Deterministic synthetic scenario, always visibly labeled as replay."""
import json
from datetime import datetime,timezone,timedelta

def scenario(count=7000):
    start=datetime.now(timezone.utc)
    for i in range(count):
        ts=(start+timedelta(milliseconds=i*75)).isoformat()
        source_ip="198.51.100.24" if i%4==0 else f"10.10.1.{10+i%30}"
        dst="10.20.0.12" if i%4==0 else f"192.0.2.{10+i%8}"
        port=[443,53,22,3389,80,445][i%6]
        deny=i%4==0 or port in (3389,445)
        kind=i%5
        if kind==0:
            name="FortiGate · perimeter"; category="firewall"
            raw=f'devname="FGT-EDGE-01" devid="FGT-LAB-001" logid="0000000013" timestamp="{ts}" type="traffic" srcip={source_ip} srcport={42000+i} dstip={dst} dstport={port} proto=6 action={"deny" if deny else "accept"} level={"warning" if deny else "information"} msg="Synthetic perimeter scenario"'
        elif kind==1:
            name="Suricata · sensor"; category="ids"
            raw=json.dumps({"timestamp":ts,"flow_id":900000+i,"event_type":"alert" if deny else "flow","src_ip":source_ip,"src_port":42000+i,"dest_ip":dst,"dest_port":port,"proto":"TCP","alert":{"action":"blocked" if deny else "allowed","signature":"Synthetic suspicious management connection" if deny else "Synthetic flow observation","severity":2 if deny else 3}})
        elif kind==2:
            name="Cisco ASA · edge"; category="firewall"
            raw=f'<166>1 {ts} ASA-LAB asa - - - %ASA-6-106023: Deny tcp src outside:{source_ip}/{42000+i} dst inside:{dst}/{port} by access-group "LAB-IN"'
        elif kind==3:
            name="CEF · gateway"; category="gateway"
            raw=f'CEF:0|Lab|Gateway|1.0|100|Synthetic connection|{7 if deny else 2}|src={source_ip} dst={dst} spt={42000+i} dpt={port} proto=TCP act={"deny" if deny else "allow"} rt={ts}'
        else:
            name="Router · unfamiliar format"; category="router"
            raw=f'origin={source_ip} target={dst} origin_port={42000+i} target_port={port} verdict={"deny" if deny else "allow"} transport=tcp observed_at={ts} message="Synthetic router event"'
        yield {"source":name,"kind":category,"raw":raw.encode()}

def drift_sample():
    return f'devname="FGT-EDGE-01" devid="FGT-LAB-001" logid="0000000013" timestamp="{datetime.now(timezone.utc).isoformat()}" type="traffic" client_ip=198.51.100.24 srcport=42318 server_ip=10.20.0.12 dstport=22 proto=6 action=deny level=warning msg="Synthetic firmware schema change"'.encode()
