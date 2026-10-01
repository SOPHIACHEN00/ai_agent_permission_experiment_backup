"""Read-only byte verification of the Task 8 handoff (standard library only)."""

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    path = root / "docs/implementation_reports/family3-v2-server-package-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    checked = 0
    for entry in manifest["files"]:
        if not entry["transfer"]:
            continue
        relative = entry["relative_path"]
        candidate = root / relative
        if not candidate.resolve().is_relative_to(root) or candidate.is_symlink() or not candidate.is_file():
            failures.append(relative)
            continue
        content = candidate.read_bytes()
        if len(content) != entry["byte_size"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            failures.append(relative)
        checked += 1
    print(json.dumps({"status": "PACKAGE_HASHES_PASS" if not failures else "PACKAGE_HASHES_FAIL",
                      "checked_transfer_files": checked, "mismatches": failures}, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
