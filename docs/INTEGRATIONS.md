# Reproducible integration experiments

Use disposable data for acceptance tests. The dashboard continues to use SQLite. Optional services below are local lab dependencies, never required by the core application. Transfer their images before air-gapped deployment.

## Docker core acceptance

```sh
docker compose up --build -d
python scripts/verify_docker.py --container "$(docker compose ps -q logflux)" --api http://127.0.0.1:8765 --port 5514
```

This verifies authenticated ingestion, original bytes, TCP/UDP receipt, sealing, and proof verification after restarting the container. It writes `docs/docker-verification.json`. Restart only a test deployment. The [CI template](ci/README.md) repeats it in GitHub Actions once a maintainer installs it. The saved token could not create workflows, so hosted CI is pending; a local pass is not a CI pass.

For bounded single-node socket concurrency, set `LOGFLUX_RECEIVER_WORKERS=2` (or another value from 1 to 32) before starting Compose. The value controls UDP queue consumers and is reported by `GET /api/status`; it does not turn SQLite into a distributed or highly available store. Measure write contention before increasing it.

## Elasticsearch Bulk output

Choose **System & Outputs → Add output → Elasticsearch Bulk**, enter the server base URL (not `/_bulk`) and a lowercase index name. Only new normalized revisions are queued after registration. Existing backlog is not automatically exported.

Set `LOGFLUX_ELASTIC_API_KEY_FILE` to a private file containing the base64 API-key credential when authentication is needed. Authenticated delivery requires HTTPS with a trusted certificate. The server process reads this file; no key appears in the UI or sink URL. The environment setting applies to all Elasticsearch sinks, so distinct credentials per sink remain future work.

Every event/revision uses a stable document ID. An HTTP 200 with a failed Bulk item stays pending and retries. Elasticsearch sees a conservative ECS projection plus the complete normalized LOGFLUX event. Exact raw bytes remain retrievable from LOGFLUX; this connector is not a raw-evidence backup. No native Splunk HEC or S3 connector is claimed.

## Redpanda / ClickHouse experiment

Set a private `LOGFLUX_LAB_PASSWORD` in your environment, then:

```sh
docker compose -p logflux-scale -f lab/compose.scale.yml up -d
python lab/scale_pipeline.py --events 2000 --workers 1 --output docs/scale-benchmark-1.json
python lab/scale_pipeline.py --events 2000 --workers 2 --output docs/scale-benchmark-2.json
python lab/scale_pipeline.py --events 2000 --workers 4 --output docs/scale-benchmark-4.json
```

The experiment uses a four-partition Redpanda topic, static partition ownership and separate Python processes. Raw bytes travel as Base64 with their hash. ClickHouse acknowledges a batch before each worker atomically commits its local offset. A restart resumes from those offsets. ReplacingMergeTree with `FINAL` gives logical deduplication by run/event ID; this is at-least-once delivery, not exactly-once execution. Each run creates a fresh topic; remove lab resources after testing to reclaim disk.

Each worker seals batch manifests into Merkle trees. Aggregation creates a higher-level tree of batch roots. The final verifier checks every raw hash, normalized hash and inclusion proof. Throughput timing includes worker startup, broker reads, normalization, Merkle creation, columnar insertion and offset commits. Producer time is separate; final verification and root aggregation are outside worker throughput timing. Compare identical event counts and retain all results, including regressions.

This is separate from the dashboard's SQLite store and parser registry. One broker and one ClickHouse node do not demonstrate a replicated cluster, HA, WORM storage, dynamic worker reassignment or enterprise capacity.

## Network witness services

Each witness needs its own private directory and signing key. Generate a random bearer secret of at least 24 characters and distribute it privately to the authorized coordinator and witnesses. Do not put credentials in Git.

```sh
python -m ulpf.witness_service --directory /private/witness1 --name witness1 --token-file /private/witness-token --port 9101
```

