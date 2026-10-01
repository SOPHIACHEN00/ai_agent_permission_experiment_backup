#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python}"
RUN_ID="${1:-distilbert_rtx3090_$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_DIR="outputs/${RUN_ID}"
LOG_FILE="logs/${RUN_ID}.log"

mkdir -p outputs logs
if [[ -e "$OUT_DIR" ]]; then
  echo "Refusing to reuse output path: $OUT_DIR" >&2
  exit 2
fi

"$PYTHON_BIN" check_gpu.py
"$PYTHON_BIN" -u ai_agent_permission_experiment/src/run_distilbert_four_label.py \
  --data ai_agent_permission_experiment/data/processed/four_label_dataset.csv \
  --out "$OUT_DIR" \
  --model-name distilbert-base-uncased \
  --model-revision 12040accade4e8a0f71eabdb258fecc2e7e948be \
  --device cuda:0 \
  --mixed-precision fp16 \
  --allow-tf32 \
  --no-local-files-only \
  --learning-rates 2e-5 5e-5 \
  --loss-weightings balanced \
  --train-batch-size 32 \
  --eval-batch-size 64 \
  --max-epochs 2 \
  --early-stopping-patience 2 \
  --weight-decay 0.01 \
  --warmup-ratio 0.1 \
  --max-grad-norm 1.0 \
  --max-length 128 \
  --torch-threads 4 \
  --seed 42 \
  --validation-seed 20260809 \
  --save-final-model \
  2>&1 | tee "$LOG_FILE"

echo "Formal run completed: $OUT_DIR"

