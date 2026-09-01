"""Fixed-formula exact preflight for all Increment 8 strategic graphs."""

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


CALIBRATION_VERSION = "increment8_v1_fixed_formula_exact_preflight_v1"
ORACLE_FLOOR = Fraction(3, 5)
CLOCK_SEMANTICS = "next_committed_effect_index"
FAMILY_FORMULA = {
    "exposure_budget": "exposure_v1=exposure_v0+8",
    "utility_target": "target_v1=max(4,target_v0-1)",
}


def build_v1_strategic_graphs() -> tuple[LifecycleGraphSpec, ...]:
    """Return the canonical forty strategic v1 graphs without changing v0 inputs."""
    graphs: list[LifecycleGraphSpec] = []
    for member in build_increment8_suite().members:
        graph = member.graph
        if graph.family_index is None:
            continue
        if graph.family_index == 3:
            graph = replace(
                graph,
                exposure_budget=graph.exposure_budget + 8,
                utility_target=max(4, graph.utility_target - 1),
            )
        graphs.append(graph)
    result = tuple(sorted(graphs, key=lambda item: item.graph_id))
    expected_ids = tuple(
        f"i8_s{family}_v{variant}"
        for family in range(4)
        for variant in range(10)
    )
    if tuple(item.graph_id for item in result) != expected_ids:
        raise ValueError("frozen strategic suite identity changed unexpectedly")
    return result


def _v0_by_id() -> dict[str, LifecycleGraphSpec]:
    return {
        member.graph.graph_id: member.graph
        for member in build_increment8_suite().members
        if member.graph.family_index is not None
    }


def _source_hashes() -> dict[str, str]:
    source_directory = Path(__file__).resolve().parent
    names = (
        "increment8_v1_preflight.py",
        "increment8_value_solver.py",
        "increment8_model.py",
        "increment8_suite.py",
        "increment8_outcome.py",
        "contracts.py",
        "scope_matching.py",
    )
    return {
        name: hashlib.sha256((source_directory / name).read_bytes()).hexdigest()
        for name in names
    }


def _signature(graph: LifecycleGraphSpec) -> str:
    return canonical_hash(
        {
            "solver_version": VALUE_SOLVER_VERSION,
            "calibration_version": CALIBRATION_VERSION,
            "base_suite_version": INCREMENT8_SUITE_VERSION,
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "pickle_protocol": _PICKLE_PROTOCOL,
            "source_sha256": _source_hashes(),
            "clock_semantics": CLOCK_SEMANTICS,
            "family_formula": FAMILY_FORMULA,
            "graph": graph.as_mapping(),
            "oracle_floor": _fraction_mapping(ORACLE_FLOOR),
        }
    )


