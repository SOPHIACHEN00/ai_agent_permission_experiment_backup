#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

MODEL_KEY="${1:?Usage: bash run_model_gpu.sh <model_key> <run_id> [physical_gpu_id]}"
RUN_ID="${2:?Usage: bash run_model_gpu.sh <model_key> <run_id> [physical_gpu_id]}"
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

MODEL_ID="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" model_id)"
MODEL_NAME="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" model_name)"
MODEL_REVISION="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" revision)"
REGISTRY_TRAIN_BATCH_SIZE="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" train_batch_size)"
REGISTRY_EVAL_BATCH_SIZE="$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" eval_batch_size)"
TRAIN_BATCH_SIZE="${TRAIN_BATCH_SIZE_OVERRIDE:-$REGISTRY_TRAIN_BATCH_SIZE}"
EVAL_BATCH_SIZE="${EVAL_BATCH_SIZE_OVERRIDE:-$REGISTRY_EVAL_BATCH_SIZE}"
if [[ ! "$TRAIN_BATCH_SIZE" =~ ^[1-9][0-9]*$ || ! "$EVAL_BATCH_SIZE" =~ ^[1-9][0-9]*$ ]]; then
  echo "Batch-size overrides must be positive integers." >&2
  exit 2
fi
read -r -a LEARNING_RATES <<< "$("$PYTHON_BIN" registry_tool.py get "$MODEL_KEY" learning_rates)"
read -r -a LOSS_WEIGHTINGS <<< "$("$PYTHON_BIN" registry_tool.py get-common loss_weightings)"
MAX_EPOCHS="$("$PYTHON_BIN" registry_tool.py get-common max_epochs)"
PATIENCE="$("$PYTHON_BIN" registry_tool.py get-common early_stopping_patience)"
MAX_LENGTH="$("$PYTHON_BIN" registry_tool.py get-common max_length)"
SEED="$("$PYTHON_BIN" registry_tool.py get-common seed)"
VALIDATION_SEED="$("$PYTHON_BIN" registry_tool.py get-common validation_seed)"
TORCH_THREADS="$("$PYTHON_BIN" registry_tool.py get-common torch_threads)"
WEIGHT_DECAY="$("$PYTHON_BIN" registry_tool.py get-common weight_decay)"
WARMUP_RATIO="$("$PYTHON_BIN" registry_tool.py get-common warmup_ratio)"
MAX_GRAD_NORM="$("$PYTHON_BIN" registry_tool.py get-common max_grad_norm)"
MIXED_PRECISION="$("$PYTHON_BIN" registry_tool.py get-common mixed_precision)"
ALLOW_TF32="$("$PYTHON_BIN" registry_tool.py get-common allow_tf32)"
SAVE_FINAL_MODEL="$("$PYTHON_BIN" registry_tool.py get-common save_final_model)"
TF32_FLAG="--no-allow-tf32"
[[ "$ALLOW_TF32" == "true" ]] && TF32_FLAG="--allow-tf32"
SAVE_FLAG="--no-save-final-model"
[[ "$SAVE_FINAL_MODEL" == "true" ]] && SAVE_FLAG="--save-final-model"

LOCK_FILE="$PACKAGE_ROOT/model_locks/${MODEL_KEY}.json"
OUT_DIR="$PACKAGE_ROOT/outputs/$RUN_ID"
LOG_FILE="$PACKAGE_ROOT/logs/$RUN_ID.log"
EXIT_FILE="$PACKAGE_ROOT/pids/$RUN_ID.exit_code"
mkdir -p outputs logs pids
if [[ ! -f "$LOCK_FILE" ]]; then
  echo "Pinned model is not prefetched: $LOCK_FILE" >&2
  echo "Run: bash prefetch_model.sh $MODEL_KEY" >&2
  exit 2
fi
"$PYTHON_BIN" verify_model_lock.py "$MODEL_KEY"
if [[ -e "$OUT_DIR" || -e "$LOG_FILE" || -e "$EXIT_FILE" ]]; then
  echo "Refusing to reuse run id or output/log path: $RUN_ID" >&2
  exit 2
fi

export HF_HOME="$PACKAGE_ROOT/hf_cache"
export HF_HUB_CACHE="$PACKAGE_ROOT/hf_cache/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export CUBLAS_WORKSPACE_CONFIG=:4096:8

echo "Model key: $MODEL_KEY"
echo "Model: $MODEL_NAME@$MODEL_REVISION"
echo "Run ID: $RUN_ID"
echo "Physical GPU ID: $GPU_ID (visible to PyTorch as cuda:0)"
echo "Train/eval batch: $TRAIN_BATCH_SIZE/$EVAL_BATCH_SIZE"
"$PYTHON_BIN" check_gpu.py --gpu-id 0

set +e
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
  --learning-rates "${LEARNING_RATES[@]}" \
  --loss-weightings "${LOSS_WEIGHTINGS[@]}" \
  --train-batch-size "$TRAIN_BATCH_SIZE" \
  --eval-batch-size "$EVAL_BATCH_SIZE" \
  --max-epochs "$MAX_EPOCHS" \
  --early-stopping-patience "$PATIENCE" \
  --weight-decay "$WEIGHT_DECAY" \
  --warmup-ratio "$WARMUP_RATIO" \
  --max-grad-norm "$MAX_GRAD_NORM" \
  --max-length "$MAX_LENGTH" \
  --torch-threads "$TORCH_THREADS" \
  --seed "$SEED" \
  --validation-seed "$VALIDATION_SEED" \
  "$SAVE_FLAG" \
  2>&1 | tee "$LOG_FILE"
RUN_CODE="${PIPESTATUS[0]}"
set -e
printf '%s\n' "$RUN_CODE" > "$EXIT_FILE"
if [[ "$RUN_CODE" -ne 0 ]]; then
  echo "Run failed with exit code $RUN_CODE; partial output is retained: $OUT_DIR" >&2
  exit "$RUN_CODE"
fi
echo "Formal run completed: $OUT_DIR"
