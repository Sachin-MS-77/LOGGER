# LOGFLUX

**Universal Log Pre-processing Framework — SIH Problem Statement 26156**

**Joining the team? Start with [TEAM_SETUP.md](docs/TEAM_SETUP.md)** for clone/download, installation, login and demo instructions.

LOGFLUX is a working, single-node perimeter-log prototype. It receives real network messages, preserves the original bytes, normalizes supported formats, and sends unfamiliar structures through a reviewed parser workflow. The dashboard, API, evidence verification, parser signatures, local AI adapter and exports use real backend operations.

![LOGFLUX Command Center — live dashboard](docs/screenshots/command-center.png)

## Start

Requires Python 3.12+ (tested with Python 3.14 on Apple Silicon). Start with 4 GB RAM for collection; allow extra memory for a local model. No Node build or cloud account is needed.

macOS / Linux:

```sh
sh scripts/setup.sh
.venv/bin/python scripts/run.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python scripts\run.py
```

Open **http://127.0.0.1:8765**. Paste the token from `data/admin-token`. The browser keeps it only for its current session. Runtime data, private keys and tokens must stay out of source-control and submitted ZIP files.

For the already-installed demo on this computer, double-click **Start LOGFLUX.command** at the root of this project. It uses the prepared workspace runtime and preserved demo database. If moving the source elsewhere, use the installation steps above.

## Demonstrate the complete flow

1. **Command center → Launch demo:** inject 120 explicitly labeled synthetic events across five source families. Counters and graphs come from stored events.
2. **Event stream:** search, filter by source/status/traffic mode, pause refresh, inspect raw bytes beside normalized fields.
3. **Parser lab:** select the unfamiliar router format. Review the deterministic suggestion or request a **Local AI proposal**. `origin` is the source address and `target` is the destination in the included synthetic fixture.
4. Add semantic assertions for a displayed sample, then **Save & validate**. Review the results, enter your reviewer name and approve. Validation does not replace semantic review.
5. **Replay retained events:** a new normalized revision appears while the original byte hash stays unchanged. **New parser version** creates a draft without overwriting prior approval. The registry supports signed bundle import/export and activation/rollback.
6. **Trigger sample drift:** the changed FortiGate fixture enters review. Map `client_ip` and `server_ip`, validate, approve and replay.
7. **Evidence vault:** inspect an event and choose **Verify evidence**. Hash, manifest, Merkle path and quorum signatures are checked when requested.
8. **Investigation:** select an address, inspect its timeline and detections, and save a case. Shared IPs indicate observations, not a proven attack narrative.
9. **System & outputs:** export complete JSONL, an ECS projection, or CSV. Configure an HTTP collector to demonstrate the durable retry outbox.

## Connect a real firewall or router

A device must export logs. LOGFLUX cannot automatically understand every proprietary format or connect to devices with no accessible log interface.

Start the collector on the intended network interface:

```sh
LOGFLUX_SYSLOG_HOST=0.0.0.0 .venv/bin/python scripts/run.py
```

Keep the dashboard bound to loopback, or place an authenticated HTTPS reverse proxy in front of it. In the device's remote-log settings, choose the collector computer's LAN IP and TCP port **5514** or UDP port **5514**. Allow that port on the host firewall. Register the sender IP under **Sources**. Do not send to `127.0.0.1` from another machine.

TCP accepts RFC6587 octet-counted frames and newline frames. UDP is best effort: messages dropped before receipt cannot be recovered. HTTP upload supports exact single-message bytes or newline framing. Use `scripts/send_logs.py` to send a captured fixture with preserved bytes.

```sh
.venv/bin/python scripts/send_logs.py samples/perimeter.log --transport tcp
```

TLS with a certificate trusted by the sender:

```sh
LOGFLUX_SYSLOG_HOST=0.0.0.0 LOGFLUX_TLS_CERT=/path/server.pem \
LOGFLUX_TLS_KEY=/path/server.key .venv/bin/python scripts/run.py
```

TLS uses **6514**. Set `LOGFLUX_TLS_CA` to require client certificates. Device-specific configuration differs by model and firmware; verify one received event before presenting hardware compatibility.

Included adapters cover tested fixture subsets of FortiGate key/value, Cisco ASA deny messages, Suricata JSON, CEF, LEEF and pfSense CSV. Structural decoders also accept JSON, safe XML, headered CSV, Syslog wrappers, key/value and plain-text token templates. New signatures enter review. Binary/unparseable bytes remain in evidence with a failed status.

## Controlled socket lab

```sh
.venv/bin/python lab/socket_range.py --token-file data/admin-token --count 100
```

This sends synthetic firewall/router/IDS messages through real localhost TCP on the dedicated **5515** lab listener. It does not scan, exploit, emulate a physical firewall or create actual malicious traffic. `lab` and `replay` remain distinct from ordinary device traffic. A mixed-source lab stream can trigger conservative structure-drift review.

## Local AI

Local model proposals are optional. Manual/deterministic review works without a model. The included adapter supports Ollama and llama.cpp's local OpenAI-compatible endpoint. Default endpoint `http://127.0.0.1:11434`, model alias `qwen3:0.6b`.

