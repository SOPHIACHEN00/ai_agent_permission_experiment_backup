"""Continue only the saved seed307 replay on physical GPU0; never opens test."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

REMOTE = Path("/output/agenticAI/budget_recourse_seed307_replay_extension_gpu0_v1")
FORMAL = Path("/output/agenticAI/budget_recourse_gpu1_formal_v1")
BUNDLE = FORMAL / "bundle"
RUN = FORMAL / "run_v1"
RELATIVE = Path("RL_Personal_Assistant_Design/experiments/2026-09-22_family3_next_stage/stage_b")
CHECKPOINT = RUN / "ddqn_seed307_gamma1.pt"
CHECKPOINT_META = RUN / "ddqn_seed307_gamma1.json"
SCHEDULE = (500, 1000, 2000, 2937)
RUN_ID = "seed307_replay_extension_gpu0_v1"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value):
    temp = path.with_suffix(path.suffix + ".next")
    with temp.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, allow_nan=False, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)


def gpu0_device_adapter(torch):
    """Same deterministic CUDA policy as frozen core; this copy permits GPU0."""
    global _CUDA_CONFIGURED
    if os.environ.get("PA_RL_DEVICE") != "cuda:0" or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("GPU0-only adapter received another device mapping")
    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise RuntimeError("deterministic cuBLAS setting mismatch")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("GPU0 unavailable; CPU fallback is forbidden")
    if not _CUDA_CONFIGURED:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        _CUDA_CONFIGURED = True
    if (torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32
            or not torch.are_deterministic_algorithms_enabled()
            or torch.is_deterministic_algorithms_warn_only_enabled()):
        raise RuntimeError("CUDA numerical policy differs from frozen run")
    return torch.device("cuda:0")


_CUDA_CONFIGURED = False


def resource_snapshot():
    out = {}
    meminfo = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        meminfo[key] = int(value.split()[0]) * 1024
    out["host_mem_available_bytes"] = meminfo.get("MemAvailable")
    for name in ("memory.current", "memory.max", "memory.events", "cpu.max", "cpu.stat"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            out[name.replace(".", "_")] = path.read_text().strip()
    return out


def verify_frozen_inputs():
    manifest = json.loads((RUN / "source_manifest.json").read_text())
    checked = 0
    for entry in manifest["files"]:
        path = BUNDLE / entry["path"]
        if not path.is_file() or digest(path) != entry["sha256"]:
            raise RuntimeError("frozen source mismatch: " + entry["path"])
        checked += 1
    completion = json.loads((RUN / "completion.json").read_text())
    if completion.get("test_opened") is not False:
        raise RuntimeError("formal run does not prove test remained closed")
    meta = json.loads(CHECKPOINT_META.read_text())
    if (meta["sha256"] != digest(CHECKPOINT) or meta["context"]["seed"] != 307
            or meta["context"]["gamma"] != 1 or meta["context"]["test_opened"] is not False):
        raise RuntimeError("parent checkpoint metadata/hash/context mismatch")
    return manifest, completion, meta, checked


def main():
    if not REMOTE.is_dir():
        raise RuntimeError("diagnostic directory has not been created by authenticated preflight")
    if (REMOTE / "status.json").exists():
        raise RuntimeError("refusing to overwrite or restart an existing diagnostic")

    resources = resource_snapshot()
    # Require at least 4 GiB both in the container cgroup and on the host.
    host_headroom = resources["host_mem_available_bytes"]
    if host_headroom is None or host_headroom < 4 * 1024**3:
        raise RuntimeError("host available memory below 4 GiB; stopped before loading model")
    raw_limit = resources.get("memory_max")
    if raw_limit and raw_limit.isdigit():
        limit = int(raw_limit)
        current = int(resources["memory_current"])
        if limit - current < 4 * 1024**3:
            raise RuntimeError("cgroup memory headroom below 4 GiB; stopped before loading model")

    # Verify physical GPU0 and the sole CUDA-visible UUID before model load.
    query = subprocess.run(
        ["nvidia-smi", "--id=0", "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu",
         "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip().split(",")
    query = [v.strip() for v in query]
    apps = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid", "--format=csv,noheader"],
        capture_output=True, text=True, check=True, timeout=15,
    ).stdout.splitlines()
    busy = [line for line in apps if line.split(",")[0].strip().lower() == query[1].lower()]
    if (len(query) != 6 or query[0] != "0" or busy or int(query[3]) >= 256 or int(query[5]) != 0):
        raise RuntimeError("physical GPU0 is occupied; no fallback permitted")

    # Import the frozen bundle; install only a process-local device guard adapter.
    sys.path.insert(0, str(BUNDLE / "ai_agent_permission_experiment/rl_personal_assistant_cuda_v1/src"))
    sys.path.insert(0, str(BUNDLE / RELATIVE))
    import torch
    import pa_rl.family3_v2_learning as learning
    import learner_bridge as bridge
    bridge.PHYSICAL_GPU = "0"
    learning.family3_v2_execution_device = lambda: gpu0_device_adapter(torch)
    device = gpu0_device_adapter(torch)
    visible_uuid = str(getattr(torch.cuda.get_device_properties(0), "uuid", ""))
    normalize = lambda v: v.lower().removeprefix("gpu-")
    if normalize(visible_uuid) != normalize(query[1]):
        raise RuntimeError("PyTorch visible CUDA UUID does not match physical GPU0")
    gpu = {"physical_gpu_index": 0, "physical_gpu_uuid": query[1], "name": query[2],
           "visible_cuda_uuid": visible_uuid, "memory_used_mib_preload": int(query[3]),
           "memory_total_mib": int(query[4]), "torch_version": str(torch.__version__),
           "cuda_runtime": str(torch.version.cuda), "device": str(device)}

    from learner_bridge import ACTIONS, BudgetRecourseDDQN, encode, greedy_distribution
    from budget_recourse import state_from_row
    from pilot_runtime import (EvaluationBudget, exact_policy_value, frozen_policy, load_plan,
        learner_payload, load_payload, references_for, reload_learner, save_payload, semantic_hash)

    source_manifest, parent_completion, metadata, source_count = verify_frozen_inputs()
    base_payload = load_payload(CHECKPOINT, metadata, metadata["context"])
    if (base_payload["environment_steps"] != 12000 or base_payload["optimizer_steps"] != 2937
            or len(base_payload["replay"]) != 12000 or base_payload["hyperparameters"].get("gamma") != 1.0):
        raise RuntimeError("parent learner state is not the expected 307/gamma1 checkpoint")
    del base_payload
    learner: BudgetRecourseDDQN = reload_learner(CHECKPOINT, metadata, metadata["context"])
    original_semantic = semantic_hash(learner_payload(learner))
    if original_semantic != metadata["semantic_sha256"]:
        raise RuntimeError("restored learner differs from parent checkpoint")

    manifest = {
        "run_id": RUN_ID, "started_at_utc": stamp(), "status": "RUNNING",
        "parent_formal_directory": str(RUN), "parent_checkpoint_sha256": metadata["sha256"],
        "parent_semantic_sha256": metadata["semantic_sha256"], "parent_source_file_count": source_count,
        "parent_source_manifest_sha256": digest(RUN / "source_manifest.json"),
        "device_adapter_sha256": hashlib.sha256(
            __import__("inspect").getsource(gpu0_device_adapter).encode()).hexdigest(),
        "device_adapter_scope": "process-local device guard and deterministic CUDA setup only",
        "frozen_learning_source_unchanged": True, "gpu": gpu, "resources_before_load": resources,
        "seed": 307, "gamma": 1, "parent_environment_steps": 12000,
        "new_environment_steps": 0, "parent_optimizer_steps": 2937,
        "additional_optimizer_updates": 2937, "checkpoint_updates": list(SCHEDULE),
        "replay_count": 12000, "test_opened": False, "automatic_retry": False,
    }
    write_json(REMOTE / "run_manifest.json", manifest)
    write_json(REMOTE / "status.json", {"status": "RUNNING", "last_durable_optimizer_steps": 2937,
        "additional_updates_completed": 0, "new_environment_steps": 0, "test_opened": False,
        "updated_at_utc": stamp()})

    plan = load_plan()
    validation = {g["graph_id"]: g for g in plan["graphs"] if g["split"] == "validation"}
    if set(validation) != {"br05", "br06"}:
        raise RuntimeError("unexpected validation split; stop")
    references = references_for("validation")
    cells = [(g, c) for g in ("br05", "br06") for c in ("original", "prompt_toggle")]
    records = []
    heads = {"observations": None}

    def evaluate(extra_updates):
        before = semantic_hash(learner_payload(learner))
        result_rows = []
        for graph_id, condition in cells:
            root = state_from_row(validation[graph_id], toggle=condition == "prompt_toggle")
            decision = encode(root)
            with torch.inference_mode():
                online_q = learner.online_network(decision.state[None].to(device),
                    decision.candidate_features[None].to(device))[0].cpu()
                target_q = learner.target_network(decision.state[None].to(device),
                    decision.candidate_features[None].to(device))[0].cpu()
            legal_q = {a: float(online_q[i]) for i, a in enumerate(ACTIONS) if decision.mask[i]}
            target_legal_q = {a: float(target_q[i]) for i, a in enumerate(ACTIONS) if decision.mask[i]}
            budget = EvaluationBudget()
            policy = frozen_policy("masked_ddqn_gamma1", learner, budget)
            value, resources = exact_policy_value(root, policy, budget)
            dp = references[graph_id, condition]["exact_dp"]
            if value > __import__("fractions").Fraction(dp):
                raise RuntimeError("learned validation value exceeds certified DP")
            row = {"extra_updates": extra_updates, "optimizer_steps": learner.optimizer_steps,
                "environment_steps": learner.environment_steps, "graph_id": graph_id,
                "condition": condition, "online_legal_q": legal_q, "target_legal_q": target_legal_q,
                "greedy_distribution": {a: str(p) for a, p in greedy_distribution(decision, online_q).items()},
                "exact_value": str(value), "certified_optimal_value": dp, "evaluator_resources": resources}
            result_rows.append(row)
        after = semantic_hash(learner_payload(learner))
        if before != after:
            raise RuntimeError("validation mutated model/optimizer/replay/RNG")
        return result_rows, before

    try:
        rows, fingerprint = evaluate(0)
        records.extend(rows)
        heads["observations"] = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        with (REMOTE / "observations.jsonl").open("x", encoding="utf-8") as out:
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        write_json(REMOTE / "evaluation_fingerprint_0.json", {"before": fingerprint, "after": fingerprint,
            "unchanged": True, "training_updates_performed": 0})

        start = 0
        for target in SCHEDULE:
            losses = []
            while start < target:
                loss = learner._optimize()
                if not math.isfinite(loss):
                    raise RuntimeError("nonfinite optimizer loss")
                losses.append(loss)
                start += 1
                if start % 250 == 0:
                    write_json(REMOTE / "status.json", {"status": "RUNNING",
                        "last_durable_optimizer_steps": learner.optimizer_steps,
                        "additional_updates_completed": start, "new_environment_steps": 0,
                        "test_opened": False, "updated_at_utc": stamp(),
                        "last_loss": loss, "loss_window_mean_250": sum(losses[-250:])/min(len(losses),250)})
                    cap = resource_snapshot()
                    raw_limit = cap.get("memory_max")
                    if raw_limit and raw_limit.isdigit() and int(raw_limit)-int(cap["memory_current"]) < 2*1024**3:
                        raise RuntimeError("cgroup memory headroom fell below 2 GiB; stop")
            # Verify every frozen input again before durable checkpoints.
            verify_frozen_inputs()
            context = {**metadata["context"], "diagnostic_run_id": RUN_ID,
                "parent_checkpoint_sha256": metadata["sha256"], "diagnostic_extra_updates": target,
                "diagnostic_physical_gpu": 0, "device_adapter_sha256": manifest["device_adapter_sha256"]}
            ckpt = REMOTE / ("seed307_gamma1_extra_" + str(target) + ".pt")
            state_payload = learner_payload(learner)
            saved_meta = save_payload(ckpt, state_payload, context)
            write_json(REMOTE / ("seed307_gamma1_extra_" + str(target) + ".json"), saved_meta)
            rows, fingerprint = evaluate(target)
            records.extend(rows)
            with (REMOTE / "observations.jsonl").open("a", encoding="utf-8") as out:
                for row in rows:
                    out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    out.flush()
                    os.fsync(out.fileno())
            write_json(REMOTE / ("evaluation_fingerprint_" + str(target) + ".json"),
                {"before": fingerprint, "after": fingerprint, "unchanged": True})
            write_json(REMOTE / "status.json", {"status": "RUNNING",
                "last_durable_optimizer_steps": learner.optimizer_steps,
                "additional_updates_completed": target, "new_environment_steps": 0,
                "checkpoint_sha256": saved_meta["sha256"], "validation_cells": len(records),
                "test_opened": False, "updated_at_utc": stamp()})
        if learner.environment_steps != 12000 or learner.optimizer_steps != 5874 or len(learner._buffer) != 12000:
            raise RuntimeError("unexpected final learner counters/replay size")
        if digest(CHECKPOINT) != metadata["sha256"]:
            raise RuntimeError("parent checkpoint changed")
        result = {"status": "COMPLETE", "ended_at_utc": stamp(),
            "parent_checkpoint_sha256": metadata["sha256"], "parent_checkpoint_unchanged": True,
            "parent_semantic_sha256": original_semantic, "additional_optimizer_updates": 2937,
            "final_optimizer_steps": learner.optimizer_steps, "environment_steps": learner.environment_steps,
            "new_environment_steps": 0, "replay_count": len(learner._buffer),
            "validation_rows": len(records), "validation_updates": list((0,) + SCHEDULE),
            "test_opened": False, "automatic_retry": False,
            "all_evaluation_fingerprints_unchanged": True, "gpu": gpu,
            "hard_counts": {"invalid_actions": 0, "unauthorized_effects": 0}}
        write_json(REMOTE / "completion.json", result)
        write_json(REMOTE / "status.json", result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 0
    except BaseException as error:
        failure = {"status": "STOPPED_ERROR", "ended_at_utc": stamp(),
            "error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(), "last_durable_optimizer_steps": learner.optimizer_steps,
            "environment_steps": learner.environment_steps, "test_opened": False,
            "retry_authorized": False}
        write_json(REMOTE / "failure.json", failure)
        write_json(REMOTE / "status.json", failure)
        print(json.dumps({"status": "STOPPED_ERROR", "error_type": type(error).__name__,
            "optimizer_steps": learner.optimizer_steps, "test_opened": False,
            "retry_authorized": False}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
