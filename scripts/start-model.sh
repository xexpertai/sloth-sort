#!/usr/bin/env bash
# Serve the open-weight model on 127.0.0.1:8187, CPU only, deliberately few threads (the sloth does not hurry).
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${LLAMA_TAG:-b11555}"; MODEL="${MODEL_FILE:-gemma-4-E2B-it-Q4_0.gguf}"
exec nice -n 10 ".tools/llama/llama-$TAG/llama-server" -m "models/$MODEL" --host 127.0.0.1 --port "${PORT:-8187}" \
  -c "${CTX:-2048}" -t "${THREADS:-4}" --jinja --reasoning off --no-webui
