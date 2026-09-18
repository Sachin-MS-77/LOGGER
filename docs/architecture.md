# AEGIS architecture — Universal Log Pre-processing Framework

## 1. Purpose and flow

AEGIS receives perimeter telemetry through TCP/UDP Syslog, optional TLS Syslog, file upload, and an authenticated HTTP API. A bounded receiver accepts a frame, writes the original bytes to an immutable SQLite-WAL evidence record, and only then acknowledges processing. Each record includes a UUID, SHA-256, source identity, transport, peer, framing, and receipt time. This preserves what the collector received; UDP loss before receipt remains outside the framework’s control.

The parser classifies Syslog, JSON/Suricata, XML, CSV, CEF, LEEF, Cisco ASA, pfSense, key-value, and unfamiliar text. Approved mappings normalize into the versioned AEGIS network-event envelope (OCSF concepts, explicit `unmapped` attributes, ECS export adapter). Every normalized revision contains raw reference, parser version, schema hash, time basis, quality issues, and source attributes. Failed, unknown, and drifted records remain queryable and are never overwritten.

```text
Firewall / router / IDS / other devices
        │ TCP · UDP · TLS Syslog · file · HTTP
        ▼
Bounded receiver → immutable raw evidence (bytes + hash + source + receipt)
        │                         │
        ├── approved parser ──────┴── normalized AEGIS event → quality checks
        │                                                   ├→ dashboard / search
        │                                                   ├→ ECS / JSONL / CSV
        │                                                   ├→ durable HTTP outbox
        │                                                   └→ graph / alerts / cases
        ▼
unknown or drifted backlog → structure discovery (Drain3) → local model proposal
        → deterministic type/semantic checks → replay + bounded WASM projection
        → reviewer approval → Ed25519-signed plugin (WASM + SBOM + vectors)
        → staged registry → replay retained events as new revisions

raw manifests → domain-separated Merkle batches → 2-of-3 signed local witnesses
```

## 2. Security, integrity, and operational boundaries

Parser projections execute in Wasmtime with no host imports, a 64 KiB memory ceiling, and a fuel limit. Model output is data, never executable code. The registry pins trusted public keys; signatures protect bundle integrity and origin, while validation and human approval establish deployment policy. Raw and revision tables are append-only; audit records form a signed hash chain. Merkle proofs detect evidence modification. The default witnesses are co-located, so their quorum is tamper evidence rather than independent custody.

Collectors use a bounded queue and frame-size limits. The outbox retries at least once with an idempotency key; receivers must deduplicate. Source modes (`live`, `lab`, `replay`) are shown in the UI. Drift detection compares a source’s observed fingerprint with its baseline and routes changed records to review. “Self-healing” means assisted correction and approved replay, not autonomous semantic changes.

The single-node SQLite implementation is a demonstrator. Production scale requires partitioned durable storage, horizontally scaled workers, a durable broker, object storage, and independently administered witness nodes. The average rate for one billion events/day is about 11,574 events/second; this prototype reports measured local throughput and makes no unmeasured billion-event claim.
