"""Server GPU1 selected under GPU0/1 authorization; never opens test."""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import random
import subprocess
import sys
from dataclasses import asdict
from fractions import Fraction as F
from pathlib import Path

import torch

from learner_bridge import (
    ACTIONS, ENCODER_SCHEMA, RNG_SCHEMA, PHYSICAL_GPU, BudgetRecourseDDQN,
    draw_tape, encode, seed_for,
)
from budget_recourse import legal_actions, state_from_row, transitions
from budget_recourse_env import Environment
from pa_rl.family3_v2_learning import family3_v2_device_metadata, family3_v2_execution_device
from pilot_criteria import HARD_COUNTERS, classify_exact
from pilot_runtime import (
    BASE, HERE, SCHEMA, EvaluationBudget, RunStore, canonical, evaluation_coordinates,
    exact_policy_value, frozen_policy, learner_payload, load_plan, references_for,
    reload_learner, sample_action, save_payload, semantic_hash, sha, stamp,
    successor_fields, training_schedule, validation_gate, verify_package,
)


class IntegrityError(RuntimeError):
    def __init__(self, counter: str, detail: str) -> None:
        super().__init__(detail)
        self.counter = counter


def require(condition: bool, detail: str, counter: str = "source_config_mismatch") -> None:
    if not condition:
        raise IntegrityError(counter, detail)


def gpu_metadata() -> dict:
    require(sys.platform.startswith("linux"), "learner runs are server Linux only")
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == PHYSICAL_GPU
            and os.environ.get("PA_RL_DEVICE") == "cuda:0", "selected physical GPU1 only")
    device = family3_v2_execution_device()
    query = subprocess.run(
        ["nvidia-smi", "--id=" + PHYSICAL_GPU, "--query-gpu=index,uuid,name", "--format=csv,noheader"],
        check=True, capture_output=True, text=True, timeout=15,
    ).stdout.strip().split(",", 2)
    require(len(query) == 3 and query[0].strip() == PHYSICAL_GPU, "cannot identify selected physical GPU1")
    visible_uuid = str(getattr(torch.cuda.get_device_properties(0), "uuid", ""))
    require(visible_uuid.lower().removeprefix("gpu-") == query[1].strip().lower().removeprefix("gpu-"),
            "visible CUDA UUID differs from selected GPU1")
    return {**family3_v2_device_metadata(device.type), "physical_gpu_index": int(PHYSICAL_GPU),
            "physical_gpu_uuid": query[1].strip(), "visible_cuda_uuid": visible_uuid,
            "torch_version": str(torch.__version__), "python_version": sys.version.split()[0]}


def checked_step(env: Environment, decision, action: str) -> None:
    before = env.state
    allowed = tuple(a for a, bit in zip(ACTIONS, decision.mask.tolist()) if bit)
    require(set(allowed) == set(env.allowed_actions()) == set(legal_actions(before)),
            "pure model/real monitor/mask disagree", "invalid_actions")
    require(action in allowed, "policy selected invalid action", "invalid_actions")
    env.step(action)
    require(env.state in tuple(child for _, child in transitions(before, action)),
            "real successor not in pure transition support")
    require(env.state.exposure >= 0 and env.state.prompts >= 0, "negative resources")
    event = env.trace[-1]
    if action == "execute_covering":
        require(event.get("effect_committed") is True and event.get("monitor_audit_valid") is True,
                "effect receipt/monitor audit invalid", "unauthorized_effects")
    if action.startswith("request_"):
        require(event.get("explicit_consent") is True, "grant without explicit consent", "unauthorized_effects")
    if env.state.status != "running":
        require(env.active_grant_count == 0, "active grant after termination", "unauthorized_effects")


def log_step(store: RunStore, coordinate: dict, env: Environment, decision, action: str,
             stream: str, loss: float | None = None) -> None:
    store.append(stream, {**coordinate, "public_observation_hash": decision.fingerprint,
                         "semantic_candidates": list(ACTIONS), "action_mask": decision.mask.tolist(),
                         "chosen_semantic_action": action, "event": env.trace[-1], "loss": loss})


