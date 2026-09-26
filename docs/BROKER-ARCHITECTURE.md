# Broker-backed scalable ingestion

The repository now includes an opt-in TCP gateway at `scripts/broker_gateway.py`.
It accepts RFC 6587 octet-counted frames, computes SHA-256 over the exact bytes,
and publishes bounded 5,000-record batches through four concurrent Redpanda
REST publishers by default. The
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

The 60-second acceptance run in `docs/benchmark-15k.json` sent 900,000 records
through this gateway, verified every raw hash, sealed 900 bounded Merkle batches
and collected three witness signatures with zero loss. The gateway remains an
opt-in scalable path; the dashboard's SQLite mode is unchanged, and production
deployment still needs replicated broker/storage nodes and independently
administered witnesses.

Trade-offs: batching improves throughput and removes SQLite contention, but
Redpanda durability depends on broker replication and its acknowledgement mode;
the gateway therefore reports broker acceptance, not witness-signed evidence.
Witness signing remains downstream of durable worker writes. A 15,000 events/s
claim requires a 60-second run that reports offered, broker-accepted, evidence-
committed and witness-anchored counts separately.
