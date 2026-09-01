"""Ordered twelve-gate exact preflight for the frozen Family-3 v2 suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping

from .contracts import canonical_hash
from .family3_v2_artifacts import (
    Family3V2PreflightStore,
    verify_frozen_v0_v1_baseline,
)
from .family3_v2_audit import (
    audit_family3_v2_binding_no_repair,
    audit_family3_v2_firewall,
    audit_family3_v2_kernel_environment_conformance,
    audit_family3_v2_markov,
    audit_family3_v2_witnesses,
)
from .family3_v2_contracts import (
    CandidateRoleV2,
    FAMILY3_V2_GRANT_LIFETIME_PROFILE,
    FAMILY3_V2_RESPONSE_PROFILE,
    FAMILY3_V2_SCHEMA_VERSION,
    FAMILY3_V2_SUITE_VERSION,
    FAMILY3_V2_TOOL_OUTCOME_PROFILE,
    ForecastModeV2,
)
from .family3_v2_exact_reference import enumerate_terminal_free_reference
from .family3_v2_exact_solver import (
    ACCOUNTING_DOMAIN,
    GUARD_VERSION,
    KEY_VERSION,
    MAX_CACHED_NONTERMINAL_STATES,
    METADATA_VERSION,
    RSS_LIMIT_BYTES,
    SERIALIZER_VERSION,
    SOLVER_VERSION,
    SQLITE_SCHEMA_VERSION,
    Family3V2ExactResourceCapError,
    Family3V2ValueFirstExactSolver,
)
from .family3_v2_model import Family3V2Model
from .family3_v2_policy import Family3V2FeatureEncoder
from .family3_v2_rng import (
    continuation_from_residue,
    draw_family3_v2_branch_residue,
)
from .family3_v2_suite import (
    Family3V2KernelInput,
    Family3V2Suite,
    build_family3_v2_suite,
)
from .scope_matching import ScopeRelation, covers, relation


GATE_ORDER = (
    (1, "suite_manifest"),
    (2, "algebra"),
    (3, "witnesses"),
    (4, "exact_values"),
    (5, "request_q_values"),
    (6, "forecast_counterfactual"),
    (7, "markov"),
    (8, "shortcut_firewall"),
    (9, "scope_binding"),
    (10, "closed_offer_no_repair"),
    (11, "invalid_action_safety"),
    (12, "frozen_v0_v1_unchanged"),
)

FIXED_OUTPUT_ROOT = PurePosixPath(
    "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight"
)
_GRAPH_IDS = tuple(f"i8_f3v2_v{index}" for index in range(10))
_ROOT_ACTION_IDS = (
    CandidateRoleV2.REQUEST_NARROW.value,
    CandidateRoleV2.REQUEST_BROADER.value,
)
_RUN_CONFIG_SCHEMA = "family3_v2_preflight_run_config_v0"
_SOURCE_PATHS = tuple(sorted((
    "src/pa_rl/authorization.py",
    "src/pa_rl/config.py",
    "src/pa_rl/contracts.py",
    "src/pa_rl/effects.py",
    "src/pa_rl/execution.py",
    "src/pa_rl/scenarios.py",
    "src/pa_rl/scope_matching.py",
    "src/pa_rl/family3_v2_artifacts.py",
    "src/pa_rl/family3_v2_audit.py",
    "src/pa_rl/family3_v2_authority.py",
    "src/pa_rl/family3_v2_contracts.py",
    "src/pa_rl/family3_v2_environment.py",
    "src/pa_rl/family3_v2_exact_reference.py",
    "src/pa_rl/family3_v2_exact_solver.py",
    "src/pa_rl/family3_v2_model.py",
    "src/pa_rl/family3_v2_outcome.py",
    "src/pa_rl/family3_v2_policy.py",
    "src/pa_rl/family3_v2_preflight.py",
    "src/pa_rl/family3_v2_rng.py",
    "src/pa_rl/family3_v2_suite.py",
)))


@dataclass(slots=True)
class _RunContext:
    project_root: Path
    output_root: Path
    baseline: Mapping[str, object]
    suite: Family3V2Suite
    model: Family3V2Model
    encoder: Family3V2FeatureEncoder
    source_fingerprints: Mapping[str, str]
    config_fingerprint: str
    shared: dict[str, object]


class _PersistenceRecoveryError(RuntimeError):
    """An ordinary primary failure whose durable recovery could not commit."""

    def __init__(
        self,
        *,
        primary_error: BaseException,
        recovery_error: BaseException,
        operation: str,
        attempted_gate: int,
        durable_checkpoint: Mapping[str, object] | None,
        reconciliation_error: BaseException | None = None,
    ) -> None:
        self.primary_error = primary_error
        self.recovery_error = recovery_error
        self.operation = operation
        self.attempted_gate = attempted_gate
        self.reconciliation_error = reconciliation_error
        durable = {} if durable_checkpoint is None else durable_checkpoint
        self.durable_last_completed_gate = durable.get(
            "last_completed_gate"
        )
        self.durable_next_gate = durable.get("next_gate")
        self.durable_status = durable.get("status")
        reconciliation_detail = (
            ""
            if reconciliation_error is None
            else (
                "; strict_reconciliation="
                f"{type(reconciliation_error).__name__}: {reconciliation_error}"
            )
        )
        super().__init__(
            "persistence recovery failed before a durable terminal transition: "
            f"primary={type(primary_error).__name__}: {primary_error}; "
            f"recovery={type(recovery_error).__name__}: {recovery_error}; "
            f"operation={operation}; attempted_gate={attempted_gate}; "
            f"durable_status={self.durable_status}; "
            f"durable_last_completed_gate={self.durable_last_completed_gate}; "
            f"durable_next_gate={self.durable_next_gate}"
            f"{reconciliation_detail}"
        )


def _is_reparse_or_symlink(path: Path) -> bool:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _validate_fixed_output_root(output_root: Path, project_root: Path) -> Path:
    project = Path(project_root).resolve(strict=True)
    if not project.is_dir() or _is_reparse_or_symlink(project):
        raise ValueError("project root must be a real directory")
    supplied = Path(output_root)
    expected = project.joinpath(*FIXED_OUTPUT_ROOT.parts)
    if supplied.is_absolute():
        if str(supplied) != str(expected):
            raise ValueError("output root must use the exact fixed spelling")
        candidate = supplied
    else:
        if supplied.parts != FIXED_OUTPUT_ROOT.parts:
            raise ValueError("output root must use the exact fixed spelling")
        candidate = project.joinpath(*supplied.parts)
    current = project
    for part in FIXED_OUTPUT_ROOT.parts:
        current = current / part
        if not current.exists():
            raise ValueError("fixed output root must exist")
        if _is_reparse_or_symlink(current):
            raise ValueError("fixed output root crosses a symlink or reparse point")
    if not candidate.is_dir() or candidate.resolve(strict=True) != expected.resolve(strict=True):
        raise ValueError("resolved output root is not the fixed result directory")
    return candidate.resolve(strict=True)


def _project_exact_json(value: object) -> object:
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is Fraction:
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Enum):
        return _project_exact_json(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _project_exact_json(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        projected: dict[str, object] = {}
        for key, item in value.items():
            if isinstance(key, Enum):
                key = key.value
            if type(key) not in {str, int, bool}:
                raise TypeError("unsupported exact JSON mapping key")
            projected_key = str(key)
            if projected_key in projected:
                raise TypeError("exact JSON mapping keys collide after string projection")
            projected[projected_key] = _project_exact_json(item)
        return projected
    if isinstance(value, (tuple, list)):
        return [_project_exact_json(item) for item in value]
    raise TypeError(f"unsupported exact JSON value: {type(value).__name__}")


def _exact_json_bytes(value: object) -> bytes:
    projected = _project_exact_json(value)
    return json.dumps(
        projected, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_output_path(output_root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if (
        not relative_path
        or relative.is_absolute()
        or str(relative) != relative_path
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ValueError("runner artifact path must be canonical and relative")
    root = Path(output_root).resolve(strict=True)
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            if _is_reparse_or_symlink(current):
                raise ValueError("runner artifact path crosses a symlink or reparse point")
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise ValueError("runner artifact path escapes the fixed root") from error
    return candidate


def _write_exact_json(output_root: Path, relative_path: str, value: object) -> dict[str, object]:
    path = _safe_output_path(output_root, relative_path)
    payload = _exact_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = _safe_output_path(output_root, relative_path)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass
    final = path.read_bytes()
    if final != payload:
        raise OSError("atomic runner artifact bytes changed after replace")
    return {
        "relative_path": relative_path,
        "sha256": hashlib.sha256(final).hexdigest(),
        "byte_size": len(final),
    }


def _read_exact_mapping(path: Path, name: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} is missing or malformed") from error
    if type(value) is not dict:
        raise ValueError(f"{name} must be a JSON mapping")
    return value


def _source_fingerprints(project_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in sorted(_SOURCE_PATHS):
        path = project_root.joinpath(*PurePosixPath(relative).parts)
        if not path.is_file() or _is_reparse_or_symlink(path):
            raise ValueError(f"runner dependency is missing or unsafe: {relative}")
        result[relative] = _sha256_file(path)
    return result


def _build_run_config(project_root: Path, suite: Family3V2Suite) -> dict[str, object]:
    fingerprints = _source_fingerprints(Path(project_root).resolve(strict=True))
    return {
        "schema_version": _RUN_CONFIG_SCHEMA,
        "suite_version": FAMILY3_V2_SUITE_VERSION,
        "graph_row_schema_version": FAMILY3_V2_SCHEMA_VERSION,
        "gate_order": [list(item) for item in GATE_ORDER],
        "graph_ids": [graph.graph_id for graph in suite.graphs],
        "root_seed": 17,
        "episode_ordinal": 0,
        "solver_version": SOLVER_VERSION,
        "sqlite_schema_version": SQLITE_SCHEMA_VERSION,
        "serializer_version": SERIALIZER_VERSION,
        "key_version": KEY_VERSION,
        "guard_version": GUARD_VERSION,
        "metadata_version": METADATA_VERSION,
        "accounting_domain": ACCOUNTING_DOMAIN,
        "max_cached_nonterminal_states": MAX_CACHED_NONTERMINAL_STATES,
        "rss_limit_bytes": RSS_LIMIT_BYTES,
        "source_fingerprints": fingerprints,
    }


def _prepare_run_config(output_root: Path, config: Mapping[str, object]) -> str:
    path = _safe_output_path(output_root, "run_config.json")
    payload = _exact_json_bytes(config)
    if path.exists():
        if not path.is_file() or _is_reparse_or_symlink(path):
            raise ValueError("run_config.json must be a real regular file")
        existing = path.read_bytes()
        if existing != payload:
            raise ValueError("committed run_config.json is immutable and incompatible")
    else:
        _write_exact_json(output_root, "run_config.json", config)
        existing = path.read_bytes()
    return hashlib.sha256(existing).hexdigest()


def _cache_path(output_root: Path, kind: str, graph_id: str) -> Path:
    if graph_id not in _GRAPH_IDS:
        raise ValueError("cache graph ID is outside the frozen suite")
    if kind == "original":
        relative = f"graphs/{graph_id}/value_cache.sqlite3"
    elif kind == "counterfactual":
        relative = f"counterfactuals/{graph_id}/value_cache.sqlite3"
    else:
        raise ValueError("cache kind must be original or counterfactual")
    return Path(output_root).joinpath(*PurePosixPath(relative).parts)


def _validated_cache_path(context: _RunContext, cache_path: Path) -> Path:
    root = context.output_root.resolve(strict=True)
    candidate = Path(cache_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError as error:
        raise ValueError("cache path escapes the fixed output root") from error
    return _safe_output_path(root, relative)


def _fraction_from_mapping(value: object) -> Fraction:
    if type(value) is not dict or set(value) != {"numerator", "denominator"}:
        raise ValueError("exact fraction mapping is malformed")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        raise ValueError("exact fraction mapping has invalid integers")
    return Fraction(numerator, denominator)


def _result_mapping(result: object) -> dict[str, object]:
    graph_id = getattr(result, "graph_id")
    root_value = getattr(result, "root_value")
    root_q_values = getattr(result, "root_q_values")
    statistics = getattr(result, "statistics")
    if type(graph_id) is not str or type(root_value) is not Fraction:
        raise ValueError("solver result identity or value is invalid")
    if not isinstance(root_q_values, tuple) or tuple(row[0] for row in root_q_values) != _ROOT_ACTION_IDS:
        raise ValueError("solver result root Q order is invalid")
    if any(type(row[1]) is not Fraction for row in root_q_values):
        raise ValueError("solver result root Q values must be exact")
    return {
        "graph_id": graph_id,
        "root_value": root_value,
        "root_q_values": [
            {"action_id": action_id, "value": value}
            for action_id, value in root_q_values
        ],
        "statistics": statistics,
    }


def _reference_mapping(reference: object) -> dict[str, object]:
    return {
        "graph_id": getattr(reference, "graph_id"),
        "root_value": getattr(reference, "root_value"),
        "root_q_values": [
            {"action_id": action_id, "value": value}
            for action_id, value in getattr(reference, "root_q_values")
        ],
        "nonterminal_state_count": getattr(reference, "nonterminal_state_count"),
        "terminal_leaf_count": getattr(reference, "terminal_leaf_count"),
        "action_count": getattr(reference, "action_count"),
        "transition_count": getattr(reference, "transition_count"),
        "max_decision_depth": getattr(reference, "max_decision_depth"),
    }


def _relative_to_output(context: _RunContext, path: Path) -> str:
    return path.relative_to(context.output_root).as_posix()


def _gate_1_suite_manifest(context: _RunContext):
    graphs = context.suite.graphs
    canonical_suite = build_family3_v2_suite()
    canonical_graphs = canonical_suite.graphs
    ids = tuple(graph.graph_id for graph in graphs)
    row_checks: list[dict[str, bool]] = []
    for ordinal, graph in enumerate(graphs):
        canonical = canonical_graphs[ordinal] if ordinal < len(canonical_graphs) else None
        mapping = graph.row_mapping()
        row_checks.append({
            "canonical_literal_equality": canonical is not None and graph.literal_row == canonical.literal_row,
            "exact_split_assignment": canonical is not None and graph.split == canonical.split,
            "exact_21_key_content_and_order": (
                canonical is not None
                and tuple(mapping) == tuple(canonical.row_mapping())
                and mapping == canonical.row_mapping()
            ),
            "recomputed_row_hash": graph.row_hash == canonical_hash(mapping),
        })
    recomputed_suite_hash = canonical_hash([graph.row_mapping() for graph in graphs])
    checks = {
        "exact_graph_count": len(graphs) == 10,
        "canonical_graph_order": ids == _GRAPH_IDS,
        "unique_graph_ids": len(set(ids)) == 10,
        "complete_21_field_rows": all(len(graph.row_mapping()) == 21 for graph in graphs),
        "canonical_literal_rows": all(len(graph.literal_row) == 10 for graph in graphs),
        "scope_costs_and_relations": all(
            graph.n < graph.b
            and covers(graph.narrow_scope, graph.narrow_scope)
            and covers(graph.broader_scope, graph.narrow_scope)
            and not covers(graph.narrow_scope, graph.broader_scope)
            and relation(graph.narrow_scope, graph.narrow_scope) is ScopeRelation.EXACT
            and relation(graph.broader_scope, graph.narrow_scope) is ScopeRelation.NARROWER
            and relation(graph.narrow_scope, graph.broader_scope) is ScopeRelation.BROADER
            for graph in graphs
        ),
        "frozen_profiles": all(
            graph.response_profile == FAMILY3_V2_RESPONSE_PROFILE
            and graph.grant_lifetime_profile == FAMILY3_V2_GRANT_LIFETIME_PROFILE
            and graph.tool_outcome_profile == FAMILY3_V2_TOOL_OUTCOME_PROFILE
            for graph in graphs
        ),
        "valid_splits": all(graph.split in {"train", "validation", "test"} for graph in graphs),
        "canonical_rows_and_splits": len(row_checks) == 10 and all(
            all(row.values()) for row in row_checks
        ),
        "recomputed_suite_hash": (
            context.suite.suite_hash == recomputed_suite_hash
            and context.suite.suite_hash == canonical_suite.suite_hash
        ),
    }
    manifest = {
        "schema_version": "family3_v2_suite_manifest_v0",
        "suite_version": FAMILY3_V2_SUITE_VERSION,
        "graph_row_schema_version": FAMILY3_V2_SCHEMA_VERSION,
        "graph_count": len(graphs),
        "graphs": [
            {
                "graph_id": graph.graph_id,
                "row_mapping": graph.row_mapping(),
                "row_hash": graph.row_hash,
                "literal_row": graph.literal_row,
            }
            for graph in graphs
        ],
        "suite_hash": context.suite.suite_hash,
    }
    manifest_ref = _write_exact_json(context.output_root, "suite_manifest.json", manifest)
    passed = all(checks.values())
    return {"passed": passed, **checks}, {
        "manifest": manifest_ref, "checks": checks, "row_checks": row_checks,
        "recomputed_suite_hash": recomputed_suite_hash,
    }


def _algebra_report(suite: Family3V2Suite) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for graph in suite.graphs:
        expressions = {
            "narrow_exact_success_exposure": (graph.e + 2) * graph.n,
            "narrow_broader_pre_failure_exposure": (graph.d + 1) * graph.n,
            "broader_exact_required_exposure": (graph.e + 2) * graph.b,
            "broader_broader_success_exposure": (graph.d + 2) * graph.b,
        }
        predicates = {
            "n_less_than_b": graph.n < graph.b,
            "e_greater_than_d_at_least_one": graph.e > graph.d >= 1,
            "e_minus_d_at_most_two": graph.e - graph.d <= 2,
            "target_equals_e_plus_one": graph.target == graph.e + 1,
            "prompt_budget_equals_one": graph.prompt_budget == 1,
            "exposure_budget_is_theorem_max": graph.exposure_budget == max(
                (graph.e + 2) * graph.n, (graph.d + 2) * graph.b
            ),
            "horizon_is_theorem_max": graph.horizon == max(8, graph.e + 4),
            "budget_below_broader_exact": graph.exposure_budget < (graph.e + 2) * graph.b,
            "narrow_exact_within_budget": expressions["narrow_exact_success_exposure"] <= graph.exposure_budget,
            "broader_exact_exceeds_budget": expressions["broader_exact_required_exposure"] > graph.exposure_budget,
            "broader_broader_within_budget": expressions["broader_broader_success_exposure"] <= graph.exposure_budget,
        }
        orientation = (
            CandidateRoleV2.REQUEST_NARROW.value
            if graph.forecast_mode is ForecastModeV2.EXACT_HEAVY
            else CandidateRoleV2.REQUEST_BROADER.value
        )
        rows.append({
            "graph_id": graph.graph_id,
            "n": graph.n,
            "b": graph.b,
            "e": graph.e,
            "d": graph.d,
            "target": graph.target,
            "prompt_budget": graph.prompt_budget,
            "exposure_budget": graph.exposure_budget,
            "horizon": graph.horizon,
            "theorem_expressions": expressions,
            "predicates": predicates,
            "forecast_conditioned_expected_best_request": orientation,
            "passed": all(predicates.values()),
        })
    return {"passed": all(row["passed"] is True for row in rows), "rows": rows}


def _gate_2_algebra(context: _RunContext):
    report = _algebra_report(context.suite)
    return {"passed": report["passed"], "graph_count": len(report["rows"])}, report


def _gate_3_witnesses(context: _RunContext):
    witness = audit_family3_v2_witnesses(context.suite, context.model)
    conformance = audit_family3_v2_kernel_environment_conformance(context.suite)
    graph_by_id = {graph.graph_id: graph for graph in context.suite.graphs}
    cells_valid = witness.cell_count == 40 and len(witness.cells) == 40
    for cell in witness.cells:
        graph = graph_by_id.get(cell.graph_id)
        if graph is None:
            cells_valid = False
            continue
        if cell.request_role == CandidateRoleV2.REQUEST_NARROW.value and cell.branch == "exact":
            expected = (True, "success", None)
        elif cell.request_role == CandidateRoleV2.REQUEST_NARROW.value:
            expected = (False, "no_coverage_failure", "irreversible_no_coverage")
        elif cell.branch == "exact":
            expected = (False, "resource_failure", "exposure_budget_exceeded")
        else:
            expected = (True, "success", None)
        cells_valid = cells_valid and (
            (cell.success, cell.classification, cell.failure_reason) == expected
            and cell.invalid_actions == 0
            and cell.unauthorized_committed_effects == 0
            and cell.monitor_blocked_attempts == 0
        )
    role_names = tuple(role for role, _ in conformance.role_coverage)
    expected_roles = tuple(role.value for role in CandidateRoleV2)
    conformance_valid = (
        conformance.passed
        and not conformance.mismatches
        and conformance.analysis_count == 20
        and conformance.state_count > 0
        and conformance.action_count > 0
        and conformance.transition_count > 0
        and role_names == expected_roles
        and sum(count for _, count in conformance.role_coverage) > 0
        and conformance.residue_coverage == (0, 1, 2, 3, 4)
        and conformance.first_effect_residue_replay_count > 0
    )
    passed = (
        witness.passed
        and not witness.mismatches
        and witness.success_count == 20
        and witness.resource_failure_count == 10
        and witness.no_coverage_count == 10
        and cells_valid
        and conformance_valid
    )
    witness_mapping = _project_exact_json(witness)
    conformance_mapping = _project_exact_json(conformance)
    context.shared["witness_audit"] = witness_mapping
    return {
        "passed": passed,
        "witness_passed": witness.passed,
        "conformance_passed": conformance.passed,
    }, {
        "witness_audit": witness_mapping,
        "kernel_environment_conformance": conformance_mapping,
        "cells_valid": cells_valid,
        "conformance_valid": conformance_valid,
    }


def _solve_result(
    context: _RunContext,
    kernel: Family3V2KernelInput,
    cache_path: Path,
    solver_factory,
):
    cache_path = _validated_cache_path(context, cache_path)
    model = Family3V2Model()
    state = model.initial_state(kernel)
    solver = solver_factory(
        model,
        cache_path,
        source_fingerprints=context.source_fingerprints,
        config_fingerprint=context.config_fingerprint,
    )
    return model, state, solver.solve(state, _ROOT_ACTION_IDS)


def _gate_4_exact_values(
    context: _RunContext,
    *,
    _solver_factory=Family3V2ValueFirstExactSolver,
    _reference_enumerator=enumerate_terminal_free_reference,
    _cache_path_factory=_cache_path,
):
    certificates: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    graph_by_id = {graph.graph_id: graph for graph in context.suite.graphs}

    def solve_graph(graph_id: str, *, reference_required: bool) -> bool:
        graph = graph_by_id[graph_id]
        kernel = Family3V2KernelInput.from_graph(graph)
        cache = _cache_path_factory(context.output_root, "original", graph_id)
        model, state, solve_result = _solve_result(
            context, kernel, cache, _solver_factory
        )
        solve_mapping = _result_mapping(solve_result)
        if solve_mapping["graph_id"] != graph_id:
            raise ValueError("solver returned a different graph ID")
        reference_mapping: dict[str, object] | None = None
        equality_result: bool | None = None
        if reference_required:
            reference = _reference_enumerator(model, state, _ROOT_ACTION_IDS)
            reference_root_value = reference.root_value
            reference_q_values = reference.root_q_values
            equality_result = (
                solve_result.root_value == reference_root_value
                and solve_result.root_q_values == reference_q_values
            )
            reference_mapping = _reference_mapping(reference)
            reference_mapping["equality_result"] = equality_result
            reference_ref = _write_exact_json(
                context.output_root,
                f"references/{graph_id}_reference.json",
                reference_mapping,
            )
        else:
            reference_ref = None
        certificate = {
            **solve_mapping,
            "cache_location": _relative_to_output(context, cache),
            "reference": reference_mapping,
            "reference_equal": equality_result,
        }
        certificate_ref = _write_exact_json(
            context.output_root,
            f"graphs/{graph_id}/exact_certificate.json",
            certificate,
        )
        certificates.append({
            "graph_id": graph_id,
            "certificate": certificate_ref,
            "reference_certificate": reference_ref,
        })
        results.append(certificate)
        return (
            solve_result.root_value == Fraction(4, 5)
            and (equality_result is not False)
        )

    for graph_id in _GRAPH_IDS[:2]:
        if not solve_graph(graph_id, reference_required=True):
            evidence = {"certificates": certificates, "results": results}
            context.shared["gate4"] = evidence
            return {
                "passed": False,
                "completed_graph_count": len(results),
                "reference_barrier_passed": False,
            }, evidence
    for graph_id in _GRAPH_IDS[2:]:
        if not solve_graph(graph_id, reference_required=False):
            evidence = {"certificates": certificates, "results": results}
            context.shared["gate4"] = evidence
            return {
                "passed": False,
                "completed_graph_count": len(results),
                "reference_barrier_passed": True,
            }, evidence
    passed = len(results) == 10 and all(
        _fraction_from_mapping(result["root_value"]) == Fraction(4, 5)
        for result in _project_exact_json(results)
    )
    evidence = {"certificates": certificates, "results": results}
    context.shared["gate4"] = _project_exact_json(evidence)
    return {
        "passed": passed,
        "completed_graph_count": len(results),
        "reference_barrier_passed": True,
        "all_initial_values": "4/5" if passed else None,
    }, evidence


def _verify_runner_ref(context: _RunContext, reference: object) -> Path:
    if type(reference) is not dict or set(reference) != {"relative_path", "sha256", "byte_size"}:
        raise ValueError("runner artifact reference schema is invalid")
    relative = reference["relative_path"]
    digest = reference["sha256"]
    byte_size = reference["byte_size"]
    if type(relative) is not str or type(digest) is not str or type(byte_size) is not int:
        raise ValueError("runner artifact reference fields are invalid")
    path = _safe_output_path(context.output_root, relative)
    if not path.is_file() or path.stat().st_size != byte_size or _sha256_file(path) != digest:
        raise ValueError("runner artifact reference bytes changed")
    return path


def _committed_gate4_bundle(context: _RunContext) -> dict[str, object]:
    checkpoint = _read_exact_mapping(
        _safe_output_path(context.output_root, "continuation_checkpoint.json"),
        "continuation checkpoint",
    )
    committed = checkpoint.get("committed_gates")
    if type(committed) is not list or len(committed) < 4:
        raise ValueError("checkpoint does not commit Gate 4")
    record = committed[3]
    if type(record) is not dict or record.get("gate") != 4:
        raise ValueError("checkpoint Gate 4 record is not canonical")
    report_ref = record.get("report")
    evidence_ref = record.get("evidence")
    report_path = _verify_runner_ref(context, report_ref)
    evidence_path = _verify_runner_ref(context, evidence_ref)
    if report_ref.get("relative_path") != "gates/gate_04_report.json":
        raise ValueError("checkpoint Gate 4 report path is incompatible")
    if evidence_ref.get("relative_path") != "gates/gate_04_evidence.json":
        raise ValueError("checkpoint Gate 4 evidence path is incompatible")
    report = _read_exact_mapping(report_path, "Gate 4 report")
    if report != {
        "passed": True,
        "completed_graph_count": 10,
        "reference_barrier_passed": True,
        "all_initial_values": "4/5",
    }:
        raise ValueError("committed Gate 4 report is not the exact ten-certificate PASS")
    evidence = _read_exact_mapping(evidence_path, "Gate 4 evidence")
    entries = evidence.get("certificates")
    results = evidence.get("results")
    if type(entries) is not list or len(entries) != 10 or type(results) is not list or len(results) != 10:
        raise ValueError("committed Gate 4 evidence cardinality is incompatible")
    return evidence


def _certificate_rows(context: _RunContext) -> list[dict[str, object]]:
    evidence = _committed_gate4_bundle(context)
    entries = evidence.get("certificates")
    results = evidence.get("results")
    if type(entries) is not list or len(entries) != 10:
        raise ValueError("Gate 4 must reference ten solver certificates")
    if type(results) is not list or len(results) != 10:
        raise ValueError("Gate 4 must contain ten ordered solver results")
    rows: list[dict[str, object]] = []
    for expected_id, entry, result in zip(_GRAPH_IDS, entries, results):
        if type(entry) is not dict or entry.get("graph_id") != expected_id:
            raise ValueError("Gate 4 certificate order is incompatible")
        certificate_ref = entry.get("certificate")
        path = _verify_runner_ref(context, certificate_ref)
        expected_path = f"graphs/{expected_id}/exact_certificate.json"
        if certificate_ref.get("relative_path") != expected_path:
            raise ValueError("Gate 4 certificate path is not bound to its graph")
        certificate = _read_exact_mapping(path, f"{expected_id} exact certificate")
        if certificate.get("graph_id") != expected_id:
            raise ValueError("Gate 4 loaded certificate graph identity is incompatible")
        if type(result) is not dict or result.get("graph_id") != expected_id:
            raise ValueError("Gate 4 result order or graph identity is incompatible")
        if result != certificate:
            raise ValueError("Gate 4 result and certificate bytes disagree")
        rows.append(certificate)
    return rows


def _q_values_from_certificate(certificate: Mapping[str, object]) -> tuple[Fraction, Fraction]:
    rows = certificate.get("root_q_values")
    if type(rows) is not list or len(rows) != 2:
        raise ValueError("certificate root Q rows are malformed")
    if tuple(row.get("action_id") for row in rows if type(row) is dict) != _ROOT_ACTION_IDS:
        raise ValueError("certificate root Q row order is malformed")
    return tuple(_fraction_from_mapping(row["value"]) for row in rows)  # type: ignore[return-value]


def _gate_5_request_q_values(context: _RunContext):
    certificates = _certificate_rows(context)
    graph_by_id = {graph.graph_id: graph for graph in context.suite.graphs}
    rows: list[dict[str, object]] = []
    for certificate in certificates:
        graph_id = certificate.get("graph_id")
        if graph_id not in graph_by_id:
            raise ValueError("certificate graph ID is outside the suite")
        graph = graph_by_id[graph_id]
        values = _q_values_from_certificate(certificate)
        expected = (
            (Fraction(4, 5), Fraction(1, 5))
            if graph.forecast_mode is ForecastModeV2.EXACT_HEAVY
            else (Fraction(1, 5), Fraction(4, 5))
        )
        gap = abs(values[0] - values[1])
        passed = values == expected and gap == Fraction(3, 5) and values[0] != values[1]
        rows.append({
            "graph_id": graph_id,
            "ordered_q_values": values,
            "expected_ordered_q_values": expected,
            "unique_best_request": _ROOT_ACTION_IDS[0] if values[0] > values[1] else _ROOT_ACTION_IDS[1],
            "q_gap": gap,
            "passed": passed,
        })
    passed = len(rows) == 10 and all(row["passed"] is True for row in rows)
    return {
        "passed": passed,
        "graph_count": len(rows),
        "all_q_gaps": "3/5" if passed else None,
    }, {"rows": rows, "source_gate": 4, "solver_invocations": 0}


def _kernel_without_forecast(kernel: Family3V2KernelInput) -> dict[str, object]:
    mapping = _project_exact_json(kernel)
    if type(mapping) is not dict or type(mapping.get("offer")) is not dict:
        raise ValueError("kernel projection is malformed")
    result = json.loads(json.dumps(mapping, sort_keys=True))
    result["offer"].pop("forecast_exact_probability")
    result["offer"].pop("forecast_broader_probability")
    return result


def _candidate_signature(model: Family3V2Model, kernel: Family3V2KernelInput) -> object:
    state = model.initial_state(kernel)
    return _project_exact_json(tuple(
        (
            candidate.role,
            candidate.action,
            candidate.semantic_candidate_id,
            candidate.mask_valid,
            candidate.invalid_reason,
            candidate.operational_scope,
            candidate.issuance_ordinal,
            candidate.emitted,
        )
        for candidate in model.candidates(state)
    ))


def _gate_6_forecast_counterfactual(
    context: _RunContext,
    *,
    _solver_factory=Family3V2ValueFirstExactSolver,
    _cache_path_factory=_cache_path,
):
    originals = {row["graph_id"]: row for row in _certificate_rows(context)}
    rows: list[dict[str, object]] = []
    certificates: list[dict[str, object]] = []
    for graph in context.suite.graphs:
        original = Family3V2KernelInput.from_graph(graph)
        counterfactual = original.forecast_counterfactual()
        original_draw = draw_family3_v2_branch_residue(17, original.branch_coupling_uid, 0)
        counterfactual_draw = draw_family3_v2_branch_residue(
            17, counterfactual.branch_coupling_uid, 0
        )
        coupling_equal = (
            original.branch_coupling_uid == counterfactual.branch_coupling_uid
            and original_draw == counterfactual_draw
        )
        catalog_and_mask_equal = (
            _candidate_signature(context.model, original)
            == _candidate_signature(context.model, counterfactual)
        )
        only_forecast_changed = (
            _kernel_without_forecast(original) == _kernel_without_forecast(counterfactual)
            and original.forecast_exact_probability == counterfactual.forecast_broader_probability
            and original.forecast_broader_probability == counterfactual.forecast_exact_probability
            and catalog_and_mask_equal
        )
        original_mode = continuation_from_residue(
            original.forecast_exact_probability,
            original.forecast_broader_probability,
            original_draw.residue,
        )
        counterfactual_mode = continuation_from_residue(
            counterfactual.forecast_exact_probability,
            counterfactual.forecast_broader_probability,
            counterfactual_draw.residue,
        )
        cache = _cache_path_factory(context.output_root, "counterfactual", graph.graph_id)
        original_cache = _cache_path_factory(context.output_root, "original", graph.graph_id)
        caches_are_separate = cache != original_cache
        _, _, result = _solve_result(context, counterfactual, cache, _solver_factory)
        result_mapping = _result_mapping(result)
        original_certificate = originals[graph.graph_id]
        original_q = _q_values_from_certificate(original_certificate)
        counterfactual_q = tuple(value for _, value in result.root_q_values)
        swapped = counterfactual_q == (original_q[1], original_q[0])
        passed = (
            coupling_equal
            and only_forecast_changed
            and caches_are_separate
            and _fraction_from_mapping(original_certificate["root_value"]) == Fraction(4, 5)
            and result.root_value == Fraction(4, 5)
            and swapped
        )
        certificate = {
            **result_mapping,
            "cache_location": _relative_to_output(context, cache),
            "original_graph_id": graph.graph_id,
            "original_q_values": original_q,
            "q_values_swapped": swapped,
            "coupling_uid": original.branch_coupling_uid,
            "original_draw": original_draw,
            "counterfactual_draw": counterfactual_draw,
            "original_continuation_mode": original_mode,
            "counterfactual_continuation_mode": counterfactual_mode,
            "only_public_forecast_pair_changed": only_forecast_changed,
            "candidate_catalog_and_mask_equal": catalog_and_mask_equal,
            "original_cache_location": _relative_to_output(context, original_cache),
            "counterfactual_cache_location": _relative_to_output(context, cache),
            "caches_are_separate": caches_are_separate,
        }
        reference = _write_exact_json(
            context.output_root,
            f"counterfactuals/{graph.graph_id}/exact_certificate.json",
            certificate,
        )
        certificates.append({"graph_id": graph.graph_id, "certificate": reference})
        rows.append({
            "graph_id": graph.graph_id,
            "coupling_equal": coupling_equal,
            "only_public_forecast_pair_changed": only_forecast_changed,
            "candidate_catalog_and_mask_equal": catalog_and_mask_equal,
            "caches_are_separate": caches_are_separate,
            "q_values_swapped": swapped,
            "original_value": _fraction_from_mapping(original_certificate["root_value"]),
            "expected_original_value": Fraction(4, 5),
            "original_value_matches_expected": (
                _fraction_from_mapping(original_certificate["root_value"]) == Fraction(4, 5)
            ),
            "counterfactual_value": result.root_value,
            "passed": passed,
        })
    passed = len(rows) == 10 and all(row["passed"] is True for row in rows)
    return {"passed": passed, "graph_count": len(rows)}, {
        "rows": rows,
        "certificates": certificates,
        "root_seed": 17,
        "episode_ordinal": 0,
    }


def _gate_7_markov(context: _RunContext):
    audit = audit_family3_v2_markov(context.suite, context.model, context.encoder)
    counts = (
        audit.occurrence_count,
        audit.public_group_count,
        audit.encoded_group_count,
        audit.row_count,
        audit.valid_action_count,
        audit.transition_count,
    )
    passed = audit.passed and not audit.mismatches and audit.analysis_count == 20 and all(
        count > 0 for count in counts
    )
    return {"passed": passed, "analysis_count": audit.analysis_count}, {
        "markov_audit": _project_exact_json(audit),
        "nonvacuous_counts": all(count > 0 for count in counts),
    }


def _gate_8_shortcut_firewall(context: _RunContext):
    audit = audit_family3_v2_firewall(context.suite, context.encoder)
    passed = (
        audit.passed
        and not audit.mismatches
        and audit.manifest_count == 480
        and audit.row_check_count == 4_800
        and audit.schema_check_count > 0
        and audit.algebra_check_count > 0
        and audit.leakage_check_count > 0
    )
    return {
        "passed": passed,
        "manifest_count": audit.manifest_count,
        "row_check_count": audit.row_check_count,
    }, {"firewall_audit": _project_exact_json(audit), "dp_invocations": 0}


def _gate_9_scope_binding(context: _RunContext):
    audit = audit_family3_v2_binding_no_repair(context.suite)
    records_valid = len(audit.binding_records) == 20 and all(
        record.four_scopes_equal
        and record.reusable
        and record.remaining_uses is None
        and record.expires_at_step == record.expected_expires_at_step
        and not record.raw_id_public_ordinal_colocated
        for record in audit.binding_records
    )
    passed = audit.passed and not audit.mismatches and audit.binding_count == 20 and records_valid
    mapping = _project_exact_json(audit)
    context.shared["binding_audit"] = mapping
    return {
        "passed": passed,
        "binding_count": audit.binding_count,
        "binding_record_count": len(audit.binding_records),
    }, {"binding_audit": mapping, "binding_records_valid": records_valid}


def _binding_mapping(context: _RunContext) -> dict[str, object]:
    evidence = _read_exact_mapping(
        _safe_output_path(context.output_root, "gates/gate_09_evidence.json"),
        "Gate 9 evidence",
    )
    mapping = evidence.get("binding_audit")
    if type(mapping) is not dict:
        raise ValueError("Gate 9 binding audit is malformed")
    return mapping


def _gate_10_closed_offer_no_repair(context: _RunContext):
    audit = _binding_mapping(context)
    records = audit.get("nonemitted_guard_records")
    records_valid = type(records) is list and len(records) == audit.get("nonemitted_guard_count") and all(
        type(record) is dict
        and record.get("failure_reason") == "irreversible_no_coverage"
        and record.get("catalog_row_count") == 7
        and record.get("all_nonemitted") is True
        and record.get("verified") is True
        and record.get("catalog_signature") == record.get("expected_catalog_signature")
        for record in records
    )
    exact_counts = (
        audit.get("catalog_row_count", 0) > 0
        and audit.get("action_type_count") == 6
        and audit.get("no_repair_state_count") == 294
        and audit.get("closed_offer_row_check_count") == 882
        and audit.get("disable_guard_count") == 294
        and audit.get("execute_guard_count") == 20
        and audit.get("nonemitted_guard_count") == 314
        and audit.get("nonemitted_catalog_row_count") == 2_198
    )
    passed = audit.get("passed") is True and records_valid and exact_counts
    return {"passed": passed, "no_repair_state_count": audit.get("no_repair_state_count")}, {
        "source_gate": 9,
        "exact_counts": exact_counts,
        "nonemitted_guards_valid": records_valid,
        "closed_offer_row_check_count": audit.get("closed_offer_row_check_count"),
    }


def _witness_mapping(context: _RunContext) -> dict[str, object]:
    evidence = _read_exact_mapping(
        _safe_output_path(context.output_root, "gates/gate_03_evidence.json"),
        "Gate 3 evidence",
    )
    mapping = evidence.get("witness_audit")
    if type(mapping) is not dict:
        raise ValueError("Gate 3 witness audit is malformed")
    return mapping


def _gate_11_invalid_action_safety(context: _RunContext):
    binding = _binding_mapping(context)
    witness = _witness_mapping(context)
    forced = binding.get("forced_invalid_count")
    forced_valid = (
        type(forced) is int
        and forced > 0
        and binding.get("forced_invalid_zero_delta_count") == forced
        and binding.get("forced_invalid_stable_key_check_count") == forced
        and binding.get("forced_invalid_closure_check_count") == forced
    )
    cells = witness.get("cells")
    witness_valid = type(cells) is list and all(
        type(cell) is dict
        and (
            not cell.get("success")
            or (
                cell.get("invalid_actions") == 0
                and cell.get("unauthorized_committed_effects") == 0
                and cell.get("monitor_blocked_attempts") == 0
            )
        )
        for cell in cells
    )
    passed = binding.get("passed") is True and witness.get("passed") is True and forced_valid and witness_valid
    return {"passed": passed, "forced_invalid_count": forced}, {
        "source_gates": [3, 9],
        "forced_invalid_zero_delta_stable_and_closed": forced_valid,
        "successful_witness_paths_safe": witness_valid,
    }


def _gate_12_frozen_v0_v1_unchanged(context: _RunContext):
    audit = verify_frozen_v0_v1_baseline(context.project_root, context.baseline)
    passed = (
        audit.passed
        and audit.expected_source_count == 14
        and audit.actual_source_count == 14
        and audit.expected_result_count == 72
        and audit.actual_result_count == 72
        and not audit.missing
        and not audit.added
        and not audit.changed
    )
    return {"passed": passed, "source_count": 14, "result_count": 72}, {
        "frozen_set_audit": _project_exact_json(audit)
    }


def _default_gate_handlers():
    return (
        (1, _gate_1_suite_manifest),
        (2, _gate_2_algebra),
        (3, _gate_3_witnesses),
        (4, _gate_4_exact_values),
        (5, _gate_5_request_q_values),
        (6, _gate_6_forecast_counterfactual),
        (7, _gate_7_markov),
        (8, _gate_8_shortcut_firewall),
        (9, _gate_9_scope_binding),
        (10, _gate_10_closed_offer_no_repair),
        (11, _gate_11_invalid_action_safety),
        (12, _gate_12_frozen_v0_v1_unchanged),
    )


def _nonpass_result(store, status: str, exit_code: int) -> dict[str, object]:
    checkpoint = store.checkpoint
    return {
        "status": status,
        "last_completed_gate": checkpoint["last_completed_gate"],
        "next_gate": checkpoint["next_gate"],
        "next_action": checkpoint["next_action"],
        "exit_code": exit_code,
    }


def _success_result() -> dict[str, object]:
    return {
        "status": "CERTIFIED_PASS",
        "committed_gates": 12,
        "graph_count": 10,
        "all_initial_values": "4/5",
        "all_q_gaps": "3/5",
    }


def _recover_persistence_boundary(
    store,
    *,
    operation: str,
    attempted_gate: int,
    status: str,
    next_action: str,
    error: BaseException,
    evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "error_type": type(error).__name__,
        "error": str(error),
        **({} if evidence is None else dict(evidence)),
    }
    try:
        return store.recover_after_persistence_exception(
            operation=operation,
            attempted_gate=attempted_gate,
            status=status,
            next_action=next_action,
            evidence=payload,
        )
    except BaseException as recovery_error:
        try:
            reconciled = store.reconcile_durable_checkpoint()
        except BaseException as reconciliation_error:
            if isinstance(error, KeyboardInterrupt):
                raise error
            raise _PersistenceRecoveryError(
                primary_error=error,
                recovery_error=recovery_error,
                operation=operation,
                attempted_gate=attempted_gate,
                durable_checkpoint=None,
                reconciliation_error=reconciliation_error,
            ) from recovery_error
        if reconciled.get("status") in {
            "INTERRUPTED", "GATE_FAILED", "RESOURCE_CAP_EXCEEDED", "CERTIFIED_PASS",
        }:
            return reconciled
        if isinstance(error, KeyboardInterrupt):
            raise error
        raise _PersistenceRecoveryError(
            primary_error=error,
            recovery_error=recovery_error,
            operation=operation,
            attempted_gate=attempted_gate,
            durable_checkpoint=reconciled,
        ) from recovery_error


def _finalize_certified_pass(store) -> None:
    checkpoint = store.checkpoint
    if (
        checkpoint.get("last_completed_gate") != 12
        or checkpoint.get("next_gate") is not None
        or len(checkpoint.get("committed_gates", ())) != 12
    ):
        raise ValueError("all twelve gates must be committed before finalization")
    store.finalize("CERTIFIED_PASS")


def _run_ordered_gates(store, gate_handlers, context) -> dict[str, object]:
    handlers = tuple(gate_handlers)
    if tuple(gate for gate, _ in handlers) != tuple(gate for gate, _ in GATE_ORDER):
        raise ValueError("gate handlers must cover the exact ordered twelve-gate registry")
    if any(not callable(handler) for _, handler in handlers):
        raise ValueError("every gate handler must be callable")
    checkpoint = store.checkpoint
    next_gate = checkpoint.get("next_gate")
    if next_gate is None:
        try:
            _finalize_certified_pass(store)
        except KeyboardInterrupt as error:
            recovered = _recover_persistence_boundary(
                store, operation="finalize", attempted_gate=12,
                status="INTERRUPTED", next_action="Finalize the twelve-gate preflight",
                error=error,
            )
            if recovered.get("status") == "CERTIFIED_PASS":
                return _success_result()
            raise
        except Exception as error:
            recovered = _recover_persistence_boundary(
                store, operation="finalize", attempted_gate=12,
                status="GATE_FAILED", next_action="Terminal GATE_FAILED during finalization",
                error=error,
            )
            if recovered.get("status") == "CERTIFIED_PASS":
                return _success_result()
            return _nonpass_result(store, "GATE_FAILED", 2)
        return _success_result()
    if type(next_gate) is not int or not 1 <= next_gate <= 12:
        raise ValueError("checkpoint next_gate must be an exact uncommitted gate")
    names = dict(GATE_ORDER)
    by_gate = dict(handlers)
    for gate in range(next_gate, 13):
        next_action = f"Run Gate {gate}: {names[gate]}"
        try:
            report, evidence = by_gate[gate](context)
            report = _project_exact_json(report)
            evidence = _project_exact_json(evidence)
            if type(report) is not dict or type(evidence) is not dict:
                raise ValueError("gate handler must return report and evidence mappings")
        except KeyboardInterrupt as error:
            _recover_persistence_boundary(
                store, operation="handler", attempted_gate=gate,
                status="INTERRUPTED", next_action=next_action, error=error,
            )
            raise
        except InterruptedError as error:
            _recover_persistence_boundary(
                store, operation="handler", attempted_gate=gate,
                status="INTERRUPTED", next_action=next_action, error=error,
            )
            return _nonpass_result(store, "INTERRUPTED", 2)
        except Family3V2ExactResourceCapError as error:
            failure = {
                "status": "RESOURCE_CAP_EXCEEDED",
                "gate": gate,
                "gate_name": names[gate],
                "cap_name": error.cap_name,
                "limit": error.limit,
                "actual": error.actual,
            }
            _recover_persistence_boundary(
                store, operation="handler", attempted_gate=gate,
                status="RESOURCE_CAP_EXCEEDED", next_action=next_action,
                error=error, evidence=failure,
            )
            return _nonpass_result(store, "RESOURCE_CAP_EXCEEDED", 3)
        except Exception as error:
            failure = {
                "status": "GATE_FAILED",
                "gate": gate,
                "gate_name": names[gate],
                "error_type": type(error).__name__,
                "error": str(error),
            }
            _recover_persistence_boundary(
                store, operation="handler", attempted_gate=gate,
                status="GATE_FAILED", next_action=next_action,
                error=error, evidence=failure,
            )
            return _nonpass_result(store, "GATE_FAILED", 2)
        if report.get("passed") is not True:
            failure = {
                "status": "GATE_FAILED",
                "gate": gate,
                "gate_name": names[gate],
                "report": report,
                "evidence": evidence,
            }
            try:
                store.mark_terminal_failure("GATE_FAILED", gate, failure)
            except KeyboardInterrupt as error:
                recovered = _recover_persistence_boundary(
                    store, operation="failed_report", attempted_gate=gate,
                    status="INTERRUPTED", next_action=next_action,
                    error=error, evidence=failure,
                )
                if recovered.get("status") in {"GATE_FAILED", "RESOURCE_CAP_EXCEEDED"}:
                    return _nonpass_result(store, recovered["status"], 2)
                raise
            except Exception as error:
                _recover_persistence_boundary(
                    store, operation="failed_report", attempted_gate=gate,
                    status="GATE_FAILED", next_action=next_action,
                    error=error, evidence=failure,
                )
            return _nonpass_result(store, "GATE_FAILED", 2)
        try:
            store.commit_gate(gate, report, evidence)
        except KeyboardInterrupt as error:
            recovered = _recover_persistence_boundary(
                store, operation="commit_gate", attempted_gate=gate,
                status="INTERRUPTED", next_action=next_action, error=error,
            )
            if recovered.get("status") == "CERTIFIED_PASS":
                return _success_result()
            raise
        except InterruptedError as error:
            _recover_persistence_boundary(
                store, operation="commit_gate", attempted_gate=gate,
                status="INTERRUPTED", next_action=next_action, error=error,
            )
            return _nonpass_result(store, "INTERRUPTED", 2)
        except Family3V2ExactResourceCapError as error:
            _recover_persistence_boundary(
                store, operation="commit_gate", attempted_gate=gate,
                status="RESOURCE_CAP_EXCEEDED", next_action=next_action, error=error,
            )
            return _nonpass_result(store, "RESOURCE_CAP_EXCEEDED", 3)
        except Exception as error:
            recovered = _recover_persistence_boundary(
                store, operation="commit_gate", attempted_gate=gate,
                status="GATE_FAILED", next_action=next_action, error=error,
            )
            if recovered.get("status") == "CERTIFIED_PASS":
                return _success_result()
            return _nonpass_result(store, "GATE_FAILED", 2)
    try:
        _finalize_certified_pass(store)
    except KeyboardInterrupt as error:
        recovered = _recover_persistence_boundary(
            store, operation="finalize", attempted_gate=12,
            status="INTERRUPTED", next_action="Finalize the twelve-gate preflight",
            error=error,
        )
        if recovered.get("status") == "CERTIFIED_PASS":
            return _success_result()
        raise
    except Exception as error:
        recovered = _recover_persistence_boundary(
            store, operation="finalize", attempted_gate=12,
            status="GATE_FAILED", next_action="Terminal GATE_FAILED during finalization",
            error=error,
        )
        if recovered.get("status") == "CERTIFIED_PASS":
            return _success_result()
        return _nonpass_result(store, "GATE_FAILED", 2)
    return _success_result()


def _project_root_from_module() -> Path:
    return Path(__file__).resolve(strict=True).parents[2]


def _run_family3_v2_preflight(
    output_root: Path,
    *,
    _gate_handlers=None,
    _store_factory=Family3V2PreflightStore,
    _project_root: Path | None = None,
    _path_resolver: Callable[[Path, Path], Path] = _validate_fixed_output_root,
) -> dict[str, object]:
    project = (
        _project_root_from_module()
        if _project_root is None
        else Path(_project_root).resolve(strict=True)
    )
    fixed_output = _path_resolver(Path(output_root), project)
    baseline = _read_exact_mapping(
        fixed_output / "frozen_v0_v1_baseline.json", "frozen v0/v1 baseline"
    )
    suite = build_family3_v2_suite()
    config = _build_run_config(project, suite)
    config_fingerprint = _prepare_run_config(fixed_output, config)
    store = _store_factory(
        project,
        fixed_output,
        baseline=baseline,
        run_config_relative_path="run_config.json",
        run_config_sha256=config_fingerprint,
    )
    context = _RunContext(
        project_root=project,
        output_root=fixed_output,
        baseline=baseline,
        suite=suite,
        model=Family3V2Model(),
        encoder=Family3V2FeatureEncoder(),
        source_fingerprints=config["source_fingerprints"],
        config_fingerprint=config_fingerprint,
        shared={},
    )
    handlers = _default_gate_handlers() if _gate_handlers is None else _gate_handlers
    return _run_ordered_gates(store, handlers, context)


def run_family3_v2_preflight(output_root: Path) -> dict[str, object]:
    """Run or resume the fixed exact preflight under its sole permitted root."""
    try:
        return _run_family3_v2_preflight(Path(output_root))
    except KeyboardInterrupt as error:
        try:
            recovered = _validated_public_fallback(Path(output_root), error)
        except Exception:
            raise error
        if recovered.get("status") == "CERTIFIED_PASS":
            return recovered
        raise error
    except _PersistenceRecoveryError:
        raise
    except Exception as error:
        try:
            return _validated_public_fallback(Path(output_root), error)
        except Exception:
            raise error


def _validated_public_fallback(
    output_root: Path, error: BaseException
) -> dict[str, object]:
    project = _project_root_from_module()
    fixed_output = _validate_fixed_output_root(Path(output_root), project)
    baseline = _read_exact_mapping(
        fixed_output / "frozen_v0_v1_baseline.json", "frozen v0/v1 baseline"
    )
    config_path = fixed_output / "run_config.json"
    config_sha256 = _sha256_file(config_path)
    checkpoint = Family3V2PreflightStore.validated_durable_checkpoint(
        project,
        fixed_output,
        baseline=baseline,
        run_config_relative_path="run_config.json",
        run_config_sha256=config_sha256,
    )
    if checkpoint.get("status") == "CERTIFIED_PASS":
        return _success_result()
    status = checkpoint.get("status")
    if status == "GATE_PASSED":
        raise error
    if status == "BASELINE_FROZEN":
        if (
            checkpoint.get("last_completed_gate") != 0
            or checkpoint.get("next_gate") != 1
            or checkpoint.get("committed_gates") != []
        ):
            raise error
        status = "GATE_FAILED"
    if status not in {
        "INTERRUPTED", "GATE_FAILED", "RESOURCE_CAP_EXCEEDED"
    }:
        raise error
    return {
        "status": status,
        "last_completed_gate": checkpoint["last_completed_gate"],
        "next_gate": checkpoint["next_gate"],
        "next_action": (
            "Failure after validated durable checkpoint: "
            f"{type(error).__name__}: {error}; durable action: {checkpoint['next_action']}"
        ),
        "exit_code": 3 if status == "RESOURCE_CAP_EXCEEDED" else 2,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen ordered Family-3 v2 exact preflight.",
        add_help=False,
    )
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = run_family3_v2_preflight(arguments.output_root)
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0 if result.get("status") == "CERTIFIED_PASS" else int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["GATE_ORDER", "build_parser", "main", "run_family3_v2_preflight"]
