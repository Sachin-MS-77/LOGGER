# LOGFLUX verification — 26 September 2026

## Completed checks

- **40.3M real-record validation passed:** 40,316,437 public event records were streamed through the full-file decoder/mapping/normalization scan, with raw bytes hashed and outcomes retained per file. [Summary](public-corpus-40m.json) · [report](coverage-public-40m.json).
- **83 tests passed**, two upstream test-library deprecation warnings. JUnit: [test-results.xml](test-results.xml).
- JavaScript syntax check passed. Seven authenticated workspaces were captured from the running container with no page-script errors during the gallery check.
- **Docker local acceptance passed**: non-root user, read-only root, health, authenticated ingestion, exact raw bytes, TCP/UDP receipt, evidence proof after restart. [Report](docker-verification.json).
- **Native Elasticsearch 8.17.3 passed**: Bulk delivery accepted; retry resulted in one document; source IP and raw-hash reference matched. Per-item HTTP-200 rejection handling is also unit-tested. [Report](elasticsearch-verification.json).
- **Network witnesses passed**: main-store proof, two-of-three availability, one-of-three refusal, restart/catch-up with three votes and conflict rejection. The tested four-worker aggregate root is in the report. Separate processes/keys, same physical host. [Report](witness-verification.json).
- **Worker experiment passed** at 1/2/4 processes with 2,000 events each: all raw hashes and shard proofs checked; committed-offset resume wrote no new records. [1 worker](scale-benchmark-1.json), [2 workers](scale-benchmark-2.json), [4 workers](scale-benchmark-4.json).
- **WASM attack tests passed**: eleven attacks/boundaries, with per-test commands in [SECURITY-EVIDENCE](SECURITY-EVIDENCE.md).
- **Drift workflow passed** in a test and the real UI: constructed FortiGate timestamp-unit variant quarantined, reviewed, approved, replayed to revision 2; original hash unchanged and proof valid. [Report](drift-verification.json).
- **120-second socket runs completed** through the actual application, with four concurrent senders. At 500 TCP events/s, 60,000/60,000 records were durably received. Overload runs show backpressure/backlog; TLS had 75 unreceived records at the drain deadline. These findings are published, not rounded away. [README tables](../README.md#measured-results).
- Full public archive acquisition completed for the six perimeter/system families, with the BGL, HDFS_v1 and Hadoop extension added for the 40M validation. Full-file built-in registry coverage is recorded in [coverage.json](coverage.json), with source hashes in [dataset-manifest.json](dataset-manifest.json).
- **Broker evidence acceptance passed** at 15,000 durably verified events/s for 60 seconds: 900,000/900,000 records, raw hashes, Merkle batches and witness signatures. [Report](benchmark-15k.json).
- **Public-corpus scale validation passed** at 40,316,437 real event records across the existing perimeter/system corpora and the BGL, HDFS_v1 and Hadoop extension. [Summary](public-corpus-40m.json) · [full-file report](coverage-public-40m.json).
- Submission description is exactly **40,000 Unicode characters** with spaces and LF line breaks, below the stated 50,000-character limit. Title is separate.

## Artifact scope

The refreshed five-slide deck uses current screenshots and clear evidence labels. The MP4 is exactly two minutes: 30 seconds of slides and 90 seconds of current application interaction, with visible captions and no narration audio. The separate drift clip is an excerpt of the same workflow. Demo and constructed-fixture labels remain visible.

## Deployment profile and next acceptance targets

The committed reports distinguish the dashboard profile, broker/evidence profile and deployment acceptance targets. The broker path, raw-byte vault, Merkle sealing, witness quorum, parser sandbox and corpus scans are independently reproducible; replicated cluster deployment, independent-machine witness custody, full OCSF conformance, trained attack ML, WORM storage and enterprise RBAC are the next acceptance targets for a production installation.

Deployment follow-through is packaged for the selected target environment: attach the physical-device acceptance capture, air-gap checklist and hosted CI artifact when those environments are selected. The workflow is supplied as `docs/ci/docker.yml`, and the local Docker acceptance report is available for comparison with the hosted run.
