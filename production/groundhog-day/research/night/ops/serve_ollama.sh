#!/usr/bin/env bash
set -euo pipefail
mkdir -p /workspace/out /workspace/models /workspace/runtime
cd /workspace/runtime
source_url="https://github.com/ollama/ollama/releases/download/v0.40.17/ollama-linux-amd64.tar.zst"
curl -fL --retry 3 --retry-delay 2 -o ollama.tar.zst "$source_url"
if [[ -n "${RUNTIME_SHA:-}" ]]; then echo "$RUNTIME_SHA  ollama.tar.zst" | sha256sum -c -; fi
tar --zstd -xf ollama.tar.zst
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS=/workspace/models
export OLLAMA_NUM_PARALLEL=3
export OLLAMA_CONTEXT_LENGTH=8192
export OLLAMA_KEEP_ALIVE=30m
export PATH="/workspace/runtime/bin:$PATH"
nohup ollama serve >/workspace/out/ollama-server.log 2>&1 </dev/null &
for n in $(seq 1 45); do
  if curl --fail --silent http://127.0.0.1:11434/api/version; then break; fi
  sleep 2
done
curl -fsS --max-time 1200 http://127.0.0.1:11434/api/pull -H 'Content-Type: application/json' -d '{"model":"qwen3.8:27b","stream":false}'
curl -fsS http://127.0.0.1:11434/api/tags >/workspace/out/models.json
echo model-ready
