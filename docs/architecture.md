# LOGFLUX architecture — Universal Log Pre-processing Framework

## 1. Purpose and flow

LOGFLUX receives perimeter telemetry through TCP/UDP Syslog, optional TLS Syslog, file upload, and an authenticated HTTP API. A bounded receiver accepts a frame, writes the original bytes to an immutable SQLite-WAL evidence record, before parsing. Each record includes a UUID, SHA-256, source identity, transport, peer, framing, and receipt time. This preserves what the collector received; UDP loss before receipt remains outside the framework’s control.

The parser classifies Syslog, JSON/Suricata, XML, CSV, CEF, LEEF, Cisco ASA, pfSense, key-value, and unfamiliar text. Approved mappings normalize into the versioned LOGFLUX network-event envelope (OCSF concepts, explicit `unmapped` attributes, ECS export adapter). Every normalized revision contains raw reference, parser version, schema hash, time basis, quality issues, and source attributes. Failed, unknown, and drifted records remain queryable and are never overwritten.

```text
Firewall / router / IDS / other devices
        │ TCP · UDP · TLS Syslog · file · HTTP
        ▼
Bounded receiver → immutable raw evidence (bytes + hash + source + receipt)
        │                         │
        ├── approved parser ──────┴── normalized LOGFLUX event → quality checks
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

Parser projections execute in Wasmtime with no host imports, a 64 KiB memory ceiling, and a fuel limit. Model output is data, never executable code. The registry pins trusted public keys; signatures protect bundle integrity and origin, while validation and human approval establish deployment policy. Raw and revision tables are append-only; audit records form a signed hash chain. Merkle proofs detect evidence modification. The 2-of-3 Ed25519 witness quorum detects and rejects conflicting checkpoints, providing tamper-evident chain of custody; network witness deployment is supported, but independent custody needs separate machines and administrators.

Collectors use a bounded queue and frame-size limits. The outbox retries at least once with an idempotency key; receivers must deduplicate. Source modes (`live`, `lab`, `replay`) are shown in the UI. Drift detection compares a source's observed fingerprint with its baseline and routes changed records to review. "Self-healing" means assisted correction and approved replay, not autonomous semantic changes.

## 3. Experimental extensions and production boundary

The dashboard remains SQLite-based. The separate `lab/scale_pipeline.py` experiment reads four Redpanda partitions with 1/2/4 worker processes and writes raw bytes plus normalized events into ClickHouse. Each batch produces a Merkle root; a higher-level tree aggregates roots. File offsets advance only after successful columnar insertion; retries use stable event IDs and logical deduplication. Local 1/2/4-worker runs completed; measured results are linked in the README. It is not connected to the dashboard or shared parser registry and does not implement automatic worker reassignment or replicated storage.

The default witnesses are local. `ulpf.witness_service` and `LOGFLUX_WITNESS_CONFIG` allow authenticated, pinned-key network witnesses. Three same-host processes passed quorum, restart/catch-up and conflict tests. Remote deployments require TLS. Physical and administrative independence are not established by process separation.

The native Elasticsearch Bulk output checks per-item errors and uses stable event/revision IDs on retries. Mock transport checks pass; live local Elasticsearch verification passed. Generic webhook output is not a native Splunk/Kafka/S3 connector.

LOGFLUX uses an OCSF-inspired custom schema and partial ECS projection. Detection uses rules; Qwen3 is optional parser-mapping assistance. There is no trained anomaly/graph model. Billion-events/day capacity, full OCSF conformance, HA, independent custody and WORM storage remain future work. No linear throughput extrapolation is valid evidence of capacity.
