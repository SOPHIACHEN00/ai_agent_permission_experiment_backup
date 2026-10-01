#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

MODEL_KEY="${1:?Usage: bash start_nohup.sh <model_key> <run_id> [physical_gpu_id]}"
RUN_ID="${2:?Usage: bash start_nohup.sh <model_key> <run_id> [physical_gpu_id]}"
GPU_ID="${3:-0}"
if [[ ! "$GPU_ID" =~ ^[0-9]+$ ]]; then
  echo "Physical GPU ID must be one non-negative integer: $GPU_ID" >&2
  exit 2
fi
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run id: $RUN_ID" >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
"$PYTHON_BIN" registry_tool.py show "$MODEL_KEY" >/dev/null
if [[ ! -f "model_locks/${MODEL_KEY}.json" ]]; then
  echo "Pinned model is not prefetched: model_locks/${MODEL_KEY}.json" >&2
  exit 2
fi
mkdir -p logs pids outputs
LAUNCH_LOG="logs/${RUN_ID}.launcher.log"
if [[ -e "outputs/$RUN_ID" || -e "logs/$RUN_ID.log" || -e "$LAUNCH_LOG" || \
      -e "pids/$RUN_ID.launcher.pid" || -e "pids/$RUN_ID.exit_code" ]]; then
  echo "Refusing to reuse run id: $RUN_ID" >&2
  exit 2
fi

nohup setsid bash "$PACKAGE_ROOT/run_with_exit_status.sh" "$MODEL_KEY" "$RUN_ID" "$GPU_ID" \
  >"$LAUNCH_LOG" 2>&1 </dev/null &
LAUNCHER_PID="$!"
printf '%s\n' "$LAUNCHER_PID" > "pids/${RUN_ID}.launcher.pid"
echo "Detached training started."
echo "Run ID: $RUN_ID"
echo "Launcher PID: $LAUNCHER_PID"
echo "Physical GPU: $GPU_ID"
echo "Status: bash status.sh $RUN_ID"
echo "Live log: bash follow_log.sh $RUN_ID"
