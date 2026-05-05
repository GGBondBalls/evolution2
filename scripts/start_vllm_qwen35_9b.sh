#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/home/fyk/models/Qwen/Qwen3.5-9B}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3.5-9b}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.85}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
DTYPE="${DTYPE:-auto}"

if [[ ! -d "${MODEL_PATH}" ]]; then
  echo "Model path does not exist: ${MODEL_PATH}" >&2
  exit 2
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${PORT}$"; then
    echo "Port ${PORT} is already listening. Reuse that service or choose PORT=..." >&2
    exit 2
  fi
fi

echo "Starting vLLM OpenAI-compatible server"
echo "  model path: ${MODEL_PATH}"
echo "  served model: ${SERVED_MODEL_NAME}"
echo "  endpoint: http://${HOST}:${PORT}/v1"
echo "  CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-all visible GPUs}"

python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL_PATH}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --trust-remote-code \
  --dtype "${DTYPE}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  "$@"
