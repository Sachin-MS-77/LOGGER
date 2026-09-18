"""Format adapters, fingerprints, and explicit vendor mappings."""
import csv
import io
import json
import re
from defusedxml import ElementTree
from .schema import digest, canonical

MAX_FIELDS = 512
KV = re.compile(r'(?:^|\s)([A-Za-z_][\w.:-]*)=("(?:\\.|[^"\\])*"|\S*)')
ALIASES = {
    "source_ip": ["srcip", "src_ip", "src", "sourceAddress", "source_ip", "source.ip"],
    "destination_ip": ["dstip", "dest_ip", "dst", "destinationAddress", "destination_ip", "destination.ip"],
    "source_port": ["srcport", "src_port", "spt", "sourcePort", "source_port"],
    "destination_port": ["dstport", "dest_port", "dpt", "destinationPort", "destination_port"],
    "protocol": ["proto", "protocol", "network.transport"], "action": ["action", "act", "decision"],
    "time": ["timestamp", "time", "@timestamp", "rt"], "severity": ["level", "severity"],
    "message": ["msg", "message", "alert.signature"], "device": ["devname", "hostname", "device"],
    "event_type": ["event_type", "type"],
}

def flatten(value, prefix="", depth=0):
    if depth > 12:
        return {prefix: value}
    out = {}
    for key, val in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(val, dict):
            out.update(flatten(val, path, depth+1))
        else:
            out[path] = val
    return out

def suggest_mapping(attributes):
    return {target: next(key for key in choices if key in attributes)
            for target, choices in ALIASES.items() if any(key in attributes for key in choices)}

def split_escaped(value, delimiter="|", maxsplit=-1):
    parts, current, escape = [], [], False
    for c in value:
        if escape:
            current.append(c if c in (delimiter, "\\") else "\\"+c)
            escape = False
        elif c == "\\":
            escape = True
        elif c == delimiter and (maxsplit < 0 or len(parts) < maxsplit):
            parts.append("".join(current)); current = []
        else:
            current.append(c)
    if escape:
        current.append("\\")
    parts.append("".join(current))
    return parts

def key_values(text):
    out = {}
    for match in KV.finditer(text):
        key, value = match.groups()
        if value.startswith('"'):
            try: value = json.loads(value)
            except ValueError: value = value[1:-1]
        if key in out:
            raise ValueError(f"duplicate key {key}; requires source-specific handling")
        out[key] = value
        if len(out) > MAX_FIELDS:
            raise ValueError("field limit exceeded")
    return out

def cef_extensions(text):
    # Extension values may contain unquoted spaces. Boundaries are unescaped keys.
    hits = list(re.finditer(r'(?:^|\s)([\w.]+)=', text))
    result = {}
    for i, hit in enumerate(hits):
        key = hit.group(1)
        if key in result: raise ValueError(f"duplicate CEF key {key}")
        value = text[hit.end():hits[i+1].start() if i+1 < len(hits) else len(text)].strip()
        result[key] = value.replace(r'\=', '=').replace(r'\n', '\n').replace(r'\\', '\\')
    return result

