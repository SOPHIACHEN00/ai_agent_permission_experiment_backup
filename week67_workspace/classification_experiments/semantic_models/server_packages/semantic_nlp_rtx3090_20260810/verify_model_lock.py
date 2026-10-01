"""Verify one pinned Hugging Face snapshot against its generated model lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = PACKAGE_ROOT / "model_registry.json"
LOCK_DIR = PACKAGE_ROOT / "model_locks"
HF_HUB_CACHE = PACKAGE_ROOT / "hf_cache" / "hub"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_key")
    args = parser.parse_args()

    registry = load_json(REGISTRY_PATH)
    models = registry.get("models", {})
    if args.model_key not in models:
        raise SystemExit(f"Unknown model key: {args.model_key!r}")
    config = models[args.model_key]
    revision = str(config.get("revision", ""))
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise SystemExit("Registry revision is not a pinned 40-character commit.")

    lock_path = LOCK_DIR / f"{args.model_key}.json"
    if not lock_path.is_file():
        raise SystemExit(f"Model lock is missing: {lock_path}")
    lock = load_json(lock_path)
    expected_identity = {
        "status": "prefetch_completed",
        "model_key": args.model_key,
        "model_id": config["model_id"],
        "model_name": config["model_name"],
        "requested_revision": revision,
        "resolved_commit": revision,
    }
    mismatches = {
        field: {"expected": expected, "actual": lock.get(field)}
        for field, expected in expected_identity.items()
        if lock.get(field) != expected
    }
    if mismatches:
        raise SystemExit(f"Model-lock identity mismatch: {json.dumps(mismatches, sort_keys=True)}")

    snapshot = (
        HF_HUB_CACHE
        / ("models--" + str(config["model_name"]).replace("/", "--"))
        / "snapshots"
        / revision
    )
    if not snapshot.is_dir():
        raise SystemExit(f"Pinned snapshot is missing: {snapshot}")
    locked_files = lock.get("snapshot_files")
    if not isinstance(locked_files, list) or not locked_files:
        raise SystemExit("Model lock has no snapshot file manifest.")

    locked_paths = set()
    for item in locked_files:
        relative = item.get("relative_path")
        relative_path = PurePosixPath(relative) if isinstance(relative, str) else None
        if (
            relative_path is None
            or not relative
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or "\\" in relative
        ):
            raise SystemExit(f"Unsafe locked path: {relative!r}")
        path = snapshot.joinpath(*relative_path.parts)
        if relative in locked_paths:
            raise SystemExit(f"Duplicate locked path: {relative}")
        locked_paths.add(relative)
        if not path.is_file():
            raise SystemExit(f"Locked model file is missing: {relative}")
        if path.stat().st_size != int(item.get("bytes", -1)):
            raise SystemExit(f"Locked model file size mismatch: {relative}")
        actual_hash = sha256_file(path)
        if actual_hash != item.get("sha256"):
            raise SystemExit(f"Locked model file SHA256 mismatch: {relative}")

    actual_paths = {
        path.relative_to(snapshot).as_posix()
        for path in snapshot.rglob("*")
        if path.is_file()
    }
    if actual_paths != locked_paths:
        missing = sorted(locked_paths - actual_paths)
        extra = sorted(actual_paths - locked_paths)
        raise SystemExit(f"Snapshot file set mismatch; missing={missing}, extra={extra}")
    print(
        f"Model-lock verification PASS: {args.model_key} "
        f"({len(locked_paths)} files, revision {revision})"
    )


if __name__ == "__main__":
    main()
