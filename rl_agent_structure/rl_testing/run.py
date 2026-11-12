"""Isolated diagnostics: functional, real update-check, or online learning-curve."""
from __future__ import annotations

import argparse
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.plots import render_plots
from rl_testing.records import REPORT_SCHEMA, RunLog, json_write, new_output, protected_state
from rl_testing.runner import RuleSelection, run_sequence
from personal_assistant.integration.readonly import NetworkBlock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("functional", "update-check", "learning-curve"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-training", action="store_true",
                        help="Explicit opt-in for real PyTorch updates (run on server only)")
    parser.add_argument("--all-wu", action="store_true", help="Functional original-query coverage only")
    args = parser.parse_args(argv)
    if args.mode != "functional" and not args.allow_training:
        parser.error("real DDQN modes require --allow-training; no torch import or update was attempted")
    if args.mode != "functional" and args.config is None:
        parser.error("real DDQN modes require --config with explicit reward_weights")
    if args.all_wu and args.mode != "functional":
        parser.error("--all-wu is only for functional coverage")
    data = {}
    if args.config is not None:
        with args.config.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict): parser.error("config must be a JSON object")
    data["mode"] = args.mode
    config = RunConfig.from_dict(data)
    if args.all_wu:
        config = replace(config, queries=tuple(range(65)))
    if config.mode != "functional" and importlib.util.find_spec("torch") is None:
        parser.error("PyTorch unavailable; run this explicit training command on the server")
    output = new_output(args.output)
    log = RunLog(config, output)
    before = protected_state()
    json_write(output / "config.json", config.to_dict())
    json_write(output / "protected_sources.json", before)
    start = time.monotonic()
    details = {}
    status, error, guard = "completed", None, NetworkBlock()
    try:
        with guard:
            if config.mode == "functional":
                observed = run_sequence(
                    config, RuleSelection(), log, queries=tuple(config.queries) * config.cycles, training=False,
                )
                details = {"optimizer_steps": 0, "update_check": "not_executed_no_torch",
                           "completed_tasks": len(observed.tasks), "policy": "least_scope_rule"}
            else:
                from rl_testing.torch_checks import update_check, learning_curve
                details = (update_check if config.mode == "update-check" else learning_curve)(config, log)
                if details["update_check"] != "passed":
                    status = "diagnostic_failed"
    except Exception as exception:
        status = "failed"
        # Do not dump arbitrary exceptions, private paths, payloads or environment values.
        error = {"type": type(exception).__name__,
                 "message": "Diagnostic stopped; inspect last event and frames. No automatic retry.",
                 "frames": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                            for frame in traceback.extract_tb(exception.__traceback__)]}
    unchanged = before == protected_state()
    if not unchanged or guard.attempts:
        status = "failed"
    summary = {
        "schema": REPORT_SCHEMA, "action_schema": "four_actions_v1",
        "status": status, "mode": config.mode, "error": error,
        "evidence": log.evidence, "answer_source": "explicit_fixture", "planner": "scripted",
        "network_attempts": guard.attempts, "protected_files_unchanged": unchanged,
        "torch_imported": "torch" in sys.modules, "elapsed_seconds": time.monotonic() - start,
        "optimizer_steps": max((u["optimizer_steps"] for u in log.updates), default=0),
        "converged": None, "convergence_verdict": "not_inferred",
        "task_rows": len(log.tasks), "loss_points": len(log.updates),
        "scheduled_task_count": len(config.queries) * (config.cycles if config.mode != "update-check" else 1),
        "evaluation_rows": len(log.evaluations), **details,
        "metrics_semantics": "four-action outcomes: PB/M and C/G are separate; source hash in protected_sources.json",
        "limitations": [
            "Constant fixture answers are not S-QSTN or human preference data.",
            "Functional charts contain no learned-policy evidence.",
            "Monitor-blocked attempts and actual unauthorized executions are separate outcomes.",
            "Loss samples record only the last optimizer update per observe when n-step flushes several.",
            "Stable curves alone are not a convergence proof.",
        ],
    }
    log.save(summary)
    render_plots(log.report(summary), output / "plots")
    print(json.dumps({k: summary[k] for k in (
        "status", "mode", "task_rows", "optimizer_steps", "network_attempts", "evidence",
    )}))
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
