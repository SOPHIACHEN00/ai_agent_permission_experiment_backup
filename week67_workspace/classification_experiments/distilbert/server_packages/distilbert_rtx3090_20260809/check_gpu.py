"""Fail-fast CUDA check for the DistilBERT server package."""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path

import numpy
import pandas
import tokenizers
import torch
import transformers


EXPECTED_DATASET_SHA256 = "4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463"
DATA_PATH = (
    Path(__file__).resolve().parent
    / "ai_agent_permission_experiment"
    / "data"
    / "processed"
    / "four_label_dataset.csv"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    print(f"python: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")
    print(f"torch: {torch.__version__}")
    print(f"torch_cuda_runtime: {torch.version.cuda}")
    print(f"transformers: {transformers.__version__}")
    print(f"tokenizers: {tokenizers.__version__}")
    print(f"numpy: {numpy.__version__}")
    print(f"pandas: {pandas.__version__}")
    print(f"cuda_available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        raise SystemExit(
            "ERROR: CUDA is unavailable. Install a CUDA-enabled PyTorch build before training."
        )

    index = torch.cuda.current_device()
    properties = torch.cuda.get_device_properties(index)
    print(f"cuda_device_index: {index}")
    print(f"cuda_device_name: {properties.name}")
    print(f"compute_capability: {properties.major}.{properties.minor}")
    print(f"gpu_memory_gib: {properties.total_memory / 1024**3:.2f}")

    dataset_hash = sha256_file(DATA_PATH)
    print(f"dataset_sha256: {dataset_hash}")
    if dataset_hash != EXPECTED_DATASET_SHA256:
        raise SystemExit("ERROR: canonical dataset SHA256 mismatch.")

    device = torch.device("cuda", index)
    left = torch.randn((1024, 1024), device=device, dtype=torch.float16)
    right = torch.randn((1024, 1024), device=device, dtype=torch.float16)
    product = left @ right
    torch.cuda.synchronize(device)
    if product.device.type != "cuda" or product.dtype != torch.float16:
        raise SystemExit("ERROR: CUDA FP16 matrix multiplication did not run as expected.")
    if not bool(torch.isfinite(product).all().item()):
        raise SystemExit("ERROR: CUDA FP16 matrix multiplication produced non-finite values.")
    print("cuda_fp16_matmul: OK")
    print("GPU package preflight: PASS")


if __name__ == "__main__":
    main()

