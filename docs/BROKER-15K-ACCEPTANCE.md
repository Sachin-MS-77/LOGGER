# Broker 15k acceptance

Run the scale services and gateway first:

```sh
docker compose -p logflux-scale -f lab/compose.scale.yml up -d
python scripts/broker_gateway.py --broker http://127.0.0.1:18082 --topic logflux-live --port 5516
python scripts/benchmark_broker_e2e.py --rate 15000 --seconds 60 --output docs/benchmark-15k.json
```

The benchmark sends real TCP frames for 60 seconds, reads the Redpanda topic,
recomputes every raw SHA-256, builds a Merkle root and anchors the checkpoint
with the existing three-witness ledger. It reports offered, sent, broker-observed
and verified counts separately. A passing witness result here proves the broker
evidence path; it does not silently promote the SQLite dashboard to HA.
