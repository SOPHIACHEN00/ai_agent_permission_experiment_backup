"""Read downloaded smoke evidence; no environment, learner or model inference."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import zipfile

import torch
from pilot_runtime import canonical, semantic_hash, WORKSPACE

HERE = Path(__file__).resolve().parent
ROOT = HERE / "evidence/b2_gpu2_smoke_v1"


def need(ok: bool, detail: str) -> None:
    if not ok:
        raise AssertionError(detail)


def main() -> None:
    path = ROOT / "server_evidence.zip"
    with zipfile.ZipFile(path) as archive:
        need(archive.testzip() is None, "archive CRC")
        names = archive.namelist()
        need(not any("test" in Path(n).parts or n.endswith("test_permit.json") for n in names), "test opened")
        def read(name: str):
            return json.loads(archive.read(name))
        completion = read("run_v1/completion.json")
        exit_receipt = read("exit_receipt.json")
        runtime = read("run_v1/runtime.json")
        need(exit_receipt["exit_code"] == 0, "server exit")
        need(completion["status"] == "NON_EVIDENCE_SMOKE_COMPLETE", "completion status")
        need((completion["transitions"], completion["checkpoints"], completion["evaluation_rows"]) == (320,1,2), "smoke counts")
        need(not completion["test_opened"] and completion["scientific_classification"] is None, "evidence boundary")
        need(all(v == 0 for v in completion["hard_counts"].values()), "hard safety counters")
        need(runtime["physical_gpu_index"] == 2 and runtime["cuda_visible_devices"] == "2", "GPU mapping")
        chains = {}
        for name, expected in completion["heads"].items():
            rows = []
            previous = None
            for i, line in enumerate(archive.read("run_v1/" + name + ".jsonl").splitlines()):
                record = json.loads(line)
                digest = record.pop("sha256")
                need(record["index"] == i and record["previous"] == previous, "chain coordinate")
                need(hashlib.sha256(canonical(record)).hexdigest() == digest, "chain digest")
                previous = digest
                rows.append(record["payload"])
            need([len(rows), previous] == expected, "chain tail/count")
            chains[name] = rows
        cells = chains["training_cells"]
        need(len(cells) == 5 and {r["graph_id"] for r in cells} == {"br00","br01","br02","br03","br04"}, "train graphs")
        need(all(r["completed_transitions"] == 64 and r["condition"] == "original" for r in cells), "per-graph quota")
        need(len(chains["train_steps"]) == 320, "logged transition count")
        checkpoint = chains["checkpoints"][0]
        raw = archive.read("run_v1/" + checkpoint["file"])
        need(hashlib.sha256(raw).hexdigest() == checkpoint["sha256"] and len(raw) == checkpoint["bytes"], "checkpoint payload")
        # Tensor-only deserialization, never instantiate an RL learner or network.
        decoded = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        payload = decoded["payload"]
        need(semantic_hash(payload) == checkpoint["semantic_sha256"], "checkpoint semantic hash")
        need((payload["environment_steps"], payload["optimizer_steps"], len(payload["replay"])) == (320,17,320), "actual optimization/replay counts")
        changed = semantic_hash(payload["online"]) != checkpoint["context"]["initial_online_sha256"]
        need(changed, "online weights unchanged")
        fingerprints = chains["evaluation_fingerprints"]
        need(len(fingerprints) == 1 and fingerprints[0]["unchanged"]
             and fingerprints[0]["before"] == fingerprints[0]["after"] == checkpoint["semantic_sha256"], "evaluation mutation")
        manifest = read("package_manifest.json")
        need(manifest == read("run_v1/source_manifest.json"), "server manifest drift")
        for entry in manifest["files"]:
            local = (WORKSPACE / entry["path"]).resolve()
            need(local.is_relative_to(WORKSPACE.resolve()), "source path escapes")
            need(hashlib.sha256(local.read_bytes()).hexdigest() == entry["sha256"], "source/config changed")
        exact = chains["exact_values"][0]
        sampled_successes = sum(r["success"] for r in chains["evaluation_rows"])
        report = {
            "status": "B2_GPU2_SMOKE_PASS_FORMAL_NOT_STARTED",
            "scope": "One NON_EVIDENCE integration smoke, not a learning-effectiveness result.",
            "server_exit_code": 0, "server_wall_seconds": exit_receipt["wall_seconds"],
            "physical_gpu": 2, "gpu3_used": False,
            "transitions":320, "optimizer_steps":17, "replay_transitions":320,
            "checkpoints":1, "checkpoint_reloaded_on_server": True, "online_weights_changed": changed,
            "evaluation_rows":2, "evaluation_state_unchanged":True,
            "sampled_successes":sampled_successes, "sampled_total":2,
            "train_br00_exact_policy_value":exact["value"],
            "hard_counts":completion["hard_counts"], "test_opened":False, "formal_training_started":False,
            "record_chains_verified":len(chains), "frozen_source_files_verified":len(manifest["files"]),
            "archive_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "checkpoint_sha256":checkpoint["sha256"], "evaluator_resources":exact["evaluator_resources"],
            "verification_did_not_train_or_infer":True
        }
        target = ROOT / "unpacked"
        target.mkdir(exist_ok=False)
        for name in names:
            need((target/name).resolve().is_relative_to(target.resolve()), "unsafe evidence member")
        archive.extractall(target)
    with (ROOT/"postflight_verification.json").open("x",encoding="utf-8") as output:
        json.dump(report,output,indent=2,ensure_ascii=False)
        output.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()

