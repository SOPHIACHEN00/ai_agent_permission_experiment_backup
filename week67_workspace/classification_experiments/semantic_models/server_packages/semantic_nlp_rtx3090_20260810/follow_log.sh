#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
RUN_ID="${1:?Usage: bash follow_log.sh <run_id>}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run id: $RUN_ID" >&2
  exit 2
fi
LOG_FILE="logs/${RUN_ID}.log"
if [[ ! -f "$LOG_FILE" ]]; then
  echo "Training log does not exist yet: $LOG_FILE" >&2
  exit 2
fi
echo "Following $LOG_FILE"
echo "Ctrl-C stops only this viewer; a run started by start_nohup.sh remains detached."
tail -F "$LOG_FILE"
