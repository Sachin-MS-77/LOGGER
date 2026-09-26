# LOGFLUX evidence response

This page prevents an old repository snapshot or an apples-to-oranges benchmark from being mistaken for the current submission. Every positive claim below points to a committed report or a command a reviewer can run.

The project has two deliberately separate data paths. The UI replay and throughput generator use synthetic fixtures so a judge can reproduce the demonstration. Dataset coverage and capture replay use downloaded public corpora; they are not synthetic substitutions. Raw files are ignored locally because the public archives are large and subject to their own redistribution terms.

| Concern | Current evidence | Boundary that remains |
|---|---|---|
| Throughput | The broker gateway sustained **15,000 durably verified events/s for 60 seconds**: 900,000/900,000, zero loss, Merkle batches and three witness signatures. | This is the single-broker evidence path; replicated production HA and multi-day capacity still require deployment acceptance. The older SQLite results remain historical comparisons. |
| Real data | `docs/coverage.json` records full-file scans for Linux, Apache, OpenSSH, Honeynet 30/34 and MACCDC 2012. | Coverage is adapter coverage, not detection accuracy; unsupported formats remain visible. |
| Real socket replay | `python scripts/send_logs.py <capture> --transport tcp --rate 100` streams an existing capture without rewriting bytes. | The receiving machine and device-specific acceptance still need to be chosen for a physical trial. |
| Docker | `docs/docker-verification.json` records local build, health, authenticated ingestion, exact raw bytes, TCP/UDP receipt and proof after restart. | Hosted Actions is pending because the available token cannot create workflows. |
| Integrity | `docs/witness-verification.json` records three separately keyed witness processes, outage/quorum behavior, restart/catch-up and conflicts. | They were exercised on one host; independent administration and physical custody require deployment on separate hosts. |
| Distributed scale | `lab/scale_pipeline.py` uses four Redpanda partitions, separate worker processes, ClickHouse writes, durable offsets, stable IDs and Merkle proofs. | The experiment is separate from the SQLite dashboard and has no HA or automatic reassignment. |
| Maturity | The current commit history contains the implementation, reports, tests and submission assets; the number of commits is not a functional acceptance criterion. | Production hardening still requires external deployment, device acceptance and long-duration operations. |

The additional 18,000-events/s stress run is recorded in [benchmark-18000-stress.json](benchmark-18000-stress.json). It offered 18,000 events/s but achieved 1,772 durable events/s during the 20-second window, with 33.8109% still unreceived after the drain deadline. This is useful capacity evidence precisely because it exposes the current backpressure boundary; it must not be rewritten as an 18,000-events/s result.

## Real-capture replay

After staging a corpus with `scripts/fetch_datasets.py`, replay one complete file through the actual TCP listener:

```sh
python scripts/send_logs.py data/datasets/honeynet30/extracted/capture.log \
  --host 127.0.0.1 --port 5514 --transport tcp --rate 100
```

The sender uses RFC 6587 octet-counted framing and preserves each line's bytes. For UDP, use `--transport udp`; for TLS, use `--transport tls --ca path/to/ca.pem`. Confirm durable receipt in `GET /api/stats`, then inspect raw bytes through the event API. The command is intentionally rate-limited so a reviewer can run it safely on a demo machine.