def decode(raw):
    # Decoding never modifies the stored raw bytes.
    text = raw.decode("utf-8", errors="strict").strip()
    meta = {}
    body = text
    pri = re.match(r'^<(\d{1,3})>', body)
    if pri:
        number = int(pri.group(1))
        if number > 191: raise ValueError("invalid Syslog PRI")
        meta = {"syslog.priority": number, "syslog.facility": number//8, "syslog.severity": number%8}
        body = body[pri.end():]
        rfc = re.match(r'^1 (\S+) (\S+) (\S+) (\S+) (\S+) (.*)$', body, re.S)
        if rfc:
            ts, host, app, proc, msgid, rest = rfc.groups()
            meta.update({"syslog.timestamp": ts, "syslog.hostname": host, "syslog.app": app, "syslog.procid": proc, "syslog.msgid": msgid})
            if rest.startswith("- "): body = rest[2:]
            elif rest.startswith("["):
                sd = re.match(r'((?:\[(?:\\.|[^\]\\])*\])+)\s?(.*)', rest, re.S)
                if not sd: raise ValueError("malformed Syslog structured data")
                meta["syslog.structured_data"], body = sd.groups()
            else: body = rest
        else:
            rfc3164 = re.match(r'^([A-Z][a-z]{2}\s+\d{1,2}\s+\d\d:\d\d:\d\d)\s+(\S+)\s+(.*)$', body, re.S)
            if rfc3164:
                meta["syslog.timestamp"], meta["syslog.hostname"], body = rfc3164.groups()
    attrs, fmt, vendor = {}, "text", "unknown"
    if body.startswith("{"):
        def unique_pairs(pairs):
            obj = {}
            for key, val in pairs:
                if key in obj: raise ValueError(f"duplicate JSON key {key}")
                obj[key] = val
            return obj
        obj = json.loads(body, object_pairs_hook=unique_pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("non-finite JSON number")))
        if not isinstance(obj, dict): raise ValueError("event must be an object")
        attrs, fmt = flatten(obj), "json"
        if "event_type" in attrs and ("flow_id" in attrs or "alert.signature" in attrs): vendor = "suricata"
    elif "CEF:" in body:
        fields = split_escaped(body[body.index("CEF:"):], maxsplit=7)
        if len(fields) != 8: raise ValueError("CEF requires seven header separators")
        attrs = dict(zip(["cef.version","cef.vendor","cef.product","cef.device_version","cef.signature","cef.name","cef.severity"], fields[:7]))
        attrs.update(cef_extensions(fields[7])); fmt, vendor = "cef", "cef"
    elif "LEEF:" in body:
        version = body[body.index("LEEF:"):].split("|", 1)[0]
        fields = split_escaped(body[body.index("LEEF:"):], maxsplit=6 if version == "LEEF:2.0" else 5)
        if len(fields) < 6: raise ValueError("invalid LEEF header")
        attrs = dict(zip(["leef.version","leef.vendor","leef.product","leef.product_version","leef.event_id"], fields[:5]))
        delimiter = "\t"
        if version == "LEEF:2.0":
            d = fields[5]; delimiter = chr(int(d[2:], 16)) if d.startswith("0x") else d
            if len(delimiter) != 1: raise ValueError("invalid LEEF delimiter")
        for item in fields[-1].split(delimiter):
            if "=" in item:
                key, val = item.split("=", 1)
                if key in attrs: raise ValueError(f"duplicate LEEF key {key}")
                attrs[key] = val
        fmt, vendor = "leef", "leef"
    elif body.startswith("<"):
        root = ElementTree.fromstring(body)
        def walk(el, prefix=""):
            out = {f"{prefix}@{k}": v for k, v in el.attrib.items()}
            for child in el:
                path = f"{prefix}{child.tag}"
                value = walk(child, path+".") if len(child) else child.text
                if isinstance(value, dict): out.update(value)
                elif path in out: raise ValueError("repeated XML elements require a source adapter")
                else: out[path] = value
            return out
        attrs, fmt = walk(root), "xml"
    elif "%ASA-" in body:
        attrs, fmt, vendor = {"message": body}, "cisco-asa", "cisco-asa"
        m = re.search(r'%ASA-(\d)-(\d+):\s*(.*)', body)
        if m:
            attrs.update({"asa.severity": m[1], "asa.code": m[2]})
            deny = re.search(r'Deny\s+(\w+)\s+src\s+[^: ]+:([\da-fA-F:.]+)/([0-9]+)\s+dst\s+[^: ]+:([\da-fA-F:.]+)/([0-9]+)', m[3], re.I)
            if deny:
                attrs.update(dict(zip(["protocol","srcip","srcport","dstip","dstport"], deny.groups()))); attrs["action"] = "deny"
    else:
        attrs = key_values(body)
        if attrs:
            fmt = "key-value"
            if "devid" in attrs and ("logid" in attrs or "devname" in attrs): vendor = "fortigate"
        elif "\n" in body and "," in body.splitlines()[0]:
            rows = list(csv.DictReader(io.StringIO(body)))
            if len(rows) != 1 or None in rows[0]: raise ValueError("CSV input must contain one header and one event row")
            attrs, fmt = rows[0], "csv"
        else:
            # pfSense filterlog: fixed documented prefix, IPv4 and IPv6 positions differ.
            pfsense = re.search(r'(?:filterlog(?:\[\d+\])?:\s*)(.*)', body)
            if pfsense:
                cols = next(csv.reader([pfsense[1]]))
                if len(cols) >= 20 and cols[8] == "4":
                    attrs = dict(zip(["rule","subrule","anchor","tracker","interface","reason","action","direction","ip_version","tos","ecn","ttl","id","offset","flags","proto","protocol","length","srcip","dstip"], cols[:20]))
                    if len(cols)>21 and attrs["protocol"] in ("tcp","udp"): attrs.update({"srcport": cols[20], "dstport": cols[21]})
                elif len(cols)>=17 and cols[8] == "6":
                    attrs = dict(zip(["rule","subrule","anchor","tracker","interface","reason","action","direction","ip_version","class","flow_label","hop_limit","protocol","proto","length","srcip","dstip"],cols[:17]))
                    if len(cols)>18 and attrs["protocol"] in ("tcp","udp"): attrs.update({"srcport":cols[17],"dstport":cols[18]})
                else: raise ValueError("unsupported pfSense filterlog layout")
                fmt, vendor = "pfsense", "pfsense"
    if len(attrs)>MAX_FIELDS: raise ValueError("field limit exceeded")
    attrs.update(meta)
    # A key-set fingerprint detects changes even if a parser still accepts syntax.
    # A bounded positional adapter lets reviewers onboard free-text templates.
    # Token meaning is explicitly mapped by a human or proposed by the local model.
    if fmt == "text":
        attrs.update({f"token_{i}": token for i, token in enumerate(body.split()[:MAX_FIELDS-len(meta)])})
    shape = sorted(k for k in attrs if not k.startswith("syslog."))
    template = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b|\b\d+\b', "<*>", body)[:300] if fmt == "text" else ""
    fingerprint = digest(canonical({"format":fmt,"keys":shape,"template":template}))[:24]
    return {"format":fmt,"vendor":vendor,"attributes":attrs,"fingerprint":fingerprint,"body":body,"template":template}

