"""Validate that a formal semantic-model run is complete and reportable."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    output = PACKAGE_ROOT / "outputs" / args.run_id
    config_path = output / "run_config.json"
    diagnostics_path = output / "training_diagnostics.json"
    exit_path = PACKAGE_ROOT / "pids" / f"{args.run_id}.exit_code"
    required = [
        config_path,
        diagnostics_path,
        output / "test_metrics.csv",
        output / "test_predictions.csv",
        exit_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Formal run is incomplete; missing={missing}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    exit_code = exit_path.read_text(encoding="utf-8").strip()
    if config.get("status") != "completed" or config.get("official_result") is not True:
        raise SystemExit("run_config does not describe a completed official result.")
    if diagnostics.get("run_completed") is not True or diagnostics.get("frozen_test_evaluations") != 1:
        raise SystemExit("training_diagnostics does not confirm one completed frozen-test evaluation.")
    if exit_code != "0":
        raise SystemExit(f"Formal run exit code is not zero: {exit_code!r}")
    print(f"Completed formal run validation PASS: {args.run_id}")


if __name__ == "__main__":
    main()
