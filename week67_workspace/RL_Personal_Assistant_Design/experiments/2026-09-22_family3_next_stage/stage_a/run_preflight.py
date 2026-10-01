"""One bounded auditor-only pass; no training, retries, or parameter search."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import time
import traceback
import zipfile
from dataclasses import asdict, replace
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path

from budget_recourse import ACTIONS, Budget, ResourceLimit, Solver, legal_actions, state_from_row, transitions
from budget_recourse_env import CORE, WORKSPACE, Environment, Tape

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = HERE / "evidence/preflight_v0"
RULES = ("forecast_transfer_rule", "current_task_rule", "reservation_rule")
METHODS = RULES + ("random_valid",)
TAPES = tuple(Tape(*bits) for bits in itertools.product((1, 2), (False, True), (1, 2)))


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    if isinstance(value, F):
        return str(value)
    raise TypeError(type(value).__name__)


def canonical(value):
    return json.dumps(value, default=encode, sort_keys=True, ensure_ascii=False)


def save(name, value):
    # New run directory only; progress receipts may be replaced within this run.
    (OUT / name).write_text(json.dumps(value, default=encode, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_inputs():
    provenance = json.loads((BASE / "data/provenance_manifest.json").read_text(encoding="utf-8"))
    archives = []
    source = None
    for entry in provenance["archives"]:
        path = WORKSPACE / entry["path"]
        actual = sha(path)
        require(actual == entry["sha256"], "old archive changed: " + entry["phase"])
        archives.append({"path": entry["path"], "sha256": actual})
        if entry["phase"] == "validation":
            with zipfile.ZipFile(path) as archive:
                source = json.loads(archive.read("formal_results/source_manifest.json"))
    for relative, expected, size in source["entries"]:
        path = (CORE / relative).resolve()
        require(path.is_relative_to(CORE.resolve()), "frozen source path escapes core")
        require(path.stat().st_size == size and sha(path) == expected, "old source changed: " + relative)
    files = [HERE / name for name in ("budget_recourse.py", "budget_recourse_env.py", "test_budget_recourse.py", "run_preflight.py")]
    files += [BASE / name for name in ("EXPERIMENT_DESIGN_zh.md", "EXPERIMENT_DESIGN_en.md", "next_experiment_plan.json")]
    old_stop = json.loads((HERE / "evidence/stop_receipt.json").read_text(encoding="utf-8"))
    expected_tests = next(row["sha256"] for row in old_stop["files"] if row["path"] == "test_budget_recourse.py")
    require(sha(HERE / "test_budget_recourse.py") == expected_tests, "original six tests changed")
    require(sha(BASE / "next_experiment_plan.json") == old_stop["approved_plan_sha256"], "approved candidate changed")
    require(sha(BASE / "EXPERIMENT_DESIGN_zh.md") == old_stop["approved_design_sha256"], "approved Chinese design changed")
    return {"new_files": [{"path": p.relative_to(WORKSPACE).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in files],
            "old_archives": archives, "old_source_files_unchanged": len(source["entries"])}


def tape_weight(root, tape):
    p2 = F(4, 5) if tape.forecast_high else F(1, 5)
    return ((root.forecast if tape.branch1 == 1 else 1 - root.forecast)
            * (root.future_high if tape.forecast_high else 1 - root.future_high)
            * (p2 if tape.branch2 == 1 else 1 - p2))


def structural_witnesses(solver, root):
    # Independent literals from the approved hand derivation (br05).
    pairs = []
    for prompts, narrow, broad in ((2, F(1, 5), F(1, 2)), (3, F(3, 5), F(1, 2))):
        state = replace(root, prompts=prompts)
        q = solver.q_values(state)
        require((q["request_narrow"], q["request_broader"]) == (narrow, broad), "hand Q witness mismatch")
        pairs.append({"state": asdict(state), "q": q, "optimal": solver.optimal_actions(state)})
    downstream = []
    for first, expected_budget, expected_value in (("request_narrow", 6, F(1)), ("request_broader", 3, F(1, 5))):
        state = root
        # First successor is the positive-probability exact branch / low p2.
        for action in (first, "execute_covering", "execute_covering"):
            state = transitions(state, action)[0][1]
        require((state.stage, state.exposure, state.prompts) == (2, expected_budget, 1), "downstream resource witness mismatch")
        require(solver.value(state) == expected_value, "last-task hand value mismatch")
        downstream.append({"first_action": first, "state": asdict(state), "value": expected_value})
    cost_rows = []
    for name, branch, actions, cost, prompts in (
        ("narrow_exact", 1, ("request_narrow", "execute_covering", "execute_covering"), 3, 1),
        ("broader_first", 2, ("request_broader", "execute_covering", "execute_covering"), 6, 1),
        ("narrow_recourse", 2, ("request_narrow", "execute_covering", "request_broader", "execute_covering"), 6, 2),
    ):
        initial = replace(root, prompts=3)
        env = Environment(initial, Tape(branch, False, 1))
        for action in actions:
            solver.budget.check()
            env.step(action)
        actual = initial.exposure - env.state.exposure, initial.prompts - env.state.prompts
        require(actual == (cost, prompts) and env.state.stage == 2 and env.active_grant_count == 0, "real issuance/effect cost or expiry mismatch")
        cost_rows.append({"path": name, "exposure": cost, "prompts": prompts, "trace": env.trace})
    return {"prompt_flip": pairs, "stage1_changes_stage2": downstream, "cost_paths": cost_rows}


def main():
    OUT.mkdir(exist_ok=False)  # Never overwrite/retry a completed or interrupted run.
    started = stamp()
    current = {"phase": "freeze_inputs"}
    rows = []
    counts = {"episodes": 0, "valid_steps": 0, "protected_effects": 0, "explicit_consents": 0,
              "intentional_invalid_rejections": 0, "policy_invalid_actions": 0, "unauthorized_effects": 0}
    budget = None
    try:
        frozen = freeze_inputs()
        save("source_manifest.json", frozen)
        config = json.loads((BASE / "next_experiment_plan.json").read_text(encoding="utf-8"))
        limits = config["stage_a"]
        budget = Budget(limits["max_nonterminal_states"], limits["max_wall_seconds"], limits["max_rss_mib"])
        solver = Solver(budget)
        root = state_from_row(next(row for row in config["graphs"] if row["graph_id"] == "br05"))
        current = {"phase": "hand_witnesses"}
        save("status.json", {"status": "RUNNING", "started_at_utc": started, "coordinate": current})
        witnesses = structural_witnesses(solver, root)
        save("witnesses.json", witnesses)
        observations = {}
        with (OUT / "conditions.jsonl").open("x", encoding="utf-8") as conditions, (OUT / "auditor_episodes.jsonl").open("x", encoding="utf-8") as episodes:
            for graph in config["graphs"]:
                for toggle in (False, True):
                    initial = state_from_row(graph, toggle=toggle)
                    condition = "prompt_toggle" if toggle else "original"
                    current = {"graph_id": graph["graph_id"], "condition": condition, "phase": "exact_values"}
                    value = solver.value(initial)
                    require(value > 0, "fixed graph has no positive feasible path")
                    values = {method: solver.policy_value(method, initial) for method in METHODS}
                    require(all(F(0) <= v <= value <= F(1) for v in values.values()), "policy value outside DP bounds")
                    row = {"graph_id": graph["graph_id"], "split": graph["split"], "condition": condition, "exact_dp": value,
                           **values, "initial_q": solver.q_values(initial), "optimal_first_actions": solver.optimal_actions(initial)}
                    for method in RULES + ("exact_dp",):
                        weighted_success = F(0)
                        require(sum((tape_weight(initial, t) for t in TAPES), F(0)) == 1, "private tape probabilities not normalized")
                        for tape_id, tape in enumerate(TAPES):
                            env = Environment(initial, tape)
                            current = {"graph_id": graph["graph_id"], "condition": condition, "method": method, "tape_id": tape_id, "phase": "real_adapter"}
                            while env.state.status == "running":
                                before = env.state
                                budget.check(before)
                                valid = legal_actions(before)
                                require(env.allowed_actions() == valid, "independent action masks differ")
                                obs = canonical(env.observation())
                                require(env.observation() == asdict(before), "observation has undeclared/private fields")
                                require(observations.setdefault(before, obs) == obs, "private tape changed equivalent public observation")
                                for invalid in set(ACTIONS) - set(valid):
                                    snapshot = env.snapshot(), len(env.monitors)
                                    try:
                                        env.step(invalid)
                                    except ValueError:
                                        pass
                                    else:
                                        raise AssertionError("invalid action accepted: " + invalid)
                                    require((env.snapshot(), len(env.monitors)) == snapshot, "invalid action changed protected state")
                                    counts["intentional_invalid_rejections"] += 1
                                action = solver.optimal_actions(before)[0] if method == "exact_dp" else solver.choose(method, before)
                                current.update({"step": len(env.trace), "action": action, "public_state": asdict(before)})
                                if action not in valid:
                                    counts["policy_invalid_actions"] += 1
                                    raise AssertionError("policy chose invalid action")
                                old_effects, old_consents = env.effect_count, env.consent_count
                                after = env.step(action)
                                outcomes = transitions(before, action)
                                require(sum((p for p, _ in outcomes), F(0)) == 1, "transition mass mismatch")
                                require(any(p > 0 and after == child for p, child in outcomes), "real step differs from pure transition")
                                require(after.exposure >= 0 and after.prompts >= 0, "budget overdraw")
                                effect_delta = int(action == "execute_covering")
                                consent_delta = int(action in ("request_narrow", "request_broader"))
                                require(env.effect_count - old_effects == effect_delta, "unexpected protected effect")
                                require(env.consent_count - old_consents == consent_delta, "consent accounting mismatch")
                                event = env.trace[-1]
                                if effect_delta and not (event.get("effect_committed") and event.get("monitor_audit_valid")):
                                    counts["unauthorized_effects"] += 1
                                    raise AssertionError("protected effect lacks safe monitor receipt")
                                require(not consent_delta or event.get("explicit_consent"), "grant issued without new explicit consent")
                                require(env.active_grant_count == int(bool(after.grant)), "ledger/public coverage mismatch")
                                counts["valid_steps"] += 1
                                counts["protected_effects"] += effect_delta
                                counts["explicit_consents"] += consent_delta
                            require(env.state.status != "success" or env.effect_count == 4, "success without all four effects")
                            weighted_success += tape_weight(initial, tape) * int(env.state.status == "success")
                            counts["episodes"] += 1
                            episodes.write(canonical({"graph_id": graph["graph_id"], "condition": condition, "method": method,
                                "tape_id": tape_id, "private_tape": asdict(tape), "weight": tape_weight(initial, tape),
                                "terminal": env.state.status, "trace": env.trace}) + "\n")
                        require(weighted_success == (value if method == "exact_dp" else values[method]), "exact real-tape policy value mismatch: " + method)
                    rows.append(row)
                    conditions.write(canonical(row) + "\n")
                    conditions.flush()
                    episodes.flush()
                    os.fsync(conditions.fileno())
                    os.fsync(episodes.fileno())
                    save("status.json", {"status": "RUNNING", "started_at_utc": started, "completed_conditions": len(rows), "last_durable_coordinate": current, "counts": counts})
                    print(f"{graph['graph_id']} {condition}: V*={value}; current={values['current_task_rule']}; reservation={values['reservation_rule']}", flush=True)
        require(len(rows) == 20, "condition set incomplete")
        gap_rows = [row for row in rows if row["split"] in ("train", "validation") and row["current_task_rule"] < row["exact_dp"]]
        require(bool(gap_rows), "no train/validation current-task regret")
        # Full-DP states are reachable; local-rule virtual reserve states are NOT used here.
        reachable = tuple(sorted(solver.values, key=lambda s: canonical(asdict(s))))
        follow_up = None
        forecast_pairs = forecast_action_changes = 0
        for state in reachable:
            budget.check()
            if state.progress == 1 and state.branch == 1 and state.grant == 1:
                other = replace(state, branch=2)
                if other in solver.values and solver.value(state) > 0 and solver.value(other) > 0:
                    first_set, second_set = solver.optimal_actions(state), solver.optimal_actions(other)
                    if follow_up is None and set(first_set).isdisjoint(second_set):
                        follow_up = {"exact_state": asdict(state), "exact_actions": first_set,
                                     "broader_state": asdict(other), "broader_actions": second_set,
                                     "scope": "revealed_actual_branch_changes_coverage_and_required_action_not_forecast_only_planning"}
            if state.stage == 2 and state.progress == 0 and state.grant == 0 and state.forecast == F(1, 5):
                other = replace(state, forecast=F(4, 5))
                if other in solver.values:
                    forecast_pairs += 1
                    forecast_action_changes += solver.optimal_actions(state) != solver.optimal_actions(other)
        require(follow_up is not None, "no reachable follow-up information witness")
        require(freeze_inputs() == frozen, "input/source changed during run")
        budget.check()
        groups = {}
        for split in ("all", "train", "validation", "test"):
            selected = [r for r in rows if split == "all" or r["split"] == split]
            groups[split] = {method: sum((r[method] for r in selected), F(0)) / len(selected) for method in ("exact_dp",) + METHODS}
        result = {"status": "STRUCTURAL_PREFLIGHT_PASS_REVIEW_PENDING", "started_at_utc": started, "ended_at_utc": stamp(),
                  "completed_conditions": len(rows), "counts": counts, "full_dp_states": len(solver.values),
                  "nonterminal_states_including_local_rule_virtual_states": len(budget.states),
                  "wall_seconds": time.monotonic() - budget.started, "peak_rss_mib": budget.peak_rss / 1024**2,
                  "fixed_caps": {"states": budget.max_states, "seconds": budget.seconds, "rss_mib": budget.rss_bytes / 1024**2},
                  "strict_current_task_gap_train_validation_conditions": len(gap_rows),
                  "reservation_optimal_conditions": sum(r["reservation_rule"] == r["exact_dp"] for r in rows),
                  "means_equal_weight_conditions": groups, "follow_up_information_witness": follow_up,
                  "stage2_forecast_entry_pairs": forecast_pairs, "stage2_forecast_optimal_action_set_changes": forecast_action_changes,
                  "conformance_scope": "All eight exogenous tapes, three fixed deterministic rules and one DP-optimal policy per condition. Random is pure-model exact only; not exhaustive real replay of every legal history.",
                  "observation_scope": "Stage A public-state adapter only; no learner encoder/replay has been implemented or certified.",
                  "auditor_test_certificates_only": True, "learner_test_opened": False, "training_started": False,
                  "server_connected": False, "api_called": False, "old_source_files_unchanged": frozen["old_source_files_unchanged"],
                  "old_archives_unchanged": len(frozen["old_archives"])}
        save("certificate.json", result)
        with (OUT / "values.csv").open("x", newline="", encoding="utf-8") as stream:
            columns = ("graph_id", "split", "condition", "exact_dp") + METHODS
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        save("status.json", result)
        print(canonical(result), flush=True)
        return 0
    except Exception as error:
        result = {"status": "COMPUTATION_UNRESOLVED" if isinstance(error, ResourceLimit) else "STOPPED_FIRST_GENUINE_FAILURE",
                  "started_at_utc": started, "ended_at_utc": stamp(), "coordinate": current, "completed_conditions": len(rows),
                  "counts": counts, "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
                  "training_started": False, "automatic_retry_allowed": False}
        save("failure.json", result)
        save("status.json", result)
        print(canonical(result), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
