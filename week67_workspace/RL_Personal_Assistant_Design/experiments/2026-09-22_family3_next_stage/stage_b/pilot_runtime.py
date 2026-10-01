"""Minimal new-scenario runtime, reusing frozen CUDA checkpoint primitives."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import random
import re
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path
from typing import Callable

import torch

from learner_bridge import (
    ACTIONS, ENCODER_SCHEMA, EXPERIMENT_ID, MODEL_SPEC, RNG_SCHEMA,
    BudgetRecourseDDQN, State, encode, greedy_distribution,
)
from budget_recourse import ResourceLimit, Solver, legal_actions, transitions
from budget_recourse_env import CORE, WORKSPACE
from pilot_criteria import HARD_COUNTERS
from pa_rl.family3_v2_pilot_checkpoints import (
    _plain_state_mapping, _semantic_digest, _transition_mapping, _transition_from_mapping,
)

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SCHEMA = "budget_recourse_runner_v1"
CONDITIONS = ("original", "prompt_toggle")
METHODS = ("masked_ddqn_gamma1", "masked_ddqn_gamma0", "forecast_transfer_rule",
           "current_task_rule", "reservation_rule", "random_valid")
COORDINATE_KEYS = ("phase", "method", "seed", "graph_id", "condition", "episode")
Distribution = Callable[[State], dict[str, F]]
semantic_hash = _semantic_digest


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> bytes:
    def convert(x: object) -> str:
        if type(x) is F:
            return str(x)
        raise TypeError(type(x).__name__)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False, default=convert).encode("utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan() -> dict:
    return json.loads((BASE / "next_experiment_plan.json").read_text(encoding="utf-8"))


def training_schedule(plan: dict, *, smoke: bool) -> list[dict]:
    graphs = [g for g in plan["graphs"] if g["split"] == "train"]
    if len(graphs) != 5:
        raise ValueError("fixed five training graphs required")
    return [{"seed": seed, "gamma": gamma, "graph_id": graph["graph_id"],
             "condition": "original", "transitions": 64 if smoke else 2400}
            for seed in ((101,) if smoke else (101, 211, 307))
            for gamma in ((1,) if smoke else (1, 0)) for graph in graphs]


def evaluation_coordinates(plan: dict, phase: str, *, smoke: bool) -> list[dict]:
    if (smoke and phase != "train") or (not smoke and phase != "validation"):
        raise ValueError("this runner does not open test; smoke is train-only")
    graphs = [g for g in plan["graphs"] if g["split"] == phase]
    if smoke:
        graphs = graphs[:1]
    methods = ("masked_ddqn_gamma1",) if smoke else METHODS
    return [{"phase": phase, "method": method, "seed": seed, "graph_id": graph["graph_id"],
             "condition": condition, "episode": episode}
            for seed in ((101,) if smoke else (101, 211, 307)) for method in methods
            for graph in graphs for condition in (("original",) if smoke else CONDITIONS)
            for episode in range(2 if smoke else 50)]


def successor_fields(state: State) -> dict:
    done = state.status != "running"
    decision = None if done else encode(state)
    return {"reward": int(state.status == "success"), "done": done,
            "next_decision": decision, "next_policy_mask": None if done else decision.mask}


def current_rss_bytes() -> int:
    """Current resident memory, never the process-lifetime high-water mark."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not get_info(current(), ctypes.byref(counters), counters.cb):
            raise OSError("cannot read current process RSS")
        return int(counters.WorkingSetSize)
    pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
    return pages * os.sysconf("SC_PAGE_SIZE")


class EvaluationBudget:
    """Per-cell bound; CUDA host-runtime allocation is recorded separately."""
    def __init__(self) -> None:
        self.started = time.monotonic()
        self.baseline_rss = current_rss_bytes()
        self.peak_rss = self.baseline_rss
        self.states: set[State] = set()

    def check(self, state: State | None = None) -> None:
        if state is not None and state.status == "running":
            self.states.add(state)
        self.peak_rss = max(self.peak_rss, current_rss_bytes())
        if (len(self.states) > 100000 or time.monotonic() - self.started > 60
                or self.peak_rss - self.baseline_rss > 512 * 1024**2):
            raise ResourceLimit("Stage B per-cell evaluator bound reached; stop without retry")

    def report(self) -> dict:
        return {"states": len(self.states), "seconds": time.monotonic() - self.started,
                "baseline_current_rss_bytes": self.baseline_rss, "sampled_peak_current_rss_bytes": self.peak_rss,
                "max_states": 100000, "max_seconds": 60, "additional_peak_rss_limit_mib": 512}


def checked_distribution(state: State, distribution: dict[str, F]) -> dict[str, F]:
    valid = legal_actions(state)
    if (not distribution or any(a not in valid or type(p) is not F or p <= 0
                                for a, p in distribution.items())
            or sum(distribution.values(), F(0)) != 1):
        raise ValueError("policy must assign exact unit probability to legal actions only")
    return distribution


