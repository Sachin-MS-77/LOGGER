# LOGFLUX verification — 21 September 2026

Reviewed the local application against Claude's remote commits through `7d1e2a1`. The application source matched the version on `origin/master`. GitHub's default branch was still `main`, pointing at the older AEGIS release.

## Changes preserved

- LOGFLUX branding and dark violet dashboard across all seven pages.
- Command-center analytics, severity styling, graph controls and Fracture Index gauge.
- Updated screenshot and existing presentation artifacts.

## Issues corrected

- Restored project files from a machine-specific `Documents/Codex/...` directory to the repository root, so documented clone/install commands work.
- Restored legacy environment-variable fallbacks while giving `LOGFLUX_*` settings priority.
- Aligned Docker's non-root writable directory, environment and Compose volume at `/var/lib/logflux`.
- Accepted the exact historical schema hash for trusted signed parser imports after the branding-only schema rename. Arbitrary schema hashes still fail validation.
- Provenance now reports the stored normalized event's schema hash separately from the current runtime schema hash. Existing evidence is not rewritten.
- Labeled the Fracture Index as uncalibrated, exposed its actual formula, displayed missing taint as N/A and removed unsupported low/medium/high color thresholds. Its existing formula is unchanged.
- Updated README, teammate setup and the 30-second PPT / 90-second demo script. Fixed metric caption wrapping.

## Verification performed

- `python -m pytest tests -q --junitxml=docs/test-results.xml`: **54 passed**, two upstream deprecation warnings.
- `node --check ulpf/static/app.js`: passed.
- `docker compose config --quiet`: passed. Docker daemon unavailable, so no image build/run is claimed.
- Browser: authenticated login; Command Center, Event Stream, Sources, Parser Lab, Evidence Vault, Investigation and System & Outputs loaded.
- Browser: IP selection, graph zoom from 100% to 120%, receipt-time filter empty state and evidence inspector verified.
- Existing event proof verified raw bytes, manifest, Merkle inclusion and local witness quorum after upgrade.
- Responsive checks: desktop 1440px and mobile 390px; no horizontal page overflow, and the sidebar/cards adapt to the mobile breakpoint.
- Real perimeter device (hardware firewall) log ingestion verified: device connected, events received, raw bytes committed, format parsed end-to-end.

## Deployment scope

The project is a verified single-node implementation with hardware firewall connectivity. Distributed enterprise scaling (Kafka/Flink/S3, horizontal workers, RBAC) is the documented production next phase. Qwen3 is an optional parser-mapping assistant; all detections use deterministic rules. See [feature coverage](FEATURES.md) and [README](../README.md).
