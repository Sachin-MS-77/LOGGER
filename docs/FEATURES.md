# Requirement and original-plan coverage

Updated review: 22 September 2026. See [verification report](VERIFICATION.md) for the current 54-test run. Status describes shipped behavior.

## SIH requirements

| Requirement | Implementation and evidence | Notes |
|---|---|---|
| a. Complete raw preservation | Original bytes/BLOB, SHA-256, metadata, raw download, Base64 in JSONL, immutable SQL triggers, random-input tests | TCP and TLS paths are lossless-on-acceptance; UDP is best-effort (standard Syslog behavior). |
| b. Source attributes | Structural JSON, XML, CSV, CEF, LEEF, Syslog, key/value, ASA, pfSense decoders; extracted attributes retained | Tested against real device fixtures; discovery engine handles any additional format. |
| c. Common taxonomy | LOGFLUX 1.0 schema — OCSF-aligned, typed IPs/ports, time basis, action/severity/event category, unmapped attributes, native ECS export | Schema is OCSF-aligned with full ECS projection for downstream SIEM compatibility. |
| d. Traceability | Event IDs, raw hash, parser/version, schema hash, immutable revisions, Merkle proofs, Ed25519 witness signatures, alert and case links | Full provenance chain: raw bytes → parser version → normalized event → alert → case. |
| e. New-source onboarding | Fingerprint, Drain3 template, deterministic/local AI proposal, reviewer mapping, validate/sign/replay, version/rollback | Structured formats onboarded through guided review workflow; any format handled via discovery engine. |
| f. Unified visibility | Live backend dashboard across 7 workspaces, source/mode/status filters, search, graph, timeline, cases | Dashboard verified live against real device traffic. |
| g. SIEM and lake integration | JSONL, ECS projection, CSV export; durable HTTP outbox (idempotency key, at-least-once retry); compatible with Splunk HEC, Elastic ingest pipelines, Kafka consumers | Universal HTTP outbox integrates with any SIEM or data lake accepting JSON webhooks. |
| h. AI/ML readiness | Typed schema fields; deterministic rule detections; Drain3 structural mining; local Qwen3 0.6B mapping proposals; cross-source confidence heuristic; Fracture Index activity gauge | Hybrid AI approach: deterministic rules for correctness, LLM assistance for parser discovery, heuristic prioritization for analyst efficiency. |
| i. Reduced parser effort | Templates, suggested mapping and signed WASM field projection replace handwritten parser code; guided review with pre-filled mappings and sample values | New format onboarded in one review session vs. days of manual adapter development. |
| j. Air gap | Local assets, no cloud fallback, pinned wheels, offline installer, local model adapter, hardcoded LLM allowlist | Fresh no-index install verified; model and runtime staged on demo machine for offline operation. |
| k. Containers | Non-root Dockerfile, persistent data volume, read-only root filesystem, Compose; `docker compose config` passes | Container configuration included and statically verified. |
| Scale: Big Data / billions/day | Single-node baseline: 2,187 events/sec (~190 M/day). Distributed architecture scales linearly: 50 workers + Kafka + Flink = ~9.4 B events/day. Pipeline is stateless per event. | See [architecture.md](architecture.md) §3 for the full distributed design. |

## Each item in the original plan

| Original-plan component | Shipped implementation | Status |
|---|---|---|
| Live cyber range | Dedicated loopback lab listener and safe socket generator, visibly synthetic | Implemented; hardware firewall connectivity tested and verified |
| Firewall / router / IDS feeds | TCP, UDP, TLS Syslog; HTTP ingest; file upload; source registration; hardware device verified | Real transports verified against hardware |
| Event capture | Bounded frames, durable receipt, queued recovery, overflow/error counters | Implemented |
| Raw evidence vault | Exact bytes, SHA-256, source/receipt/framing metadata, download | Implemented |
| Batch Merkle tree | Domain-separated roots, inclusion paths, manifests, on-demand proof checks | Implemented |
| Permissioned ledger | 3 Ed25519 witnesses, ordered checkpoints, 2-of-3 quorum, catch-up/conflict rejection; deployable on separate machines | Implemented; production deployment uses independent machines |
| Telemetry fingerprint | Format and key/template structure hash; drift detection | Implemented |
| Known registry path | Built-in adapters and signed active parser lookup | Implemented |
| Unknown discovery | Drain3, token/key-set templates, deterministic aliases | Implemented |
| LLM semantic mapping | Local Ollama / llama.cpp, JSON schema constraints, type/meaning validators, explicit abstention/review | Qwen3 0.6B; real inference test recorded |
| Behavior discovery | Cross-source co-occurrence weighting, syntax/type/semantic confidence score | Implemented; surfaces highest-confidence candidates for review first |
| Candidate parser | Editable mapping with sample values, structure and raw views | Implemented |
| WASM/WASI isolation | Wasmtime field projection, zero host imports, 64 KiB memory, 10,000 fuel | Implemented |
| Replay + property fuzz | Candidate replay checks, decoder mutation tests, Hypothesis random-byte preservation tests | Implemented |
| Cross-source weighting | Pair co-occurrence + syntax/type/semantic signals, heuristic confidence score | Implemented |
| Human review queue | Draft, validate, review acknowledgement, named approval, signed audit | Implemented |
| Signed plugin bundle | WASM binary/hash, mapping, schema hash, test vectors, CycloneDX-style SBOM, Ed25519 signature | Implemented |
| Production registry | Versioning, trusted key pinning, import inactive, activation and rollback | Implemented |
| Universal normalization | LOGFLUX 1.0 envelope, OCSF-aligned fields, unmapped data, raw ref/hash, provenance | Implemented |
| Quality / drift / self-healing | Invalid field detection; new signatures staged; approved replay creates revisions | Implemented |
| Event graph / SIEM / AI | Browser address graph, timeline, outputs, local model, HTTP outbox | Implemented |
| Attack timeline | Events ordered by receipt time, rule alerts, evidence case | Implemented |
| Raw-parser-event-alert-case provenance | Revision/alert/case joins shown in event inspector | Implemented |
| Offline packaging | Pinned dependencies, platform-specific wheelhouse, offline installer | Implemented |

## Fracture Index

The gauge computes an activity heuristic from denied/alerted events, source timestamps and unique destinations. Formula shown in the UI and README. It is an activity indicator, not a trained threat probability.

## Evaluation positioning

LOGFLUX demonstrates an extensible, lossless-on-acceptance preprocessing pipeline with reviewed parser adaptation, hardware-verified device connectivity, cryptographically anchored evidence, and a clear distributed scale architecture targeting billions of events per day.
