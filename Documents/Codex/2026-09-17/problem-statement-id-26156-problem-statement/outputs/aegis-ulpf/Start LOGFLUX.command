#!/bin/zsh
set -eu
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$PROJECT_DIR/../.." && pwd)"
if [ -x "$WORKSPACE_DIR/work/venv/bin/python" ]; then
  LOGFLUX_PYTHON="$WORKSPACE_DIR/work/venv/bin/python"
  export LOGFLUX_DATA_DIR="$WORKSPACE_DIR/work/runtime-data"
  export LOGFLUX_LLM_API_KEY_FILE="$LOGFLUX_DATA_DIR/admin-token"
  if ! /usr/bin/curl -sf http://127.0.0.1:11434/health >/dev/null 2>&1 && [ -x "$WORKSPACE_DIR/work/ollama-runtime/llama-server" ]; then
    "$WORKSPACE_DIR/work/ollama-runtime/llama-server" -m "$WORKSPACE_DIR/work/models/Qwen3-0.6B-Q8_0.gguf" --alias qwen3:0.6b --host 127.0.0.1 --port 11434 --ctx-size 4096 --threads 4 --device none --gpu-layers 0 --fit off --no-op-offload --no-kv-offload --reasoning off --no-webui --api-key-file "$LOGFLUX_LLM_API_KEY_FILE" > "$WORKSPACE_DIR/work/local-model.log" 2>&1 &
  fi
else
  LOGFLUX_PYTHON="$PROJECT_DIR/.venv/bin/python"
  if [ ! -x "$LOGFLUX_PYTHON" ]; then
    cd "$PROJECT_DIR"
    sh scripts/setup.sh
  fi
fi
if /usr/bin/curl -sf http://127.0.0.1:8765/health >/dev/null; then
  printf '\nLOGFLUX is already running: http://127.0.0.1:8765\n'
else
  "$LOGFLUX_PYTHON" "$PROJECT_DIR/scripts/run.py"
fi
