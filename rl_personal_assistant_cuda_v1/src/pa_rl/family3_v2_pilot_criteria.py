"""Strict frozen configuration and certified-dependency boundary for the v2 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_CONFIG_CANONICAL_SHA256 = "27ecd5b5614c1542a971265b8f3ca657a82c434cdcd3fd5e17df9a1c0c07596d"
_TOP_LEVEL = (
    "schema_version", "experiment_id", "certified_environment", "split", "methods",
    "training", "hyperparameters", "evaluation", "hard_zero_counts",
    "phase_completion_only_counts", "validation_gate", "result_classification",
    "external_services",
)
_BASELINE_TOP_LEVEL = {"schema_version", "created_at_utc", "certified_suite", "approved_specs", "certified_preflight", "certified_source_files", "additional_learner_dependencies", "pilot_config"}
_CERTIFICATE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)])
_CACHE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)])
_SPEC_PATHS = ("docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md", "docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md")
_SOURCE_ENTRIES_SHA256 = "3d51cc6f50bbfadde77e0adc3e7d05189e19eb94f3ccaab1196c444ae739044d"
_LEARNER_DEPENDENCIES_SHA256 = "f39def7a36b90e4f2abb32d43e0008d40433ca30336ed1c266c80e2dcae8ca22"
_PILOT_CONFIG_ENTRY_SHA256 = "6d3c085d5a7c6b2cc1aed55f1755931728b930381d65891b78de4226715a86e3"
_PREFLIGHT_ARTIFACTS_SHA256 = "84ce6746c795f5c00869140a9e6c7d4a379e0b08c83fff3621c4aed02c602287"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig:
    schema_version: str
    experiment_id: str
    certified_environment: Mapping[str, object]
    split: Mapping[str, object]
    methods: tuple[Mapping[str, object], ...]
    training: Mapping[str, object]
    hyperparameters: Mapping[str, object]
    evaluation: Mapping[str, object]
    hard_zero_counts: tuple[str, ...]
    phase_completion_only_counts: tuple[str, ...]
    validation_gate: Mapping[str, object]
    result_classification: Mapping[str, object]
    external_services: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CertifiedDependencyVerification:
    passed: bool
    mismatches: tuple[str, ...]
    suite_hash: str
    approved_spec_hashes: tuple[str, ...]


def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("pilot config must be readable JSON") from error
    if not isinstance(raw, dict) or tuple(raw) != _TOP_LEVEL:
        raise ValueError("pilot config has missing, unknown, or noncanonical fields")
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("pilot config differs from the approved frozen contract")
    frozen = _freeze(raw)
    assert isinstance(frozen, Mapping)
    return Family3V2PilotConfig(
        schema_version=frozen["schema_version"], experiment_id=frozen["experiment_id"],
        certified_environment=frozen["certified_environment"], split=frozen["split"],
        methods=frozen["methods"], training=frozen["training"],
        hyperparameters=frozen["hyperparameters"], evaluation=frozen["evaluation"],
        hard_zero_counts=frozen["hard_zero_counts"],
        phase_completion_only_counts=frozen["phase_completion_only_counts"],
        validation_gate=frozen["validation_gate"], result_classification=frozen["result_classification"],
        external_services=frozen["external_services"],
    )


def verify_certified_dependency_baseline(baseline_path: str | Path) -> CertifiedDependencyVerification:
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dependency baseline must be readable JSON") from error
    if not isinstance(baseline, dict) or set(baseline) != _BASELINE_TOP_LEVEL or baseline.get("schema_version") != "family3_v2_learner_source_baseline_v0":
        raise ValueError("dependency baseline schema is invalid")
    root = Path(__file__).resolve().parents[2]
    mismatches: list[str] = []

    def verify(entries: object, base: Path = root) -> None:
        if not isinstance(entries, list):
            raise ValueError("baseline file list is invalid")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"relative_path", "sha256", "byte_size"}:
                raise ValueError("baseline entry is invalid")
            relative, expected_hash, expected_size = entry.get("relative_path"), entry.get("sha256"), entry.get("byte_size")
            if type(relative) is not str or type(expected_hash) is not str or type(expected_size) is not int:
                raise ValueError("baseline entry types are invalid")
            candidate = (base / relative).resolve()
            try:
                candidate.relative_to(base.resolve())
            except ValueError as error:
                raise ValueError("baseline path escapes its allowlisted root") from error
            if not candidate.is_file() or candidate.stat().st_size != expected_size or _sha256(candidate) != expected_hash:
                mismatches.append(relative)

    def require_authoritative(entries: object, digest: str, name: str) -> None:
        if not isinstance(entries, list) or hashlib.sha256(_canonical(entries)).hexdigest() != digest:
            raise ValueError(f"{name} inventory is noncanonical")

    approved_specs = baseline.get("approved_specs")
    if not isinstance(approved_specs, list) or tuple(entry.get("relative_path") for entry in approved_specs if isinstance(entry, dict)) != _SPEC_PATHS:
        raise ValueError("approved-spec inventory is noncanonical")
    verify(approved_specs)
    sources = baseline.get("certified_source_files")
    dependencies = baseline.get("additional_learner_dependencies")
    pilot_config = baseline.get("pilot_config")
    require_authoritative(sources, _SOURCE_ENTRIES_SHA256, "certified source")
    require_authoritative(dependencies, _LEARNER_DEPENDENCIES_SHA256, "learner dependency")
    if hashlib.sha256(_canonical(pilot_config)).hexdigest() != _PILOT_CONFIG_ENTRY_SHA256:
        raise ValueError("pilot config inventory is noncanonical")
    verify(sources)
    verify(dependencies)
    verify([pilot_config])
    preflight = baseline.get("certified_preflight")
    if not isinstance(preflight, dict) or set(preflight) != {"result_root", "final_verdict", "artifacts", "certificate_entries", "cache_entries"} or preflight.get("final_verdict") != "CERTIFIED_PASS" or preflight.get("result_root") != "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight":
        raise ValueError("certified preflight baseline is invalid")
    result_root = root / preflight.get("result_root", "")
    if not result_root.is_dir():
        mismatches.append("certified_preflight.result_root")
    else:
        require_authoritative(preflight.get("artifacts"), _PREFLIGHT_ARTIFACTS_SHA256, "preflight artifact")
        verify(preflight.get("artifacts"), result_root)
        for key, expected_paths in (("certificate_entries", _CERTIFICATE_PATHS), ("cache_entries", _CACHE_PATHS)):
            entries = preflight.get(key)
            if not isinstance(entries, list) or tuple(entry.get("relative_path") for entry in entries if isinstance(entry, dict)) != expected_paths or len({entry.get("relative_path") for entry in entries if isinstance(entry, dict)}) != 20:
                raise ValueError("certified preflight inventory is noncanonical")
            verify(entries, result_root)
    suite = baseline.get("certified_suite")
    if not isinstance(suite, dict) or set(suite) != {"version", "suite_hash"} or suite.get("version") != "increment8_family3_v2_forecast_scope_reservation_v0" or suite.get("suite_hash") != "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c":
        raise ValueError("certified suite inventory is noncanonical")
    hashes = tuple(entry["sha256"] for entry in baseline["approved_specs"])
    return CertifiedDependencyVerification(not mismatches, tuple(mismatches), str(suite.get("suite_hash", "")), hashes)


ROOT_ACTION_MISSING = "__missing_root_action__"
ROOT_ACTION_MULTIPLE = "__multiple_root_actions__"

_HARD_COUNT_NAMES = (
    "invalid_action_attempts", "policy_mask_violations",
    "unauthorized_committed_effects", "monitor_blocked_attempts",
    "monitor_bypass_effects", "environment_invalid_runs",
    "scope_binding_integrity_failures", "authorization_binding_failures",
    "semantic_conformance_failures", "effect_integrity_failures",
    "adapter_contract_failures", "candidate_id_resolution_failures",
    "oracle_feature_leaks", "split_leakage_events",
    "test_access_before_unlock", "evaluation_state_mutations",
    "source_freeze_mismatches", "config_freeze_mismatches",
    "certified_dependency_hash_mismatches", "artifact_hash_mismatches",
    "checkpoint_policy_violations", "common_random_coordinate_mismatches",
    "duplicate_result_rows", "unexpected_result_rows",
    "missing_expected_result_rows", "nonfinite_events",
)
_METHOD_IDS = (
    "random_valid", "forecast_ablated_rule", "forecast_rule",
    "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
    "masked_ddqn_gamma1",
)
_EVALUATION_SEEDS = (17, 29, 43)
_CONDITIONS = ("original", "forecast_counterfactual")
_VALIDATION_GRAPHS = ("i8_f3v2_v5", "i8_f3v2_v6")
_TEST_GRAPHS = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")
_CANDIDATE_IDS = (
    "request_narrow", "request_broader", "execute_covering", "refresh_closed",
    "disable_active", "deny", "escalate", ROOT_ACTION_MISSING,
    ROOT_ACTION_MULTIPLE,
)
_TERMINATION_KINDS = (
    "natural_completion", "horizon_exhaustion", "deny_with_reason", "escalate",
    "irreversible_failure",
)


def _require_exact_str(value: object, name: str) -> None:
    if type(value) is not str:
        raise ValueError(f"{name} must be an exact str")


def _require_exact_int(value: object, name: str, *, minimum: int | None = None) -> None:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"{name} must be an exact integer in range")


@dataclass(frozen=True, slots=True)
class HardIntegrityCounts:
    invalid_action_attempts: int
    policy_mask_violations: int
    unauthorized_committed_effects: int
    monitor_blocked_attempts: int
    monitor_bypass_effects: int
    environment_invalid_runs: int
    scope_binding_integrity_failures: int
    authorization_binding_failures: int
    semantic_conformance_failures: int
    effect_integrity_failures: int
    adapter_contract_failures: int
    candidate_id_resolution_failures: int
    oracle_feature_leaks: int
    split_leakage_events: int
    test_access_before_unlock: int
    evaluation_state_mutations: int
    source_freeze_mismatches: int
    config_freeze_mismatches: int
    certified_dependency_hash_mismatches: int
    artifact_hash_mismatches: int
    checkpoint_policy_violations: int
    common_random_coordinate_mismatches: int
    duplicate_result_rows: int
    unexpected_result_rows: int
    missing_expected_result_rows: int
    nonfinite_events: int

    def __post_init__(self) -> None:
        for name in _HARD_COUNT_NAMES:
            _require_exact_int(getattr(self, name), name, minimum=0)


def _hard_values(counts: HardIntegrityCounts) -> tuple[int, ...]:
    if type(counts) is not HardIntegrityCounts:
        raise ValueError("hard_counts must be exactly HardIntegrityCounts")
    return tuple(getattr(counts, name) for name in _HARD_COUNT_NAMES)


def _zero_hard_counts() -> HardIntegrityCounts:
    return HardIntegrityCounts(*(0 for _ in _HARD_COUNT_NAMES))


def _add_hard_counts(*counts: HardIntegrityCounts) -> HardIntegrityCounts:
    values = [0] * len(_HARD_COUNT_NAMES)
    for item in counts:
        for index, value in enumerate(_hard_values(item)):
            values[index] += value
    return HardIntegrityCounts(*values)


def _increment_hard_counts(
    counts: HardIntegrityCounts, **increments: int,
) -> HardIntegrityCounts:
    if any(name not in _HARD_COUNT_NAMES or type(value) is not int or value < 0
           for name, value in increments.items()):
        raise ValueError("hard-count increment is invalid")
    values = list(_hard_values(counts))
    for name, value in increments.items():
        values[_HARD_COUNT_NAMES.index(name)] += value
    return HardIntegrityCounts(*values)


def _hard_counts_are_zero(counts: HardIntegrityCounts) -> bool:
    return all(value == 0 for value in _hard_values(counts))


@dataclass(frozen=True, slots=True)
class EvaluationEpisodeRow:
    phase: str
    method_id: str
    evaluation_seed: int
    graph_id: str
    condition: str
    episode_ordinal: int
    root_seed: int
    root_semantic_candidate_id: str
    terminal_success: int
    termination_kind: str
    decision_count: int
    prompt_count: int
    hard_counts: HardIntegrityCounts

    def __post_init__(self) -> None:
        for name in (
            "phase", "method_id", "graph_id", "condition",
            "root_semantic_candidate_id", "termination_kind",
        ):
            _require_exact_str(getattr(self, name), name)
        for name in (
            "evaluation_seed", "episode_ordinal", "root_seed", "terminal_success",
            "decision_count", "prompt_count",
        ):
            _require_exact_int(getattr(self, name), name)
        if not 0 <= self.root_seed < 2**64:
            raise ValueError("root_seed must be an unsigned 64-bit integer")
        if self.terminal_success not in (0, 1):
            raise ValueError("terminal_success must be zero or one")
        if self.decision_count < 0 or self.prompt_count < 0:
            raise ValueError("decision and prompt counts must be nonnegative")
        if self.termination_kind not in _TERMINATION_KINDS:
            raise ValueError("termination_kind is not a frozen terminal value")
        if self.root_semantic_candidate_id not in _CANDIDATE_IDS:
            raise ValueError("root semantic candidate ID is invalid")
        _hard_values(self.hard_counts)
        if self.hard_counts.missing_expected_result_rows != 0:
            raise ValueError("missing_expected_result_rows is classifier-owned")


@dataclass(frozen=True, slots=True)
class EvaluationCellResult:
    phase: str
    method_id: str
    evaluation_seed: int
    graph_id: str
    condition: str
    episode_count: int
    terminal_success_count: int
    first_request_match_count: int
    forecast_rule_terminal_match_count: int
    hard_counts: HardIntegrityCounts

    def __post_init__(self) -> None:
        for name in ("phase", "method_id", "graph_id", "condition"):
            _require_exact_str(getattr(self, name), name)
        for name in (
            "evaluation_seed", "episode_count", "terminal_success_count",
            "first_request_match_count", "forecast_rule_terminal_match_count",
        ):
            _require_exact_int(getattr(self, name), name, minimum=0)
        graphs = _VALIDATION_GRAPHS if self.phase == "validation" else _TEST_GRAPHS
        if (self.phase not in ("validation", "test") or self.method_id not in _METHOD_IDS
                or self.evaluation_seed not in _EVALUATION_SEEDS
                or self.graph_id not in graphs or self.condition not in _CONDITIONS):
            raise ValueError("cell coordinate is invalid")
        if self.episode_count != 50 or any(
            value > self.episode_count for value in (
                self.terminal_success_count, self.first_request_match_count,
                self.forecast_rule_terminal_match_count,
            )
        ):
            raise ValueError("cell counts are invalid")
        if not _hard_counts_are_zero(self.hard_counts):
            raise ValueError("emitted cell hard counts must be zero")


def _validate_seed_ids(value: object, name: str) -> tuple[int, ...]:
    if type(value) is not tuple or any(type(item) is not int for item in value):
        raise ValueError(f"{name} must be an exact integer tuple")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} contains duplicate seeds")
    expected = tuple(seed for seed in _EVALUATION_SEEDS if seed in value)
    if value != expected:
        raise ValueError(f"{name} is not a fixed-order seed subsequence")
    return value


def _cell_rank(cell: EvaluationCellResult) -> int:
    graphs = _VALIDATION_GRAPHS if cell.phase == "validation" else _TEST_GRAPHS
    rank = _METHOD_IDS.index(cell.method_id)
    rank = rank * len(_EVALUATION_SEEDS) + _EVALUATION_SEEDS.index(cell.evaluation_seed)
    rank = rank * len(graphs) + graphs.index(cell.graph_id)
    return rank * len(_CONDITIONS) + _CONDITIONS.index(cell.condition)


def _validate_cells(value: object, phase: str) -> tuple[EvaluationCellResult, ...]:
    if type(value) is not tuple or any(type(item) is not EvaluationCellResult for item in value):
        raise ValueError("cell_results must be an exact EvaluationCellResult tuple")
    previous = -1
    for cell in value:
        if cell.phase != phase or _cell_rank(cell) <= previous:
            raise ValueError("cell_results are not in canonical order")
        previous = _cell_rank(cell)
    return value


@dataclass(frozen=True, slots=True)
class ValidationGateResult:
    phase_complete: bool
    status: str | None
    qualifying_seed_ids: tuple[int, ...]
    observed_row_count: int
    hard_counts: HardIntegrityCounts
    cell_results: tuple[EvaluationCellResult, ...]

    def __post_init__(self) -> None:
        if type(self.phase_complete) is not bool:
            raise ValueError("phase_complete must be an exact bool")
        if self.status not in (None, "INVALID_RUN", "NO_TEST", "READY_FOR_TEST"):
            raise ValueError("validation status is invalid")
        seeds = _validate_seed_ids(self.qualifying_seed_ids, "qualifying_seed_ids")
        _require_exact_int(self.observed_row_count, "observed_row_count", minimum=0)
        zero = _hard_counts_are_zero(self.hard_counts)
        cells = _validate_cells(self.cell_results, "validation")
        if self.status is None:
            if self.phase_complete or seeds or cells or not zero:
                raise ValueError("clean partial validation result is incoherent")
        elif self.status == "INVALID_RUN":
            if seeds or cells or zero:
                raise ValueError("invalid validation result is incoherent")
        else:
            if (not self.phase_complete or self.observed_row_count != 4_200
                    or len(cells) != 84 or not zero):
                raise ValueError("completed validation result is incoherent")
            expected_seeds, expected_status = _validation_summary_from_cells(cells)
            if seeds != expected_seeds or self.status != expected_status:
                raise ValueError("validation claims disagree with cell evidence")


@dataclass(frozen=True, slots=True)
class TestClassificationResult:
    phase_complete: bool
    test_opened: bool
    classification: str | None
    validation_qualified_seed_ids: tuple[int, ...]
    rule_parity_seed_ids: tuple[int, ...]
    credit_signal_seed_ids: tuple[int, ...]
    observed_row_count: int
    hard_counts: HardIntegrityCounts
    cell_results: tuple[EvaluationCellResult, ...]

    def __post_init__(self) -> None:
        if type(self.phase_complete) is not bool or type(self.test_opened) is not bool:
            raise ValueError("phase/test state must use exact bools")
        allowed = (
            None, "INVALID_RUN", "NO_TEST", "RULE_PARITY_SIGNAL",
            "CREDIT_SIGNAL_BELOW_RULE", "NO_CREDIT_SIGNAL",
        )
        if self.classification not in allowed:
            raise ValueError("test classification is invalid")
        qualified = _validate_seed_ids(
            self.validation_qualified_seed_ids, "validation_qualified_seed_ids"
        )
        parity = _validate_seed_ids(self.rule_parity_seed_ids, "rule_parity_seed_ids")
        credit = _validate_seed_ids(self.credit_signal_seed_ids, "credit_signal_seed_ids")
        if any(seed not in qualified for seed in credit) or any(seed not in credit for seed in parity):
            raise ValueError("test proof seed tuples are inconsistent")
        _require_exact_int(self.observed_row_count, "observed_row_count", minimum=0)
        zero = _hard_counts_are_zero(self.hard_counts)
        cells = _validate_cells(self.cell_results, "test")
        if self.classification is None:
            if (self.phase_complete or parity or credit or cells or not zero
                    or (not self.test_opened and self.observed_row_count != 0)):
                raise ValueError("pending test result is incoherent")
        elif self.classification == "INVALID_RUN":
            if parity or credit or cells or zero:
                raise ValueError("invalid test result is incoherent")
        elif self.classification == "NO_TEST":
            if (self.phase_complete or self.test_opened or self.observed_row_count != 0
                    or parity or credit or cells or not zero or len(qualified) > 1):
                raise ValueError("NO_TEST result is incoherent")
        else:
            if (not self.phase_complete or not self.test_opened
                    or self.observed_row_count != 6_300 or len(cells) != 126
                    or not zero or len(qualified) < 2):
                raise ValueError("completed test result is incoherent")
            expected_credit, expected_parity, expected_classification = (
                _test_summary_from_cells(cells, qualified)
            )
            if (
                credit != expected_credit
                or parity != expected_parity
                or self.classification != expected_classification
            ):
                raise ValueError("test claims disagree with cell evidence")


def _thaw_for_config(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_for_config(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_for_config(item) for item in value]
    return value


def _validate_classifier_config(config: object) -> Family3V2PilotConfig:
    if type(config) is not Family3V2PilotConfig:
        raise ValueError("config must be exactly Family3V2PilotConfig")
    raw = {name: _thaw_for_config(getattr(config, name)) for name in _TOP_LEVEL}
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("classifier config differs from the approved frozen contract")
    return config


def _validate_rows(rows: object) -> tuple[EvaluationEpisodeRow, ...]:
    if type(rows) is not tuple or any(type(item) is not EvaluationEpisodeRow for item in rows):
        raise ValueError("rows must be an exact EvaluationEpisodeRow tuple")
    return rows


def _derive_root_seed(config: Family3V2PilotConfig, row: EvaluationEpisodeRow) -> int:
    payload = [
        "family3_v2_eval_coord_v0", config.experiment_id, "environment",
        row.evaluation_seed, row.graph_id, row.episode_ordinal,
    ]
    return int.from_bytes(hashlib.sha256(_canonical(payload)).digest()[:8], "big")


def _phase_graphs(phase: str) -> tuple[str, ...]:
    return _VALIDATION_GRAPHS if phase == "validation" else _TEST_GRAPHS


def _row_rank(row: EvaluationEpisodeRow, graphs: tuple[str, ...]) -> int:
    rank = _METHOD_IDS.index(row.method_id)
    rank = rank * len(_EVALUATION_SEEDS) + _EVALUATION_SEEDS.index(row.evaluation_seed)
    rank = rank * len(graphs) + graphs.index(row.graph_id)
    rank = rank * len(_CONDITIONS) + _CONDITIONS.index(row.condition)
    return rank * 50 + row.episode_ordinal


def _audit_phase(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    phase: str,
    phase_complete: bool,
) -> HardIntegrityCounts:
    graphs = _phase_graphs(phase)
    aggregate = _zero_hard_counts()
    for item in rows:
        aggregate = _add_hard_counts(aggregate, item.hard_counts)
    derived = {name: 0 for name in _HARD_COUNT_NAMES}
    seen_full_coordinates: set[tuple[object, ...]] = set()
    observed_expected_coordinates: set[tuple[object, ...]] = set()
    previous_rank: int | None = None
    for item in rows:
        coordinate = (
            item.method_id, item.evaluation_seed, item.graph_id, item.condition,
            item.episode_ordinal,
        )
        full_coordinate = (item.phase,) + coordinate
        if full_coordinate in seen_full_coordinates:
            derived["duplicate_result_rows"] += 1
        else:
            seen_full_coordinates.add(full_coordinate)
        valid_coordinate = (
            item.phase == phase
            and item.method_id in _METHOD_IDS
            and item.evaluation_seed in _EVALUATION_SEEDS
            and item.graph_id in graphs
            and item.condition in _CONDITIONS
            and 0 <= item.episode_ordinal < 50
        )
        if not valid_coordinate:
            derived["unexpected_result_rows"] += 1
            previous_rank = None
        else:
            rank = _row_rank(item, graphs)
            if previous_rank is not None and rank <= previous_rank:
                derived["unexpected_result_rows"] += 1
            previous_rank = rank
            observed_expected_coordinates.add(coordinate)
        if item.root_seed != _derive_root_seed(config, item):
            derived["common_random_coordinate_mismatches"] += 1
        if item.root_semantic_candidate_id in (ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE):
            derived["semantic_conformance_failures"] += 1
        elif (phase_complete and valid_coordinate and item.method_id == "forecast_rule"
              and item.root_semantic_candidate_id not in ("request_narrow", "request_broader")):
            derived["semantic_conformance_failures"] += 1
    if phase_complete:
        expected_count = len(_METHOD_IDS) * len(_EVALUATION_SEEDS) * len(graphs) * len(_CONDITIONS) * 50
        derived["missing_expected_result_rows"] = expected_count - len(observed_expected_coordinates)
    return _increment_hard_counts(
        aggregate,
        **{name: value for name, value in derived.items() if value},
    )


def _build_cell_results(
    rows: tuple[EvaluationEpisodeRow, ...], phase: str,
) -> tuple[EvaluationCellResult, ...]:
    graphs = _phase_graphs(phase)
    indexed = {
        (item.method_id, item.evaluation_seed, item.graph_id, item.condition,
         item.episode_ordinal): item
        for item in rows
    }
    zero = _zero_hard_counts()
    cells: list[EvaluationCellResult] = []
    for method_id in _METHOD_IDS:
        for seed in _EVALUATION_SEEDS:
            for graph_id in graphs:
                for condition in _CONDITIONS:
                    episodes = tuple(
                        indexed[(method_id, seed, graph_id, condition, ordinal)]
                        for ordinal in range(50)
                    )
                    forecast = tuple(
                        indexed[("forecast_rule", seed, graph_id, condition, ordinal)]
                        for ordinal in range(50)
                    )
                    cells.append(EvaluationCellResult(
                        phase=phase,
                        method_id=method_id,
                        evaluation_seed=seed,
                        graph_id=graph_id,
                        condition=condition,
                        episode_count=50,
                        terminal_success_count=sum(item.terminal_success for item in episodes),
                        first_request_match_count=sum(
                            int(item.root_semantic_candidate_id == paired.root_semantic_candidate_id)
                            for item, paired in zip(episodes, forecast)
                        ),
                        forecast_rule_terminal_match_count=sum(
                            int(item.terminal_success == paired.terminal_success)
                            for item, paired in zip(episodes, forecast)
                        ),
                        hard_counts=zero,
                    ))
    return tuple(cells)


def _cells_for(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> tuple[EvaluationCellResult, ...]:
    return tuple(
        cell for cell in cells
        if cell.method_id == method_id and cell.evaluation_seed == seed
    )


def _pooled_success(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> int:
    return sum(cell.terminal_success_count for cell in _cells_for(cells, method_id, seed))


def _pooled_first_match(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> int:
    return sum(cell.first_request_match_count for cell in _cells_for(cells, method_id, seed))


def _validation_summary_from_cells(
    cells: tuple[EvaluationCellResult, ...],
) -> tuple[tuple[int, ...], str]:
    qualifying: list[int] = []
    for seed in _EVALUATION_SEEDS:
        gamma1 = _cells_for(cells, "masked_ddqn_gamma1", seed)
        if (
            all(cell.first_request_match_count == 50 for cell in gamma1)
            and all(cell.forecast_rule_terminal_match_count == 50 for cell in gamma1)
            and _pooled_success(cells, "masked_ddqn_gamma1", seed)
            > _pooled_success(cells, "masked_ddqn_gamma0", seed)
            and _pooled_success(cells, "masked_ddqn_gamma1", seed)
            > _pooled_success(cells, "forecast_ablated_rule", seed)
        ):
            qualifying.append(seed)
    qualifying_ids = tuple(qualifying)
    status = "READY_FOR_TEST" if len(qualifying_ids) >= 2 else "NO_TEST"
    return qualifying_ids, status


def _test_summary_from_cells(
    cells: tuple[EvaluationCellResult, ...],
    permitted_seed_ids: tuple[int, ...],
) -> tuple[tuple[int, ...], tuple[int, ...], str]:
    credit: list[int] = []
    parity: list[int] = []
    for seed in permitted_seed_ids:
        gamma1_success = _pooled_success(cells, "masked_ddqn_gamma1", seed)
        gamma1_first = _pooled_first_match(cells, "masked_ddqn_gamma1", seed)
        is_credit = (
            gamma1_success > _pooled_success(cells, "masked_ddqn_gamma0", seed)
            and gamma1_success > _pooled_success(cells, "forecast_ablated_rule", seed)
            and gamma1_first > _pooled_first_match(cells, "masked_ddqn_gamma0", seed)
            and gamma1_first > _pooled_first_match(cells, "forecast_ablated_rule", seed)
        )
        if is_credit:
            credit.append(seed)
            gamma1_cells = _cells_for(cells, "masked_ddqn_gamma1", seed)
            if (
                all(cell.first_request_match_count == 50 for cell in gamma1_cells)
                and all(cell.forecast_rule_terminal_match_count == 50 for cell in gamma1_cells)
            ):
                parity.append(seed)
    credit_ids = tuple(credit)
    parity_ids = tuple(parity)
    if len(parity_ids) >= 2:
        classification = "RULE_PARITY_SIGNAL"
    elif len(credit_ids) >= 2:
        classification = "CREDIT_SIGNAL_BELOW_RULE"
    else:
        classification = "NO_CREDIT_SIGNAL"
    return credit_ids, parity_ids, classification


def evaluate_validation_gate(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    phase_complete: bool,
) -> ValidationGateResult:
    checked_config = _validate_classifier_config(config)
    checked_rows = _validate_rows(rows)
    if type(phase_complete) is not bool:
        raise ValueError("phase_complete must be an exact bool")
    hard_counts = _audit_phase(
        checked_config, checked_rows, "validation", phase_complete
    )
    if not _hard_counts_are_zero(hard_counts):
        return ValidationGateResult(
            phase_complete=phase_complete,
            status="INVALID_RUN",
            qualifying_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=hard_counts,
            cell_results=(),
        )
    if not phase_complete:
        return ValidationGateResult(
            phase_complete=False,
            status=None,
            qualifying_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=hard_counts,
            cell_results=(),
        )
    cells = _build_cell_results(checked_rows, "validation")
    qualifying_ids, status = _validation_summary_from_cells(cells)
    return ValidationGateResult(
        phase_complete=True,
        status=status,
        qualifying_seed_ids=qualifying_ids,
        observed_row_count=len(checked_rows),
        hard_counts=hard_counts,
        cell_results=cells,
    )


def _make_invalid_test_result(
    validation_gate: ValidationGateResult,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    test_opened: bool,
    phase_complete: bool,
    hard_counts: HardIntegrityCounts,
) -> TestClassificationResult:
    return TestClassificationResult(
        phase_complete=phase_complete,
        test_opened=test_opened,
        classification="INVALID_RUN",
        validation_qualified_seed_ids=validation_gate.qualifying_seed_ids,
        rule_parity_seed_ids=(),
        credit_signal_seed_ids=(),
        observed_row_count=len(rows),
        hard_counts=hard_counts,
        cell_results=(),
    )


def classify_test_result(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    validation_gate: ValidationGateResult,
    permitted_seed_ids: tuple[int, ...],
    test_opened: bool,
    phase_complete: bool,
) -> TestClassificationResult:
    checked_config = _validate_classifier_config(config)
    checked_rows = _validate_rows(rows)
    if type(validation_gate) is not ValidationGateResult:
        raise ValueError("validation_gate must be exactly ValidationGateResult")
    permitted = _validate_seed_ids(permitted_seed_ids, "permitted_seed_ids")
    if type(test_opened) is not bool or type(phase_complete) is not bool:
        raise ValueError("test_opened and phase_complete must be exact bools")

    qualified = validation_gate.qualifying_seed_ids
    zero = _zero_hard_counts()
    premature_test_counts = (
        _audit_phase(checked_config, checked_rows, "test", False)
        if checked_rows else zero
    )
    combined = _add_hard_counts(validation_gate.hard_counts, premature_test_counts)

    if validation_gate.status == "INVALID_RUN":
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=test_opened,
            phase_complete=phase_complete, hard_counts=combined,
        )

    if validation_gate.status is None:
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        if not _hard_counts_are_zero(combined):
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=test_opened,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    if validation_gate.status == "NO_TEST":
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        if not _hard_counts_are_zero(combined):
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=test_opened,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification="NO_TEST",
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    if validation_gate.status != "READY_FOR_TEST":
        raise ValueError("validation gate status is incoherent")
    if permitted != qualified:
        combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=test_opened,
            phase_complete=phase_complete, hard_counts=combined,
        )
    if not test_opened:
        if checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=False,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    test_counts = _audit_phase(
        checked_config, checked_rows, "test", phase_complete
    )
    combined = _add_hard_counts(validation_gate.hard_counts, test_counts)
    if not _hard_counts_are_zero(combined):
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=True,
            phase_complete=phase_complete, hard_counts=combined,
        )
    if not phase_complete:
        return TestClassificationResult(
            phase_complete=False,
            test_opened=True,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=combined,
            cell_results=(),
        )

    cells = _build_cell_results(checked_rows, "test")
    credit_ids, parity_ids, classification = _test_summary_from_cells(
        cells, permitted
    )
    return TestClassificationResult(
        phase_complete=True,
        test_opened=True,
        classification=classification,
        validation_qualified_seed_ids=qualified,
        rule_parity_seed_ids=parity_ids,
        credit_signal_seed_ids=credit_ids,
        observed_row_count=len(checked_rows),
        hard_counts=combined,
        cell_results=cells,
    )
