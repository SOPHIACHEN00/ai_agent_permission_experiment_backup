"""Fail-fast environment and dataset check for the semantic NLP GPU package."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
from pathlib import Path

import numpy
import pandas
import sentencepiece
import tokenizers
import torch
import transformers
from packaging.version import Version


PACKAGE_ROOT = Path(__file__).resolve().parent
DATA_PATH = (
    PACKAGE_ROOT
    / "ai_agent_permission_experiment"
    / "data"
    / "processed"
    / "four_label_dataset.csv"
)
REGISTRY_PATH = PACKAGE_ROOT / "model_registry.json"
RUNNER_PATH = PACKAGE_ROOT / "ai_agent_permission_experiment" / "src" / "run_transformer_four_label.py"
EXPECTED_DATASET_SHA256 = "4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_registry() -> int:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if payload.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
        raise SystemExit("ERROR: model registry dataset SHA does not match the canonical dataset.")
    models = payload.get("models")
    if not isinstance(models, dict) or len(models) != 3:
        raise SystemExit("ERROR: expected exactly three registered models.")
    for key, model in models.items():
        if re.fullmatch(r"[a-z0-9][a-z0-9_]{1,63}", key) is None:
            raise SystemExit(f"ERROR: unsafe model key in registry: {key!r}")
        if re.fullmatch(r"[0-9a-f]{40}", str(model.get("revision", ""))) is None:
            raise SystemExit(f"ERROR: model {key!r} is not pinned to a full commit.")
    return len(models)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-id", type=int, default=0, help="Visible CUDA device index to test.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"python: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")
    print(f"torch: {torch.__version__}")
    print(f"torch_cuda_runtime: {torch.version.cuda}")
    print(f"transformers: {transformers.__version__}")
    print(f"tokenizers: {tokenizers.__version__}")
    print(f"sentencepiece: {sentencepiece.__version__}")
    print(f"protobuf: {importlib.metadata.version('protobuf')}")
    print(f"numpy: {numpy.__version__}")
    print(f"pandas: {pandas.__version__}")
    if Version(torch.__version__.split("+", 1)[0]) < Version("2.6"):
        raise SystemExit(
            "ERROR: torch>=2.6 is required to safely load the official DeBERTa .bin checkpoint. "
            "Create the isolated environment with bootstrap_env.sh; do not bypass this check."
        )
    print(f"cuda_available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        raise SystemExit("ERROR: CUDA is unavailable; install the CUDA PyTorch wheel.")
    if args.gpu_id < 0 or args.gpu_id >= torch.cuda.device_count():
        raise SystemExit(
            f"ERROR: GPU index {args.gpu_id} is invalid; visible devices={torch.cuda.device_count()}."
        )
    torch.cuda.set_device(args.gpu_id)
    properties = torch.cuda.get_device_properties(args.gpu_id)
    print(f"cuda_device_count: {torch.cuda.device_count()}")
    print(f"cuda_device_index: {args.gpu_id}")
    print(f"cuda_device_name: {properties.name}")
    print(f"compute_capability: {properties.major}.{properties.minor}")
    print(f"gpu_memory_gib: {properties.total_memory / 1024**3:.2f}")
    if not DATA_PATH.is_file() or not RUNNER_PATH.is_file():
        raise SystemExit("ERROR: package runner or canonical dataset is missing.")
    dataset_hash = sha256_file(DATA_PATH)
    print(f"dataset_sha256: {dataset_hash}")
    if dataset_hash != EXPECTED_DATASET_SHA256:
        raise SystemExit("ERROR: canonical dataset SHA256 mismatch.")
    print(f"registered_models: {validate_registry()}")
    device = torch.device("cuda", args.gpu_id)
    left = torch.randn((1024, 1024), device=device, dtype=torch.float16)
    right = torch.randn((1024, 1024), device=device, dtype=torch.float16)
    product = left @ right
    torch.cuda.synchronize(device)
    if product.device.type != "cuda" or product.dtype != torch.float16:
        raise SystemExit("ERROR: CUDA FP16 matrix multiplication did not execute correctly.")
    if not bool(torch.isfinite(product).all().item()):
        raise SystemExit("ERROR: CUDA FP16 matrix multiplication produced non-finite values.")
    print("cuda_fp16_matmul: OK")
    print("Semantic NLP GPU package preflight: PASS")


if __name__ == "__main__":
    main()
