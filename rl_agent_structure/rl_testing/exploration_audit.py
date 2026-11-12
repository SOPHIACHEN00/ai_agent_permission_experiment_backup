"""Independent receipt audit for the from-scratch exploration comparison.

Uses recorded actions and effects, not Q values or a learned policy. No torch,
training, API calls, or edits to input reports are performed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

SEEDS = (3, 7, 11)
ARMS = ("candidate", "family")
QUERIES = (40, 41, 55)
CHECKPOINTS = (0, 20, 40, 60)
ACTIONS = {"REQUEST", "EXECUTE", "RELEASE", "END"}
COUNTS = {
    "ER": "extra_read_instances", "ED": "extra_write_instances",
    "M": "extra_permission_messages", "K": "idle_gate_key_checkpoints",
    "PB": "permission_messages", "control_steps": "decisions",
}
EXPECTED_REWARD = {"success": 1., "failure": 1., "extra_read": .01,
                   "extra_write": .01, "extra_question": .01, "retention": .001}
EXPECTED_LIMITS = {"max_control_steps": 64, "max_planner_turns": 16,
                   "max_permission_messages": 16, "max_active_gates": 16,
                   "max_checkpoints": 8, "max_read_instances": 32,
                   "max_write_instances": 32, "max_release_steps": 32,
                   "max_candidates": 128}


class AuditFailure(ValueError):
    """A short public check identifier, never an arbitrary data payload."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AuditFailure(code)


def close(left: float, right: float) -> bool:
    return (type(left) in (int, float) and math.isfinite(left)
            and math.isclose(left, right, rel_tol=1e-7, abs_tol=1e-7))


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        result = json.load(handle)
    require(isinstance(result, dict), "report.not_object")
    return result


def safe_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), "path.invalid")
    result = (root / relative).resolve()
    require(result.is_relative_to(root.resolve()), "path.outside_results")
    return result


@lru_cache(maxsize=3)
def task_definition(query: int):
    from personal_assistant.integration.wu import load_wu_binding
    return load_wu_binding(query).task


