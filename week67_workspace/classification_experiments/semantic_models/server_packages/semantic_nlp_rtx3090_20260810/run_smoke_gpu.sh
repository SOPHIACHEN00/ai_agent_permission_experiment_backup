#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

MODEL_KEY="${1:?Usage: bash run_smoke_gpu.sh <model_key> [physical_gpu_id] [smoke_run_id]}"
GPU_ID="${2:-0}"
RUN_ID="${3:-smoke_${MODEL_KEY}_$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$GPU_ID" =~ ^[0-9]+$ ]]; then
  echo "Physical GPU ID must be one non-negative integer: $GPU_ID" >&2
  exit 2
fi
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Unsafe smoke run id: $RUN_ID" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-$PACKAGE_ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment not found: $PYTHON_BIN. Run bootstrap_env.sh first." >&2
  exit 2
fi
MODEL_ID="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" model_id)"
MODEL_NAME="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" model_name)"
MODEL_REVISION="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" revision)"
TRAIN_BATCH_SIZE="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" train_batch_size)"
EVAL_BATCH_SIZE="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" eval_batch_size)"
FIRST_LR="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" learning_rates | awk '{print $1}')"
MAX_LENGTH="$("$PYTHON_BIN" registry_tool.py get-common max_length)"
TORCH_THREADS="$("$PYTHON_BIN" registry_tool.py get-common torch_threads)"
SEED="$("$PYTHON_BIN" registry_tool.py get-common seed)"
VALIDATION_SEED="$("$PYTHON_BIN" registry_tool.py get-common validation_seed)"
MIXED_PRECISION="$("$PYTHON_BIN" registry_tool.py get-common mixed_precision)"
ALLOW_TF32="$("$PYTHON_BIN" registry_tool.py get-common allow_tf32)"
TF32_FLAG="--no-allow-tf32"
[[ "$ALLOW_TF32" == "true" ]] && TF32_FLAG="--allow-tf32"
OUT_DIR="$PACKAGE_ROOT/outputs/$RUN_ID"
LOG_FILE="$PACKAGE_ROOT/logs/$RUN_ID.log"
mkdir -p outputs logs
if [[ ! -f "$PACKAGE_ROOT/model_locks/${MODEL_KEY}.json" ]]; then
  echo "Run prefetch_model.sh $MODEL_KEY before smoke." >&2
  exit 2
fi
"$PYTHON_BIN" verify_model_lock.py "$MODEL_KEY"
if [[ -e "$OUT_DIR" || -e "$LOG_FILE" ]]; then
  echo "Refusing to reuse smoke run id: $RUN_ID" >&2
  exit 2
fi

export HF_HOME="$PACKAGE_ROOT/hf_cache"
export HF_HUB_CACHE="$PACKAGE_ROOT/hf_cache/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
"$PYTHON_BIN" check_gpu.py --gpu-id 0
"$PYTHON_BIN" -u ai_agent_permission_experiment/src/run_transformer_four_label.py \
  --data ai_agent_permission_experiment/data/processed/four_label_dataset.csv \
  --out "$OUT_DIR" \
  --model-id "$MODEL_ID" \
  --model-name "$MODEL_NAME" \
  --model-revision "$MODEL_REVISION" \
  --device cuda:0 \
  --mixed-precision "$MIXED_PRECISION" \
  "$TF32_FLAG" \
  --local-files-only \
  --learning-rates "$FIRST_LR" \
  --loss-weightings balanced \
  --train-batch-size "$TRAIN_BATCH_SIZE" \
  --eval-batch-size "$EVAL_BATCH_SIZE" \
  --max-length "$MAX_LENGTH" \
  --torch-threads "$TORCH_THREADS" \
  --seed "$SEED" \
  --validation-seed "$VALIDATION_SEED" \
  --smoke \
  --smoke-train-batches 2 \
  --smoke-eval-batches 2 \
  2>&1 | tee "$LOG_FILE"
echo "Smoke completed; this is not a reportable result: $OUT_DIR"
