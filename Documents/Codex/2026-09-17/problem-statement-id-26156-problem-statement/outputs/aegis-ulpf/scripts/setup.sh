#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
if [ -d wheelhouse ]; then
  .venv/bin/python -m pip install --no-index --find-links wheelhouse -r requirements.lock
else
  .venv/bin/python -m pip install -r requirements.lock
fi
printf '\nSetup complete. Start: .venv/bin/python scripts/run.py\n'
