#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
MODEL_KEY="${1:?Usage: bash run_with_exit_status.sh <model_key> <run_id> [physical_gpu_id]}"
RUN_ID="${2:?Usage: bash run_with_exit_status.sh <model_key> <run_id> [physical_gpu_id]}"
GPU_ID="${3:-0}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run id: $RUN_ID" >&2
  exit 2
fi
mkdir -p pids
EXIT_FILE="pids/${RUN_ID}.exit_code"

set +e
bash "$PACKAGE_ROOT/run_model_gpu.sh" "$MODEL_KEY" "$RUN_ID" "$GPU_ID"
RUN_CODE="$?"
set -e
if [[ ! -f "$EXIT_FILE" ]]; then
  printf '%s\n' "$RUN_CODE" > "$EXIT_FILE"
fi
exit "$RUN_CODE"
