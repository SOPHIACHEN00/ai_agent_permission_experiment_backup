"""Exact single-candidate calibration for the approved Family-3 target repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from .contracts import canonical_hash
from .increment8_suite import (
    INCREMENT8_SUITE_VERSION,
    LifecycleGraphSpec,
    build_increment8_suite,
)
from .increment8_value_solver import (
    S3_V9_CHECKPOINT_INTERVAL,
    S3_V9_MEMORY_CACHE_SIZE,
    S3_V9_STATE_LIMIT,
    VALUE_SOLVER_VERSION,
    DiskBackedExactValueSolver,
    _ClockFixedCalibrationModel,
    _PICKLE_PROTOCOL,
    _atomic_json,
    _utc_now,
)


CALIBRATION_VERSION = (
    "increment8_v1_s3_v9_exposure_plus8_target_minus1_v1"
)
ORACLE_FLOOR = Fraction(3, 5)
DEFAULT_OUTPUT = Path(
    "results/increment8_v1_s3_v9_target6_exposure24_calibration"
)


def build_fixed_s3_v9_target_reduction_candidate() -> LifecycleGraphSpec:
    """Apply only the declared Family-3 formulas to frozen v0 s3_v9."""

    graph = next(
        member.graph
        for member in build_increment8_suite().members
        if member.graph.graph_id == "i8_s3_v9"
    )
    frozen_v0 = (
        graph.prompt_budget,
        graph.exposure_budget,
        graph.utility_target,
        graph.horizon,
    )
    if frozen_v0 != (3, 16, 7, 12):
        raise ValueError("frozen v0 s3_v9 parameters changed unexpectedly")
    return replace(
        graph,
        exposure_budget=graph.exposure_budget + 8,
        utility_target=max(4, graph.utility_target - 1),
    )


def _calibration_signature(graph: LifecycleGraphSpec) -> str:
    source_directory = Path(__file__).resolve().parent
    source_names = (
        "increment8_target_reduction_calibration.py",
        "increment8_value_solver.py",
        "increment8_model.py",
        "increment8_suite.py",
        "increment8_outcome.py",
        "contracts.py",
        "scope_matching.py",
    )
    return canonical_hash(
        {
            "solver_version": VALUE_SOLVER_VERSION,
            "calibration_version": CALIBRATION_VERSION,
            "base_suite_version": INCREMENT8_SUITE_VERSION,
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "pickle_protocol": _PICKLE_PROTOCOL,
            "source_sha256": {
                name: hashlib.sha256((source_directory / name).read_bytes()).hexdigest()
                for name in source_names
            },
            "clock_semantics": "next_committed_effect_index",
            "family_formula": {
                "exposure_budget": "exposure_v1=exposure_v0+8",
                "utility_target": "target_v1=max(4,target_v0-1)",
            },
            "graph": graph.as_mapping(),
            "oracle_floor": {
                "numerator": ORACLE_FLOOR.numerator,
                "denominator": ORACLE_FLOOR.denominator,
            },
        }
    )


def run_fixed_s3_v9_target_reduction_calibration(
    output_directory: Path,
) -> dict[str, object]:
    """Solve only s3_v9 at exposure 24 and target 6 with exact Bellman DP."""

    if not isinstance(output_directory, Path):
        raise ValueError("output_directory must be pathlib.Path")
    output_directory.mkdir(parents=True, exist_ok=True)
    graph = build_fixed_s3_v9_target_reduction_candidate()
    signature = _calibration_signature(graph)
    model = _ClockFixedCalibrationModel()
    with DiskBackedExactValueSolver(
        model,
        cache_path=output_directory / "value_cache.sqlite3",
        cache_signature=signature,
        state_limit=S3_V9_STATE_LIMIT,
        memory_cache_size=S3_V9_MEMORY_CACHE_SIZE,
        checkpoint_path=output_directory / "progress_checkpoint.json",
        checkpoint_interval=S3_V9_CHECKPOINT_INTERVAL,
    ) as solver:
        result = solver.solve(model.initial_state(graph))

    threshold_pass = result.value >= ORACLE_FLOOR
    certificate: dict[str, object] = {
        "calibration_version": CALIBRATION_VERSION,
        "solver_version": VALUE_SOLVER_VERSION,
        "status": "CERTIFIED_PASS" if threshold_pass else "CERTIFIED_FAIL",
        "completed_at": _utc_now(),
        "cache_signature": signature,
        "base_suite_version": INCREMENT8_SUITE_VERSION,
        "graph_id": graph.graph_id,
        "graph_hash": canonical_hash(graph.as_mapping()),
        "clock_semantics": "next_committed_effect_index",
        "family_formula": {
            "exposure_budget": "exposure_v1=exposure_v0+8",
            "utility_target": "target_v1=max(4,target_v0-1)",
        },
        "parameter_change": {
            "family": 3,
            "prompt_budget": 3,
            "exposure_budget_v0": 16,
            "exposure_budget_candidate": 24,
            "utility_target_v0": 7,
            "utility_target_candidate": 6,
            "horizon": 12,
        },
        "oracle_value": {
            "numerator": result.value.numerator,
            "denominator": result.value.denominator,
        },
        "oracle_floor": {
            "numerator": ORACLE_FLOOR.numerator,
            "denominator": ORACLE_FLOOR.denominator,
        },
        "threshold_pass": threshold_pass,
        "solver_evidence": {
            "state_limit": S3_V9_STATE_LIMIT,
            "memory_cache_size": S3_V9_MEMORY_CACHE_SIZE,
            "total_cached_states": result.total_cached_states,
            "states_added_this_process": result.states_added,
            "memory_cache_hits": result.memory_cache_hits,
            "disk_cache_hits": result.disk_cache_hits,
            "peak_memory_cache_entries": result.peak_memory_cache_entries,
            "max_recursion_depth": result.max_recursion_depth,
        },
    }
    _atomic_json(output_directory / "certificate.json", certificate)
    return certificate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run or resume only the approved Increment 8 s3_v9 target-reduction "
            "exact calibration."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)
    certificate = run_fixed_s3_v9_target_reduction_calibration(arguments.output)
    print(json.dumps(certificate, ensure_ascii=False, sort_keys=True))
    return 0 if certificate["status"] == "CERTIFIED_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_fixed_s3_v9_target_reduction_candidate",
    "run_fixed_s3_v9_target_reduction_calibration",
]
