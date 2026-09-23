# Drawback resolution — 23 September 2026

“Verified” below names a specific experiment. It does not mean the full enterprise specification is complete.

| Original drawback | Change and evidence | Remaining boundary |
|---|---|---|
| 1. SQLite single writer | Added separate Redpanda → Python workers → ClickHouse experiment | Dashboard remains SQLite; no production storage migration |
| 2. Unsupported scale extrapolation | Removed billions/day and linear-worker claims; measured 1/2/4 worker runs and 120-second socket loads | Short local runs, no HA or 24-hour capacity certification |
| 3. Sequential/local witnesses | Parallel network services, pinned keys, separate process databases; aggregate root signed; single-key verifier | Same computer/administrator, not independent custody |
| 4. Untested Docker | Build, health, ingest, TCP/UDP, exact bytes and post-restart proof passed | Hosted CI is pending workflow installation by a maintainer |
| 5. OCSF overclaim | README/PPT explicitly say OCSF-inspired custom schema / partial ECS | Full OCSF conformance not implemented |
| 6. No native SIEM connector | Elasticsearch Bulk; live 8.17.3 acceptance and retry dedup passed | Remote authenticated cluster not tested; no native Splunk/S3 |
| 7. Inflated ML claim | Qwen3 parser assistance, Drain3 templates, rules and uncalibrated gauge explicitly distinguished | No trained anomaly/Graph ML/SHAP model |
| 8. Narrow formats | Added iptables adapter and full public-file coverage reports | Unsupported sources and parse errors remain explicit |
| 9. Lossless UDP wording | Prefer TCP/TLS; preservation begins at durable acceptance | UDP loss and pre-commit loss possible; TLS load discrepancy reported |
| 10. PPT stack mismatch | Refreshed five slides separate shipped features from remaining deployment work | Broker/ClickHouse experiment is not the dashboard backend |
| 11. Leftover prompt | Inspected and proofread committed five-slide deck | Cited prompt fragment was not in this supplied deck |
| 12. llama.cpp typo | Correct tool name in current docs | No claim to have corrected an unprovided external slide |
| 13. Stale assets | Current screenshots, two-minute live walkthrough, drift clip and refreshed architecture/PPT | Captions, no narration audio; fixtures are synthetic/constructed |
| 14. Authorship | Team roster preserved; actual history preserved | Team must confirm SIH roster and real contributions; no fake stars/contributors |

New requested evidence: full corpus downloader/coverage scanner; controlled real-file replay; real TCP/UDP/TLS load driver; Docker CI workflow template; a-k reviewer actions; single-witness proof verification; eleven adversarial WASM tests; documented timestamp-unit drift with review/replay recording. See [README](../README.md) and [FEATURES](FEATURES.md).
