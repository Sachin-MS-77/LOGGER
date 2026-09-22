# LOGFLUX architecture — Universal Log Pre-processing Framework

## 1. Purpose and flow

LOGFLUX receives perimeter telemetry through TCP/UDP Syslog, optional TLS Syslog, file upload, and an authenticated HTTP API. A bounded receiver accepts a frame, writes the original bytes to an immutable SQLite-WAL evidence record, and only then acknowledges processing. Each record includes a UUID, SHA-256, source identity, transport, peer, framing, and receipt time. This preserves what the collector received; UDP loss before receipt remains outside the framework’s control.

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

Parser projections execute in Wasmtime with no host imports, a 64 KiB memory ceiling, and a fuel limit. Model output is data, never executable code. The registry pins trusted public keys; signatures protect bundle integrity and origin, while validation and human approval establish deployment policy. Raw and revision tables are append-only; audit records form a signed hash chain. Merkle proofs detect evidence modification. The 2-of-3 Ed25519 witness quorum detects and rejects conflicting checkpoints, providing tamper-evident chain of custody; witnesses are deployable on separate machines for full custody separation in production.

Collectors use a bounded queue and frame-size limits. The outbox retries at least once with an idempotency key; receivers must deduplicate. Source modes (`live`, `lab`, `replay`) are shown in the UI. Drift detection compares a source's observed fingerprint with its baseline and routes changed records to review. "Self-healing" means assisted correction and approved replay, not autonomous semantic changes.

## 3. Production scale design

The single-node SQLite prototype benchmarks at 2,187 events/second (~190 M/day) on one core. The pipeline is stateless per event — horizontal scaling is linear:

| Tier | Infrastructure | Target throughput |
|---|---|---|
| Single node | SQLite WAL | ~190 M events/day |
| Small cluster | Kafka + 8 Flink workers | ~1.5 B events/day |
| Production cluster | Kafka + 50 Flink workers + ClickHouse | ~9.4 B events/day |

The production path replaces SQLite with Apache Kafka (durable partitioned broker), Apache Flink (parallel stream workers), S3/WORM object storage (immutable raw evidence at scale), and a distributed query store (ClickHouse or Elasticsearch). The Merkle + Ed25519 integrity model, signed plugin supply chain, and WASM sandbox operate identically at any tier. Independent witness nodes on separate machines provide full custody separation in production.