def train_group(store: RunStore, plan: dict, schedule: list[dict], context: dict,
                progress: dict) -> dict:
    seed, gamma = context["seed"], context["gamma"]
    learner = BudgetRecourseDDQN(seed=seed, gamma=gamma)
    initial_hash = semantic_hash(learner.online_network.state_dict())
    graphs = {g["graph_id"]: g for g in plan["graphs"] if g["split"] == "train"}
    for cell in schedule:
        root = state_from_row(graphs[cell["graph_id"]])
        used = episode = 0
        while used < cell["transitions"]:
            tape = draw_tape(root, seed=seed, graph_id=cell["graph_id"], episode=episode, phase="train")
            env = Environment(root, tape)
            coordinate = {"phase": "train", "seed": seed, "gamma": gamma,
                          "graph_id": cell["graph_id"], "condition": "original", "episode": episode}
            store.append("auditor_train_truth", {**coordinate, "private_tape": asdict(tape)})
            explore = random.Random(seed_for("exploration", seed, cell["graph_id"], episode, "train"))
            ties = random.Random(seed_for("tie", seed, cell["graph_id"], episode, "train"))
            while env.state.status == "running" and used < cell["transitions"]:
                coordinate = {**coordinate, "step": len(env.trace)}
                progress["attempted_coordinate"] = coordinate
                decision = encode(env.state)
                epsilon = 1.0 - 0.95 * min(learner.environment_steps / 9600, 1.0)
                action = learner.select_candidate(decision, policy_mask=decision.mask, epsilon=epsilon,
                                                  exploration_rng=explore, tie_rng=ties)
                checked_step(env, decision, action)
                fields = successor_fields(env.state)
                loss = learner.observe(decision, policy_mask=decision.mask, action_candidate_id=action, **fields)
                require(loss is None or math.isfinite(loss), "nonfinite optimizer loss")
                used += 1
                progress["transitions"] += 1
                log_step(store, coordinate, env, decision, action, "train_steps", loss)
                progress["last_durable_coordinate"] = coordinate
                if progress["transitions"] % 64 == 0:
                    store.snapshot({**progress, "status": "TRAINING", "test_opened": False})
            store.append("train_episodes", {**coordinate, "success": env.state.status == "success",
                         "termination": env.state.status,
                         "budget_cutoff": env.state.status == "running",
                         "decisions": len(env.trace), "exposure": root.exposure - env.state.exposure,
                         "prompts": root.prompts - env.state.prompts,
                         "hard_counts": dict(progress["hard_counts"])})
            episode += 1
        store.append("training_cells", {**cell, "completed_transitions": used, "episodes": episode})
    total = sum(c["transitions"] for c in schedule)
    require(learner.environment_steps == total, "training transition quota mismatch")
    expected_updates = 0 if total < 256 else (total - 256) // 4 + 1
    require(learner.optimizer_steps == expected_updates, "optimizer update count mismatch")
    require(semantic_hash(learner.online_network.state_dict()) != initial_hash, "training did not change online weights")
    context = {**context, "initial_online_sha256": initial_hash}
    name = f"ddqn_seed{seed}_gamma{gamma}"
    path = store.root / (name + ".pt")
    payload = learner_payload(learner)
    metadata = save_payload(path, payload, context)
    store.save(name, metadata)
    del payload, learner
    gc.collect()
    reloaded = reload_learner(path, metadata, context)
    store.append("checkpoints", {"seed": seed, "gamma": gamma, "environment_steps": reloaded.environment_steps,
                               "optimizer_steps": reloaded.optimizer_steps, **metadata})
    progress["checkpoints"] += 1
    store.snapshot({**progress, "status": "CHECKPOINT_RELOADED", "test_opened": False})
    del reloaded
    gc.collect()
    return metadata