def exact_policy_value(initial: State, policy: Distribution,
                       budget: EvaluationBudget | None = None) -> tuple[F, dict]:
    budget = budget or EvaluationBudget()
    cache: dict[State, F] = {}
    def visit(state: State) -> F:
        budget.check(state)
        if state.status != "running":
            return F(state.status == "success")
        if state not in cache:
            distribution = checked_distribution(state, policy(state))
            cache[state] = sum((mass * chance * visit(child)
                               for action, mass in distribution.items()
                               for chance, child in transitions(state, action)), F(0))
        return cache[state]
    return visit(initial), budget.report()


def frozen_policy(method: str, learner: BudgetRecourseDDQN | None,
                  budget: EvaluationBudget) -> Distribution:
    solver = Solver(budget)
    cache: dict[State, dict[str, F]] = {}
    def policy(state: State) -> dict[str, F]:
        budget.check(state)
        if state not in cache:
            if method.startswith("masked_ddqn_"):
                if learner is None:
                    raise ValueError("DDQN evaluation requires its frozen checkpoint")
                decision = encode(state)
                cache[state] = greedy_distribution(decision, learner.scores(decision))
            elif method == "random_valid":
                valid = legal_actions(state)
                cache[state] = {a: F(1, len(valid)) for a in valid}
            else:
                cache[state] = {solver.choose(method, state): F(1)}
        return checked_distribution(state, cache[state])
    return policy


def sample_action(distribution: dict[str, F], rng: random.Random) -> str:
    # All built-in distributions are uniform ties or deterministic; no float CDF.
    probabilities = set(distribution.values())
    if probabilities != {F(1, len(distribution))}:
        raise ValueError("this pilot supports only deterministic or uniform-tie policies")
    return rng.choice(tuple(distribution))