def _fraction_mapping(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _json_compatible(value: object) -> object:
    return json.loads(json.dumps(value))


def _candidate_change(graph: LifecycleGraphSpec) -> dict[str, int]:
    v0 = _v0_by_id()[graph.graph_id]
    return {
        "family": graph.family_index,
        "prompt_budget_v0": v0.prompt_budget,
        "prompt_budget_candidate": graph.prompt_budget,
        "exposure_budget_v0": v0.exposure_budget,
        "exposure_budget_candidate": graph.exposure_budget,
        "utility_target_v0": v0.utility_target,
        "utility_target_candidate": graph.utility_target,
        "horizon_v0": v0.horizon,
        "horizon_candidate": graph.horizon,
    }


def run_graph(graph_id: str, output_root: Path) -> dict[str, object]:
    """Run or resume one canonical strategic graph's exact DP certificate."""
    if not isinstance(output_root, Path):
        raise ValueError("output_root must be pathlib.Path")
    graphs = {graph.graph_id: graph for graph in build_v1_strategic_graphs()}
    if graph_id not in graphs:
        raise ValueError("graph_id must be one of the 40 canonical strategic IDs")
    graph = graphs[graph_id]
    graph_directory = output_root / "graphs" / graph_id
    signature = _signature(graph)
    model = _ClockFixedCalibrationModel()
    with DiskBackedExactValueSolver(
        model,
        cache_path=graph_directory / "value_cache.sqlite3",
        cache_signature=signature,
        state_limit=S3_V9_STATE_LIMIT,
        memory_cache_size=S3_V9_MEMORY_CACHE_SIZE,
        checkpoint_path=graph_directory / "progress_checkpoint.json",
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
        "source_sha256": _source_hashes(),
        "graph_id": graph_id,
        "graph": graph.as_mapping(),
        "graph_hash": canonical_hash(graph.as_mapping()),
        "clock_semantics": CLOCK_SEMANTICS,
        "family_formula": FAMILY_FORMULA,
        "parameter_change": _candidate_change(graph),
        "oracle_value": _fraction_mapping(result.value),
        "oracle_floor": _fraction_mapping(ORACLE_FLOOR),
        "threshold_pass": threshold_pass,
        "solver_evidence": {
            "state_limit": S3_V9_STATE_LIMIT,
            "memory_cache_size": S3_V9_MEMORY_CACHE_SIZE,
            "checkpoint_interval": S3_V9_CHECKPOINT_INTERVAL,
            "total_cached_states": result.total_cached_states,
            "states_added_this_process": result.states_added,
            "memory_cache_hits": result.memory_cache_hits,
            "disk_cache_hits": result.disk_cache_hits,
            "peak_memory_cache_entries": result.peak_memory_cache_entries,
            "max_recursion_depth": result.max_recursion_depth,
        },
    }
    _atomic_json(graph_directory / "certificate.json", certificate)
    return certificate


def _expected_ids(phase: str) -> tuple[str, ...]:
    if phase == "family3":
        return tuple(f"i8_s3_v{variant}" for variant in range(10))
    if phase == "strategic":
        return tuple(graph.graph_id for graph in build_v1_strategic_graphs())
    raise ValueError("phase must be family3 or strategic")


def _read_fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a fraction mapping")
    numerator, denominator = value.get("numerator"), value.get("denominator")
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        raise ValueError(f"{name} must have integer numerator and non-zero denominator")
    return Fraction(numerator, denominator)


def _validate_solver_evidence(evidence: object) -> None:
    if not isinstance(evidence, dict):
        raise ValueError("certificate solver evidence must be a JSON object")
    fixed_fields = {
        "state_limit": S3_V9_STATE_LIMIT,
        "memory_cache_size": S3_V9_MEMORY_CACHE_SIZE,
        "checkpoint_interval": S3_V9_CHECKPOINT_INTERVAL,
    }
    for name, expected in fixed_fields.items():
        if evidence.get(name) != expected:
            raise ValueError(f"certificate solver evidence {name} is incompatible")
    measured_fields = (
        "total_cached_states",
        "states_added_this_process",
        "memory_cache_hits",
        "disk_cache_hits",
        "peak_memory_cache_entries",
        "max_recursion_depth",
    )
    for name in measured_fields:
        value = evidence.get(name)
        if type(value) is not int or value < 0:
            raise ValueError(f"certificate solver evidence {name} is invalid")
    if evidence["total_cached_states"] > S3_V9_STATE_LIMIT:
        raise ValueError("certificate solver evidence exceeds the state limit")
    if evidence["states_added_this_process"] > evidence["total_cached_states"]:
        raise ValueError("certificate solver evidence has impossible state counts")
    if evidence["peak_memory_cache_entries"] > S3_V9_MEMORY_CACHE_SIZE:
        raise ValueError("certificate solver evidence exceeds the memory cache size")


def _validate_certificate(certificate: object, graph: LifecycleGraphSpec) -> Fraction:
    if not isinstance(certificate, dict):
        raise ValueError("certificate must be a JSON object")
    if certificate.get("calibration_version") != CALIBRATION_VERSION:
        raise ValueError("certificate calibration version is incompatible")
    if certificate.get("solver_version") != VALUE_SOLVER_VERSION:
        raise ValueError("certificate solver version is incompatible")
    if certificate.get("base_suite_version") != INCREMENT8_SUITE_VERSION:
        raise ValueError("certificate base suite version is incompatible")
    if certificate.get("source_sha256") != _source_hashes():
        raise ValueError("certificate source hashes are incompatible")
    if certificate.get("graph_id") != graph.graph_id:
        raise ValueError("certificate graph identity is incompatible")
    if certificate.get("graph") != _json_compatible(graph.as_mapping()):
        raise ValueError("certificate graph mapping is incompatible")
    if certificate.get("graph_hash") != canonical_hash(graph.as_mapping()):
        raise ValueError("certificate graph hash is incompatible")
    if certificate.get("clock_semantics") != CLOCK_SEMANTICS:
        raise ValueError("certificate clock semantics are incompatible")
    if certificate.get("family_formula") != FAMILY_FORMULA:
        raise ValueError("certificate family formula is incompatible")
    if _read_fraction(certificate.get("oracle_floor"), "oracle_floor") != ORACLE_FLOOR:
        raise ValueError("certificate oracle floor is incompatible")
    if certificate.get("cache_signature") != _signature(graph):
        raise ValueError("certificate cache signature is incompatible")
    if certificate.get("parameter_change") != _candidate_change(graph):
        raise ValueError("certificate candidate parameters are incompatible")
    _validate_solver_evidence(certificate.get("solver_evidence"))
    value = _read_fraction(certificate.get("oracle_value"), "oracle_value")
    threshold_pass = value >= ORACLE_FLOOR
    if certificate.get("threshold_pass") is not threshold_pass:
        raise ValueError("certificate threshold flag is inconsistent with exact value")
    expected_status = "CERTIFIED_PASS" if threshold_pass else "CERTIFIED_FAIL"
    if certificate.get("status") != expected_status:
        raise ValueError("certificate status is inconsistent with exact value")
    return value


def write_phase_summary(output_root: Path, phase: str) -> dict[str, object]:
    """Validate complete certificate evidence and write an atomic phase summary."""
    if not isinstance(output_root, Path):
        raise ValueError("output_root must be pathlib.Path")
    expected_ids = _expected_ids(phase)
    certificate_paths = tuple((output_root / "graphs").glob("*/certificate.json")) if (output_root / "graphs").exists() else ()
    actual_ids = tuple(sorted(path.parent.name for path in certificate_paths))
    if actual_ids != expected_ids:
        raise ValueError("expected complete certificates for the requested phase")
    graphs = {graph.graph_id: graph for graph in build_v1_strategic_graphs()}
    rows: list[dict[str, object]] = []
    values: list[Fraction] = []
    for graph_id in expected_ids:
        path = output_root / "graphs" / graph_id / "certificate.json"
        try:
            certificate = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"certificate is not valid JSON: {graph_id}") from error
        value = _validate_certificate(certificate, graphs[graph_id])
        values.append(value)
        rows.append(
            {
                "graph_id": graph_id,
                "oracle_value": _fraction_mapping(value),
                "status": certificate["status"],
            }
        )
    minimum_value = min(values)
    minimum_graph_id = next(row["graph_id"] for row, value in zip(rows, values) if value == minimum_value)
    pass_count = sum(value >= ORACLE_FLOOR for value in values)
    summary: dict[str, object] = {
        "calibration_version": CALIBRATION_VERSION,
        "phase": phase,
        "graph_count": len(rows),
        "pass_count": pass_count,
        "fail_count": len(rows) - pass_count,
        "graphs": rows,
        "macro_mean": _fraction_mapping(sum(values, Fraction()) / len(values)),
        "minimum_value": _fraction_mapping(minimum_value),
        "minimum_graph_id": minimum_graph_id,
        "oracle_floor": _fraction_mapping(ORACLE_FLOOR),
        "status": "CERTIFIED_PASS" if pass_count == len(rows) else "CERTIFIED_FAIL",
    }
    _atomic_json(output_root / f"{phase}_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fixed-formula Increment 8 v1 exact preflight.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--graph-id", choices=tuple(graph.graph_id for graph in build_v1_strategic_graphs()))
    group.add_argument("--summary", choices=("family3", "strategic"))
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.graph_id is not None:
        result = run_graph(arguments.graph_id, arguments.output_root)
    else:
        result = write_phase_summary(arguments.output_root, arguments.summary)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "CERTIFIED_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CALIBRATION_VERSION",
    "ORACLE_FLOOR",
    "build_parser",
    "build_v1_strategic_graphs",
    "run_graph",
    "write_phase_summary",
]
