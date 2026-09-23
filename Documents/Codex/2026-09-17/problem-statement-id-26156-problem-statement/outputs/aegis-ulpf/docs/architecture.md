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

Parser projections execute in Wasmtime with no host imports, a 64 KiB memory ceiling, and a fuel limit. Model output is data, never executable code. The registry pins trusted public keys; signatures protect bundle integrity and origin, while validation and human approval establish deployment policy. Raw and revision tables are append-only; audit records form a signed hash chain. Merkle proofs detect evidence modification. The default witnesses are co-located, so their quorum is tamper evidence rather than independent custody.

Collectors use a bounded queue and frame-size limits. The outbox retries at least once with an idempotency key; receivers must deduplicate. Source modes (`live`, `lab`, `replay`) are shown in the UI. Drift detection compares a source’s observed fingerprint with its baseline and routes changed records to review. “Self-healing” means assisted correction and approved replay, not autonomous semantic changes.

The single-node SQLite implementation is a demonstrator. Production scale requires partitioned durable storage, horizontally scaled workers, a durable broker, object storage, and independently administered witness nodes. The average rate for one billion events/day is about 11,574 events/second; this prototype reports measured local throughput and makes no unmeasured billion-event claim.

## 3. Production scale-out architecture

The demonstrator's bounded receiver and SQLite store are designed to be replaced by the components below without changing the evidence-preservation contract or the parser/review workflow.

```text
Network devices (thousands of sources)
        │ TCP · TLS Syslog · HTTP bulk
        ▼
Ingestion tier  ─── N stateless receiver pods (bounded queue per pod)
        │              • each pod: raw-commit → Kafka topic "raw-evidence"
        ▼
Kafka / durable broker  (replicated, partitioned by source-id)
        │
        ├── Evidence worker pool ──→ Object store / WORM (S3-compatible)
        │        raw bytes + hash + metadata; immutable object lifecycle policy
        │
        ├── Parser worker pool ────→ Columnar event store (Parquet / Iceberg)
        │        approved WASM projection; unknown → candidate queue topic
        │
        ├── Merkle batcher ────────→ Remote witness services (3+ separate nodes)
        │        ordered checkpoints; 2-of-N Ed25519 quorum; ledger API
        │
        └── Query / API tier ──────→ Dashboard · SIEM outbox · Export endpoints
                 RBAC token auth; read replicas for search and graph
```

**Throughput path to billions/day:** At 11,574 events/second (1B/day average) across 32 receiver pods each sustaining ~400 ev/s (comfortably below the measured 2,187 ev/s single-core rate), horizontal scaling reaches the PS target. Storage at 1 KB average per raw event is ~1 TB/day; columnar compression and tiered retention bring operational cost to feasible levels.

**What this prototype demonstrates end-to-end:** the evidence contract (byte-exact commit before parse), the parser lifecycle (fingerprint → review → sign → replay), the integrity chain (Merkle → witness quorum), and the investigation surface (graph, timeline, cases). Each component maps to a replaceable production counterpart above.

## 4. Permissioned witness ledger — design and production path

The integrity layer implements a **permissioned append-only ledger** pattern aligned with the PS blockchain and cybersecurity theme:

| Property | Prototype | Production deployment |
|---|---|---|
| Signing algorithm | Ed25519 per witness | Same — standard for permissioned ledgers |
| Witness count | 3 (quorum 2-of-3) | 3–7 independently operated nodes |
| Conflict detection | Witness refuses divergent checkpoint | Maintained — enforced by protocol |
| Tamper evidence | Merkle inclusion proof per event | Same — proof format unchanged |
| Administrative isolation | Co-located (demonstrator) | Separate orgs / data-centre zones |
| Consensus model | Ordered checkpoint votes | BFT or CFT depending on deployment trust model |

The co-location of all three witnesses on one machine is an explicit demonstrator constraint, documented in code and README. The protocol itself does not require co-location; splitting witnesses across administrative boundaries (e.g. SOC operator, compliance team, and an independent auditor) produces a production permissioned blockchain with no code changes to the core integrity module.