For a different machine, specify `--host`, `--cert` and `--key`; remote binding requires TLS. The coordinator verifies certificates through the system trust store and pins distinct Ed25519 public keys. Fetch a witness's authenticated `/state` through a trusted administrative channel to establish the initial pin. A key included in untrusted evidence is not an independent trust anchor.

Set `LOGFLUX_WITNESS_CONFIG` to a private JSON file:

```json
{
  "token_file": "/private/witness-token",
  "witnesses": [
    {"name":"w1","url":"https://w1.example:9101","public_key":"BASE64_PUBLIC_KEY_1"},
    {"name":"w2","url":"https://w2.example:9102","public_key":"BASE64_PUBLIC_KEY_2"},
    {"name":"w3","url":"https://w3.example:9103","public_key":"BASE64_PUBLIC_KEY_3"}
  ]
}
```

Start a **fresh data directory** when switching trust sets. Existing batches signed by different keys cause startup rejection; the system does not silently reinterpret historical trust. Requests run concurrently, require two valid signatures, catch up missing ordered checkpoints and reject conflicts. The status page reports configured network services, not an unmeasured live availability claim.

Run `python scripts/verify_remote_witnesses.py` for the three-process outage/restart/conflict test. Pass `--aggregate-root HEX_ROOT` from a scale result to anchor that aggregate root. Separate processes on one computer share an administrator and failure domain, so independent custody still requires separately administered machines.

## Verify with one witness offline

Export an event's `/api/events/{id}/proof` JSON and obtain one public key independently. Then:

```sh
python scripts/verify_witness_proof.py proof.json --public-key-file witness-public.txt
```

This checks the Merkle inclusion path and that one witness signed the checkpoint. It explicitly reports `quorum_verified: false`; it does not prove two-of-three agreement or verify raw bytes without the original event. Full event verification remains available through the application.

## Dataset coverage and live replay

```sh
python scripts/fetch_datasets.py
python scripts/measure_coverage.py --manifest docs/dataset-manifest.json
python scripts/send_logs.py data/datasets/honeynet30/extracted/capture.log --transport tcp --port 5514 --rate 100
```

Dataset acquisition is optional and online; everything after staging can run offline. Downloaded archives and logs stay under ignored `data/`. The manifest records source URLs and hashes. Complete corpora are used; unavailable downloads are reported rather than replaced by 2,000-line samples. Respect publisher terms and do not redistribute raw corpora in the submission.

Coverage is a full-file **built-in registry dry-run**, excluding learned plugins, drift history and storage. It reports metadata lines separately, and counts every event as normalized, partial, discovery-eligible or failed. It is not semantic ground-truth accuracy or full live-pipeline coverage. The separate replay command retains line terminators and uses octet-counted TCP/TLS framing. Register replay/lab attribution appropriately before sending archived data.

## Sustained network benchmark

```sh
python scripts/benchmark_sustained.py --rates 2000 4000 8000 16000 --seconds 120
python scripts/benchmark_sustained.py --transport udp --rates 500 2000 --seconds 120 --output docs/benchmark-udp.json
```

Each run creates an isolated collector with a temporary database. Four independent connections offer synthetic events for the requested duration; actual writes may be slower under backpressure. Both sender and receiver share the test computer. Receipts during the load window and receipts after a 15-second drain are separate. Unreceived at that deadline may include queued data, so it is not automatically proven permanent transport loss. Failed send calls have an uncertain final frame and are counted separately. The collector is stopped after the measurement.

For TLS, supply `--cert`, `--key` and `--ca` for a certificate valid for localhost. This option verifies the certificate; it does not disable TLS checks. Daily event numbers are arithmetic projections from the measured window, never a 24-hour capacity test.

Protocol references: [Elastic Bulk API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk), [Redpanda HTTP Proxy](https://docs.redpanda.com/streaming/current/develop/http-proxy/), [ClickHouse HTTP interface](https://github.com/ClickHouse/clickhouse-docs/blob/main/docs/integrations/interfaces/http.md).