def evaluate(store: RunStore, plan: dict, checkpoints: dict, progress: dict, *, smoke: bool) -> list[dict]:
    phase = "train" if smoke else "validation"
    coords = evaluation_coordinates(plan, phase, smoke=smoke)
    groups: dict[tuple, list[dict]] = {}
    for coord in coords:
        key = coord["seed"], coord["method"], coord["graph_id"], coord["condition"]
        groups.setdefault(key, []).append(coord)
    graphs = {g["graph_id"]: g for g in plan["graphs"] if g["split"] == phase}
    references = references_for(phase)
    exact_rows = []
    for (seed, method, graph_id, condition), cell_coords in groups.items():
        progress["attempted_coordinate"] = {"phase": phase, "seed": seed, "method": method,
                                            "graph_id": graph_id, "condition": condition}
        learner = None
        metadata = None
        before = None
        if method.startswith("masked_ddqn"):
            gamma = 1 if method.endswith("gamma1") else 0
            metadata = checkpoints[seed, gamma]
            learner = reload_learner(store.root / metadata["file"], metadata, metadata["context"])
            before = semantic_hash(learner_payload(learner))
        root = state_from_row(graphs[graph_id], toggle=condition == "prompt_toggle")
        budget = EvaluationBudget()
        policy = frozen_policy(method, learner, budget)
        value, resource_report = exact_policy_value(root, policy, budget)
        reference = references[graph_id, condition]
        require(value <= F(reference["exact_dp"]), "exact learned policy exceeds certified V*")
        if learner is None:
            require(value == F(reference[method]), "rule changed from frozen Stage A reference")
        root_distribution = policy(root)
        exact_row = {"phase": phase, "seed": seed, "method": method, "graph_id": graph_id,
                     "condition": condition, "value": value, "exact_dp": F(reference["exact_dp"]),
                     "regret": F(reference["exact_dp"]) - value,
                     "root_action_distribution": root_distribution, "evaluator_resources": resource_report,
                     "checkpoint_sha256": None if metadata is None else metadata["sha256"]}
        exact_rows.append(exact_row)
        store.append("exact_values", exact_row)
        for coordinate in cell_coords:
            progress["attempted_coordinate"] = coordinate
            tape = draw_tape(root, seed=seed, graph_id=graph_id, episode=coordinate["episode"], phase=phase)
            env = Environment(root, tape)
            store.append("auditor_eval_truth", {**coordinate, "private_tape": asdict(tape)})
            # Method/gamma/condition excluded: matched policy-randomness coordinates.
            rng = random.Random(seed_for("eval_tie", phase, seed, graph_id, coordinate["episode"]))
            while env.state.status == "running":
                decision = encode(env.state)
                action = sample_action(policy(env.state), rng)
                checked_step(env, decision, action)
                log_step(store, {**coordinate, "step": len(env.trace) - 1}, env, decision, action, "evaluation_steps")
            row = {**coordinate, "success": env.state.status == "success",
                   "termination": env.state.status, "decisions": len(env.trace),
                   "exposure": root.exposure - env.state.exposure, "prompts": root.prompts - env.state.prompts,
                   "checkpoint_sha256": None if metadata is None else metadata["sha256"],
                   "rng_schema": RNG_SCHEMA, "hard_counts": dict(progress["hard_counts"])}
            store.append("evaluation_rows", row)
            progress["evaluation_rows"] += 1
            progress["last_durable_coordinate"] = coordinate
        if learner is not None:
            after = semantic_hash(learner_payload(learner))
            require(before == after == metadata["semantic_sha256"],
                    "evaluation changed model/optimizer/replay/RNG", "checkpoint_mismatch")
            store.append("evaluation_fingerprints", {**progress["attempted_coordinate"],
                         "before": before, "after": after, "unchanged": True})
        store.snapshot({**progress, "status": "EVALUATING", "test_opened": False})
        del learner, policy
        gc.collect()
    return exact_rows


