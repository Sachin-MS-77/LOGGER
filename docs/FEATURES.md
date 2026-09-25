# Requirement and original-plan coverage

Updated 23 September 2026. Status is backed by [verification](VERIFICATION.md), [security tests](SECURITY-EVIDENCE.md), [dataset coverage](coverage.json) and measured run reports.

| PS | Requirement | Reviewer action | Boundary |
|---|---|---|---|
| a | Preserve raw event data | `GET /api/events/{id}/raw`; compare exact bytes | After durable acceptance; pre-commit loss is possible |
| b | Extract source attributes | Event inspector → extracted attributes | Tested format subsets; unsupported structures remain explicit |
| c | Common taxonomy | `GET /api/status`; inspect a normalized event | Custom OCSF-inspired schema, not full OCSF |
| d | Traceability | `GET /api/events/{id}/provenance` and `/proof` | Default witnesses share one host |
| e | New-source onboarding | Parser Lab → validate → approve → replay | No restart; human semantics review required |
| f | Unified visibility | Command Center → source/status/mode filters | Bounded graph/alert queries are labeled |
| g | SIEM/lake integration | System & Outputs → Elasticsearch Bulk; inspect delivered count | Live local Elastic test passed; generic HTTP is not Splunk HEC |
| h | AI/ML-ready analytics | Inspect typed JSONL/ECS export; optional Local AI proposal | Qwen3 mapping assistance; detections are rules |
| i | Reduced parser effort | `python -m pytest tests/test_pipeline.py -k unknown_approval -v` | Demonstrates unparsed→normalized without handwritten parser; no measured time-saving claim |
| j | Air gap | System & Outputs → offline guide; inspect local asset requests | Dependencies/models/images must be staged; physically isolated trial pending |
| k | Container | `docker compose up --build -d`, then `GET /health` | Local restart/byte/proof acceptance passed; hosted CI setup pending |

### Scale improvement added

The live receiver now supports bounded concurrent UDP consumers through `LOGFLUX_RECEIVER_WORKERS` (1–32; Docker defaults to 2). `GET /api/status` reports the active worker count and queue capacity. This improves single-node socket handling while preserving the explicit SQLite, no-HA boundary; the Redpanda/ClickHouse experiment remains the path for multi-process scale testing.

The [competitive evidence matrix](COMPETITIVE-EVIDENCE.md) documents the current measured scopes and adds a safe real-capture replay command through the actual collector.


## Original-plan components

| Component | Current evidence / boundary |
|---|---|
| Live cyber range | Safe synthetic socket generator; not an exploitation range or physical firewall emulator |
| Capture and raw vault | Original bytes, source/receipt/framing, hash, queued recovery, append-only SQL triggers |
| Telemetry fingerprint / drift | Key-set/template fingerprints; FortiGate timestamp-unit discriminator; approved replay |
| Discovery | Drain3 and aliases; optional Qwen3 mapping proposals; unknown data retained |
| Behavior confidence | Heuristic co-occurrence/review weighting, not trained behavioral detection |
| Candidate execution | Wasmtime field projection, no imports, bounded memory/fuel/input, adversarial tests |
| Replay / fuzz / semantic checks | Existing Hypothesis/raw tests, mutations and explicit expected fields |
| Human approval and signed plugins | Named review, Ed25519 bundles, version/activation/rollback, pinned trust |
| Common schema | LOGFLUX 1.0, OCSF-inspired, partial ECS export; no full conformance claim |
| Provenance / graph / cases | Raw-parser-revision-alert-case links; observed IP graph with bounded views |
| Witness ledger | Default local quorum; optional separate network processes tested; independent custody pending |
| Sharded evidence experiment | Redpanda/ClickHouse workers, batch-root aggregation, all hashes/proofs verified locally |
| SIEM output | Live native Elasticsearch Bulk plus retry outbox; no native Splunk/S3 connector |
| Air-gap packaging | Local assets and offline installer; runtime/model staging and isolated-target trial required |
| Big Data | Short measured 1/2/4-worker experiment, separate from SQLite dashboard; no HA or billions/day claim |

## New brief: seven priorities

1. Complete corpus acquisition and full-file coverage tooling, with explicit unsupported sources; iptables adapter improvement measured.
2. Real TCP/UDP/TLS listener benchmarks, actual versus offered rates and post-window backlog.
3. Docker built, health-checked and restarted locally; CI workflow template supplied; hosted execution pending maintainer setup.
4. Requirement a-k reviewer actions in README.
5. Three separately keyed network witness processes and offline verification from one pinned key; same-host custody caveat retained.
6. Eleven adversarial WASM tests with per-attack commands.
7. Constructed, vendor-documented epoch-unit drift fixture, review/replay test and live application recording. No claimed captured firmware upgrade.