class RunStore:
    """One fresh directory, immutable evidence and chained durable records."""
    def __init__(self, root: Path, manifest: dict) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        self.heads: dict[str, tuple[int, str | None]] = {}
        self.save("run_manifest", manifest)
        self.snapshot({"status": "STARTED", "started_at_utc": stamp(),
                       "last_durable_coordinate": None, "test_opened": False})

    def _path(self, name: str, suffix: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
            raise ValueError("flat artifact name required")
        return self.root / (name + suffix)

    def save(self, name: str, value: object) -> None:
        with self._path(name, ".json").open("xb") as output:
            output.write(canonical(value) + b"\n")
            output.flush()
            os.fsync(output.fileno())

    def snapshot(self, value: dict) -> None:
        path = self.root / "status.next"
        with path.open("wb") as output:
            output.write(canonical({**value, "updated_at_utc": stamp()}) + b"\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(path, self.root / "status.json")

    def append(self, name: str, value: dict) -> dict:
        count, previous = self.heads.get(name, (0, None))
        body = {"index": count, "previous": previous, "payload": value}
        digest = hashlib.sha256(canonical(body)).hexdigest()
        record = {**body, "sha256": digest}
        with self._path(name, ".jsonl").open("ab") as output:
            output.write(canonical(record) + b"\n")
            output.flush()
            os.fsync(output.fileno())
        self.heads[name] = count + 1, digest
        return record

    def read_verified(self, name: str) -> list[dict]:
        rows = []
        previous = None
        with self._path(name, ".jsonl").open(encoding="utf-8") as source:
            for index, line in enumerate(source):
                record = json.loads(line)
                digest = record.pop("sha256")
                if (record["index"] != index or record["previous"] != previous
                        or hashlib.sha256(canonical(record)).hexdigest() != digest):
                    raise ValueError("record chain mismatch")
                previous = digest
                rows.append(record["payload"])
        if (len(rows), previous) != self.heads[name]:
            raise ValueError("record count/head mismatch")
        return rows

    def fail(self, error: BaseException, coordinate: dict) -> None:
        failure = {"status": "STOPPED_ERROR", "ended_at_utc": stamp(),
                   "error_type": type(error).__name__, "error": str(error),
                   "traceback": "".join(traceback.format_exception(error)),
                   "last_durable_coordinate": coordinate, "test_opened": False,
                   "retry_authorized": False, "heads": self.heads}
        self.save("failure", failure)
        self.snapshot(failure)


def save_payload(path: Path, payload: dict, context: dict) -> dict:
    plain = _plain_state_mapping(payload)
    archive = {"schema": SCHEMA, "context": context, "payload": plain}
    buffer = io.BytesIO()
    torch.save(archive, buffer)
    with path.open("xb") as output:
        output.write(buffer.getvalue())
        output.flush()
        os.fsync(output.fileno())
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha(path),
            "semantic_sha256": semantic_hash(plain), "context": context}


def load_payload(path: Path, metadata: dict, context: dict) -> dict:
    if (metadata["context"] != context or metadata["bytes"] != path.stat().st_size
            or metadata["sha256"] != sha(path)):
        raise ValueError("checkpoint context/file mismatch")
    archive = torch.load(path, map_location="cpu", weights_only=True)
    if archive["schema"] != SCHEMA or archive["context"] != context:
        raise ValueError("checkpoint schema/context mismatch")
    payload = archive["payload"]
    if semantic_hash(payload) != metadata["semantic_sha256"]:
        raise ValueError("checkpoint semantic mismatch")
    return payload


def learner_payload(learner: BudgetRecourseDDQN) -> dict:
    learner.require_execution_device("cuda")
    return {"model_spec": asdict(learner.model_spec), "hyperparameters": asdict(learner.hyperparameters),
            "online": _plain_state_mapping(learner.online_network.state_dict()),
            "target": _plain_state_mapping(learner.target_network.state_dict()),
            "optimizer": _plain_state_mapping(learner._optimizer.state_dict()),
            "replay": [_transition_mapping(t) for t in learner._buffer._items],
            "replay_capacity": learner._buffer._capacity, "replay_cursor": learner._buffer._cursor,
            "replay_rng": learner._buffer._rng.getstate(), "learner_rng": learner._rng.getstate(),
            "environment_steps": learner.environment_steps, "optimizer_steps": learner.optimizer_steps,
            "last_loss": learner.last_loss, "online_training": learner.online_network.training,
            "target_training": learner.target_network.training}


def reload_learner(path: Path, metadata: dict, context: dict) -> BudgetRecourseDDQN:
    payload = load_payload(path, metadata, context)
    learner = BudgetRecourseDDQN(seed=context["seed"], gamma=context["gamma"])
    if payload["model_spec"] != asdict(MODEL_SPEC) or payload["hyperparameters"] != asdict(learner.hyperparameters):
        raise ValueError("checkpoint model/hyperparameters mismatch")
    learner.online_network.load_state_dict(payload["online"], strict=True)
    learner.target_network.load_state_dict(payload["target"], strict=True)
    learner._optimizer.load_state_dict(payload["optimizer"])
    learner._buffer._items = [_transition_from_mapping(t) for t in payload["replay"]]
    learner._buffer._cursor = payload["replay_cursor"]
    if learner._buffer._capacity != payload["replay_capacity"]:
        raise ValueError("checkpoint replay capacity mismatch")
    learner._buffer._rng.setstate(payload["replay_rng"])
    learner._rng.setstate(payload["learner_rng"])
    learner.environment_steps = payload["environment_steps"]
    learner.optimizer_steps = payload["optimizer_steps"]
    learner.last_loss = payload["last_loss"]
    learner.online_network.train(payload["online_training"])
    learner.target_network.train(payload["target_training"])
    if semantic_hash(learner_payload(learner)) != metadata["semantic_sha256"]:
        raise ValueError("reloaded learner differs from saved full training state")
    return learner


def validation_gate(plan: dict, rows: list[dict], checkpoints: dict) -> dict:
    expected = {tuple(c[k] for k in COORDINATE_KEYS)
                for c in evaluation_coordinates(plan, "validation", smoke=False)}
    actual = [tuple(r[k] for k in COORDINATE_KEYS) for r in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("validation missing/duplicate/foreign coordinate")
    if set(checkpoints) != {(s, g) for s in (101, 211, 307) for g in (0, 1)}:
        raise ValueError("six final checkpoint coordinates required")
    if any(not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in checkpoints.values()):
        raise ValueError("checkpoint fingerprints missing")
    for row in rows:
        counts = row["hard_counts"]
        if set(counts) != HARD_COUNTERS or any(type(v) is not int or v != 0 for v in counts.values()):
            raise ValueError("nonzero/malformed hard integrity counts")
    return {"status": "READY_FOR_TEST_REVIEW", "validation_rows": len(rows),
            "checkpoints": len(checkpoints), "performance_filtered": False,
            "test_opened": False, "test_execution_authorized": False}


def references_for(phase: str) -> dict:
    # Evaluator-only reference, never passed into learner selection or observe.
    with (BASE / "stage_a/evidence/preflight_v0/values.csv").open(encoding="utf-8") as source:
        return {(r["graph_id"], r["condition"]): r for r in csv.DictReader(source) if r["split"] == phase}


def verify_package(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["files"]
    required = {
        (p.relative_to(WORKSPACE)).as_posix()
        for p in [HERE / "pilot_runtime.py", HERE / "run_learner_pilot.py", HERE / "learner_bridge.py",
                  HERE / "pilot_criteria.py", HERE / "criteria_v1.json", HERE / "execution_profile_gpu1_formal_v1.json",
                  BASE / "next_experiment_plan.json",
                  BASE / "stage_a/budget_recourse.py", BASE / "stage_a/budget_recourse_env.py",
                  BASE / "stage_a/evidence/preflight_v0/values.csv"]
    }
    listed = {e["path"] for e in entries}
    if len(listed) != len(entries) or not required <= listed:
        raise ValueError("source manifest omits required runner inputs")
    for entry in entries:
        path = (WORKSPACE / entry["path"]).resolve()
        if not path.is_relative_to(WORKSPACE.resolve()) or not path.is_file() or sha(path) != entry["sha256"]:
            raise ValueError("frozen package file mismatch")
    # All imported legacy Python sources, including serialization helpers, must be frozen.
    if any(p.relative_to(WORKSPACE).as_posix() not in listed for p in (CORE / "src/pa_rl").glob("*.py")):
        raise ValueError("legacy source missing from package manifest")
    return manifest
