"""Verify the CUDA overlay and every unchanged baseline transfer file."""
import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "cuda_variant_manifest.json").read_text(encoding="utf-8"))
    mismatches = []
    for entry in manifest["files"]:
        path = root / entry["relative_path"]
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            mismatches.append(entry["relative_path"])
            continue
        content = path.read_bytes()
        if len(content) != entry["byte_size"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            mismatches.append(entry["relative_path"])
    print(json.dumps({
        "status": "CUDA_VARIANT_HASHES_PASS" if not mismatches else "CUDA_VARIANT_HASHES_FAIL",
        "checked_files": len(manifest["files"]), "mismatches": mismatches,
    }))
    return int(bool(mismatches))


if __name__ == "__main__":
    raise SystemExit(main())
