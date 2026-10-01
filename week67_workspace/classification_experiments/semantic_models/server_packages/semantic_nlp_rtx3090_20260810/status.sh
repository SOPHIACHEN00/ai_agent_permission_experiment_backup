#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
RUN_ID="${1:?Usage: bash status.sh <run_id>}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run id: $RUN_ID" >&2
  exit 2
fi
PID_FILE="pids/${RUN_ID}.launcher.pid"
EXIT_FILE="pids/${RUN_ID}.exit_code"
LOG_FILE="logs/${RUN_ID}.log"
LAUNCH_LOG="logs/${RUN_ID}.launcher.log"

if [[ -f "$EXIT_FILE" ]]; then
  CODE="$(tr -d '[:space:]' < "$EXIT_FILE")"
  if [[ "$CODE" == "0" ]]; then
    echo "status: completed"
  else
    echo "status: failed (exit code $CODE)"
  fi
elif [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "status: running (launcher PID $(cat "$PID_FILE"))"
else
  echo "status: not running or launcher state unknown"
fi

if [[ -f "$LOG_FILE" ]]; then
  echo "--- latest training log ---"
  tail -n 25 "$LOG_FILE"
elif [[ -f "$LAUNCH_LOG" ]]; then
  echo "--- latest launcher log ---"
  tail -n 25 "$LAUNCH_LOG"
else
  echo "No log found for $RUN_ID"
fi
