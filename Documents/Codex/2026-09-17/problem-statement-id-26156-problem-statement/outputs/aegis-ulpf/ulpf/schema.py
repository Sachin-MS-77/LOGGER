"""Versioned, OCSF-derived event envelope; extensions are explicit.

This is NOT a claim of full OCSF conformance. Exports state their schema.
"""
import hashlib
import ipaddress
import json
from datetime import datetime, timezone

SCHEMA = {
    "name": "logflux.network_event", "version": "1.0.0",
    "fields": ["time", "source_ip", "destination_ip", "source_port", "destination_port",
               "protocol", "action", "severity", "message", "device", "event_type"],
    "actions": ["allow", "deny", "alert", "unknown"],
    "severities": ["unknown", "informational", "low", "medium", "high", "critical"],
}
SCHEMA_HASH = hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def digest(value):
    return hashlib.sha256(value).hexdigest()

def getpath(obj, path):
    if path in obj:
        return obj[path]
    for part in path.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj

def normalize(attributes, mapping, context):
    """Never guess IP direction. Unmapped input and ambiguous values survive."""
    event = {"schema": SCHEMA["name"], "schema_version": SCHEMA["version"],
             "schema_hash": SCHEMA_HASH, "time": None, "source_ip": None,
             "destination_ip": None, "source_port": None, "destination_port": None,
             "protocol": None, "action": "unknown", "severity": "unknown",
             "message": "", "device": context["source"], "event_type": "network_activity"}
    issues = []
    used = set()
    for target, source in mapping.items():
        if target not in SCHEMA["fields"]:
            continue
        value = getpath(attributes, source)
        if value is None:
            if target in ("source_ip", "destination_ip", "action"):
                issues.append({"field": target, "reason": "mapped field absent", "source_field": source})
            continue
        used.add(source)
        original = value
        try:
            if target.endswith("_ip"):
                value = str(ipaddress.ip_address(str(value)))
            elif target.endswith("_port"):
                if isinstance(value, bool):
                    raise ValueError("boolean port")
                value = int(str(value))
                if not 0 <= value <= 65535:
                    raise ValueError("port outside 0–65535")
            elif target == "time":
                if isinstance(value, (int, float)):
                    value = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc).isoformat()
                else:
                    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        raise ValueError("timezone absent; original timestamp retained")
                    value = dt.astimezone(timezone.utc).isoformat()
            elif target == "action":
                value = str(value).lower()
                value = {"accept":"allow", "accepted":"allow", "permit":"allow", "permitted":"allow",
                         "pass":"allow", "allowed":"allow", "drop":"deny", "blocked":"deny",
                         "block":"deny", "reject":"deny", "denied":"deny", "detected":"alert"}.get(value, value)
                if value not in SCHEMA["actions"]:
                    raise ValueError("unrecognized action; retained in source attributes")
            elif target == "severity":
                value = str(value).lower()
                value = {"info":"informational", "information":"informational", "notice":"low",
                         "warning":"medium", "warn":"medium", "error":"high", "emergency":"critical",
                         "debug":"informational"}.get(value, value)
                if value not in SCHEMA["severities"]:
                    raise ValueError("source severity requires explicit mapping")
            elif target == "protocol":
                value = {"6":"tcp", "17":"udp", "1":"icmp", "58":"icmpv6"}.get(str(value), str(value).lower())
            else:
                value = str(value)
            event[target] = value
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            issues.append({"field": target, "reason": str(exc), "value": original})
    event["time_basis"] = "source" if event["time"] else "receipt"
    if not event["time"]:
        event["time"] = context["received_at"]
    # Canonical event taxonomy is independent of vendor labels.
    source_type = event["event_type"].lower()
    event["source_event_type"] = source_type
    event["event_type"] = {"alert":"intrusion_detection","intrusion_detection":"intrusion_detection",
                            "traffic":"network_activity","flow":"network_activity","netflow":"network_activity",
                            "network_activity":"network_activity","device_network_stats":"device_status",
                            "device_status":"device_status"}.get(source_type,"network_activity")
    event["category"] = "network"
    event["unmapped"] = {k: v for k, v in attributes.items() if k not in used}
    event["provenance"] = context
    event["quality"] = {"issues": issues, "mapped_fields": sum(event.get(k) is not None for k in ("source_ip", "destination_ip", "source_port", "destination_port", "protocol")),
                        "semantic_validation": "approved mapping; runtime type checks"}
    return event

def ecs_export(event):
    """A conservative ECS field mapping, preserving the complete LOGFLUX event."""
    n = event["normalized"] or {}
    return {"@timestamp": n.get("time", event["received_at"]), "ecs": {"version": "8.11.0"},
            "event": {"id": event["id"], "kind": "event", "category": ["network"],
                      "action": n.get("action", "unknown"), "hash": event["raw_hash"],
                      "original": event.get("raw_text", "")},
            "source": {"ip": n.get("source_ip"), "port": n.get("source_port")},
            "destination": {"ip": n.get("destination_ip"), "port": n.get("destination_port")},
            "network": {"transport": n.get("protocol")}, "observer": {"name": event["source"]},
            "logflux": {"event": n, "status": event["status"], "raw_reference": f"/api/events/{event['id']}/raw"}}
