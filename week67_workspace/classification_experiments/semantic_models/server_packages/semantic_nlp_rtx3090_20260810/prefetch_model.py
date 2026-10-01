"""Download and validate one pinned model, then write a cache lock file."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import transformers
from transformers import AutoModelForSequenceClassification, AutoTokenizer


PACKAGE_ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = PACKAGE_ROOT / "model_registry.json"
HF_HOME_ROOT = PACKAGE_ROOT / "hf_cache"
HF_HUB_CACHE = HF_HOME_ROOT / "hub"
LOCK_DIR = PACKAGE_ROOT / "model_locks"
LABELS = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_config(model_key: str) -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    models = registry["models"]
    if model_key not in models:
        raise SystemExit(f"Unknown model key {model_key!r}; valid keys: {', '.join(models)}")
    config = models[model_key]
    if re.fullmatch(r"[0-9a-f]{40}", config["revision"]) is None:
        raise SystemExit(f"Model {model_key!r} is not pinned to a full commit.")
    return config


def snapshot_path(model_name: str, commit: str) -> Path:
    repo_dir = HF_HUB_CACHE / ("models--" + model_name.replace("/", "--"))
    return repo_dir / "snapshots" / commit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_key")
    args = parser.parse_args()

    config = load_model_config(args.model_key)
    model_name = config["model_name"]
    revision = config["revision"]
    HF_HUB_CACHE.mkdir(parents=True, exist_ok=True)
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(HF_HOME_ROOT)
    os.environ["HF_HUB_CACHE"] = str(HF_HUB_CACHE)

    print(f"Downloading tokenizer: {model_name}@{revision}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        revision=revision,
        cache_dir=HF_HUB_CACHE,
        local_files_only=False,
        trust_remote_code=False,
        use_fast=True,
    )
    print(f"Downloading/loading model: {model_name}@{revision}", flush=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        revision=revision,
        cache_dir=HF_HUB_CACHE,
        local_files_only=False,
        trust_remote_code=False,
        num_labels=4,
        id2label=LABELS,
        label2id={text: label for label, text in LABELS.items()},
    )
    resolved_commit = getattr(model.config, "_commit_hash", None)
    if resolved_commit != revision:
        raise RuntimeError(
            f"Resolved model commit mismatch: requested {revision}, resolved {resolved_commit!r}"
        )
    parameters = int(sum(parameter.numel() for parameter in model.parameters()))
    model_class = model.__class__.__name__
    tokenizer_class = tokenizer.__class__.__name__
    del model
    gc.collect()

    snapshot = snapshot_path(model_name, revision)
    if not snapshot.is_dir():
        raise FileNotFoundError(f"Expected Hugging Face snapshot directory is missing: {snapshot}")
    files = []
    for path in sorted(snapshot.rglob("*")):
        if not path.is_file():
            continue
        files.append(
            {
                "relative_path": path.relative_to(snapshot).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    lock = {
        "status": "prefetch_completed",
        "model_key": args.model_key,
        "model_id": config["model_id"],
        "model_name": model_name,
        "requested_revision": revision,
        "resolved_commit": resolved_commit,
        "model_class": model_class,
        "tokenizer_class": tokenizer_class,
        "parameter_count": parameters,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "snapshot_path": str(snapshot),
        "snapshot_file_count": len(files),
        "snapshot_total_bytes": sum(item["bytes"] for item in files),
        "snapshot_files": files,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    lock_path = LOCK_DIR / f"{args.model_key}.json"
    lock_path.write_text(
        json.dumps(lock, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Prefetch PASS: {lock_path}", flush=True)


if __name__ == "__main__":
    main()
