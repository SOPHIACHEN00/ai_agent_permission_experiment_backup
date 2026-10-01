"""Offline artifact audit only: no learner construction, inference or training."""
from __future__ import annotations
from collections import Counter, defaultdict
import gc
import hashlib
import io
import json
from fractions import Fraction as F
from pathlib import Path
import zipfile

import torch
from pilot_runtime import canonical, semantic_hash, WORKSPACE

HERE = Path(__file__).resolve().parent
ROOT = HERE / "formal_gpu01_v1"
SEEDS = (101, 211, 307)
METHODS = ("masked_ddqn_gamma1", "masked_ddqn_gamma0", "forecast_transfer_rule",
           "current_task_rule", "reservation_rule", "random_valid")
HARD = {"invalid_actions", "unauthorized_effects", "data_leakage", "source_config_mismatch", "checkpoint_mismatch"}


def need(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> None:
    path = ROOT / "server_evidence/server_evidence.zip"
    archive_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None, "archive CRC mismatch")
        names = z.namelist()
        need(not any("test" in Path(n).parts or n.endswith("test_permit.json") for n in names), "test opened")
        def read(name):
            return json.loads(z.read(name))
        completion = read("run_v1/completion.json")
        exit_receipt = read("exit_receipt.json")
        runtime = read("run_v1/runtime.json")
        manifest = read("run_v1/run_manifest.json")
        package = read("package_manifest.json")
        need(exit_receipt["exit_code"] == 0, "server nonzero exit")
        need(completion["status"] == "TRAIN_VALIDATION_COMPLETE_TEST_LOCKED", "incomplete run")
        need((completion["transitions"], completion["checkpoints"], completion["evaluation_rows"]) == (72000, 6, 3600), "budget mismatch")
        need(not completion["test_opened"] and not manifest["test_opened"], "test flag")
        need(runtime["physical_gpu_index"] == 1 and runtime["cuda_visible_devices"] == "1", "wrong GPU mapping")
        need(runtime["physical_gpu_uuid"].lower().removeprefix("gpu-") == runtime["visible_cuda_uuid"].lower().removeprefix("gpu-"), "UUID mismatch")
        need(manifest["mode"] == "train-validate" and manifest["evidence_mode"] == "FORMAL", "wrong mode")
        need(set(completion["hard_counts"]) == HARD and all(v == 0 for v in completion["hard_counts"].values()), "safety/integrity counter")
        need(package == read("run_v1/source_manifest.json"), "server source drift")
        need(z.read("package_manifest.json") == (ROOT/"package/package_manifest.json").read_bytes(), "uploaded manifest differs")
        for item in package["files"]:
            local = (WORKSPACE/item["path"]).resolve()
            need(local.is_relative_to(WORKSPACE.resolve()) and hashlib.sha256(local.read_bytes()).hexdigest() == item["sha256"], "frozen source/config changed")
        need(manifest["source_manifest_sha256"] == hashlib.sha256(z.read("package_manifest.json")).hexdigest(), "manifest fingerprint")
        for field, file in (("execution_profile_sha256", HERE/"execution_profile_gpu1_formal_v1.json"),
                            ("criteria_sha256", HERE/"criteria_v1.json"),
                            ("design_sha256", HERE.parent/"next_experiment_plan.json")):
            need(manifest[field] == hashlib.sha256(file.read_bytes()).hexdigest(), field)

        kept = {n: [] for n in ("training_cells", "checkpoints", "evaluation_rows", "evaluation_fingerprints", "exact_values")}
        transition_counts = Counter()
        episode_counts = defaultdict(Counter)
        chain_counts = {}
        for name, expected in completion["heads"].items():
            previous = None
            count = 0
            with z.open("run_v1/"+name+".jsonl") as stream:
                for line in stream:
                    record = json.loads(line)
                    digest = record.pop("sha256")
                    need(record["index"] == count and record["previous"] == previous, "chain order")
                    need(hashlib.sha256(canonical(record)).hexdigest() == digest, "chain hash")
                    previous = digest
                    count += 1
                    row = record["payload"]
                    if name in kept:
                        kept[name].append(row)
                    elif name == "train_steps":
                        need(row["phase"] == "train" and row["condition"] == "original", "training split")
                        transition_counts[row["seed"],row["gamma"],row["graph_id"]] += 1
                    elif name == "train_episodes":
                        key = row["seed"], row["gamma"], row["graph_id"]
                        episode_counts[key]["episodes"] += 1
                        episode_counts[key]["successes"] += int(row["success"])
                        episode_counts[key]["budget_cutoffs"] += int(row["budget_cutoff"])
            need([count, previous] == expected, "chain tail/count")
            chain_counts[name] = count
        desired_training = {(s,g,"br0"+str(i)) for s in SEEDS for g in (0,1) for i in range(5)}
        need(set(transition_counts) == desired_training and set(transition_counts.values()) == {2400}, "per-graph training quota")
        need(chain_counts["train_steps"] == 72000 and len(kept["training_cells"]) == 30, "training completeness")
        need(all(r["completed_transitions"] == 2400 for r in kept["training_cells"]), "cell quota")
        checkpoints = {(r["seed"],r["gamma"]):r for r in kept["checkpoints"]}
        need(len(kept["checkpoints"]) == 6 and set(checkpoints) == {(s,g) for s in SEEDS for g in (0,1)}, "checkpoint coordinates")
        for (seed,gamma), meta in checkpoints.items():
            raw = z.read("run_v1/"+meta["file"])
            need(hashlib.sha256(raw).hexdigest() == meta["sha256"] and len(raw) == meta["bytes"], "checkpoint binary hash")
            decoded = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
            payload = decoded["payload"]
            need(decoded["context"] == meta["context"], "checkpoint context")
            need(semantic_hash(payload) == meta["semantic_sha256"], "checkpoint semantic hash")
            need((payload["environment_steps"],payload["optimizer_steps"],len(payload["replay"])) == (12000,2937,12000), "optimizer/replay counts")
            need(semantic_hash(payload["online"]) != meta["context"]["initial_online_sha256"], "weights unchanged")
            need(payload["hyperparameters"]["gamma"] == gamma, "gamma arm")
            need(meta["context"]["physical_gpu_index"] == 1, "checkpoint device context")
            del raw, decoded, payload
            gc.collect()
        for seed in SEEDS:
            need(checkpoints[seed,0]["context"]["initial_online_sha256"] == checkpoints[seed,1]["context"]["initial_online_sha256"], "unmatched initialization")

        expected_eval = {(s,m,g,c,e) for s in SEEDS for m in METHODS for g in ("br05","br06")
                         for c in ("original","prompt_toggle") for e in range(50)}
        eval_rows = kept["evaluation_rows"]
        actual_eval = [(r["seed"],r["method"],r["graph_id"],r["condition"],r["episode"]) for r in eval_rows]
        need(len(actual_eval) == 3600 and set(actual_eval) == expected_eval, "validation coverage")
        sampled = defaultdict(Counter)
        for r in eval_rows:
            need(r["phase"] == "validation" and set(r["hard_counts"]) == HARD and all(v == 0 for v in r["hard_counts"].values()), "evaluation safety/split")
            key = r["seed"],r["method"]
            sampled[key]["successes"] += int(r["success"])
            sampled[key]["episodes"] += 1
            if r["method"].startswith("masked_ddqn"):
                gamma = int(r["method"][-1])
                need(r["checkpoint_sha256"] == checkpoints[r["seed"],gamma]["sha256"], "evaluation model mismatch")
        fingerprints = kept["evaluation_fingerprints"]
        need(len(fingerprints) == 24, "evaluation fingerprint coverage")
        for row in fingerprints:
            meta = checkpoints[row["seed"],int(row["method"][-1])]
            need(row["unchanged"] and row["before"] == row["after"] == meta["semantic_sha256"], "evaluation mutated state")
        exact = kept["exact_values"]
        need(len(exact) == 72 and len({(r["seed"],r["method"],r["graph_id"],r["condition"]) for r in exact}) == 72, "exact coverage")
        means = read("run_v1/validation_exact_means.json")
        summary = []
        for seed in SEEDS:
            for method in METHODS:
                rows = [r for r in exact if r["seed"] == seed and r["method"] == method]
                need(len(rows) == 4, "exact mean cells")
                value = sum((F(r["value"]) for r in rows),F(0))/4
                optimum = sum((F(r["exact_dp"]) for r in rows),F(0))/4
                need(value == F(means[str(seed)][method]) and optimum == F(means[str(seed)]["exact_dp"]), "exact mean mismatch")
                summary.append(dict(seed=seed,method=method,exact_value=str(value),exact_value_float=float(value),
                                    exact_regret=str(optimum-value),**sampled[seed,method]))
        gate = read("run_v1/validation_gate.json")
        need(gate == completion["gate"] and gate["status"] == "READY_FOR_TEST_REVIEW"
             and not gate["test_opened"] and not gate["test_execution_authorized"] and not gate["performance_filtered"], "validation integrity gate")
        classification = read("run_v1/validation_classification.json")
        need(classification == completion["scientific_classification"], "classification mismatch")
        for seed in SEEDS:
            values = means[str(seed)]
            regret = F(values["exact_dp"])-F(values["masked_ddqn_gamma1"])
            learned = F(values["masked_ddqn_gamma1"]) > max(F(values["masked_ddqn_gamma0"]),F(values["current_task_rule"]))
            need(classification["near_optimal_by_seed"][str(seed)] == (regret <= F(1,20)), "near-optimal criterion")
            need(classification["learning_by_seed"][str(seed)] == learned, "learning criterion")
        target = ROOT/"server_evidence/unpacked"
        need(not target.exists(), "do not overwrite evidence")
        for name in names:
            need((target/name).resolve().is_relative_to(target.resolve()), "unsafe archive member")
        target.mkdir()
        z.extractall(target)
        report = dict(status="FORMAL_ARTIFACTS_VERIFIED_TEST_LOCKED",server_exit_code=0,
                      server_wall_seconds=exit_receipt["wall_seconds"],physical_gpu=1,transitions=72000,
                      checkpoints=6,optimizer_steps_per_checkpoint=2937,validation_rows=3600,exact_rows=72,
                      hard_counts=completion["hard_counts"],test_opened=False,source_files_verified=len(package["files"]),
                      record_chains_verified=len(chain_counts),record_counts=chain_counts,archive_sha256=archive_sha,
                      validation_gate=gate,scientific_classification=classification,per_seed_summary=summary,
                      training_episodes_by_cell=[dict(seed=k[0],gamma=k[1],graph_id=k[2],**v) for k,v in sorted(episode_counts.items())],
                      evaluation_state_unchanged=True,verification_did_not_train_or_infer=True)
    with (ROOT/"postflight_verification.json").open("x",encoding="utf-8") as output:
        json.dump(report,output,indent=2,ensure_ascii=False)
        output.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("training_episodes_by_cell","record_counts")},ensure_ascii=False))


if __name__ == "__main__":
    main()
