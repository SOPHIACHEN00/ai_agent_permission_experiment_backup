#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
GPU_ID="${1:-0}"
if [[ ! "$GPU_ID" =~ ^[0-9]+$ ]]; then
  echo "Physical GPU ID must be one non-negative integer: $GPU_ID" >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
while IFS= read -r MODEL_KEY; do
  RUN_ID="smoke_${MODEL_KEY}_$(date -u +%Y%m%dT%H%M%SZ)"
  bash run_smoke_gpu.sh "$MODEL_KEY" "$GPU_ID" "$RUN_ID"
done < <("$PYTHON_BIN" registry_tool.py keys)
echo "All three GPU smoke tests passed."