def traces_for(report: dict, directory: Path) -> list[dict]:
    for name in ("action_scores", "control_trace", "traces"):
        if name in report:
            require(isinstance(report[name], list), "trace.not_list")
            return report[name]
    rows = []
    with (directory / "events.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event.get("kind") == "action_scores":
                rows.append(event)
    return rows


def audit_task(row: dict, decisions: list[dict], traces: list[dict]) -> dict:
    metrics = row["metrics"]
    require(row["query_id"] in QUERIES, "task.query")
    require(not row.get("integrity_failures"), "task.integrity")
    require(metrics["task_success"] + metrics["task_failure"] == 1, "task.unsettled")
    require(metrics.get("authorization_evidence_complete") is True, "task.authority_evidence")
    require(metrics.get("ledger_replay_verified") is True, "task.ledger_replay")
    require(metrics.get("monitor_audit_verified") is True, "task.monitor_replay")
    require(not metrics.get("unknown_effect"), "task.unknown_effect")
    for key in ("unauthorized_executed_field_instances", "unverifiable_authorization_field_instances",
                "authorization_violations"):
        require(metrics.get(key) == 0, "task.unauthorized_or_unverified")
    require(decisions and all(d["action"] in ACTIONS for d in decisions), "task.actions")
    require(sum(bool(d["sequence_ended"]) for d in decisions) == 1
            and decisions[-1]["sequence_ended"] is True, "task.query_episode_end")

    messages = row["permission_cost_events"]
    require(len({m["message_id"] for m in messages}) == len(messages), "task.duplicate_message")
    questions = sum(bool(m["extra"]) for m in messages)
    checkpoints = row["checkpoint_events"]
    require(len({c["checkpoint_id"] for c in checkpoints}) == len(checkpoints), "task.duplicate_checkpoint")
    idle = 0
    for checkpoint in checkpoints:
        actual = set(checkpoint["active"]) - set(checkpoint["needed"])
        require(actual == set(checkpoint["idle"])
                and len(actual) == checkpoint["idle_count"], "task.idle_gate_recount")
        idle += len(actual)

    flow_map = {}
    for flow in row["data_usage_events"]:
        identity = tuple(flow.get(k) for k in
                         ("effect_id", "step_id", "direction", "tool", "recipient", "field"))
        require(identity not in flow_map or flow_map[identity] == flow, "task.conflicting_flow")
        flow_map[identity] = flow
    flows = list(flow_map.values())
    committed = [p for p in row["execution_checks"] if p.get("tool_effect_status") == "committed"]
    for proof in committed:
        require(proof.get("pre_execution_authorized") is True, "receipt.not_authorized")
        require(proof.get("checks") and all(value is True for value in proof["checks"].values()),
                "receipt.failed_check")
    for flow in flows:
        proofs = [p for p in committed if p.get("effect_id") == flow["effect_id"]]
        require(len(proofs) == 1, "flow.authorization_identity")
        proof = proofs[0]
        direction = "read" if proof["operation"] == "read" else "write"
        require(flow["tool"] == proof["tool"] and flow["recipient"] == proof["recipient"]
                and flow["direction"] == direction
                and flow["step_id"] == proof["task_step_id"]
                and flow["field"] in proof["authorized_fields"], "flow.authorized_scope")

    task = task_definition(row["query_id"])
    by_step = defaultdict(list)
    for flow in flows:
        by_step[flow["step_id"]].append(flow)
    declared = {step.step_id for step in task.steps}
    require(set(by_step) <= declared, "flow.undeclared_step")
    extras = Counter()
    for step in task.steps:
        specification = task.oracle.expectations[step.step_id]
        direction = specification["direction"]
        used = by_step[step.step_id]
        require(all(f["direction"] == direction for f in used), "flow.direction")
        fields = {f["field"] for f in used}
        universe = set().union(*(set(s.data_attributes) for s in step.operation_scopes))
        require(fields <= universe, "flow.undeclared_field")
        alternatives = specification.get("alternative_required_fields") or (specification["required_fields"],)
        alternatives = tuple(frozenset(x) for x in alternatives)
        necessary = max(alternatives, key=lambda need: (need <= fields, len(need & fields)))
        extras[direction] += sum(f["field"] not in necessary for f in used)
        if metrics["task_success"]:
            require(any(need <= fields for need in alternatives), "success.missing_required_fields")
    recounted = {"ER": extras["read"], "ED": extras["write"], "M": questions,
                 "K": idle, "PB": len(messages), "control_steps": len(decisions)}
    for key, metric in COUNTS.items():
        require(recounted[key] == metrics[metric], "task.metric_recount")
    expected = 2 * metrics["task_success"] - 1 - .01 * (
        recounted["ER"] + recounted["ED"] + questions) - .001 * idle
    require(close(row["return"], expected), "task.return")
    require(close(math.fsum(d["reward"] for d in decisions), expected), "task.transition_rewards")

    executions = [t for t in traces if t["selected_action"] == "EXECUTE"]
    executed_ids = {d["transition_id"] for d in decisions if d["action"] == "EXECUTE"}
    require({t["token"] for t in executions} == executed_ids, "task.execute_trace")
    for trace in executions:
        budget = trace["runtime_budgets"]
        require(type(budget["release_steps_used"]) is int
                and type(budget["release_step_limit"]) is int, "trace.release_budget")
    timely = bool(metrics["task_success"] and committed and executions and all(
        t["runtime_budgets"]["release_steps_used"] < t["runtime_budgets"]["release_step_limit"]
        for t in executions))
    return {**recounted, "query_id": row["query_id"], "return": expected,
            "task_success": metrics["task_success"], "timely": timely,
            "actual_field_instances": len(flows), "committed_effects": len(committed)}


def audit_report(directory: Path, summaries: list[dict], *, training: bool) -> dict:
    report = read_json(directory / "report.json")
    require(report.get("action_schema") == "four_actions_v1", "report.action_schema")
    config = report["config"]
    require(config["reward_weights"] == EXPECTED_REWARD, "report.reward_changed")
    require(config["runtime_limits"] == EXPECTED_LIMITS, "report.runtime_limits_changed")
    require(config["episode_mode"] == "query", "report.episode_mode")
    require(config["fixture_answer"] == "allow_reuse", "report.fixture")
    require(config["public_effects"] is False and config["retention_weight"] == 0,
            "report.other_enhancements")
    require(report["tasks"] and len(report["tasks"]) == len(summaries), "report.task_count")
    expected_queries = QUERIES * 20 if training else QUERIES
    require(tuple(t["query_id"] for t in report["tasks"]) == expected_queries, "report.task_order")
    traces = traces_for(report, directory)
    results = []
    for index, (task, summary) in enumerate(zip(report["tasks"], summaries), 1):
        task_id = task["task_id"]
        decisions = [d for d in report["decisions"] if d["task_id"] == task_id]
        task_traces = [t for t in traces if t["task_id"] == task_id]
        calculated = audit_task(task, decisions, task_traces)
        for key in (*COUNTS, "query_id", "task_success", "timely"):
            require(summary.get(key) == calculated[key], "summary.metric_mismatch")
        require(close(summary["return"], calculated["return"]), "summary.return")
        if training:
            require(summary.get("index") == index, "summary.training_index")
        else:
            require(task["epsilon"] == 0 and task_traces, "evaluation.not_greedy")
            first = task_traces[0]["state_features"]
            require(all(first[name] == 0 for name in
                        ("observed_answer_count", "active_consent_count", "active_gate_count")),
                    "evaluation.not_fresh_context")
            require(all(t["epsilon"] == 0 for t in task_traces), "evaluation.exploration")
        results.append(calculated)
    require(len({t["task_id"] for t in report["tasks"]}) == len(report["tasks"]), "report.duplicate_task")
    for update in report["updates"]:
        require(update.get("auxiliary_loss") is None, "update.auxiliary_loss")
        require(close(update["total_loss"], update["td_loss_derived"]), "update.not_pure_td")
    if not training:
        require(not report["updates"], "evaluation.updated_weights")
    return {"tasks": len(results), "successes": sum(t["task_success"] for t in results),
            "timely_successes": sum(t["timely"] for t in results),
            "actual_field_instances": sum(t["actual_field_instances"] for t in results),
            "committed_effects": sum(t["committed_effects"] for t in results),
            "updates_recorded": len(report["updates"]),
            "totals": {k: sum(t[k] for t in results) for k in COUNTS}}


def audit_results(path: Path) -> dict:
    data = read_json(path)
    runs = data["runs"]
    require(Counter((r["seed"], r["arm"]) for r in runs)
            == Counter((s, a) for s in SEEDS for a in ARMS), "results.run_matrix")
    require(data["seeds"] == list(SEEDS) and data["arms"] == list(ARMS), "results.protocol")
    initialized, configurations, zero_trajectories, audits = {}, {}, {}, []
    for run in runs:
        directory = safe_path(path.parent, run["directory"])
        initial = read_json(directory / "initialization.json")
        final = read_json(directory / "final_state.json")
        require(all(initial[k] == 0 for k in
                    ("optimizer_steps", "environment_steps", "replay_size", "retention_applications",
                     "rule_warmup_tasks", "delivered_count", "pending_nstep")),
                "initialization.not_empty")
        require(initial["bank_hash"] is None and initial["last_auxiliary_loss"] is None
                and initial["auxiliary_supervision"] is False, "initialization.supervised")
        require(initial["network_digest"] == initial["target_digest"], "initialization.target")
        initialized[run["seed"], run["arm"]] = tuple(initial[key] for key in
            ("network_digest", "optimizer_digest", "rng_digest"))
        require(final["optimizer_steps"] > 0 and final["environment_steps"] > 0,
                "training.no_updates")
        require(final["retention_applications"] == 0, "training.retention")
        require(final["network_digest"] != initial["network_digest"], "training.unchanged_network")
        train = audit_report(directory / "train", run["train_tasks"], training=True)
        config = dict(read_json(directory / "train/report.json")["config"])
        require(config["exploration"] == run["arm"] and config["seed"] == run["seed"],
                "training.exploration_arm")
        del config["exploration"]
        configurations[run["seed"], run["arm"]] = config
        evaluations = run["evaluations"]
        require(Counter((e["after_tasks"], e["context"], e["arm"]) for e in evaluations)
                == Counter((n, "fresh", "updated") for n in CHECKPOINTS), "evaluation.matrix")
        eval_results = []
        for evaluation in evaluations:
            name = f"eval_{evaluation['after_tasks']:03d}_fresh_updated"
            result = audit_report(directory / name, evaluation["tasks"], training=False)
            if evaluation["after_tasks"] == 0:
                report = read_json(directory / name / "report.json")
                zero_trajectories[run["seed"], run["arm"]] = tuple(
                    (task["query_id"], task["metrics"]["task_success"], tuple(
                        (decision["action"], decision["candidate_id"], decision["reward"])
                        for decision in report["decisions"]
                        if decision["task_id"] == task["task_id"]))
                    for task in report["tasks"])
            eval_results.append({"after_tasks": evaluation["after_tasks"], **result})
        audits.append({"seed": run["seed"], "arm": run["arm"], "train": train,
                       "evaluations": eval_results})
    for seed in SEEDS:
        require(initialized[seed, "candidate"] == initialized[seed, "family"],
                "initialization.unmatched_arms")
        require(configurations[seed, "candidate"] == configurations[seed, "family"],
                "training.unmatched_configuration")
        require(zero_trajectories[seed, "candidate"] == zero_trajectories[seed, "family"],
                "evaluation.unmatched_zero_step_trajectories")
    return {"status": "passed", "audit_kind": "independent_receipt_and_reward_reconciliation",
            "training_tasks": sum(r["train"]["tasks"] for r in audits),
            "evaluation_tasks": sum(e["tasks"] for r in audits for e in r["evaluations"]),
            "actual_unauthorized_fields": 0, "same_initial_network_per_seed": True,
            "same_initial_optimizer_and_rng_per_seed": True,
            "same_zero_step_action_candidate_reward_trajectories_per_seed": True,
            "rule_warmup_tasks": 0, "auxiliary_supervision": False,
            "runs": audits,
            "limitations": ["Uses stored runtime oracle outcome; raw tool values are not in audit logs.",
                            "Fixed Allow Reuse fixture is not personal-preference evidence.",
                            "Three seeds and repeated queries are diagnostic, not convergence proof."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = args.output or args.input.parent / "audit.json"
    if output.exists():
        parser.error("audit output already exists; refusing overwrite")
    try:
        result = audit_results(args.input.resolve())
    except AuditFailure as error:
        result = {"status": "failed", "check": str(error)}
    except (OSError, KeyError, TypeError, ValueError):
        result = {"status": "failed", "check": "missing_or_invalid_evidence"}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "runs"}))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
