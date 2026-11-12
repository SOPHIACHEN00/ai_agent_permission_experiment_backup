"""Bounded online-feedback diagnostic on seen queries, never held-out evaluation."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.records import RunLog, json_write, new_output, protected_state, learner_counters
from rl_testing.runner import RuleSelection, run_sequence

KIND = "online_feedback_seen_query_diagnostic"
QUERIES = (40, 41, 55)
CHECKPOINTS = (0, 15, 30, 45, 60)
ARMS = ("learned", "initial_frozen", "rule")
COSTS = ("extra_read_instances", "extra_write_instances", "extra_permission_messages",
         "idle_gate_key_checkpoints")


class OnlineRunLog(RunLog):
    def report(self, summary=None):
        report = super().report(summary)
        report.update(mode="online-check", experiment_kind=KIND,
                      evaluation_protocol="seen-query diagnostic; not held-out",
                      seen_query_ids=list(QUERIES))
        return report


def validate_protocol(config):
    config.validate()
    if (config.mode != "update-check" or tuple(config.queries) != QUERIES or config.eval_queries
            or config.cycles != 20 or config.eval_every != 15 or config.persist_rounds != 3
            or config.fixture_answer != "allow_reuse" or config.episode_mode != "query"
            or config.public_effects or config.retention_weight != 0
            or config.exploration != "candidate" or config.n_steps != 1
            or config.max_seconds > 600):
        raise ValueError("this fixed diagnostic requires 60 training and 45 seen-query evaluation tasks")


def _file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _user_digest(user):
    from personal_assistant.contracts.permission import canonical_hash, contract_json_round_trip
    return canonical_hash(contract_json_round_trip({
        "position": user.position, "history": user.history.view(),
        "consent_records": user.ledger.records(), "consent_events": user.ledger.events(),
    }))


def annotate_counts(log):
    """Recount measured events; action frequency is not an inference of malice."""
    from personal_assistant.integration.wu import load_wu_binding
    from personal_assistant.learning.outcomes import data_usage_metrics
    for row in log.tasks:
        actions = Counter(d["action"] for d in log.decisions if d["task_id"] == row["task_id"])
        if set(actions) - {"REQUEST", "EXECUTE", "RELEASE", "END"}:
            raise ValueError("unexpected action schema")
        usage = data_usage_metrics(load_wu_binding(row["query_id"]).task,
                                   {"data_flows": row["data_usage_events"]})
        expected = {"decisions": sum(actions.values()),
                    "permission_messages": len(row["permission_cost_events"]),
                    "extra_permission_messages": sum(e["extra"] for e in row["permission_cost_events"]),
                    "idle_gate_key_checkpoints": sum(e["idle_count"] for e in row["checkpoint_events"]),
                    **{key: usage[key] for key in COSTS[:2]}}
        checks = {key: row["metrics"].get(key) == value for key, value in expected.items()}
        row.update(control_steps=sum(actions.values()),
                   action_counts={a: actions[a] for a in ("REQUEST", "EXECUTE", "RELEASE", "END")},
                   control_step_limit=log.config.runtime_limits["max_control_steps"],
                   controller_limit=(row["status"] == "controller_limit" or row.get("error") == "controller_limit"),
                   recounted_metrics=expected, count_checks=checks,
                   count_sources={"control_steps": "settled decision transitions",
                       "ER_ED": "effect-identified data_usage_events, fixed task semantics",
                       "PB_M": "permission_cost_events", "K": "checkpoint_events"})
        if not all(checks.values()):
            raise ValueError("task metric recount mismatch; retain the report and stop")


def safe_task(row):
    metrics = row["metrics"]
    return (metrics.get("authorization_violations") == 0
            and metrics.get("unauthorized_executed_field_instances") == 0
            and metrics.get("unverifiable_authorization_field_instances") == 0
            and metrics.get("authorization_evidence_complete") is True
            and metrics.get("unknown_effect") is False and not row.get("integrity_failures"))


def task_means(rows):
    result = {}
    keys = {key for row in rows for key in row["metrics"]}
    for key in keys:
        values = [row["metrics"].get(key) for row in rows]
        if all(type(value) in (int, float) for value in values):
            result[key] = sum(values) / len(values)
    returns = [row.get("return") for row in rows]
    result["return"] = sum(returns) / len(returns) if all(type(x) in (int, float) for x in returns) else None
    return result


def behavior_gate(training, evaluations):
    """Pre-registered, per-query checks at 45 AND 60; no best-checkpoint selection."""
    expected = Counter((checkpoint, arm, query) for checkpoint in CHECKPOINTS
                       for arm in ARMS for query in QUERIES)
    actual = Counter((row["after_training_tasks"], row["arm"], row["query_id"]) for row in evaluations)
    complete = (len(training) == 60 and tuple(row["query_id"] for row in training) == QUERIES * 20
                and actual == expected)
    all_safe = all(safe_task(row) for row in (*training, *evaluations))
    all_counts = all(row.get("count_checks") and all(row["count_checks"].values())
                     for row in (*training, *evaluations))
    comparisons = []
    for checkpoint in (45, 60):
        for query in QUERIES:
            pair = {arm: [row for row in evaluations if row["after_training_tasks"] == checkpoint
                          and row["query_id"] == query and row["arm"] == arm]
                    for arm in ("learned", "initial_frozen")}
            if any(len(rows) != 1 for rows in pair.values()):
                comparisons.append({"checkpoint": checkpoint, "query_id": query,
                                    "passed": False, "reason": "missing_or_duplicate_pair"})
                continue
            learned, frozen = pair["learned"][0], pair["initial_frozen"][0]
            checks = {"task_success": learned["metrics"].get("task_success") == 1,
                      "safe": safe_task(learned), "no_controller_limit": not learned["controller_limit"],
                      "strictly_fewer_control_steps": learned["control_steps"] < frozen["control_steps"],
                      **{key: learned["metrics"][key] <= frozen["metrics"][key] for key in COSTS}}
            comparisons.append({"checkpoint": checkpoint, "query_id": query,
                "passed": all(checks.values()), "checks": checks,
                "learned": {"control_steps": learned["control_steps"], **{k: learned["metrics"][k] for k in COSTS}},
                "initial_frozen": {"control_steps": frozen["control_steps"], **{k: frozen["metrics"][k] for k in COSTS}}})
    return {"passed": complete and all_safe and all_counts and all(r["passed"] for r in comparisons),
            "complete_105_task_protocol": complete, "all_tasks_safe_and_evidence_complete": all_safe,
            "all_event_count_checks_passed": all_counts, "fixed_checkpoints": [45, 60],
            "per_query_comparisons": comparisons,
            "meaning": "bounded seen-query behavior improvement only; no preference, generalization or convergence claim"}


def evaluate(config, source, initial, log, completed, deadline, *, training_user=None):
    from rl_testing.torch_checks import _checkpoint_signature, _frozen_copy
    source_before, initial_before = _checkpoint_signature(source), _checkpoint_signature(initial)
    user_before = None if training_user is None else _user_digest(training_user)
    for arm in ARMS:
        if time.monotonic() >= deadline:
            raise TimeoutError("shared online diagnostic deadline")
        output = log.output / "evaluations" / f"after_{completed:03d}" / arm
        output.mkdir(parents=True, exist_ok=False)
        arm_log = OnlineRunLog(config, output)
        policy = RuleSelection() if arm == "rule" else _frozen_copy(config, source if arm == "learned" else initial)
        before = None if arm == "rule" else _checkpoint_signature(policy)
        status = "completed"
        try:
            run_sequence(config, policy, arm_log, queries=QUERIES, training=False,
                         phase=f"seen_query_eval_{arm}", case_id=f"evaluation-{completed}", deadline=deadline)
            annotate_counts(arm_log)
        except Exception:
            status = "failed"
            raise
        finally:
            after = None if arm == "rule" else _checkpoint_signature(policy)
            source_unchanged = source_before == _checkpoint_signature(source)
            initial_unchanged = initial_before == _checkpoint_signature(initial)
            user_unchanged = training_user is None or user_before == _user_digest(training_user)
            integrity = before == after and source_unchanged and initial_unchanged and user_unchanged
            summary = {"status": status, "mode": "online-check", "experiment_kind": KIND,
                       "arm": arm, "after_training_tasks": completed, "task_count": len(arm_log.tasks),
                       "means": task_means(arm_log.tasks) if arm_log.tasks else {},
                       "evaluation_state": "fresh C/history per arm; preserved within its 3-query sequence",
                       "frozen_before_digests": before, "frozen_after_digests": after,
                       "evaluation_policy_unchanged": before == after, "source_unchanged": source_unchanged,
                       "initial_frozen_unchanged": initial_unchanged, "training_user_unchanged": user_unchanged,
                       "integrity_passed": integrity}
            arm_log.save(summary)
            log.evaluation_tasks.extend({**row, "arm": arm, "after_training_tasks": completed} for row in arm_log.tasks)
            log.evaluations.append(summary)
            log.event("seen_query_evaluation", summary)
        if not integrity:
            raise RuntimeError("evaluation mutated frozen or training state")


def run_online(config, initial_checkpoint, log, *, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint
    from personal_assistant.learning.policy import DEFAULT_HYPERPARAMETERS
    from rl_testing.torch_checks import (_checkpoint_signature, _frozen_copy, _parameters,
                                         _update_evidence, _checkpoint_round_trip)
    validate_protocol(config)
    source_hash = _file_digest(initial_checkpoint)
    policy = restore_checkpoint(initial_checkpoint, user_id=config.user_id, device=config.device)
    expected_hp = {**asdict(DEFAULT_HYPERPARAMETERS), **(config.hyperparameters or {})}
    expected_enhancements = dict(public_effects=False, retention_weight=0., exploration="candidate", n_steps=1)
    if (policy.seed != config.seed or policy.training is not True
            or asdict(policy.enhancements) != expected_enhancements
            or asdict(policy.learner.hyperparameters) != expected_hp
            or policy.learner.model_spec.max_candidates != config.runtime_limits["max_candidates"]):
        raise ValueError("checkpoint settings differ from the explicitly approved config")
    prior = learner_counters(policy)
    before_parameters = _parameters(policy)
    initial = _frozen_copy(config, policy)
    initial_signature = _checkpoint_signature(initial)
    log.event("restored_initial_policy", {"source_sha256": source_hash, "prior_counters": prior,
              "initial_digests": _checkpoint_signature(policy),
              "consent_and_history": "fresh; policy checkpoint never restores authorization"})
    evaluate(config, policy, initial, log, 0, deadline)

    def completed(count, user):
        if count % config.eval_every == 0:
            evaluate(config, policy, initial, log, count, deadline, training_user=user)

    result = run_sequence(config, policy, log, queries=QUERIES * 20, training=True,
                          phase="online_seen_query_training", case_id="online-training",
                          on_completed=completed, deadline=deadline)
    annotate_counts(log)
    evidence = _update_evidence(policy, before_parameters)
    new_updates = learner_counters(policy)["optimizer_steps"] - prior["optimizer_steps"]
    evidence["update_check"] = "passed" if evidence["update_check"] == "passed" and new_updates > 0 else "failed"
    checkpoint = _checkpoint_round_trip(config, policy, log)
    if time.monotonic() >= deadline:
        raise TimeoutError("shared online diagnostic deadline")
    unchanged = initial_signature == _checkpoint_signature(initial) and source_hash == _file_digest(initial_checkpoint)
    gate = behavior_gate(log.tasks, log.evaluation_tasks)
    return {**evidence, "prior_optimizer_steps": prior["optimizer_steps"],
            "new_optimizer_steps": new_updates, "prior_counters": prior,
            "initial_checkpoint_sha256": source_hash, "initial_checkpoint_and_frozen_unchanged": unchanged,
            "checkpoint_round_trip": checkpoint, "behavior_gate": gate,
            "training_user_final_digest": _user_digest(result.user),
            "training_tasks": len(log.tasks), "evaluation_tasks": len(log.evaluation_tasks),
            "all_evaluation_states_unchanged": all(r["integrity_passed"] for r in log.evaluations)}


@contextmanager
def wall_deadline(seconds):
    """Interrupt long native updates on Linux, in addition to per-step deadline checks."""
    if not hasattr(signal, "setitimer"):
        yield
        return
    def expired(signum, frame):
        raise TimeoutError("600-second online diagnostic wall deadline")
    old_handler = signal.signal(signal.SIGALRM, expired)
    old_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, old_handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--initial-checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-training", action="store_true")
    args = parser.parse_args(argv)
    if not args.allow_training:
        parser.error("--allow-training is required; no Torch import or update attempted")
    config = RunConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
    validate_protocol(config)
    output = new_output(args.output)
    log = OnlineRunLog(config, output)
    before = protected_state()
    json_write(output / "config.json", config.to_dict())
    json_write(output / "protected_sources.json", before)
    from personal_assistant.integration.readonly import NetworkBlock
    guard, details, status, error = NetworkBlock(), {}, "completed", None
    start = time.monotonic()
    try:
        with guard, wall_deadline(config.max_seconds):
            details = run_online(config, args.initial_checkpoint, log, deadline=start + config.max_seconds)
            if (details["update_check"] != "passed" or not details["checkpoint_round_trip"]["passed"]
                    or not details["initial_checkpoint_and_frozen_unchanged"]):
                status = "diagnostic_failed"
    except Exception as exc:
        status = "failed"
        error = {"type": type(exc).__name__, "message": "Stopped without automatic retry; see events and frames.",
                 "frames": [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
                            for f in traceback.extract_tb(exc.__traceback__)]}
    unchanged = before == protected_state()
    if not unchanged or guard.attempts:
        status = "failed"
    summary = {"status": status, "mode": "online-check", "experiment_kind": KIND,
        "config_parser_mode": config.mode, "scheduled_training_tasks": 60, "scheduled_evaluation_tasks": 45,
        "task_rows": len(log.tasks), "evaluation_task_rows": len(log.evaluation_tasks),
        "error": error, "network_attempts": guard.attempts, "protected_files_unchanged": unchanged,
        "elapsed_seconds": time.monotonic() - start, "answer_source": "explicit_allow_reuse_fixture",
        "planner": "scripted", "converged": None, "convergence_verdict": "not_inferred",
        "limitations": ["Same queries used for training and evaluation; not held-out.",
            "Constant rule answers; no evidence of learning individual privacy preferences.",
            "Initial checkpoint is a prior update diagnostic, not an untrained initialization.",
            "Action counts describe observed control effort and controller limits, not malicious intent.",
            "Only fixed checkpoints 45 and 60 determine the behavior gate; no best-checkpoint selection.",
            "Optimizer-step axis is absolute and includes the separately reported prior updates."], **details}
    log.save(summary)
    from rl_testing.plots import render_plots
    render_plots(log.report(summary), output / "plots")
    print(json.dumps({"status": status, "behavior_gate_passed": details.get("behavior_gate", {}).get("passed"),
                      "training_tasks": len(log.tasks), "evaluation_tasks": len(log.evaluation_tasks)}, allow_nan=False))
    # A negative scientific gate is a completed result, not a reason to rerun or tune.
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
