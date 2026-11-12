"""Audit records and safe output directories, without modifying learner internals."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .config import RunConfig

ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = "rl_testing.four_actions.v2"


def json_write(path: Path, data: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def new_output(path: Path) -> Path:
    resolved = path.resolve()
    allowed = (ROOT / "outputs").resolve()
    if resolved == allowed or not resolved.is_relative_to(allowed):
        raise ValueError("output must be a NEW directory underneath rl_agent_structure/outputs")
    resolved.mkdir(parents=True, exist_ok=False)
    return resolved


def protected_state() -> dict:
    """Hash experiment source; inventory external dependencies without opening .env."""
    from personal_assistant.integration.readonly import dependency_inventory
    paths = [ROOT / "run_noapi.py"]
    for name in ("src", "tests"):
        paths.extend((ROOT / name).rglob("*.py"))
    core = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}
    inventory = dependency_inventory(ROOT.parent)
    from mock_tools.sources import SOURCE_FILE
    diagnostic = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted((ROOT / "rl_testing").rglob("*.py"))}
    return {"core_sha256": core, "diagnostic_source_sha256": diagnostic,
            "wu_queries_sha256": hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest(),
            "dependency_metadata_sha256":
            hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()}


def learner_counters(policy: Any) -> dict:
    learner = getattr(policy, "learner", None)
    if learner is None:
        return {"optimizer_steps": 0, "environment_steps": 0, "replay_size": 0,
                "last_loss": None, "last_auxiliary_loss": None, "retention_applications": 0}
    return {name: getattr(learner, name) for name in (
        "optimizer_steps", "environment_steps", "replay_size", "last_loss",
        "last_auxiliary_loss", "retention_applications",
    )}


class RunLog:
    def __init__(self, config: RunConfig, output: Path | None = None):
        self.config, self.output = config, output
        self.tasks: list[dict] = []
        self.updates: list[dict] = []
        self.decisions: list[dict] = []
        self.evaluations: list[dict] = []
        self.evaluation_tasks: list[dict] = []
        self.evidence = "functional_only" if config.mode == "functional" else "real_ddqn_fixture_diagnostic"

    def event(self, kind: str, value: dict) -> None:
        # Incremental audit survives an interrupted run. Only counts/IDs; no raw tool data.
        if self.output is not None:
            with (self.output / "events.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"kind": kind, **value}, ensure_ascii=False, allow_nan=False) + "\n")

    def record_update(self, before: dict, after: dict, *, decision: int, retention_weight: float) -> None:
        count = after["optimizer_steps"] - before["optimizer_steps"]
        if count < 0:
            raise ValueError("optimizer counter moved backwards")
        if count == 0:
            return  # last_loss can be stale during warmup / skipped update steps.
        total = after["last_loss"]
        auxiliary = after.get("last_auxiliary_loss") if retention_weight else None
        values = (total,) if auxiliary is None else (total, auxiliary)
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
            raise ValueError("optimizer reported a nonfinite/missing loss")
        if retention_weight and auxiliary is None:
            raise ValueError("retention update did not report its auxiliary loss")
        row = {
            "optimizer_steps": after["optimizer_steps"], "decision": decision,
            "environment_steps": after["environment_steps"], "replay_size": after["replay_size"],
            "updates_in_observe": count, "total_loss": total, "auxiliary_loss": auxiliary,
            "td_loss_derived": total - retention_weight * auxiliary if auxiliary is not None else total,
            "loss_sampling": "last_optimizer_update_per_observe",
        }
        self.updates.append(row)
        self.event("update", row)

    def record_transition(self, transition: Any) -> None:
        from personal_assistant.contracts.permission import contract_json_round_trip
        position = transition.pre_decision.view.position
        candidate = next(c for c in transition.pre_decision.view.candidates
                         if c.candidate_id == transition.action_candidate_id)
        scope = candidate.request_scope or candidate.operation_scope
        row = {
            "transition_id": transition.transition_id, "task_id": position.task_id,
            "round": position.round_index, "decision": position.decision_index,
            "action": candidate.action.value, "candidate_id": candidate.candidate_id,
            "scope": None if scope is None else contract_json_round_trip(scope),
            "released_keys": contract_json_round_trip(candidate.release_keys),
            "active_gates_before": contract_json_round_trip(transition.pre_decision.view.active_gates),
            "reward": transition.reward if self.config.reward_weights is not None else None,
            "task_ended": transition.task_ended, "sequence_ended": transition.done,
        }
        self.decisions.append(row)
        self.event("transition", row)

    def report(self, summary: dict | None = None) -> dict:
        report = {"schema": REPORT_SCHEMA, "action_schema": "four_actions_v1",
                "evidence": self.evidence, "config": self.config.to_dict(),
                "tasks": self.tasks, "updates": self.updates, "decisions": self.decisions,
                "evaluations": self.evaluations, "evaluation_tasks": self.evaluation_tasks}
        if summary is not None:
            report["summary"] = summary
        return report

    def save(self, summary: dict) -> None:
        if self.output is None:
            raise ValueError("output directory not attached")
        json_write(self.output / "report.json", self.report(summary))
        json_write(self.output / "summary.json", summary)