For Ollama, stage its runtime and run `ollama pull qwen3:0.6b` while connected, then `ollama serve`. For llama.cpp, load the GGUF locally and use `--alias qwen3:0.6b`. Configure `LOGFLUX_LLM_URL`, `LOGFLUX_LLM_MODEL` and optionally `LOGFLUX_LLM_API_KEY_FILE`. Explicit private-host allowlisting uses `LOGFLUX_LLM_ALLOWED_HOSTS`. No cloud fallback exists.

On this demo computer, a Qwen3 0.6B GGUF and llama.cpp runtime are already staged in the workspace. **Start LOGFLUX.command** can start them. Model weights and the model executable are not included in the portable source ZIP. Transfer the model/runtime separately for another air-gapped computer.

AI output is constrained to known fields and checked against sample types. It cannot approve or deploy itself. The recorded local-model test demonstrates three rejected invalid fields. Model accuracy is not guaranteed.

## Air-gapped setup

On a connected machine matching the target's OS, CPU and Python version:

```sh
python scripts/prepare_offline.py
```

Transfer the source and `wheelhouse/`, a compatible Python installer and any optional model/runtime. On the isolated target, run `scripts/setup.sh`: it installs with `--no-index`. Verify the wheel hashes in `wheelhouse/manifest.json` against a trusted copy before transfer. The provided wheelhouse targets **macOS ARM64 / Python 3.14**, not Linux/Windows.

A fresh virtual environment was installed from these wheels without a package index, and all 48 tests passed there. An actual physically disconnected hardware-network test remains an evaluation step. The application serves all assets locally and makes outbound requests only to configured local AI or output endpoints.

## Container deployment

```sh
docker compose up --build
```

The image uses a non-root user, a writable data volume, a read-only root filesystem and no extra Linux capabilities. The dashboard is published on loopback. Syslog ports are exposed for devices. Stage images using `docker save` / `docker load` before isolation; a Docker build itself requires dependencies/base images unless already staged.

**The Docker daemon was unavailable on the build computer.** The configuration is included and statically checked, but an actual image build/run is not claimed.

## Tests and benchmark

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/benchmark.py --events 2000 --output docs/benchmark.json
```

The 48-test suite covers format adapters, random raw preservation, immutable evidence, malformed inputs, replay/semantic checks, parser revisions and rollback, signature trust, sandbox bounds, witness conflicts/catch-up, HTTP auth, real TCP/UDP/TLS sockets, source edits that preserve historical evidence, and HTTP retry idempotency. Two upstream test-library deprecation warnings remain.

Measured on this Mac: **2,000 events, 2,187.8 events/s, 0.08 ms p95 processing**, 1,600 normalized and 400 intentionally unknown, with a verified sealed proof. This sequential Store benchmark excludes network, LLM and concurrent UI. See `docs/benchmark.json` for precise scope. It does not establish sustained production throughput or billions/day.

## API and integrations

All `/api/*` routes require `Authorization: Bearer <token>`. `GET /health` is a shallow public health check. Useful routes:

- `POST /api/sources`, `POST /api/ingest`, `POST /api/upload`
- `GET /api/events`, `GET /api/events/{id}/raw`, `/proof`, `/provenance`
- `GET /api/export?format=jsonl|ecs|csv&offset=0` (maximum 1,000 per page; increment offset)
- `GET /api/candidates`, `PUT /api/candidates/{id}/mapping`, `POST .../validate`, `/approve`, `/replay`, `/revise`
- `GET /api/plugins`, `POST /api/plugins/import`, `POST /api/plugins/{id}/activate`
- `GET /api/metrics` (Prometheus text, authenticated)

HTTP outputs accept LOGFLUX JSON envelopes, use stable delivery IDs and retry with backoff. Receivers should deduplicate on `Idempotency-Key`. Delivery is at least once; it is not exactly once. Native Splunk/Elastic/Kafka/S3 integrations are not included. The ECS adapter is a projection; the canonical schema is LOGFLUX 1.0, not full OCSF conformance.

## Evidence and operating limits

Original event bytes commit before parsing. Normalized revisions are append-only. Evidence leaves commit to the event hash plus receipt/source/transport metadata. Three local Ed25519 witnesses sign ordered Merkle checkpoints with a quorum of two. These witnesses share one machine: this demonstrates signed permissioned checkpoints, not independent custody or a production BFT blockchain. SQLite immutability guards do not protect against a privileged attacker who controls files and all keys.

Wasmtime executes a bounded field-selection module, with no host imports, 64 KiB memory and 10,000 fuel. Trusted Python handles structural decoding. This is not arbitrary LLM-generated parser code running in WASI.

The prototype uses a single SQLite node. There is no Kafka/Flink cluster, object-store retention, independent remote ledger quorum, trained anomaly model, HA failover or RBAC. See `docs/FEATURES.md` for every original-plan item and its actual implementation boundary. Production-scale architecture is a documented next phase, not shipped infrastructure.

## Submission files

- `docs/architecture.pdf` — two pages
- `docs/LOGFLUX-SIH-final.pptx` — five slides, refreshed dashboard screenshots
- `docs/LOGFLUX-demo.mp4` — 60-second screenshot walkthrough with selectable English captions, no audio
- `docs/demo-script.md` — live presentation script
- `docs/FEATURES.md` — requirements and original-plan coverage
- `docs/test-results.xml`, `docs/benchmark.json` — reproducible evidence

The source ZIP is ready to upload to your own GitHub repository or Drive. No repository was published and no public submission URL was invented. Add the real share URL, team details and actual device models before submission.
