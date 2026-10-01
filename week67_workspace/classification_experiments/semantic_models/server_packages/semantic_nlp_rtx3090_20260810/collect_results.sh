#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
RUN_ID="${1:?Usage: bash collect_results.sh <run_id> [--include-model]}"
MODE="${2:---exclude-model}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run id: $RUN_ID" >&2
  exit 2
fi
if [[ ! -d "outputs/$RUN_ID" || ! -f "logs/$RUN_ID.log" ]]; then
  echo "Run output or log is missing for $RUN_ID" >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
"$PYTHON_BIN" validate_completed_run.py "$RUN_ID"

mkdir -p return
SUFFIX="results_without_model"
TAR_EXCLUDES=("--exclude=outputs/$RUN_ID/final_model")
if [[ "$MODE" == "--include-model" ]]; then
  SUFFIX="results_with_model"
  TAR_EXCLUDES=()
elif [[ "$MODE" != "--exclude-model" ]]; then
  echo "Second argument must be --include-model or --exclude-model." >&2
  exit 2
fi
ARCHIVE="return/${RUN_ID}_${SUFFIX}.tar.gz"
PARTIAL="${ARCHIVE}.partial"
if [[ -e "$ARCHIVE" || -e "$PARTIAL" ]]; then
  echo "Refusing to overwrite return archive: $ARCHIVE" >&2
  exit 2
fi

INCLUDE_PATHS=(
  "outputs/$RUN_ID"
  "logs/$RUN_ID.log"
  "model_registry.json"
  "model_locks"
)
[[ -f "pids/$RUN_ID.exit_code" ]] && INCLUDE_PATHS+=("pids/$RUN_ID.exit_code")
[[ -f "logs/$RUN_ID.launcher.log" ]] && INCLUDE_PATHS+=("logs/$RUN_ID.launcher.log")
tar "${TAR_EXCLUDES[@]}" -czf "$PARTIAL" "${INCLUDE_PATHS[@]}"
mv "$PARTIAL" "$ARCHIVE"
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"
echo "Return archive: $ARCHIVE"
cat "${ARCHIVE}.sha256"
