# Requirement and original-plan coverage

Updated review: 21 September 2026. See [verification report](VERIFICATION.md) for the current 54-test run. Status describes shipped behavior, not future intent.

## SIH requirements

| Requirement | Implementation and evidence | Boundary |
|---|---|---|
| a. Complete raw preservation | Original bytes/BLOB, SHA-256, metadata, raw download, Base64 in JSONL, immutable SQL triggers, random-input tests | Applies to accepted messages. UDP/network loss before receipt cannot be prevented. |
| b. Source attributes | Structural JSON, XML, CSV, CEF, LEEF, Syslog, key/value, ASA, pfSense decoders; extracted attributes retained | Tested vendor subsets, not every model or firmware. |
| c. Common taxonomy | LOGFLUX schema, typed IPs/ports, time basis, action/severity/event category, unmapped attributes | Inspired by OCSF concepts. No full OCSF conformance claim. |
| d. Traceability | Event IDs, raw hash, parser/version, schema hash, immutable revisions, alert and case links | Single-host database and signing keys. |
| e. New-source onboarding | Fingerprint, Drain3 template, deterministic/local AI proposal, reviewer mapping, validate/sign/replay, version/rollback | Requires semantic review. Unknown formats are not automatically understood. |
| f. Unified visibility | Live backend dashboard, source/mode/status filters, search, graph, timeline, cases | Graph window latest 1,000 matching events; no global distributed index. |
| g. SIEM and lake integration | Complete JSONL, ECS projection, CSV; HTTP outbox with retry and delivery key; paginated export | No native Splunk, Kafka, S3 or Elastic connector. Destination adapter may be required. |
| h. AI/ML readiness | Typed fields and CSV/JSONL; rule detections; local Qwen mapping proposal; behavior summaries | No trained anomaly detector, feature store or attack classifier. |
| i. Reduced parser effort | Templates, suggested mapping and signed WASM field projection avoid handwritten parser code for supported structures | Benefit demonstrated by workflow; no measured developer-time reduction claim. |
| j. Air gap | Local assets, no cloud fallback, pinned wheels, offline installer, local model adapter | Fresh no-index install/test verified. Physical isolated-network test and transfer of model/runtime remain deployment steps. |
| k. Containers | Non-root Dockerfile, persistent data volume, read-only root, Compose | Docker daemon unavailable here. Actual image build/run remains unverified. |
| Scale: billions/day | Documented partitioned architecture and an actual 2,000-event local benchmark | Distributed platform is not implemented. Current SQLite node cannot support the stated enterprise-scale requirement. |

## Each item in the original plan

| Original-plan component | Shipped implementation | Status |
|---|---|---|
| Live cyber range | Dedicated loopback lab listener and safe socket generator, visibly synthetic | Functional simulator, not a multi-VM attack range |
| Firewall / router / IDS feeds | TCP, UDP, verified TLS integration tests; source registration; five synthetic source families | Real transports; physical hardware pending |
| Event capture | Bounded frames, durable receipt, queued recovery, overflow/error counters | Implemented |
| Raw evidence vault | Exact bytes, SHA-256, source/receipt/framing metadata, download | Implemented |
| Batch Merkle tree | Roots, inclusion paths, manifests, proof checks | Implemented |
| Permissioned ledger | 3 local Ed25519 witnesses, ordered checkpoints, 2-signature quorum, catch-up/conflict rejection | Local demonstrator; no independent distributed consensus |
| Telemetry fingerprint | Format and key/template structure hash | Implemented; conservative drift can flag legitimate changes |
| Known registry path | Built-in adapters and signed active parser lookup | Implemented |
| Unknown discovery | Drain3, tokens/key sets, deterministic aliases | Implemented |
| LLM semantic mapping | Local Ollama / llama.cpp, JSON constraints, type/meaning filters, explicit abstention/review | Real Qwen test recorded; accuracy remains conditional |
| Behavior discovery | Observed address relationships, action counts, unique destinations | Heuristics only; no learned behavioral discovery engine |
| Candidate parser | Editable mapping with sample values, structure and raw views | Implemented |
| WASM/WASI isolation | Wasmtime field projection with zero host imports, fuel and memory bounds | WASM mapping implemented; trusted Python parses structures; full WASI parser sandbox not implemented |
| Replay + property fuzz | Candidate replay checks and decoder mutations, Hypothesis random-byte preservation tests | Implemented within stated scope; mutation count is not a proof of semantic correctness |
| Cross-source weighting | Pair co-occurrence plus syntax/type/semantic signals, heuristic score | Implemented heuristic; no calibrated probability or causal identity claim |
| Human review queue | Draft, validate, review acknowledgement, named approval, signed audit | Implemented; single admin role |
| Signed plugin bundle | WASM binary/hash, mapping, schema hash, test vectors, CycloneDX-style SBOM, Ed25519 signature | Implemented; SBOM describes mapping module, not full dependency provenance |
| Production registry | Versioning, trusted key pinning, import inactive, activation and rollback | Single-node registry prototype |
| Universal normalization | LOGFLUX envelope, attributes, unmapped data, raw ref/hash, provenance | Implemented; finite adapters and review boundary |
| Quality / drift / self-healing | Invalid field issues; new signatures staged; approved replay creates revisions | Recovery requires reviewed approval, not unattended self-modification |
| Event graph / SIEM / AI | Browser address graph, timeline, outputs, local model | Implemented without Neo4j/RDF server or trained anomaly model |
| Attack timeline | Observations ordered by event/receipt time, rule alerts, evidence case | Investigation aid, not an automated confirmed attack narrative |
| Raw-parser-event-alert-case provenance | Revision/alert/case joins shown in event inspector | Implemented |
| Offline packaging | Pinned source dependencies, platform-specific wheelhouse, installer, staged model on demo machine | Source ZIP excludes model weights, private keys and runtime data |
| Submission assets | Source archive, README, 2-page architecture, 5-slide presentation, <2-minute walkthrough | See submission-checklist.md |

## Fracture Index added in the UI redesign

The gauge is an uncalibrated count formula based on denied/alerted events, source timestamps and unique destinations. Taint is unavailable; the current formula reaches at most 75 on the 0–100 display. It is not a threat probability, learned model or validated accuracy measure. The formula is shown in the UI and README.

## Evaluation claims

Say: “We demonstrate an extensible, lossless-on-acceptance preprocessing pipeline with reviewed parser adaptation and verifiable evidence.”

Do not say: “It understands every device automatically,” “the witnesses are independently operated,” “this is a complete production blockchain,” or “we tested a billion events per day.”

Production work remains: distributed durable ingestion, bounded worker queues with backpressure, object storage/WORM retention, remote independent witness services, RBAC and service authentication, signed offline update governance, horizontal query storage, sustained load/failure testing, full schema conformance, actual vendor hardware tests and a real isolated multi-device cyber range.
