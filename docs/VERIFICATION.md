# LOGFLUX verification — 23 September 2026

## Completed checks

- **81 tests passed**, two upstream test-library deprecation warnings. JUnit: [test-results.xml](test-results.xml).
- JavaScript syntax check passed. Seven authenticated workspaces were captured from the running container with no page-script errors during the gallery check.
- **Docker local acceptance passed**: non-root user, read-only root, health, authenticated ingestion, exact raw bytes, TCP/UDP receipt, evidence proof after restart. [Report](docker-verification.json).
- **Native Elasticsearch 8.17.3 passed**: Bulk delivery accepted; retry resulted in one document; source IP and raw-hash reference matched. Per-item HTTP-200 rejection handling is also unit-tested. [Report](elasticsearch-verification.json).
- **Network witnesses passed**: main-store proof, two-of-three availability, one-of-three refusal, restart/catch-up with three votes and conflict rejection. The tested four-worker aggregate root is in the report. Separate processes/keys, same physical host. [Report](witness-verification.json).
- **Worker experiment passed** at 1/2/4 processes with 2,000 events each: all raw hashes and shard proofs checked; committed-offset resume wrote no new records. [1 worker](scale-benchmark-1.json), [2 workers](scale-benchmark-2.json), [4 workers](scale-benchmark-4.json).
- **WASM attack tests passed**: eleven attacks/boundaries, with per-test commands in [SECURITY-EVIDENCE](SECURITY-EVIDENCE.md).
- **Drift workflow passed** in a test and the real UI: constructed FortiGate timestamp-unit variant quarantined, reviewed, approved, replayed to revision 2; original hash unchanged and proof valid. [Report](drift-verification.json).
- **120-second socket runs completed** through the actual application, with four concurrent senders. At 500 TCP events/s, 60,000/60,000 records were durably received. Overload runs show backpressure/backlog; TLS had 75 unreceived records at the drain deadline. These findings are published, not rounded away. [README tables](../README.md#measured-results).
- Full public archive acquisition completed for the requested six dataset families. Full-file built-in registry coverage is recorded in [coverage.json](coverage.json), with source hashes in [dataset-manifest.json](dataset-manifest.json). This is adapter dry-run coverage, not detection accuracy.
- Submission description is exactly **40,000 Unicode characters** with spaces and LF line breaks, below the stated 50,000-character limit. Title is separate.

## Artifact scope

The refreshed five-slide deck uses current screenshots and explicit shipped/pending boundaries. The MP4 is exactly two minutes: 30 seconds of slides and 90 seconds of current application interaction, with visible captions and no narration audio. The separate drift clip is an excerpt of the same workflow. Synthetic and constructed-fixture labels remain visible.

## Limits that remain

No billion-events/day, 24-hour sustained capacity, replicated cluster, independent-machine witness custody, full OCSF conformance, trained attack ML, WORM storage or enterprise RBAC is certified. The separate scale lab is not connected to the dashboard or its parser-review registry. Corpus coverage remains zero for several unsupported families. The TLS discrepancy warrants a dedicated sender/receiver shutdown and drain investigation before a lossless transport claim.

Earlier team documentation reports physical firewall connectivity, but no model, firmware and captured acceptance report was supplied for independent review. Physically air-gapped operation also remains a target-deployment acceptance task. Hosted CI is pending: GitHub rejected workflow creation because the saved token lacks workflow permission. The workflow is supplied as `docs/ci/docker.yml` for maintainer installation; a local pass is not represented as a hosted CI pass.
