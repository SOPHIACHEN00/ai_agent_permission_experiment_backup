"""Build a fresh minimal source archive; no imports of torch, env or learners."""
from __future__ import annotations

import ast
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
WORKSPACE = HERE.parents[3]
CORE = WORKSPACE / "ai_agent_permission_experiment/rl_personal_assistant_cuda_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    # Verify all old evidence and frozen inputs; never copy models/results/credentials.
    provenance = json.loads((BASE / "data/provenance_manifest.json").read_text(encoding="utf-8"))
    legacy = None
    for entry in provenance["archives"]:
        path = WORKSPACE / entry["path"]
        if sha(path) != entry["sha256"]:
            raise ValueError("sealed prior archive changed")
        if entry["phase"] == "validation":
            with zipfile.ZipFile(path) as archive:
                legacy = json.loads(archive.read("formal_results/source_manifest.json"))
    if legacy is None:
        raise ValueError("missing frozen legacy source manifest")
    for relative, digest, size in legacy["entries"]:
        path = (CORE / relative).resolve()
        if not path.is_relative_to(CORE.resolve()) or path.stat().st_size != size or sha(path) != digest:
            raise ValueError("frozen legacy source changed")
    stage_a = json.loads((BASE / "stage_a/evidence/preflight_v0/source_manifest.json").read_text(encoding="utf-8"))
    for entry in stage_a["new_files"]:
        if sha(WORKSPACE / entry["path"]) != entry["sha256"]:
            raise ValueError("frozen Stage A input changed")
    previous = json.loads((HERE / "evidence/rng_fix1_receipt.json").read_text(encoding="utf-8"))
    execution = json.loads((HERE / "execution_profile_gpu1_formal_v1.json").read_text(encoding="utf-8"))
    for entry in previous["unchanged_and_fingerprints"]["current_bridge_files"]:
        amendment = execution["authorized_b1_changes"].get(entry["path"])
        expected = entry["sha256"]
        if amendment is not None:
            if amendment["previous_sha256"] != expected:
                raise ValueError("execution amendment does not bind original B1 source")
            expected = amendment["authorized_sha256"]
        if sha(HERE / entry["path"]) != expected:
            raise ValueError("frozen B1 input changed")
    files = list((CORE / "src/pa_rl").glob("*.py"))
    files += [BASE / "stage_a" / name for name in ("budget_recourse.py", "budget_recourse_env.py")]
    files += [HERE / name for name in ("learner_bridge.py", "pilot_criteria.py", "pilot_runtime.py",
                                       "run_learner_pilot.py", "criteria_v1.json", "GOAL_AMENDMENT_zh_en.md",
                                       "execution_profile_gpu1_formal_v1.json")]
    files += [BASE / "next_experiment_plan.json", BASE / "stage_a/evidence/preflight_v0/values.csv"]
    entries = []
    for path in sorted(files):
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
        entries.append({"path": path.relative_to(WORKSPACE).as_posix(), "sha256": sha(path),
                        "bytes": path.stat().st_size})
    manifest = {"schema": "budget_recourse_package_v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "files": entries, "frozen_old_sources_verified": len(legacy["entries"]),
                "sealed_old_archives_verified": len(provenance["archives"]),
                "stage_a_inputs_verified": len(stage_a["new_files"]),
                "b1_inputs_verified": len(previous["unchanged_and_fingerprints"]["current_bridge_files"]),
                "mode_authorized_this_turn": "FORMAL_TRAIN_VALIDATE_TEST_LOCKED",
                "physical_gpu_this_run": 1, "user_authorized_gpu_indices": [0, 1],
                "no_credentials_or_connection_coordinates": True}
    output = HERE / "formal_gpu01_v1/package"
    output.mkdir(exist_ok=False)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    manifest_path = output / "package_manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    archive_path = output / "budget_recourse_formal_v1.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("package_manifest.json", manifest_bytes)
        for entry in entries:
            archive.write(WORKSPACE / entry["path"], entry["path"])
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("package archive CRC mismatch")
        for entry in entries:
            if hashlib.sha256(archive.read(entry["path"])).hexdigest() != entry["sha256"]:
                raise ValueError("package member hash mismatch")
    receipt = {"archive": archive_path.name, "sha256": sha(archive_path), "bytes": archive_path.stat().st_size,
               "source_files": len(entries), "source_syntax_checked": True,
               "gpu_smoke_started": False, "test_opened": False}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
