# Broker-backed scalable ingestion

The repository now includes an opt-in TCP gateway at `scripts/broker_gateway.py`.
It accepts RFC 6587 octet-counted frames, computes SHA-256 over the exact bytes,
and publishes bounded batches to Redpanda's Kafka-compatible REST API. The
socket process does not write SQLite; Redpanda is the durable burst buffer.

```sh
docker compose -p logflux-scale -f lab/compose.scale.yml up -d
python scripts/broker_gateway.py --broker http://127.0.0.1:18082 --topic logflux-live --port 5516
```

The envelope contains the raw bytes as Base64, the raw hash, sender peer,
receipt timestamp and framing. A batch is removed from the gateway's bounded
queue only after Redpanda acknowledges it. This makes backpressure visible and
prevents silent socket-process drops. UDP is deliberately not routed through
this gateway: UDP remains best effort unless a sender uses TCP/TLS.

The existing `lab/scale_pipeline.py` remains the verified worker/evidence
experiment. Wiring its consumer directly to the live gateway is the next
acceptance step: workers must write raw envelopes to the shared evidence vault,
seal Merkle batches, and call the configured witness quorum before this mode can
replace the dashboard's SQLite path. Until that acceptance is complete, the
gateway is experimental and does not change the dashboard's storage guarantee.

Trade-offs: batching improves throughput and removes SQLite contention, but
Redpanda durability depends on broker replication and its acknowledgement mode;
the gateway therefore reports broker acceptance, not witness-signed evidence.
Witness signing remains downstream of durable worker writes. A 15,000 events/s
claim requires a 60-second run that reports offered, broker-accepted, evidence-
committed and witness-anchored counts separately.
