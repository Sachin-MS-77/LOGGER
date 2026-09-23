# Teammate quick start

## Team

| Name | Role |
|---|---|
| **Praveena R K** | Team Lead · Architecture & System Design |
| **Sachin M** | Backend Developer · Security, Integrity & API |
| **Pavithra S** | Frontend Developer · UI/UX & Dashboard |
| **Madhusree S** | Data Pipeline · Parser Development & Testing |

Clone the repository or use GitHub's **Code → Download ZIP**, then extract it.

```sh
git clone https://github.com/Sachin-MS-77/LOGGER.git
cd LOGGER
```

Install Python 3.12 or newer first. Python 3.14 on macOS Apple Silicon is the tested platform. The initial dependency installation needs internet access. The repository does not contain the platform-specific offline wheelhouse or model weights.

## macOS / Linux

```sh
sh scripts/setup.sh
.venv/bin/python scripts/run.py
```

## Windows PowerShell

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe scripts\run.py
```

## Open and demonstrate

1. Keep the server terminal open and visit http://127.0.0.1:8765.
2. Open the newly generated `data/admin-token` file locally and paste its contents into the dashboard login. Each installation generates its own token. Do not commit or share that file.
3. Choose **Command center → Run demo replay** to populate the fresh database with labeled synthetic events.
4. Explore Event stream, Parser lab, Evidence vault and Investigation. Use **Obsidian** for the dark violet dashboard, or **Pearl** / **Rose** in the theme selector.

The dashboard and core workflow need no frontend build, cloud account or local language model. Manual parser review works immediately. For optional local AI, real-device connections, offline deployment and Docker instructions, see [README](../README.md). **Docker `docker build` and `docker compose up` are verified working.** Windows/Linux installations have not been validated on the build machine.

## Run the tests

From the repository root:

```sh
.venv/bin/python -m pytest tests -q
```

On Windows, use `.venv\Scripts\python.exe -m pytest tests -q`.

## Submission assets

- `docs/architecture.pdf`: two-page architecture
- `docs/LOGFLUX-final.pptx`: five-slide presentation
- `docs/LOGFLUX-demo.mp4`: 60-second screenshot walkthrough with selectable captions
- `docs/FEATURES.md`: implementation coverage and remaining work

No preloaded operational database, private signing keys, access tokens or local model weights are included. A fresh installation creates its own local data. Device logging must be configured explicitly; the synthetic demonstration is not evidence of physical hardware compatibility.
