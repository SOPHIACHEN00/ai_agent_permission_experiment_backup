#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"
RUN_GROUP="${1:?Usage: bash start_all_parallel_nohup.sh <run_group>}"
if [[ ! "$RUN_GROUP" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe run group: $RUN_GROUP" >&2
  exit 2
fi
if [[ "$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l)" -lt 3 ]]; then
  echo "At least three visible GPUs are required for the parallel launcher." >&2
  exit 2
fi

# Use one independent process per physical GPU. Run all three smoke tests first.
bash start_nohup.sh roberta_base "${RUN_GROUP}_roberta_base" 0
bash start_nohup.sh deberta_v3_small "${RUN_GROUP}_deberta_v3_small" 1
bash start_nohup.sh modernbert_base "${RUN_GROUP}_modernbert_base" 2
echo "Three isolated runs were launched on physical GPUs 0, 1, and 2."
