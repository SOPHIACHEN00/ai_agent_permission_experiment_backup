#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
MODEL_KEY="${1:?Usage: bash start_tmux.sh <model_key> <run_id> [physical_gpu_id]}"
RUN_ID="${2:?Usage: bash start_tmux.sh <model_key> <run_id> [physical_gpu_id]}"
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
SESSION="semantic_${RUN_ID//[^A-Za-z0-9_]/_}"
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session already exists: $SESSION" >&2
  exit 2
fi
tmux new-session -d -s "$SESSION" \
  "cd '$PACKAGE_ROOT' && bash run_with_exit_status.sh '$MODEL_KEY' '$RUN_ID' '$GPU_ID'"
echo "Detached tmux session started: $SESSION"
echo "Inspect without attaching: tmux capture-pane -pt '$SESSION' | tail -n 30"
echo "Attach: tmux attach -t '$SESSION'  (detach with Ctrl-b, then d)"