def run(mode: str, output: Path, package_manifest: Path) -> int:
    if not sys.platform.startswith("linux"):
        raise ValueError("no local learner runs; use the authorized Linux server")
    if not output.resolve().is_relative_to(Path("/output/agenticAI").resolve()):
        raise ValueError("run output must remain inside the authorized server project")
    smoke = mode == "smoke"
    plan = load_plan()
    progress = {"transitions": 0, "checkpoints": 0, "evaluation_rows": 0,
                "last_durable_coordinate": None, "attempted_coordinate": {"phase": "preflight"},
                "hard_counts": {k: 0 for k in sorted(HARD_COUNTERS)}}
    manifest = {"schema": SCHEMA, "mode": mode, "evidence_mode": "NON_EVIDENCE" if smoke else "FORMAL",
                "started_at_utc": stamp(), "design_sha256": sha(BASE / "next_experiment_plan.json"),
                "criteria_sha256": sha(HERE / "criteria_v1.json"),
                "execution_profile_sha256": sha(HERE / "execution_profile_gpu1_formal_v1.json"),
                "physical_gpu_index": int(PHYSICAL_GPU),
                "source_manifest_sha256": sha(package_manifest), "encoder_schema": ENCODER_SCHEMA,
                "rng_schema": RNG_SCHEMA, "test_opened": False, "automatic_retry": False}
    store = RunStore(output, manifest)
    try:
        package = verify_package(package_manifest)
        store.save("source_manifest", package)
        store.save("runtime", gpu_metadata())
        schedule = training_schedule(plan, smoke=smoke)
        store.save("schedule", schedule)
        checkpoints = {}
        initial_by_seed = {}
        for seed, gamma in dict.fromkeys((c["seed"], c["gamma"]) for c in schedule):
            verify_package(package_manifest)
            cells = [c for c in schedule if (c["seed"], c["gamma"]) == (seed, gamma)]
            context = {**manifest, "seed": seed, "gamma": gamma}
            metadata = train_group(store, plan, cells, context, progress)
            initial = metadata["context"]["initial_online_sha256"]
            require(seed not in initial_by_seed or initial_by_seed[seed] == initial,
                    "gamma arms did not use matched fresh initialization")
            initial_by_seed[seed] = initial
            checkpoints[seed, gamma] = metadata
        expected_transitions = 320 if smoke else 72000
        require(progress["transitions"] == expected_transitions, "total training budget mismatch")
        exact = evaluate(store, plan, checkpoints, progress, smoke=smoke)
        verify_package(package_manifest)
        rows = store.read_verified("evaluation_rows")
        # Read all record chains before publishing a completion receipt.
        for name in store.heads:
            if name != "evaluation_rows":
                store.read_verified(name)
        if smoke:
            require(len(rows) == 2 and len(checkpoints) == 1, "smoke coverage mismatch")
            classification = None
            gate = {"status": "NON_EVIDENCE_SMOKE_COMPLETE", "test_opened": False}
        else:
            gate = validation_gate(plan, rows, {key: meta["sha256"] for key, meta in checkpoints.items()})
            values = {}
            for seed in (101, 211, 307):
                values[seed] = {}
                for method in plan["methods"]:
                    cells = [r for r in exact if r["seed"] == seed and r["method"] == method]
                    require({(r["graph_id"], r["condition"]) for r in cells}
                            == {(g, c) for g in ("br05", "br06") for c in ("original", "prompt_toggle")}
                            and len(cells) == 4, "exact evaluation cell coverage mismatch")
                    values[seed][method] = sum((r["value"] for r in cells), F(0)) / 4
                refs = references_for("validation")
                values[seed]["exact_dp"] = sum((F(r["exact_dp"]) for r in refs.values()), F(0)) / 4
            classification = classify_exact(values, progress["hard_counts"], complete=True)
            store.save("validation_exact_means", values)
        require(not (store.root / "test").exists() and not (store.root / "test_permit.json").exists(),
                "test must remain unopened")
        store.save("validation_gate" if not smoke else "smoke_gate", gate)
        if classification is not None:
            store.save("validation_classification", classification)
        status = "NON_EVIDENCE_SMOKE_COMPLETE" if smoke else "TRAIN_VALIDATION_COMPLETE_TEST_LOCKED"
        result = {**progress, "status": status, "ended_at_utc": stamp(),
                  "test_opened": False, "heads": store.heads, "gate": gate,
                  "scientific_classification": classification}
        store.save("completion", result)
        store.snapshot(result)
        print(json.dumps({"status": status, "transitions": progress["transitions"],
                          "checkpoints": progress["checkpoints"], "evaluation_rows": len(rows),
                          "hard_counts": progress["hard_counts"], "test_opened": False}), flush=True)
        return 0
    except BaseException as error:
        if isinstance(error, IntegrityError):
            progress["hard_counts"][error.counter] += 1
        store.fail(error, progress)
        print(json.dumps({"status": "STOPPED_ERROR", "error_type": type(error).__name__,
                          "test_opened": False, "retry_authorized": False}), flush=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "train-validate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    return run(args.mode, args.output, args.manifest)


if __name__ == "__main__":
    raise SystemExit(main())
