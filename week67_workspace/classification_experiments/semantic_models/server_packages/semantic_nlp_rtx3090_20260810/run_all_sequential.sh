#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
RUN_GROUP="${1:?Usage: bash run_all_sequential.sh <run_group> [physical_gpu_id]}"
GPU_ID="${2:-0}"
if [[ ! "$GPU_ID" =~ ^[0-9]+$ ]]; then
  echo "Physical GPU ID must be one non-negative integer: $GPU_ID" >&2
  exit 2
fi
if [[ ! "$RUN_GROUP" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run group: $RUN_GROUP" >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
while IFS= read -r MODEL_KEY; do
  bash run_with_exit_status.sh "$MODEL_KEY" "${RUN_GROUP}_${MODEL_KEY}" "$GPU_ID"
done < <("$PYTHON_BIN" registry_tool.py keys)
echo "All registered formal runs completed."
