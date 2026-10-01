#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
while IFS= read -r MODEL_KEY; do
  bash prefetch_model.sh "$MODEL_KEY"
done < <("$PYTHON_BIN" registry_tool.py keys)
echo "All pinned models were prefetched and locked."
