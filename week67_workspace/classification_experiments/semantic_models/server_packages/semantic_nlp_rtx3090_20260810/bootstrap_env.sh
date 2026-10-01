#!/usr/bin/env bash
set -euo pipefail

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_ROOT"

BOOTSTRAP_PYTHON="${BOOTSTRAP_PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$PACKAGE_ROOT/.venv}"

"$BOOTSTRAP_PYTHON" - <<'PY'
import sys
if not ((3, 10) <= sys.version_info[:2] <= (3, 12)):
    raise SystemExit(f"Python 3.10-3.12 is required; found {sys.version.split()[0]}")
print(f"Bootstrap Python: {sys.version.split()[0]}")
PY

if [[ ! -d "$VENV_DIR" ]]; then
  "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip

# DeBERTa-v3-small is distributed as a PyTorch .bin checkpoint. Transformers
# requires torch>=2.6 for safe loading. CUDA 12.4 wheels are compatible with
# the audited RTX 3090 server driver (580.x) and keep this environment isolated
# from the server's older base environment.
python -m pip install --upgrade "torch==2.6.0" --index-url https://download.pytorch.org/whl/cu124
python -m pip install -r requirements-gpu.txt

python check_gpu.py --gpu-id 0
echo "Environment ready. Activate with: source '$VENV_DIR/bin/activate'"
