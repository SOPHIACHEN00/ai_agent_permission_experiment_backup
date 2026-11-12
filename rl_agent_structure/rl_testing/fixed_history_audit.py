"""Independently audit frozen cold/fixed-history evaluations without torch."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from personal_assistant.contracts.permission import AuthorizationStatus, canonical_hash
from rl_testing.exploration_audit import (
    ACTIONS, ARMS, COUNTS, EXPECTED_LIMITS, EXPECTED_REWARD, QUERIES, SEEDS,
    AuditFailure, audit_task, close, read_json, require, safe_path, traces_for,
)
from rl_testing.history_snapshot import snapshot_from_report, user_from_snapshot

CONTEXTS = ("cold", "fixed")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initial_fingerprint(first: dict) -> str:
    """Exclude model scores while keeping the actual candidate identities."""
    return canonical_hash({
        "state": first["state_features"], "runtime_budgets": first["runtime_budgets"],
        "candidates": [{key: value for key, value in candidate.items() if key != "q"}
                       for candidate in first["candidates"]],
        "raw_history": first["raw_observed_answers"], "raw_allows": first["raw_active_allows"],
        "round": first["round_index"], "decision": first["decision_index"],
    })


def q_statistics(traces: list[dict]) -> dict:
    values = [candidate["q"] for trace in traces for candidate in trace["candidates"]
              if candidate["valid"]]
    require(values and all(type(x) in (int, float) and math.isfinite(x) for x in values),
            "q.nonfinite_or_missing")
    branch = None
    for trace in traces:
        executions = [c["q"] for c in trace["candidates"] if c["valid"] and c["action"] == "EXECUTE"]
        releases = [c["q"] for c in trace["candidates"] if c["valid"] and c["action"] == "RELEASE"]
        if executions and releases:
            budget = trace["runtime_budgets"]
            branch = {"tool": trace["pending_tool"], "step": trace["pending_step"],
                      "execute_Q": max(executions), "release_Q": max(releases),
                      "execute_minus_release": max(executions) - max(releases),
                      "selected_action": trace["selected_action"],
                      "remaining_release_steps": budget["release_step_limit"] - budget["release_steps_used"]}
            break
    return {"max_valid_Q": max(values), "valid_Q_above_one": sum(x > 1 for x in values),
            "valid_Q_count": len(values), "first_execute_release_branch": branch}


def compare_cold(report: dict, source_report: dict, query: int) -> None:
    matches = [t for t in source_report["tasks"] if t["query_id"] == query]
    require(len(matches) == 1, "cold.source_query_count")
    original = matches[0]
    old = [(d["action"], d["candidate_id"], d["reward"]) for d in source_report["decisions"]
           if d["task_id"] == original["task_id"]]
    new = [(d["action"], d["candidate_id"], d["reward"]) for d in report["decisions"]]
    require(old == new, "cold.archived_action_trace_mismatch")
    require(original["metrics"] == report["tasks"][0]["metrics"], "cold.archived_metrics_mismatch")
    require(close(original["return"], report["tasks"][0]["return"]), "cold.archived_return_mismatch")


def audit_case(directory: Path, row: dict, snapshot: dict, next_context: dict,
               reference: dict | None) -> dict:
    report = read_json(directory / "report.json")
    require(report.get("action_schema") == "four_actions_v1", "case.action_schema")
    require(len(report["tasks"]) == 1, "case.task_count")
    config = report["config"]
    require(config["reward_weights"] == EXPECTED_REWARD, "case.reward_changed")
    require(config["runtime_limits"] == EXPECTED_LIMITS, "case.limits_changed")
    require(config["fixture_answer"] == "allow_reuse" and config["episode_mode"] == "query",
            "case.fixture_or_episode")
    require(config["retention_weight"] == 0 and config["public_effects"] is False,
            "case.other_enhancements")
    require(config["seed"] == row["seed"] and config["user_id"] == snapshot["user_id"],
            "case.policy_identity")
    require(not report["updates"], "case.training_updates")
    task = report["tasks"][0]
    require(task["query_id"] == row["query_id"] and task["epsilon"] == 0, "case.query_or_epsilon")
    require(all(d["task_id"] == task["task_id"] and d["action"] in ACTIONS
                for d in report["decisions"]), "case.foreign_decision")
    traces = traces_for(report, directory)
    require(traces and all(t["task_id"] == task["task_id"] and t["epsilon"] == 0 for t in traces),
            "case.foreign_or_exploratory_trace")
    expected = audit_task(task, report["decisions"], traces)
    summary = row.get("summary", row)
    for key in (*COUNTS, "query_id", "task_success", "timely", "committed_effects"):
        require(summary.get(key) == expected[key], "case.summary_metric_mismatch")
    require(close(summary["return"], expected["return"]), "case.summary_return")
    first = traces[0]
    require(initial_fingerprint(first) == row["first_context_fingerprint"], "case.context_fingerprint")
    public = {k: first[k] for k in ("round_index", "decision_index", "raw_observed_answers",
                                   "raw_active_allows", "raw_active_gates")}
    require(public == row["first_public_context"], "case.public_context_metadata")
    require(q_statistics(traces) == row["Q"], "case.q_diagnostics")
    if row["context"] == "cold":
        require(row["context_before"] is None and row["cold_reproduced"] is True,
                "cold.invalid_context_or_failed_runtime_reproduction")
        require(public == {"round_index": 1, "decision_index": 0, "raw_observed_answers": 0,
                           "raw_active_allows": 0, "raw_active_gates": 0}, "cold.nonempty_context")
        if reference is not None:
            compare_cold(report, reference, row["query_id"])
    else:
        require(row["context_before"] == snapshot["digest"], "fixed.wrong_initial_digest")
        require(row["cold_reproduced"] is None, "fixed.invalid_cold_flag")
        require(public == next_context, "fixed.wrong_public_context")
    report_summary = report.get("summary", {})
    require(report_summary.get("status") == "completed" and report_summary.get("training") is False
            and report_summary.get("updates") == 0, "case.incomplete_or_training")
    return {"seed": row["seed"], "arm": row["arm"], "context": row["context"],
            **expected, "status": task["status"], "Q": row["Q"],
            "first_context_fingerprint": row["first_context_fingerprint"]}


def summarize(rows: list[dict]) -> dict:
    count = len(rows)
    return {"tasks": count, "successes": sum(r["task_success"] for r in rows),
            "TCR": sum(r["task_success"] for r in rows) / count,
            "timely_successes": sum(r["timely"] for r in rows),
            "return_mean": sum(r["return"] for r in rows) / count,
            "totals": {key: sum(r[key] for r in rows) for key in COUNTS},
            "actual_field_instances": sum(r["actual_field_instances"] for r in rows),
            "committed_effects": sum(r["committed_effects"] for r in rows)}


def audit_fixed_history(path: Path, source_root: Path | None = None) -> dict:
    data = read_json(path)
    require(data["seeds"] == list(SEEDS) and data["contexts"] == list(CONTEXTS), "results.protocol")
    rows = data["rows"]
    expected_cases = Counter((s, a, c, q) for s in SEEDS for a in ARMS for c in CONTEXTS for q in QUERIES)
    require(Counter((r["seed"], r["arm"], r["context"], r["query_id"]) for r in rows)
            == expected_cases, "results.case_matrix")
    root = path.parent.resolve()
    snapshots, fingerprints, audited, references = {}, {}, [], {}
    source_snapshot = None
    if source_root is not None:
        source_root = source_root.resolve()
        source_snapshot = snapshot_from_report(safe_path(source_root, "seed3/s3_candidate/train/report.json"))
    for seed in SEEDS:
        seed_root = safe_path(root, f"seed{seed}")
        snapshot = read_json(seed_root / "fixed_context.json")
        user = user_from_snapshot(snapshot)
        require(snapshot["source_report_sha256"] == (source_snapshot or snapshot)["source_report_sha256"],
                "snapshot.source_report_mismatch")
        if source_snapshot is not None:
            require(snapshot == source_snapshot, "snapshot.differs_from_fixed_actual_anchor")
        snapshots[seed] = snapshot
        provenance = read_json(seed_root / "context_provenance.json")
        require(provenance["source_report_sha256"] == snapshot["source_report_sha256"]
                and provenance["history_and_consent_digest"] == snapshot["digest"]
                and provenance["round_index"] == user.position.round_index
                and provenance["decision_index"] == user.position.decision_index
                and provenance["observed_answers"] == len(user.history.view()), "snapshot.provenance")
        active = [r for r in user.ledger.records() if r.allows and r.status == AuthorizationStatus.ACTIVE]
        require(provenance["active_allows_at_anchor"] == len(active)
                and provenance["prior_allows_not_expired_at_next_round"] == sum(
                    r.expires_at_round > user.position.round_index + 1 for r in active),
                "snapshot.allow_lifecycle")
        for arm in ARMS:
            integrity = read_json(seed_root / f"s{seed}_{arm}_integrity.json")
            require(integrity.get("passed") is True and integrity["before"] == integrity["after"]
                    and integrity["counters_before"] == integrity["counters_after"]
                    and integrity["optimizer_updates_during_evaluation"] == 0, "model.frozen_integrity")
            if source_root is not None:
                old_root = safe_path(source_root, f"seed{seed}/s{seed}_{arm}")
                require(file_hash(old_root / "policy_after_060.pt") == integrity["checkpoint_sha256"],
                        "model.source_checkpoint_sha256")
                references[seed, arm] = read_json(old_root / "eval_060_fresh_updated/report.json")
        state = read_json(seed_root / "summary.json")
        require(state.get("status") == "completed" and state["evaluations"] == 12
                and state["optimizer_updates"] == 0 and state["network_attempts"] == 0
                and state["protected_sources_unchanged"] is True, "seed.incomplete_or_mutated")
    require(all(snapshots[s] == snapshots[SEEDS[0]] for s in SEEDS), "snapshot.not_shared_across_seeds")
    if "snapshot_hash" in data:
        require(data["snapshot_hash"] == snapshots[SEEDS[0]]["snapshot_hash"], "results.snapshot_hash")
    for row in rows:
        case = safe_path(root, row["directory"])
        expected_name = f"s{row['seed']}_{row['arm']}_{row['context']}_q{row['query_id']}"
        require(case.parent == root / f"seed{row['seed']}" and case.name == expected_name,
                "case.directory_identity")
        snapshot = snapshots[row["seed"]]
        user = user_from_snapshot(snapshot)
        user.ledger.begin_task("audit-next-task", row["query_id"])
        position = user.position
        next_context = {"round_index": position.round_index, "decision_index": position.decision_index,
                        "raw_observed_answers": len(user.history.view()),
                        "raw_active_allows": sum(r.allows and r.status == AuthorizationStatus.ACTIVE
                                                 and r.expires_at_round > position.round_index
                                                 for r in user.ledger.records()), "raw_active_gates": 0}
        result = audit_case(case, row, snapshot, next_context, references.get((row["seed"], row["arm"])))
        if row["context"] == "fixed":
            fingerprints.setdefault(row["query_id"], set()).add(result["first_context_fingerprint"])
        audited.append(result)
    require(all(len(fingerprints[q]) == 1 for q in QUERIES), "fixed.unmatched_first_states")
    groups, paired = [], []
    for arm in ARMS:
        for context in CONTEXTS:
            group = [r for r in audited if r["arm"] == arm and r["context"] == context]
            groups.append({"arm": arm, "context": context, **summarize(group),
                           "per_seed": [{"seed": s, **summarize([r for r in group if r["seed"] == s])}
                                        for s in SEEDS]})
        for seed in SEEDS:
            pair = {c: summarize([r for r in audited if r["arm"] == arm
                                  and r["seed"] == seed and r["context"] == c]) for c in CONTEXTS}
            paired.append({"seed": seed, "arm": arm,
                           "success_difference_fixed_minus_cold": pair["fixed"]["successes"] - pair["cold"]["successes"],
                           "cost_difference_fixed_minus_cold": {
                               k: pair["fixed"]["totals"][k] - pair["cold"]["totals"][k] for k in COUNTS}})
    return {"status": "passed", "audit_kind": "frozen_fixed_history_independent_receipt_audit",
            "evaluations": len(audited), "optimizer_updates": 0, "actual_unauthorized_fields": 0,
            "snapshot_hash": snapshots[SEEDS[0]]["snapshot_hash"],
            "same_fixed_initial_context_for_all_six_models": True,
            "cold_reference_independently_checked": source_root is not None,
            "cold_reference_cases_checked": 18 if source_root is not None else 0,
            "groups": groups, "paired_by_seed": paired, "cases": audited,
            "limitations": ["Fixed human responses and historical consent are not individual-preference learning evidence.",
                            "History and valid consent change together; their effects are not isolated.",
                            "Stored runtime oracle outcomes are checked against receipts, not raw tool values.",
                            *([] if source_root is not None else ["Cold reproduction uses recorded assertions; source reports were not independently loaded."])]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    source = args.input.resolve()
    output = (args.output or source.parent / "fixed_history_audit.json").resolve()
    if not output.is_relative_to(source.parent) or output.exists():
        parser.error("audit output must be a new file within the results directory")
    try:
        result = audit_fixed_history(source, args.source_root)
    except AuditFailure as error:
        result = {"status": "failed", "check": str(error)}
    except (OSError, KeyError, TypeError, ValueError):
        result = {"status": "failed", "check": "missing_or_invalid_evidence"}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("groups", "paired_by_seed", "cases")}))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