def built_in_mapping(parsed):
    attrs, vendor = parsed["attributes"], parsed["vendor"]
    if vendor == "unknown": return None
    mapping = suggest_mapping(attrs)
    if vendor == "suricata":
        mapping.update({"source_ip":"src_ip", "destination_ip":"dest_ip", "time":"timestamp"})
        if "alert.action" in attrs: mapping["action"] = "alert.action"
        if "alert.signature" in attrs: mapping["message"] = "alert.signature"
        # Numeric IDS signature priority is not the same as Syslog severity.
        if "alert.severity" in attrs:
            attrs["normalized_severity"] = {1:"high",2:"medium",3:"low"}.get(attrs["alert.severity"], "unknown")
            mapping["severity"] = "normalized_severity"
    if vendor == "cef":
        mapping["message"] = "cef.name"
        sev = attrs.get("cef.severity", "").lower()
        if sev.isdigit():
            num = int(sev); sev = "low" if num <= 3 else "medium" if num <= 6 else "high" if num <= 8 else "critical"
        attrs["normalized_severity"] = sev; mapping["severity"] = "normalized_severity"
    if "syslog.timestamp" in attrs and "time" not in mapping: mapping["time"] = "syslog.timestamp"
    if vendor == "cisco-asa" and "srcip" not in attrs: return None
    return mapping
