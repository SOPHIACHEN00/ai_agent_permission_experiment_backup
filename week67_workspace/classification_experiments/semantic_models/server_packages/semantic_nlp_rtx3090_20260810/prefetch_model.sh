#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

MODEL_KEY="${1:?Usage: bash prefetch_model.sh <model_key>}"
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi

export HF_HOME="$PACKAGE_ROOT/hf_cache"
export HF_HUB_CACHE="$PACKAGE_ROOT/hf_cache/hub"
unset HF_HUB_OFFLINE TRANSFORMERS_OFFLINE
"$PYTHON_BIN" registry_tool.py show "$MODEL_KEY" >/dev/null
"$PYTHON_BIN" prefetch_model.py "$MODEL_KEY"
"$PYTHON_BIN" verify_model_lock.py "$MODEL_KEY"
