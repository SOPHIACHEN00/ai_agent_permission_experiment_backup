"""Durable final-checkpoint and test-once store for the Family-3 v2 pilot."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, fields
from io import BytesIO
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import random
import stat
import tempfile
from typing import Callable, Iterator, Mapping, TypeAlias

import torch

from .baselines import TabularQLearner
from .ddqn import DDQNHyperparameters, _ReplayBuffer, _ReplayTransition
from .family3_v2_learning import (
    FAMILY3_V2_DDQN_MODEL_SPEC,
    Family3V2LearnerRngDeriver,
    Family3V2MaskedDoubleDQN,
    derive_family3_v2_eval_environment_seed,
)
from .family3_v2_pilot_criteria import (
    EvaluationCellResult,
    EvaluationEpisodeRow,
    Family3V2PilotConfig,
    HardIntegrityCounts,
    TestClassificationResult,
    ValidationGateResult,
    classify_test_result,
    evaluate_validation_gate,
    load_family3_v2_pilot_config,
    verify_certified_dependency_baseline,
)


PathLike: TypeAlias = str | os.PathLike[str]
EvaluationCoordinate: TypeAlias = tuple[str, int, str, str, int]
CheckpointLearner: TypeAlias = Family3V2MaskedDoubleDQN | TabularQLearner
_TestCrashHook: TypeAlias = Callable[[str, str], None]

_METHOD_IDS = (
    "random_valid", "forecast_ablated_rule", "forecast_rule",
    "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
    "masked_ddqn_gamma1",
)
_TRAINED_METHOD_IDS = (
    "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
    "masked_ddqn_gamma1",
)
_TRAIN_GRAPHS = tuple(f"i8_f3v2_v{index}" for index in range(5))
_VALIDATION_GRAPHS = ("i8_f3v2_v5", "i8_f3v2_v6")
_TEST_GRAPHS = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")
_CONDITIONS = ("original", "forecast_counterfactual")
_FORMAL_SEEDS = (17, 29, 43)
_SMOKE_SEEDS = (17,)
_ZERO_HASH = "0" * 64
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "configs/evaluation/family3_v2_learner_pilot_v0.json"
_BASELINE_PATH = _PROJECT_ROOT / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
_FORMAL_ROOT_NAME = "increment8_family3_v2_learner_pilot_v0"
_SMOKE_ROOT_NAME = "increment8_family3_v2_learner_pilot_v0_non_evidence_smoke"
_DURABILITY_PROFILE = "file_fsync_atomic_replace_atomic_exclusive_link_dirsync_v0"
_CONFIG_SHA256 = "7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2"
_BASELINE_SHA256 = "c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef"
_SUITE_SHA256 = "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c"
_CERTIFIED_VERDICT_SHA256 = "ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552"
_ENGLISH_SPEC_SHA256 = "f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9"
_CHINESE_SPEC_SHA256 = "0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20"
_CERTIFIED_VERDICT_PATH = (
    "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/"
    "final_verdict.json"
)
_SUITE_VERSION = "increment8_family3_v2_forecast_scope_reservation_v0"
_HARD_FIELDS = (
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


class DuplicateCoordinateError(ValueError):
    """A coordinate already exists with the same canonical payload."""


class ConflictingCoordinateError(ValueError):
    """A coordinate already exists with a different canonical payload."""


@dataclass(slots=True)
class _FaultGuard:
    root: Path
    hook: _TestCrashHook
    active: bool = True


_FAULT_GUARD: ContextVar[_FaultGuard | None] = ContextVar(
    "family3_v2_task5_fault_guard", default=None
)


def _is_reparse(path: Path) -> bool:
    info = path.lstat()
    attributes = getattr(info, "st_file_attributes", 0)
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & marker)


def _reject_symlink_or_reparse(path: Path) -> None:
    if path.is_symlink() or _is_reparse(path):
        raise ValueError("path contains a symbolic link or reparse point")


@contextmanager
def _task5_test_fault_injection(
    test_root: PathLike, hook: _TestCrashHook,
) -> Iterator[None]:
    if not callable(hook):
        raise ValueError("hook must be callable")
    supplied = Path(test_root)
    if not supplied.is_absolute() or supplied != supplied.resolve():
        raise ValueError("test root must be the exact resolved path")
    _reject_symlink_or_reparse(supplied)
    if (
        supplied.name in (_FORMAL_ROOT_NAME, _SMOKE_ROOT_NAME)
        or not supplied.is_dir()
        or any(supplied.iterdir())
    ):
        raise ValueError("fault injection requires an empty temporary root")
    guard = _FaultGuard(supplied, hook)
    token = _FAULT_GUARD.set(guard)
    try:
        yield None
    finally:
        guard.active = False
        _FAULT_GUARD.reset(token)


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("value is not canonical-JSON serializable") from error


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _raw_ref(path: Path, root: Path, logical_name: str) -> list[object]:
    content = path.read_bytes()
    return [
        logical_name, path.relative_to(root).as_posix(),
        _sha256_bytes(content), len(content),
    ]


def _exact_str(value: object, name: str, *, nonempty: bool = True) -> str:
    if type(value) is not str or (nonempty and not value):
        raise ValueError(f"{name} must be an exact nonempty string")
    return value


def _exact_int(
    value: object, name: str, *, minimum: int = 0,
) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an exact integer in range")
    return value


def _digest(value: object, name: str) -> str:
    text = _exact_str(value, name)
    if (
        len(text) != 64
        or text != text.lower()
        or any(character not in "0123456789abcdef" for character in text)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return text


def _tuple_of_unique_strings(
    value: object, name: str,
) -> tuple[str, ...]:
    if (
        type(value) is not tuple
        or any(type(item) is not str or not item for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{name} must be a unique exact string tuple")
    return value


def _runtime_has_absolute_hint(value: str) -> bool:
    return (
        "\x00" in value
        or value.startswith(("/", "\\"))
        or "\\" in value
        or (len(value) >= 3 and value[1] == ":" and value[2] in "/\\")
    )


def _device_mapping(boundary: "PilotBoundary") -> dict[str, object]:
    return {
        "python_implementation": boundary.python_implementation,
        "python_version": boundary.python_version,
        "torch_version": boundary.torch_version,
        "platform_system": boundary.platform_system,
        "platform_machine": boundary.platform_machine,
        "device_type": boundary.device_type,
    }


@dataclass(frozen=True, slots=True)
class PilotBoundary:
    schema_version: str
    evidence_mode: str
    experiment_id: str
    config_relative_path: str
    config_sha256: str
    config_byte_size: int
    source_manifest_relative_path: str
    source_manifest_sha256: str
    source_manifest_byte_size: int
    certified_dependency_manifest_relative_path: str
    certified_dependency_manifest_sha256: str
    certified_dependency_manifest_byte_size: int
    certified_suite_version: str
    certified_suite_sha256: str
    certified_final_verdict_relative_path: str
    certified_final_verdict_sha256: str
    english_spec_sha256: str
    chinese_spec_sha256: str
    method_ids: tuple[str, ...]
    trained_method_ids: tuple[str, ...]
    training_seeds: tuple[int, ...]
    train_graph_ids: tuple[str, ...]
    validation_graph_ids: tuple[str, ...]
    test_graph_ids: tuple[str, ...]
    condition_ids: tuple[str, ...]
    transitions_per_arm: int
    transitions_per_train_graph: int
    episodes_per_evaluation_cell: int
    python_implementation: str
    python_version: str
    torch_version: str
    platform_system: str
    platform_machine: str
    device_type: str
    device_identity_sha256: str
    durability_profile: str

    def __post_init__(self) -> None:
        if self.schema_version != "family3_v2_pilot_boundary_v0":
            raise ValueError("boundary schema is invalid")
        if self.evidence_mode not in ("FORMAL", "NON_EVIDENCE_SMOKE"):
            raise ValueError("evidence mode is invalid")
        if self.experiment_id != "increment8_family3_v2_learner_pilot_v0":
            raise ValueError("experiment ID is invalid")
        if (
            self.config_relative_path != "config.json"
            or self.source_manifest_relative_path != "source_manifest.json"
            or self.certified_dependency_manifest_relative_path
            != "certified_dependency_manifest.json"
        ):
            raise ValueError("boundary copied paths are invalid")
        for name in (
            "config_sha256", "source_manifest_sha256",
            "certified_dependency_manifest_sha256", "certified_suite_sha256",
            "certified_final_verdict_sha256", "english_spec_sha256",
            "chinese_spec_sha256", "device_identity_sha256",
        ):
            _digest(getattr(self, name), name)
        for name in (
            "config_byte_size", "source_manifest_byte_size",
            "certified_dependency_manifest_byte_size",
        ):
            _exact_int(getattr(self, name), name)
        if self.method_ids != _METHOD_IDS:
            raise ValueError("method order is invalid")
        if self.trained_method_ids != _TRAINED_METHOD_IDS:
            raise ValueError("trained method order is invalid")
        if (
            type(self.training_seeds) is not tuple
            or any(type(seed) is not int for seed in self.training_seeds)
            or len(set(self.training_seeds)) != len(self.training_seeds)
        ):
            raise ValueError("training seeds are invalid")
        guard = _FAULT_GUARD.get()
        expected_seeds = (
            _FORMAL_SEEDS if self.evidence_mode == "FORMAL" else _SMOKE_SEEDS
        )
        if self.training_seeds != expected_seeds:
            if (
                guard is None
                or not self.training_seeds
                or self.training_seeds
                != tuple(seed for seed in _FORMAL_SEEDS if seed in self.training_seeds)
            ):
                raise ValueError("training seed order is invalid")
        if (
            self.train_graph_ids != _TRAIN_GRAPHS
            or self.validation_graph_ids != _VALIDATION_GRAPHS
            or self.test_graph_ids != _TEST_GRAPHS
            or self.condition_ids != _CONDITIONS
        ):
            raise ValueError("graph or condition order is invalid")
        for name in (
            "train_graph_ids", "validation_graph_ids", "test_graph_ids",
            "condition_ids",
        ):
            _tuple_of_unique_strings(getattr(self, name), name)
        for name in (
            "transitions_per_arm", "transitions_per_train_graph",
            "episodes_per_evaluation_cell",
        ):
            _exact_int(getattr(self, name), name, minimum=1)
        expected_budget = (
            (12_000, 2_400, 50)
            if self.evidence_mode == "FORMAL"
            else (320, 64, 1)
        )
        actual_budget = (
            self.transitions_per_arm, self.transitions_per_train_graph,
            self.episodes_per_evaluation_cell,
        )
        if actual_budget != expected_budget:
            if (
                guard is None
                or self.transitions_per_arm
                != len(_TRAIN_GRAPHS) * self.transitions_per_train_graph
            ):
                raise ValueError("boundary budgets are invalid")
        if (
            self.config_sha256 != _CONFIG_SHA256
            or self.config_byte_size != 8_377
            or self.certified_dependency_manifest_sha256 != _BASELINE_SHA256
            or self.certified_dependency_manifest_byte_size != 11_338
            or self.certified_suite_version != _SUITE_VERSION
            or self.certified_suite_sha256 != _SUITE_SHA256
            or self.certified_final_verdict_relative_path
            != _CERTIFIED_VERDICT_PATH
            or self.certified_final_verdict_sha256
            != _CERTIFIED_VERDICT_SHA256
            or self.english_spec_sha256 != _ENGLISH_SPEC_SHA256
            or self.chinese_spec_sha256 != _CHINESE_SPEC_SHA256
        ):
            raise ValueError("boundary frozen authority is invalid")
        for name in (
            "python_implementation", "python_version", "torch_version",
            "platform_system", "platform_machine", "device_type",
        ):
            value = _exact_str(getattr(self, name), name)
            if _runtime_has_absolute_hint(value):
                raise ValueError("runtime values cannot contain absolute paths")
        if self.device_type != "cpu":
            raise ValueError("device type must be cpu")
        if (
            self.device_identity_sha256
            != _sha256_bytes(_canonical(_device_mapping(self)))
        ):
            raise ValueError("device identity hash is invalid")
        if self.durability_profile != _DURABILITY_PROFILE:
            raise ValueError("durability profile is invalid")


def _checkpoint_paths(
    method_id: str, seed: int, attempt: int,
) -> tuple[str, str]:
    suffix = "checkpoint.json" if method_id.startswith("tabular_") else "checkpoint.pt"
    base = f"training/{method_id}/{seed}/attempts/{attempt:04d}"
    return f"{base}/{suffix}", f"{base}/checkpoint_manifest.json"


def _canonical_relative(value: object, name: str) -> str:
    text = _exact_str(value, name)
    if (
        "\x00" in text or "\\" in text or text.startswith("/")
        or len(text) >= 2 and text[1] == ":"
    ):
        raise ValueError(f"{name} is not canonical POSIX-relative text")
    pure = PurePosixPath(text)
    if (
        str(pure) != text or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise ValueError(f"{name} is not canonical POSIX-relative text")
    return text


@dataclass(frozen=True, slots=True)
class FinalCheckpointRef:
    schema_version: str
    method_id: str
    training_seed: int
    attempt_number: int
    checkpoint_kind: str
    payload_relative_path: str
    payload_sha256: str
    payload_byte_size: int
    manifest_relative_path: str
    manifest_sha256: str
    manifest_byte_size: int
    boundary_sha256: str
    transition_count: int
    per_graph_transition_counts: tuple[tuple[str, int], ...]
    semantic_state_sha256: str
    evaluation_fingerprint_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "family3_v2_final_checkpoint_ref_v0":
            raise ValueError("checkpoint ref schema is invalid")
        if self.method_id not in _TRAINED_METHOD_IDS:
            raise ValueError("checkpoint method is invalid")
        if type(self.training_seed) is not int:
            raise ValueError("checkpoint seed must be an exact integer")
        _exact_int(self.attempt_number, "attempt_number", minimum=1)
        if self.attempt_number > 9_999:
            raise ValueError("attempt number exceeds the fixed path width")
        expected_kind = (
            "tabular_q"
            if self.method_id.startswith("tabular_") else "masked_ddqn"
        )
        if self.checkpoint_kind != expected_kind:
            raise ValueError("checkpoint kind is invalid")
        payload_path, manifest_path = _checkpoint_paths(
            self.method_id, self.training_seed, self.attempt_number
        )
        if (
            _canonical_relative(
                self.payload_relative_path, "payload_relative_path"
            ) != payload_path
            or _canonical_relative(
                self.manifest_relative_path, "manifest_relative_path"
            ) != manifest_path
        ):
            raise ValueError("checkpoint ref paths are not coordinate-derived")
        for name in (
            "payload_sha256", "manifest_sha256", "boundary_sha256",
            "semantic_state_sha256", "evaluation_fingerprint_sha256",
        ):
            _digest(getattr(self, name), name)
        _exact_int(self.payload_byte_size, "payload_byte_size")
        _exact_int(self.manifest_byte_size, "manifest_byte_size")
        _exact_int(self.transition_count, "transition_count", minimum=1)
        if (
            type(self.per_graph_transition_counts) is not tuple
            or any(
                type(pair) is not tuple or len(pair) != 2
                or type(pair[0]) is not str or type(pair[1]) is not int
                for pair in self.per_graph_transition_counts
            )
        ):
            raise ValueError("per-graph counts are invalid")


def _boundary_mapping(boundary: PilotBoundary) -> dict[str, object]:
    return {field.name: getattr(boundary, field.name) for field in fields(PilotBoundary)}


def _ref_mapping(reference: FinalCheckpointRef) -> dict[str, object]:
    return {
        "schema_version": reference.schema_version,
        "method_id": reference.method_id,
        "training_seed": reference.training_seed,
        "attempt_number": reference.attempt_number,
        "checkpoint_kind": reference.checkpoint_kind,
        "payload_relative_path": reference.payload_relative_path,
        "payload_sha256": reference.payload_sha256,
        "payload_byte_size": reference.payload_byte_size,
        "manifest_relative_path": reference.manifest_relative_path,
        "manifest_sha256": reference.manifest_sha256,
        "manifest_byte_size": reference.manifest_byte_size,
        "boundary_sha256": reference.boundary_sha256,
        "transition_count": reference.transition_count,
        "per_graph_transition_counts": [
            [graph_id, count]
            for graph_id, count in reference.per_graph_transition_counts
        ],
        "semantic_state_sha256": reference.semantic_state_sha256,
        "evaluation_fingerprint_sha256": (
            reference.evaluation_fingerprint_sha256
        ),
    }


def _ref_from_mapping(value: object) -> FinalCheckpointRef:
    keys = tuple(field.name for field in fields(FinalCheckpointRef))
    if type(value) is not dict or tuple(value) != keys:
        raise ValueError("checkpoint ref mapping is malformed")
    counts = value["per_graph_transition_counts"]
    if (
        type(counts) is not list
        or any(type(pair) is not list or len(pair) != 2 for pair in counts)
    ):
        raise ValueError("checkpoint graph counts are malformed")
    return FinalCheckpointRef(
        **{
            **{name: value[name] for name in keys if name != "per_graph_transition_counts"},
            "per_graph_transition_counts": tuple(
                (pair[0], pair[1]) for pair in counts
            ),
        }
    )


def _hard_mapping(counts: HardIntegrityCounts) -> dict[str, object]:
    if type(counts) is not HardIntegrityCounts:
        raise ValueError("hard counts have the wrong exact type")
    return {name: getattr(counts, name) for name in _HARD_FIELDS}


def _hard_from_mapping(value: object) -> HardIntegrityCounts:
    if type(value) is not dict or tuple(value) != _HARD_FIELDS:
        raise ValueError("hard-count mapping is malformed")
    return HardIntegrityCounts(**{name: value[name] for name in _HARD_FIELDS})


def _row_mapping(row: EvaluationEpisodeRow) -> dict[str, object]:
    if type(row) is not EvaluationEpisodeRow:
        raise ValueError("row must be exactly EvaluationEpisodeRow")
    return {
        "phase": row.phase,
        "method_id": row.method_id,
        "evaluation_seed": row.evaluation_seed,
        "graph_id": row.graph_id,
        "condition": row.condition,
        "episode_ordinal": row.episode_ordinal,
        "root_seed": row.root_seed,
        "root_semantic_candidate_id": row.root_semantic_candidate_id,
        "terminal_success": row.terminal_success,
        "termination_kind": row.termination_kind,
        "decision_count": row.decision_count,
        "prompt_count": row.prompt_count,
        "hard_counts": _hard_mapping(row.hard_counts),
    }


def _row_from_mapping(value: object) -> EvaluationEpisodeRow:
    keys = tuple(field.name for field in fields(EvaluationEpisodeRow))
    if type(value) is not dict or tuple(value) != keys:
        raise ValueError("row mapping is malformed")
    return EvaluationEpisodeRow(
        phase=value["phase"], method_id=value["method_id"],
        evaluation_seed=value["evaluation_seed"], graph_id=value["graph_id"],
        condition=value["condition"], episode_ordinal=value["episode_ordinal"],
        root_seed=value["root_seed"],
        root_semantic_candidate_id=value["root_semantic_candidate_id"],
        terminal_success=value["terminal_success"],
        termination_kind=value["termination_kind"],
        decision_count=value["decision_count"],
        prompt_count=value["prompt_count"],
        hard_counts=_hard_from_mapping(value["hard_counts"]),
    )


def _cell_mapping(cell: EvaluationCellResult) -> dict[str, object]:
    if type(cell) is not EvaluationCellResult:
        raise ValueError("cell must be exactly EvaluationCellResult")
    return {
        "phase": cell.phase,
        "method_id": cell.method_id,
        "evaluation_seed": cell.evaluation_seed,
        "graph_id": cell.graph_id,
        "condition": cell.condition,
        "episode_count": cell.episode_count,
        "terminal_success_count": cell.terminal_success_count,
        "first_request_match_count": cell.first_request_match_count,
        "forecast_rule_terminal_match_count": (
            cell.forecast_rule_terminal_match_count
        ),
        "hard_counts": _hard_mapping(cell.hard_counts),
    }


def _cell_from_mapping(value: object) -> EvaluationCellResult:
    keys = tuple(field.name for field in fields(EvaluationCellResult))
    if type(value) is not dict or tuple(value) != keys:
        raise ValueError("cell mapping is malformed")
    return EvaluationCellResult(
        phase=value["phase"], method_id=value["method_id"],
        evaluation_seed=value["evaluation_seed"], graph_id=value["graph_id"],
        condition=value["condition"], episode_count=value["episode_count"],
        terminal_success_count=value["terminal_success_count"],
        first_request_match_count=value["first_request_match_count"],
        forecast_rule_terminal_match_count=(
            value["forecast_rule_terminal_match_count"]
        ),
        hard_counts=_hard_from_mapping(value["hard_counts"]),
    )


def _validation_mapping(result: ValidationGateResult) -> dict[str, object]:
    if type(result) is not ValidationGateResult:
        raise ValueError("validation result has the wrong exact type")
    return {
        "phase_complete": result.phase_complete,
        "status": result.status,
        "qualifying_seed_ids": list(result.qualifying_seed_ids),
        "observed_row_count": result.observed_row_count,
        "hard_counts": _hard_mapping(result.hard_counts),
        "cell_results": [_cell_mapping(cell) for cell in result.cell_results],
    }


def _validation_from_mapping(value: object) -> ValidationGateResult:
    keys = tuple(field.name for field in fields(ValidationGateResult))
    if type(value) is not dict or tuple(value) != keys:
        raise ValueError("validation-result mapping is malformed")
    if (
        type(value["qualifying_seed_ids"]) is not list
        or type(value["cell_results"]) is not list
    ):
        raise ValueError("validation result arrays are malformed")
    return ValidationGateResult(
        phase_complete=value["phase_complete"], status=value["status"],
        qualifying_seed_ids=tuple(value["qualifying_seed_ids"]),
        observed_row_count=value["observed_row_count"],
        hard_counts=_hard_from_mapping(value["hard_counts"]),
        cell_results=tuple(
            _cell_from_mapping(cell) for cell in value["cell_results"]
        ),
    )


def _test_mapping(result: TestClassificationResult) -> dict[str, object]:
    if type(result) is not TestClassificationResult:
        raise ValueError("test result has the wrong exact type")
    return {
        "phase_complete": result.phase_complete,
        "test_opened": result.test_opened,
        "classification": result.classification,
        "validation_qualified_seed_ids": list(
            result.validation_qualified_seed_ids
        ),
        "rule_parity_seed_ids": list(result.rule_parity_seed_ids),
        "credit_signal_seed_ids": list(result.credit_signal_seed_ids),
        "observed_row_count": result.observed_row_count,
        "hard_counts": _hard_mapping(result.hard_counts),
        "cell_results": [_cell_mapping(cell) for cell in result.cell_results],
    }


def _test_from_mapping(value: object) -> TestClassificationResult:
    keys = tuple(field.name for field in fields(TestClassificationResult))
    if type(value) is not dict or tuple(value) != keys:
        raise ValueError("test-result mapping is malformed")
    array_names = (
        "validation_qualified_seed_ids", "rule_parity_seed_ids",
        "credit_signal_seed_ids", "cell_results",
    )
    if any(type(value[name]) is not list for name in array_names):
        raise ValueError("test result arrays are malformed")
    return TestClassificationResult(
        phase_complete=value["phase_complete"],
        test_opened=value["test_opened"],
        classification=value["classification"],
        validation_qualified_seed_ids=tuple(
            value["validation_qualified_seed_ids"]
        ),
        rule_parity_seed_ids=tuple(value["rule_parity_seed_ids"]),
        credit_signal_seed_ids=tuple(value["credit_signal_seed_ids"]),
        observed_row_count=value["observed_row_count"],
        hard_counts=_hard_from_mapping(value["hard_counts"]),
        cell_results=tuple(
            _cell_from_mapping(cell) for cell in value["cell_results"]
        ),
    )


_TENSOR_DTYPES = {
    torch.bool: "torch.bool",
    torch.uint8: "torch.uint8",
    torch.int8: "torch.int8",
    torch.int16: "torch.int16",
    torch.int32: "torch.int32",
    torch.int64: "torch.int64",
    torch.float16: "torch.float16",
    torch.bfloat16: "torch.bfloat16",
    torch.float32: "torch.float32",
    torch.float64: "torch.float64",
}


def _tensor_bytes(tensor: torch.Tensor) -> bytes:
    contiguous = tensor.detach().to(device="cpu").contiguous()
    # Optimizer step counters are scalars; dtype views require a dimension.
    return contiguous.reshape(-1).view(torch.uint8).numpy().tobytes()


def _normalize(value: object) -> object:
    if value is None:
        return ["none"]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", str(value)]
    if type(value) is str:
        return ["str", value]
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite float cannot be normalized")
        return ["float", value.hex()]
    if type(value) is bytes:
        return ["bytes", len(value), _sha256_bytes(value)]
    if type(value) is list:
        return ["list", [_normalize(item) for item in value]]
    if type(value) is tuple:
        return ["tuple", [_normalize(item) for item in value]]
    if isinstance(value, Mapping):
        normalized: list[tuple[bytes, object, object]] = []
        seen: set[bytes] = set()
        for key, item in value.items():
            normalized_key = _normalize(key)
            key_bytes = _canonical(normalized_key)
            if key_bytes in seen:
                raise ValueError("mapping has duplicate normalized keys")
            seen.add(key_bytes)
            normalized.append((
                key_bytes, normalized_key, _normalize(item),
            ))
        normalized.sort(key=lambda item: item[0])
        return [
            "mapping",
            [[key, item] for _, key, item in normalized],
        ]
    if isinstance(value, torch.Tensor):
        tensor = value.detach()
        if (
            tensor.layout is not torch.strided
            or tensor.is_sparse
            or tensor.is_quantized
            or tensor.device.type == "meta"
            or tensor.dtype not in _TENSOR_DTYPES
        ):
            raise ValueError("tensor representation is unsupported")
        cpu = tensor.to(device="cpu").contiguous()
        if (
            cpu.dtype in (
                torch.float16, torch.bfloat16, torch.float32, torch.float64,
            )
            and not bool(torch.isfinite(cpu).all().item())
        ):
            raise ValueError("tensor contains nonfinite values")
        raw = _tensor_bytes(cpu)
        return [
            "tensor", _TENSOR_DTYPES[cpu.dtype], list(cpu.shape),
            len(raw), _sha256_bytes(raw),
        ]
    raise ValueError(f"unsupported semantic value type: {type(value)!r}")


def _semantic_digest(value: object) -> str:
    return _sha256_bytes(_canonical(_normalize(value)))


def _float_hex(value: object, name: str) -> str:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be finite numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number.hex()


def _decode_float_hex(value: object, name: str) -> float:
    text = _exact_str(value, name)
    try:
        number = float.fromhex(text)
    except ValueError as error:
        raise ValueError(f"{name} is not a float.hex value") from error
    if not math.isfinite(number) or number.hex() != text:
        raise ValueError(f"{name} is not a canonical finite float.hex value")
    return number


def _path_within(root: Path, relative: str, *, final_file: bool = False) -> Path:
    text = _canonical_relative(relative, "relative_path")
    candidate = root.joinpath(*PurePosixPath(text).parts)
    resolved_root = root.resolve()
    current = resolved_root
    for part in PurePosixPath(text).parts[:-1]:
        current = current / part
        if current.exists():
            _reject_symlink_or_reparse(current)
            if not current.is_dir():
                raise ValueError("artifact ancestor is not a directory")
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("artifact path escapes the output root") from error
    if os.name == "nt":
        if (
            os.path.normcase(str(resolved)).split(":", 1)[0]
            != os.path.normcase(str(resolved_root)).split(":", 1)[0]
        ):
            raise ValueError("artifact path crosses Windows drives")
    if final_file and candidate.exists():
        _reject_symlink_or_reparse(candidate)
        if not candidate.is_file():
            raise ValueError("artifact is not a regular file")
    return candidate


def _make_parent(root: Path, relative: str) -> Path:
    destination = _path_within(root, relative, final_file=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    parent_relative = destination.parent.relative_to(root).as_posix()
    if parent_relative != ".":
        _path_within(root, f"{parent_relative}/.sentinel")
    return destination


def _read_exact_json(path: Path, keys: tuple[str, ...]) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("artifact is not strict UTF-8 JSON") from error
    if (
        type(value) is not dict or tuple(value) != keys
        or _canonical(value) != raw
    ):
        raise ValueError("artifact JSON is noncanonical or has wrong fields")
    return value


def _runtime_matches(boundary: PilotBoundary) -> bool:
    return _device_mapping(boundary) == {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "torch_version": str(torch.__version__),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "device_type": "cpu",
    }


def _artifact_ref(
    root: Path, logical_name: str, relative_path: str,
) -> list[object]:
    path = _path_within(root, relative_path, final_file=True)
    if not path.is_file():
        raise ValueError(f"required artifact is absent: {relative_path}")
    content = path.read_bytes()
    return [logical_name, relative_path, _sha256_bytes(content), len(content)]


def _short_ref(root: Path, relative_path: str) -> list[object]:
    path = _path_within(root, relative_path, final_file=True)
    if not path.is_file():
        raise ValueError(f"required artifact is absent: {relative_path}")
    content = path.read_bytes()
    return [relative_path, _sha256_bytes(content), len(content)]


def _method_gamma(config: Family3V2PilotConfig, method_id: str) -> float:
    for method in config.methods:
        if method.get("id") == method_id:
            value = method.get("gamma")
            if type(value) not in (int, float) or type(value) is bool:
                raise ValueError("trained method gamma is malformed")
            return float(value)
    raise ValueError("trained method is absent from the frozen config")


def _model_mapping(model_spec: object) -> dict[str, object]:
    values = {
        "state_dim": getattr(model_spec, "state_dim", None),
        "candidate_dim": getattr(model_spec, "candidate_dim", None),
        "max_candidates": getattr(model_spec, "max_candidates", None),
    }
    if any(type(value) is not int or value < 1 for value in values.values()):
        raise ValueError("DDQN model specification is malformed")
    return values


def _hyperparameter_mapping(hyperparameters: object) -> dict[str, object]:
    values = {
        "gamma": _float_hex(getattr(hyperparameters, "gamma", None), "gamma"),
        "learning_rate": _float_hex(
            getattr(hyperparameters, "learning_rate", None), "learning_rate"
        ),
        "batch_size": getattr(hyperparameters, "batch_size", None),
        "replay_capacity": getattr(hyperparameters, "replay_capacity", None),
        "warmup_transitions": getattr(
            hyperparameters, "warmup_transitions", None
        ),
        "optimize_every": getattr(hyperparameters, "optimize_every", None),
        "target_update_every": getattr(
            hyperparameters, "target_update_every", None
        ),
        "gradient_clip": _float_hex(
            getattr(hyperparameters, "gradient_clip", None), "gradient_clip"
        ),
    }
    for name in (
        "batch_size", "replay_capacity", "warmup_transitions",
        "optimize_every", "target_update_every",
    ):
        _exact_int(values[name], name, minimum=1)
    return values


def _expected_ddqn_hyperparameters(
    config: Family3V2PilotConfig, method_id: str,
) -> DDQNHyperparameters:
    frozen = config.hyperparameters["ddqn"]
    if frozen["target_update_unit"] != "optimizer_steps":
        raise ValueError("DDQN target-update unit is not optimizer steps")
    return DDQNHyperparameters(
        gamma=_method_gamma(config, method_id),
        learning_rate=float(frozen["learning_rate"]),
        batch_size=int(frozen["batch_size"]),
        replay_capacity=int(frozen["replay_capacity"]),
        warmup_transitions=int(frozen["warmup_transitions"]),
        optimize_every=int(frozen["optimize_every"]),
        target_update_every=int(frozen["target_update_interval"]),
        gradient_clip=float(frozen["gradient_clip"]),
    )


def _plain_state_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("state mapping is malformed")
    result: dict[str, object] = {}
    for key, item in value.items():
        if type(key) not in (str, int):
            raise ValueError("state mapping key type is unsupported")
        if isinstance(item, torch.Tensor):
            tensor = item.detach().to(device="cpu").contiguous().clone()
            _normalize(tensor)
            result[key] = tensor
        elif isinstance(item, Mapping):
            result[key] = _plain_state_mapping(item)
        elif type(item) is list:
            result[key] = [
                _plain_state_value(child) for child in item
            ]
        elif type(item) is tuple:
            result[key] = tuple(
                _plain_state_value(child) for child in item
            )
        else:
            result[key] = _plain_state_value(item)
    return result


def _plain_state_value(value: object) -> object:
    if isinstance(value, torch.Tensor):
        tensor = value.detach().to(device="cpu").contiguous().clone()
        _normalize(tensor)
        return tensor
    if isinstance(value, Mapping):
        return _plain_state_mapping(value)
    if type(value) is list:
        return [_plain_state_value(item) for item in value]
    if type(value) is tuple:
        return tuple(_plain_state_value(item) for item in value)
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("checkpoint contains a weights-only-unsafe value")


def _transition_mapping(transition: object) -> dict[str, object]:
    expected = tuple(field.name for field in fields(_ReplayTransition))
    if type(transition) is not _ReplayTransition:
        raise ValueError("replay transition has the wrong exact type")
    mapping = {
        name: _plain_state_value(getattr(transition, name))
        for name in expected
    }
    if tuple(mapping) != expected:
        raise AssertionError("replay field order drift")
    return mapping


def _transition_from_mapping(value: object) -> _ReplayTransition:
    names = tuple(field.name for field in fields(_ReplayTransition))
    if type(value) is not dict or tuple(value) != names:
        raise ValueError("archived replay transition is malformed")
    tensors = (
        "state", "candidates", "mask", "next_state",
        "next_candidates", "next_mask",
    )
    if any(type(value[name]) is not torch.Tensor for name in tensors):
        raise ValueError("archived replay transition tensor is malformed")
    transition = _ReplayTransition(**{name: value[name] for name in names})
    _normalize(_transition_mapping(transition))
    return transition


def _initial_hash_mapping(
    method_id: str, initial_state_hashes: object,
) -> list[list[object]]:
    expected_names = (
        ("tabular_empty_table",)
        if method_id.startswith("tabular_")
        else ("ddqn_online", "ddqn_target", "ddqn_optimizer")
    )
    if (
        type(initial_state_hashes) is not tuple
        or tuple(
            pair[0]
            for pair in initial_state_hashes
            if type(pair) is tuple and len(pair) == 2
        ) != expected_names
        or len(initial_state_hashes) != len(expected_names)
    ):
        raise ValueError("initial-state hash names are invalid")
    encoded: list[list[object]] = []
    for pair in initial_state_hashes:
        if (
            type(pair) is not tuple or len(pair) != 2
            or type(pair[0]) is not str
        ):
            raise ValueError("initial-state hash pair is malformed")
        encoded.append([pair[0], _digest(pair[1], pair[0])])
    return encoded


def _training_metadata(
    *,
    transition_count: int,
    per_graph_transition_counts: tuple[tuple[str, int], ...],
    environment_steps: int,
    optimizer_steps: int,
    learner_update_count: int,
    last_loss: float | None,
) -> dict[str, object]:
    return {
        "transition_count": transition_count,
        "per_graph_transition_counts": [
            [graph_id, count]
            for graph_id, count in per_graph_transition_counts
        ],
        "environment_steps": environment_steps,
        "optimizer_steps": optimizer_steps,
        "learner_update_count": learner_update_count,
        "last_loss_hex": (
            None if last_loss is None else _float_hex(last_loss, "last_loss")
        ),
        "rng_derivation_schema": "family3_v2_learner_rng_v0",
    }


def _semantic_state_mapping(
    *,
    boundary_sha256: str,
    method_id: str,
    training_seed: int,
    attempt_number: int,
    checkpoint_kind: str,
    training_metadata: dict[str, object],
    algorithm_state: dict[str, object],
    initial_state_hashes: list[list[object]],
) -> dict[str, object]:
    return {
        "schema_version": "family3_v2_checkpoint_semantic_state_v0",
        "boundary_sha256": boundary_sha256,
        "method_id": method_id,
        "training_seed": training_seed,
        "attempt_number": attempt_number,
        "checkpoint_kind": checkpoint_kind,
        "training_metadata": training_metadata,
        "algorithm_state": algorithm_state,
        "initial_state_hashes": initial_state_hashes,
    }


def _q_rows(learner: TabularQLearner) -> list[list[object]]:
    if type(learner) is not TabularQLearner:
        raise ValueError("tabular checkpoint has the wrong learner type")
    rows: list[list[object]] = []
    for key, value in learner.q_values.items():
        if (
            type(key) is not tuple or len(key) != 2
            or any(type(item) is not str or not item for item in key)
        ):
            raise ValueError("tabular Q key is malformed")
        rows.append([key[0], key[1], _float_hex(value, "q_value")])
    rows.sort(key=lambda row: (row[0], row[1]))
    if len({(row[0], row[1]) for row in rows}) != len(rows):
        raise ValueError("tabular Q rows contain a duplicate")
    return rows


def _evaluation_fingerprint_mapping(
    *,
    boundary: PilotBoundary,
    reference_values: tuple[str, int, int, str],
    learner: CheckpointLearner,
    training_metadata: dict[str, object],
    replay_summary: dict[str, object] | None,
    initial_state_hashes: list[list[object]],
) -> dict[str, object]:
    method_id, training_seed, attempt_number, checkpoint_kind = reference_values
    if checkpoint_kind == "tabular_q":
        if type(learner) is not TabularQLearner:
            raise ValueError("evaluation learner kind does not match checkpoint")
        rows = _q_rows(learner)
        return {
            "schema_version": "family3_v2_evaluation_fingerprint_v0",
            "boundary_sha256": _sha256_bytes(
                _canonical(_boundary_mapping(boundary))
            ),
            "method_id": method_id,
            "training_seed": training_seed,
            "attempt_number": attempt_number,
            "checkpoint_kind": checkpoint_kind,
            "live_model_spec": None,
            "live_hyperparameters": {
                "alpha_hex": _float_hex(learner.alpha, "alpha"),
                "gamma_hex": _float_hex(learner.gamma, "gamma"),
            },
            "live_rng_deriver": None,
            "model_or_table_state_sha256": _sha256_bytes(_canonical(rows)),
            "target_state_sha256": None,
            "optimizer_state_sha256": None,
            "live_training_state": None,
            "archived_training_metadata": training_metadata,
            "archived_replay_state": None,
            "live_replay_state": None,
            "initial_state_hashes": initial_state_hashes,
        }
    if type(learner) is not Family3V2MaskedDoubleDQN:
        raise ValueError("evaluation learner kind does not match checkpoint")
    buffer = getattr(learner, "_buffer", None)
    if type(buffer) is not _ReplayBuffer:
        raise ValueError("evaluation replay buffer layout drift")
    live_items = tuple(_transition_mapping(item) for item in buffer._items)
    live_replay = {
        "capacity": buffer._capacity,
        "size": len(buffer._items),
        "cursor": buffer._cursor,
        "content_sha256": _semantic_digest(live_items),
        "rng_state_sha256": _semantic_digest(buffer._rng.getstate()),
    }
    return {
        "schema_version": "family3_v2_evaluation_fingerprint_v0",
        "boundary_sha256": _sha256_bytes(
            _canonical(_boundary_mapping(boundary))
        ),
        "method_id": method_id,
        "training_seed": training_seed,
        "attempt_number": attempt_number,
        "checkpoint_kind": checkpoint_kind,
        "live_model_spec": _model_mapping(learner.model_spec),
        "live_hyperparameters": _hyperparameter_mapping(
            learner.hyperparameters
        ),
        "live_rng_deriver": {
            "experiment_id": learner.rng_deriver.experiment_id,
            "learner_family": learner.rng_deriver.learner_family,
            "base_seed": learner.rng_deriver.base_seed,
        },
        "model_or_table_state_sha256": _semantic_digest(
            _plain_state_mapping(learner.online_network.state_dict())
        ),
        "target_state_sha256": _semantic_digest(
            _plain_state_mapping(learner.target_network.state_dict())
        ),
        "optimizer_state_sha256": _semantic_digest(
            _plain_state_mapping(learner._optimizer.state_dict())
        ),
        "live_training_state": {
            "environment_steps": learner.environment_steps,
            "optimizer_steps": learner.optimizer_steps,
            "last_loss_hex": (
                None if learner.last_loss is None
                else _float_hex(learner.last_loss, "last_loss")
            ),
        },
        "archived_training_metadata": training_metadata,
        "archived_replay_state": replay_summary,
        "live_replay_state": live_replay,
        "initial_state_hashes": initial_state_hashes,
    }


class Family3V2PilotArtifactStore:
    """Single-writer persistence boundary for one immutable pilot root."""

    def __init__(
        self,
        root: Path,
        boundary: PilotBoundary,
        config: Family3V2PilotConfig,
        guard: _FaultGuard | None,
        directory_fsync: bool,
    ) -> None:
        self._root = root
        self._boundary = boundary
        self._boundary_sha256 = _sha256_bytes(
            _canonical(_boundary_mapping(boundary))
        )
        self._config = config
        self._guard = guard
        self._directory_fsync = directory_fsync
        self._state_cache: tuple[dict[str, object], ...] | None = None
        self._row_cache: dict[
            str,
            tuple[
                tuple[dict[str, object], ...],
                tuple[EvaluationEpisodeRow, ...],
                tuple[list[object], ...],
            ],
        ] = {}
        self._row_seen: dict[
            str, dict[EvaluationCoordinate, EvaluationEpisodeRow]
        ] = {}

    def _require_mutation(self) -> None:
        if self._guard is not None and not self._guard.active:
            raise RuntimeError("test-only store cannot mutate outside its guard")
        if (self._root / "final_verdict.json").exists():
            raise ValueError("the pilot root is terminal")

    def _fault(self, seam: str, relative: str) -> None:
        guard = self._guard
        if guard is not None and guard.active:
            guard.hook(seam, relative)

    def _fsync_directory(self, directory: Path) -> None:
        if not self._directory_fsync:
            return
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _publish_immutable(self, relative: str, content: bytes) -> Path:
        destination = _make_parent(self._root, relative)
        if destination.exists():
            if destination.read_bytes() != content:
                raise ValueError("immutable artifact already exists with different bytes")
            return destination
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".task5-", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self._fault(
                "after_temp_file_fsync_before_immutable_link", relative
            )
            os.link(temporary, destination)
            self._fault(
                "after_immutable_link_before_directory_fsync", relative
            )
            if destination.read_bytes() != content:
                raise ValueError("immutable artifact readback mismatch")
            self._fsync_directory(destination.parent)
            return destination
        finally:
            if temporary.exists():
                temporary.unlink()

    def _replace_snapshot(self, relative: str, content: bytes) -> Path:
        destination = _make_parent(self._root, relative)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".task5-", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self._fault(
                "after_temp_file_fsync_before_snapshot_replace", relative
            )
            os.replace(temporary, destination)
            self._fault(
                "after_snapshot_replace_before_directory_fsync", relative
            )
            if destination.read_bytes() != content:
                raise ValueError("snapshot readback mismatch")
            self._fsync_directory(destination.parent)
            return destination
        finally:
            if temporary.exists():
                temporary.unlink()

    def _append_jsonl(self, relative: str, line: bytes) -> None:
        if not line.endswith(b"\n") or line.count(b"\n") != 1:
            raise ValueError("JSONL append must be exactly one LF line")
        destination = _make_parent(self._root, relative)
        if not destination.exists():
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".task5-", dir=destination.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(line)
                    handle.flush()
                    self._fault(
                        "after_jsonl_write_before_file_fsync", relative
                    )
                    os.fsync(handle.fileno())
                    self._fault(
                        "after_jsonl_file_fsync_before_return", relative
                    )
                self._fault(
                    "after_temp_file_fsync_before_immutable_link", relative
                )
                os.link(temporary, destination)
                self._fault(
                    "after_immutable_link_before_directory_fsync", relative
                )
                self._fsync_directory(destination.parent)
            finally:
                if temporary.exists():
                    temporary.unlink()
            return
        with destination.open("ab") as handle:
            handle.write(line)
            handle.flush()
            self._fault("after_jsonl_write_before_file_fsync", relative)
            os.fsync(handle.fileno())
            self._fault("after_jsonl_file_fsync_before_return", relative)

    def _records(
        self, relative: str, schema: str,
    ) -> tuple[dict[str, object], ...]:
        path = _path_within(self._root, relative, final_file=True)
        if not path.exists():
            return ()
        content = path.read_bytes()
        if not content or not content.endswith(b"\n") or b"\r" in content:
            raise ValueError("JSONL artifact has a corrupt tail")
        records: list[dict[str, object]] = []
        previous = _ZERO_HASH
        keys = (
            "schema_version", "sequence", "boundary_sha256",
            "previous_record_sha256", "payload_sha256", "payload",
            "record_sha256",
        )
        for sequence, raw_line in enumerate(content.splitlines()):
            if not raw_line:
                raise ValueError("JSONL contains a blank line")
            try:
                value = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("JSONL contains malformed JSON") from error
            if type(value) is not dict or tuple(value) != keys:
                raise ValueError("chained record fields are malformed")
            if (
                value["schema_version"] != schema
                or value["sequence"] != sequence
                or value["boundary_sha256"] != self._boundary_sha256
                or value["previous_record_sha256"] != previous
                or value["payload_sha256"]
                != _sha256_bytes(_canonical(value["payload"]))
            ):
                raise ValueError("chained record sequence or hash is invalid")
            prefix = {name: value[name] for name in keys[:-1]}
            if value["record_sha256"] != _sha256_bytes(_canonical(prefix)):
                raise ValueError("chained record hash is invalid")
            if _canonical(value) != raw_line:
                raise ValueError("chained record is noncanonical")
            previous = value["record_sha256"]
            records.append(value)
        return tuple(records)

    def _chain_record(
        self, schema: str, sequence: int, previous: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        prefix = {
            "schema_version": schema,
            "sequence": sequence,
            "boundary_sha256": self._boundary_sha256,
            "previous_record_sha256": previous,
            "payload_sha256": _sha256_bytes(_canonical(payload)),
            "payload": payload,
        }
        return {
            **prefix,
            "record_sha256": _sha256_bytes(_canonical(prefix)),
        }

    def _state_records(self) -> tuple[dict[str, object], ...]:
        if self._state_cache is None:
            self._state_cache = self._records(
                "state/ledger.jsonl", "family3_v2_pilot_state_record_v0"
            )
        return self._state_cache

    def _state(self) -> str:
        records = self._state_records()
        return "ABSENT" if not records else str(records[-1]["payload"]["to_state"])

    def _state_head(self) -> str:
        records = self._state_records()
        return _ZERO_HASH if not records else str(records[-1]["record_sha256"])

    def _transaction(
        self, kind: str, *, coordinate: object, command: tuple[str, ...],
        input_refs: list[object], input_values: list[object],
        prior_head: str | None = None,
    ) -> str:
        checked_command = self._command(command)
        return _sha256_bytes(_canonical({
            "schema_version": "family3_v2_store_transaction_v0",
            "transaction_kind": kind,
            "boundary_sha256": self._boundary_sha256,
            "prior_state_ledger_head_sha256": (
                self._state_head() if prior_head is None else prior_head
            ),
            "coordinate": coordinate,
            "command": list(checked_command),
            "input_refs": input_refs,
            "input_values": input_values,
        }))

    @staticmethod
    def _command(command: object) -> tuple[str, ...]:
        if (
            type(command) is not tuple or not command
            or any(type(item) is not str or not item for item in command)
        ):
            raise ValueError("command must be a nonempty exact string tuple")
        return command

    def _append_state(
        self, *, event_type: str, transaction_sha256: str,
        from_state: str | None, to_state: str, command: tuple[str, ...],
        completed_boundary: list[object], artifacts: list[object],
        output_paths: list[str], ledger_heads: list[object],
        active_attempt: list[object] | None, next_action: str,
    ) -> None:
        records = self._state_records()
        if (records and records[-1]["payload"]["to_state"] != from_state) or (
            not records and from_state is not None
        ):
            raise ValueError("state transition source does not match")
        generation = len(records)
        payload = {
            "generation": generation,
            "event_type": _exact_str(event_type, "event_type"),
            "transaction_sha256": _digest(
                transaction_sha256, "transaction_sha256"
            ),
            "from_state": from_state,
            "to_state": _exact_str(to_state, "to_state"),
            "active_command": list(self._command(command)),
            "completed_boundary": completed_boundary,
            "artifacts": artifacts,
            "output_paths": output_paths + [
                "state/ledger.jsonl", "continuation_checkpoint.json",
                "progress.json",
            ],
            "ledger_heads": ledger_heads,
            "active_attempt": active_attempt,
            "status": to_state,
            "next_action": _exact_str(next_action, "next_action"),
        }
        previous = (
            _ZERO_HASH if not records else str(records[-1]["record_sha256"])
        )
        record = self._chain_record(
            "family3_v2_pilot_state_record_v0",
            generation, previous, payload,
        )
        self._append_jsonl(
            "state/ledger.jsonl", _canonical(record) + b"\n"
        )
        self._state_cache = records + (record,)
        self._write_snapshots(record)

    def _write_snapshots(self, record: dict[str, object]) -> None:
        payload = record["payload"]
        snapshot = {
            "schema_version": "family3_v2_pilot_state_snapshot_v0",
            "generation": payload["generation"],
            "boundary_sha256": self._boundary_sha256,
            "state_ledger_head_sha256": record["record_sha256"],
            "state": payload["to_state"],
            "active_command": payload["active_command"],
            "completed_boundary": payload["completed_boundary"],
            "artifacts": payload["artifacts"],
            "output_paths": payload["output_paths"],
            "ledger_heads": payload["ledger_heads"],
            "active_attempt": payload["active_attempt"],
            "status": payload["status"],
            "next_action": payload["next_action"],
        }
        content = _canonical(snapshot)
        self._replace_snapshot("continuation_checkpoint.json", content)
        self._replace_snapshot("progress.json", content)

    def _reconcile_snapshots(self) -> None:
        records = self._state_records()
        if not records:
            return
        expected_record = records[-1]
        expected_payload = expected_record["payload"]
        expected = _canonical({
            "schema_version": "family3_v2_pilot_state_snapshot_v0",
            "generation": expected_payload["generation"],
            "boundary_sha256": self._boundary_sha256,
            "state_ledger_head_sha256": expected_record["record_sha256"],
            "state": expected_payload["to_state"],
            "active_command": expected_payload["active_command"],
            "completed_boundary": expected_payload["completed_boundary"],
            "artifacts": expected_payload["artifacts"],
            "output_paths": expected_payload["output_paths"],
            "ledger_heads": expected_payload["ledger_heads"],
            "active_attempt": expected_payload["active_attempt"],
            "status": expected_payload["status"],
            "next_action": expected_payload["next_action"],
        })
        paths = (
            self._root / "continuation_checkpoint.json",
            self._root / "progress.json",
        )
        if all(path.exists() and path.read_bytes() == expected for path in paths):
            return
        self._write_snapshots(expected_record)

    @staticmethod
    def _probe_capabilities(root: Path) -> bool:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".task5-capability-", dir=root
        )
        temporary = Path(temporary_name)
        linked = root / f"{temporary.name}.linked"
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"family3-v2-pilot-hard-link-probe")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, linked)
            except OSError as error:
                raise RuntimeError(
                    "atomic same-directory hard-link publication is unavailable"
                ) from error
            if linked.read_bytes() != b"family3-v2-pilot-hard-link-probe":
                raise RuntimeError("hard-link capability readback failed")
            directory_fsync = True
            try:
                directory_descriptor = os.open(root, os.O_RDONLY)
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
            except OSError:
                directory_fsync = False
            return directory_fsync
        finally:
            if linked.exists():
                linked.unlink()
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _validate_source_manifest(
        source_manifest_bytes: bytes, guard: _FaultGuard | None,
    ) -> None:
        try:
            manifest = json.loads(source_manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("source manifest must be strict UTF-8 JSON") from error
        if (
            type(manifest) is not dict
            or tuple(manifest) != ("schema_version", "entries")
            or manifest["schema_version"]
            != "family3_v2_pilot_source_manifest_v0"
            or type(manifest["entries"]) is not list
            or _canonical(manifest) != source_manifest_bytes
        ):
            raise ValueError("source manifest schema is invalid")
        try:
            baseline = json.loads(_BASELINE_PATH.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("frozen dependency manifest is malformed") from error
        expected = [
            [
                entry["relative_path"], entry["sha256"], entry["byte_size"],
            ]
            for entry in (
                baseline["certified_source_files"]
                + baseline["additional_learner_dependencies"]
            )
        ]
        base_paths = (
            "src/pa_rl/family3_v2_learning.py",
            "src/pa_rl/family3_v2_pilot_criteria.py",
            "src/pa_rl/family3_v2_pilot_checkpoints.py",
        )
        expected.extend(
            _raw_ref(_PROJECT_ROOT / relative, _PROJECT_ROOT, relative)[1:]
            for relative in base_paths
        )
        runner_relative = "src/pa_rl/family3_v2_learner_pilot.py"
        if guard is None:
            runner = _PROJECT_ROOT / runner_relative
            if not runner.is_file():
                raise ValueError(
                    "production roots require the resealed Task 6 source manifest"
                )
            expected.append(
                _raw_ref(runner, _PROJECT_ROOT, runner_relative)[1:]
            )
        if manifest["entries"] != expected:
            raise ValueError("source manifest differs from the live frozen inputs")
        paths: set[str] = set()
        for entry in manifest["entries"]:
            if (
                type(entry) is not list or len(entry) != 3
                or type(entry[0]) is not str
                or type(entry[1]) is not str
                or type(entry[2]) is not int
                or entry[0] in paths
            ):
                raise ValueError("source-manifest entry is malformed")
            paths.add(entry[0])
            candidate = _PROJECT_ROOT / _canonical_relative(
                entry[0], "source_relative_path"
            )
            content = candidate.read_bytes()
            if (
                len(content) != entry[2]
                or _sha256_bytes(content) != entry[1]
            ):
                raise ValueError("source-manifest entry does not verify")

    @classmethod
    def create_or_validate(
        cls,
        output_root: PathLike,
        *,
        boundary: PilotBoundary,
        config_bytes: bytes,
        source_manifest_bytes: bytes,
        certified_dependency_manifest_bytes: bytes,
    ) -> "Family3V2PilotArtifactStore":
        if type(boundary) is not PilotBoundary:
            raise ValueError("boundary must have the exact PilotBoundary type")
        if any(
            type(value) is not bytes
            for value in (
                config_bytes, source_manifest_bytes,
                certified_dependency_manifest_bytes,
            )
        ):
            raise ValueError("frozen inputs must be exact bytes")
        supplied = Path(output_root)
        if not supplied.is_absolute() or supplied != supplied.resolve():
            raise ValueError("output root must be an exact resolved path")
        if supplied.exists():
            _reject_symlink_or_reparse(supplied)
            if not supplied.is_dir():
                raise ValueError("output root must be a directory")
        else:
            supplied.mkdir(parents=False)
            _reject_symlink_or_reparse(supplied)
        guard = _FAULT_GUARD.get()
        if guard is not None and supplied != guard.root:
            raise ValueError("fault guard root does not match output root")
        if (
            supplied.name in (_FORMAL_ROOT_NAME, _SMOKE_ROOT_NAME)
            and guard is not None
        ):
            raise ValueError("test guard cannot target a named evidence root")
        if not _runtime_matches(boundary):
            raise ValueError("boundary runtime does not match this process")
        actual_config = _CONFIG_PATH.read_bytes()
        actual_baseline = _BASELINE_PATH.read_bytes()
        if (
            config_bytes != actual_config
            or len(config_bytes) != boundary.config_byte_size
            or _sha256_bytes(config_bytes) != boundary.config_sha256
            or certified_dependency_manifest_bytes != actual_baseline
            or len(certified_dependency_manifest_bytes)
            != boundary.certified_dependency_manifest_byte_size
            or _sha256_bytes(certified_dependency_manifest_bytes)
            != boundary.certified_dependency_manifest_sha256
            or len(source_manifest_bytes)
            != boundary.source_manifest_byte_size
            or _sha256_bytes(source_manifest_bytes)
            != boundary.source_manifest_sha256
        ):
            raise ValueError("supplied frozen bytes do not match the boundary")
        config = load_family3_v2_pilot_config(_CONFIG_PATH)
        verification = verify_certified_dependency_baseline(_BASELINE_PATH)
        if not verification.passed:
            raise ValueError("certified dependency verification failed")
        cls._validate_source_manifest(source_manifest_bytes, guard)

        durability_path = supplied / "durability.json"
        if durability_path.exists():
            durability = _read_exact_json(
                durability_path,
                (
                    "schema_version", "file_fsync", "snapshot_publish",
                    "immutable_publish", "directory_fsync",
                    "platform_system", "python_version",
                ),
            )
            directory_fsync = (
                durability["directory_fsync"] == "supported_and_used"
            )
            if durability != {
                "schema_version": "family3_v2_pilot_durability_v0",
                "file_fsync": "required",
                "snapshot_publish": "same_directory_os_replace",
                "immutable_publish": "same_directory_hard_link_exclusive",
                "directory_fsync": (
                    "supported_and_used"
                    if directory_fsync else "unavailable_recorded"
                ),
                "platform_system": platform.system(),
                "python_version": platform.python_version(),
            }:
                raise ValueError("durability record does not match this runtime")
        else:
            directory_fsync = cls._probe_capabilities(supplied)
        store = cls(supplied, boundary, config, guard, directory_fsync)
        durability_bytes = _canonical({
            "schema_version": "family3_v2_pilot_durability_v0",
            "file_fsync": "required",
            "snapshot_publish": "same_directory_os_replace",
            "immutable_publish": "same_directory_hard_link_exclusive",
            "directory_fsync": (
                "supported_and_used"
                if directory_fsync else "unavailable_recorded"
            ),
            "platform_system": platform.system(),
            "python_version": platform.python_version(),
        })
        fixed = (
            ("config.json", config_bytes),
            ("source_manifest.json", source_manifest_bytes),
            (
                "certified_dependency_manifest.json",
                certified_dependency_manifest_bytes,
            ),
            ("boundary.json", _canonical(_boundary_mapping(boundary))),
            ("durability.json", durability_bytes),
        )
        for relative, content in fixed:
            store._publish_immutable(relative, content)
        refs = [
            _artifact_ref(supplied, logical, relative)
            for logical, relative in (
                ("config", "config.json"),
                ("source_manifest", "source_manifest.json"),
                (
                    "certified_dependency_manifest",
                    "certified_dependency_manifest.json",
                ),
                ("boundary", "boundary.json"),
                ("durability", "durability.json"),
            )
        ]
        transaction = store._transaction(
            "BOUNDARY_FREEZE", coordinate=None,
            command=("artifact-store:create-or-validate",),
            input_refs=refs, input_values=[], prior_head=_ZERO_HASH,
        )
        records = store._state_records()
        if not records:
            store._append_state(
                event_type="BOUNDARY_FREEZE",
                transaction_sha256=transaction,
                from_state=None, to_state="BOUNDARY_FROZEN",
                command=("artifact-store:create-or-validate",),
                completed_boundary=["BOUNDARY_FROZEN"],
                artifacts=refs,
                output_paths=[
                    "config.json", "source_manifest.json",
                    "certified_dependency_manifest.json", "boundary.json",
                    "durability.json",
                ],
                ledger_heads=[], active_attempt=None,
                next_action="BEGIN_NEXT_TRAINING_ATTEMPT",
            )
        else:
            first = records[0]["payload"]
            if (
                first["event_type"] != "BOUNDARY_FREEZE"
                or first["transaction_sha256"] != transaction
                or first["from_state"] is not None
                or first["to_state"] != "BOUNDARY_FROZEN"
            ):
                raise ValueError("existing root boundary event is invalid")
            store._reconcile_snapshots()
        return store

    def _canonical_arms(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (method_id, seed)
            for method_id in self._boundary.trained_method_ids
            for seed in self._boundary.training_seeds
        )

    @staticmethod
    def _final_ref_relative(method_id: str, seed: int) -> str:
        return f"training/{method_id}/{seed}/final_checkpoint.json"

    def _load_ref_file(self, method_id: str, seed: int) -> FinalCheckpointRef:
        relative = self._final_ref_relative(method_id, seed)
        path = _path_within(self._root, relative, final_file=True)
        mapping = _read_exact_json(
            path, tuple(field.name for field in fields(FinalCheckpointRef))
        )
        reference = _ref_from_mapping(mapping)
        if reference.method_id != method_id or reference.training_seed != seed:
            raise ValueError("final checkpoint ref coordinate mismatch")
        return reference

    def _completed_refs(self) -> tuple[FinalCheckpointRef, ...]:
        refs: list[FinalCheckpointRef] = []
        missing_seen = False
        for method_id, seed in self._canonical_arms():
            path = self._root / self._final_ref_relative(method_id, seed)
            if path.exists():
                if missing_seen:
                    raise ValueError("completed checkpoint arms are not a prefix")
                refs.append(self._load_ref_file(method_id, seed))
            else:
                missing_seen = True
        return tuple(refs)

    @staticmethod
    def _attempt_event_relative(
        method_id: str, seed: int, attempt_number: int,
    ) -> str:
        return (
            f"training/{method_id}/{seed}/attempts/"
            f"{attempt_number:04d}/events.jsonl"
        )

    def _append_attempt_event(
        self, method_id: str, seed: int, attempt_number: int,
        *, event_type: str, command: tuple[str, ...],
        artifact_refs: list[object], message: str | None,
    ) -> str:
        relative = self._attempt_event_relative(
            method_id, seed, attempt_number
        )
        records = self._records(
            relative, "family3_v2_training_attempt_event_v0"
        )
        payload = {
            "event_type": event_type,
            "method_id": method_id,
            "training_seed": seed,
            "attempt_number": attempt_number,
            "command": list(self._command(command)),
            "artifact_refs": artifact_refs,
            "message": message,
        }
        previous = (
            _ZERO_HASH if not records else str(records[-1]["record_sha256"])
        )
        record = self._chain_record(
            "family3_v2_training_attempt_event_v0",
            len(records), previous, payload,
        )
        self._append_jsonl(relative, _canonical(record) + b"\n")
        return str(record["record_sha256"])

    def _last_completed_boundary(self) -> list[object]:
        records = self._state_records()
        if not records:
            raise ValueError("state ledger is absent")
        value = records[-1]["payload"]["completed_boundary"]
        if type(value) is not list:
            raise ValueError("state completed boundary is malformed")
        return value

    def begin_training_attempt(
        self,
        method_id: str,
        training_seed: int,
        *,
        command: tuple[str, ...],
        manual_restart_of_attempt: int | None = None,
    ) -> int:
        self._require_mutation()
        checked_command = self._command(command)
        if (
            method_id not in self._boundary.trained_method_ids
            or type(training_seed) is not int
            or training_seed not in self._boundary.training_seeds
        ):
            raise ValueError("training arm is outside the boundary")
        completed = self._completed_refs()
        arms = self._canonical_arms()
        if len(completed) >= len(arms) or arms[len(completed)] != (
            method_id, training_seed
        ):
            raise ValueError("only the first incomplete canonical arm may start")
        state = self._state()
        if state not in (
            "BOUNDARY_FROZEN", "TRAINING_INTERRUPTED", "ARM_COMMITTED",
        ):
            raise ValueError("state does not allow a training attempt")
        attempt_number = 1
        while (
            self._root
            / f"training/{method_id}/{training_seed}/attempts/"
            f"{attempt_number:04d}/attempt.json"
        ).exists():
            attempt_number += 1
        if attempt_number > 9_999:
            raise ValueError("attempt count exceeds fixed path width")
        if attempt_number == 1:
            if manual_restart_of_attempt is not None:
                raise ValueError("first attempt cannot name a restart")
        else:
            if (
                type(manual_restart_of_attempt) is not int
                or manual_restart_of_attempt != attempt_number - 1
            ):
                raise ValueError("manual restart must name the prior attempt")
            failure_path = self._root / (
                f"training/{method_id}/{training_seed}/attempts/"
                f"{attempt_number - 1:04d}/failure.json"
            )
            failure = _read_exact_json(
                failure_path,
                (
                    "schema_version", "boundary_sha256", "failure_number",
                    "failure_kind", "failure_code", "message", "method_id",
                    "training_seed", "attempt_number", "command",
                    "prior_state_ledger_head_sha256", "transaction_sha256",
                    "next_action",
                ),
            )
            if failure["failure_kind"] != "RESTARTABLE_ARM_FAILURE":
                raise ValueError("prior attempt is not restartable")
        prior = self._state_head()
        coordinate = [method_id, training_seed, attempt_number]
        transaction = self._transaction(
            "ATTEMPT_BEGIN", coordinate=coordinate,
            command=checked_command, input_refs=[],
            input_values=[
                ["manual_restart_of_attempt", manual_restart_of_attempt]
            ], prior_head=prior,
        )
        relative = (
            f"training/{method_id}/{training_seed}/attempts/"
            f"{attempt_number:04d}/attempt.json"
        )
        attempt = {
            "schema_version": "family3_v2_training_attempt_v0",
            "boundary_sha256": self._boundary_sha256,
            "method_id": method_id,
            "training_seed": training_seed,
            "attempt_number": attempt_number,
            "manual_restart_of_attempt": manual_restart_of_attempt,
            "command": list(checked_command),
            "start_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
            "start_transition": 0,
            "creation_status": "ACTIVE",
        }
        self._publish_immutable(relative, _canonical(attempt))
        attempt_ref = _short_ref(self._root, relative)
        event_head = self._append_attempt_event(
            method_id, training_seed, attempt_number,
            event_type="ATTEMPT_STARTED", command=checked_command,
            artifact_refs=[attempt_ref], message=None,
        )
        self._append_state(
            event_type="ATTEMPT_BEGIN", transaction_sha256=transaction,
            from_state=state, to_state="TRAINING_ATTEMPT_ACTIVE",
            command=checked_command,
            completed_boundary=self._last_completed_boundary(),
            artifacts=[_artifact_ref(self._root, "attempt", relative)],
            output_paths=[
                relative,
                self._attempt_event_relative(
                    method_id, training_seed, attempt_number
                ),
            ],
            ledger_heads=[[
                (
                    f"attempt_events/{method_id}/{training_seed}/"
                    f"{attempt_number:04d}"
                ),
                event_head,
            ]],
            active_attempt=coordinate,
            next_action="EXECUTE_ACTIVE_TRAINING_ATTEMPT_FROM_ZERO",
        )
        return attempt_number

    def _validate_training_counts(
        self,
        transition_count: int,
        per_graph_transition_counts: tuple[tuple[str, int], ...],
    ) -> None:
        if (
            type(transition_count) is not int
            or transition_count != self._boundary.transitions_per_arm
            or type(per_graph_transition_counts) is not tuple
            or per_graph_transition_counts
            != tuple(
                (graph_id, self._boundary.transitions_per_train_graph)
                for graph_id in self._boundary.train_graph_ids
            )
            or sum(count for _, count in per_graph_transition_counts)
            != transition_count
        ):
            raise ValueError("final checkpoint transition counts are invalid")

    def _encode_tabular_checkpoint(
        self, method_id: str, training_seed: int, attempt_number: int,
        learner: CheckpointLearner, transition_count: int,
        per_graph_transition_counts: tuple[tuple[str, int], ...],
        learner_update_count: int, initial: list[list[object]],
    ) -> tuple[
        bytes, str, dict[str, object], dict[str, object],
        list[list[object]], str, str,
    ]:
        if type(learner) is not TabularQLearner:
            raise ValueError("tabular arm requires exact TabularQLearner")
        alpha = float(self._config.hyperparameters["tabular"]["alpha"])
        gamma = _method_gamma(self._config, method_id)
        if learner.alpha != alpha or learner.gamma != gamma:
            raise ValueError("tabular learner hyperparameters mismatch")
        if learner_update_count != transition_count:
            raise ValueError("tabular update count must equal transition count")
        rows = _q_rows(learner)
        training = _training_metadata(
            transition_count=transition_count,
            per_graph_transition_counts=per_graph_transition_counts,
            environment_steps=transition_count, optimizer_steps=0,
            learner_update_count=learner_update_count, last_loss=None,
        )
        archive = {
            "schema_version": "family3_v2_tabular_final_checkpoint_v0",
            "boundary_sha256": self._boundary_sha256,
            "method_id": method_id,
            "training_seed": training_seed,
            "attempt_number": attempt_number,
            "alpha_hex": _float_hex(learner.alpha, "alpha"),
            "gamma_hex": _float_hex(learner.gamma, "gamma"),
            "training_metadata": training,
            "q_rows": rows,
            "initial_state_hashes": initial,
        }
        semantic = _semantic_digest(_semantic_state_mapping(
            boundary_sha256=self._boundary_sha256,
            method_id=method_id, training_seed=training_seed,
            attempt_number=attempt_number, checkpoint_kind="tabular_q",
            training_metadata=training,
            algorithm_state={
                "alpha_hex": archive["alpha_hex"],
                "gamma_hex": archive["gamma_hex"], "q_rows": rows,
            },
            initial_state_hashes=initial,
        ))
        fresh = self._tabular_from_archive(archive)
        fingerprint = _semantic_digest(_evaluation_fingerprint_mapping(
            boundary=self._boundary,
            reference_values=(
                method_id, training_seed, attempt_number, "tabular_q"
            ),
            learner=fresh, training_metadata=training,
            replay_summary=None, initial_state_hashes=initial,
        ))
        algorithm = {
            "alpha_hex": archive["alpha_hex"],
            "gamma_hex": archive["gamma_hex"],
            "q_row_count": len(rows),
            "q_rows_sha256": _sha256_bytes(_canonical(rows)),
        }
        return (
            _canonical(archive), "tabular_q", training, algorithm,
            initial, semantic, fingerprint,
        )

    def _encode_checkpoint(
        self,
        method_id: str,
        training_seed: int,
        attempt_number: int,
        learner: CheckpointLearner,
        transition_count: int,
        per_graph_transition_counts: tuple[tuple[str, int], ...],
        learner_update_count: int,
        initial_state_hashes: tuple[tuple[str, str], ...],
    ) -> tuple[
        bytes, str, dict[str, object], dict[str, object],
        list[list[object]], str, str,
    ]:
        self._validate_training_counts(
            transition_count, per_graph_transition_counts
        )
        _exact_int(learner_update_count, "learner_update_count", minimum=0)
        initial = _initial_hash_mapping(method_id, initial_state_hashes)
        if method_id.startswith("tabular_"):
            return self._encode_tabular_checkpoint(
                method_id, training_seed, attempt_number, learner,
                transition_count, per_graph_transition_counts,
                learner_update_count, initial,
            )
        if type(learner) is not Family3V2MaskedDoubleDQN:
            raise ValueError("DDQN arm requires exact Family3V2MaskedDoubleDQN")
        expected_hp = _expected_ddqn_hyperparameters(
            self._config, method_id
        )
        if (
            learner.model_spec != FAMILY3_V2_DDQN_MODEL_SPEC
            or learner.hyperparameters != expected_hp
            or learner.rng_deriver
            != Family3V2LearnerRngDeriver(
                experiment_id=self._boundary.experiment_id,
                learner_family="masked_ddqn", base_seed=training_seed,
            )
            or type(learner.environment_steps) is not int
            or learner.environment_steps != transition_count
        ):
            raise ValueError("DDQN learner identity or counters mismatch")
        hp = learner.hyperparameters
        threshold = max(hp.warmup_transitions, hp.batch_size)
        first_update = (
            (threshold + hp.optimize_every - 1)
            // hp.optimize_every * hp.optimize_every
        )
        expected_updates = (
            0 if transition_count < first_update
            else 1 + (transition_count - first_update) // hp.optimize_every
        )
        if (
            type(learner.optimizer_steps) is not int
            or learner.optimizer_steps != expected_updates
            or learner_update_count != expected_updates
            or (expected_updates == 0 and learner.last_loss is not None)
            or (
                expected_updates > 0
                and (
                    type(learner.last_loss) not in (int, float)
                    or type(learner.last_loss) is bool
                    or not math.isfinite(float(learner.last_loss))
                )
            )
        ):
            raise ValueError("DDQN optimizer metadata mismatch")
        buffer = getattr(learner, "_buffer", None)
        if type(buffer) is not _ReplayBuffer:
            raise ValueError("DDQN replay-buffer layout drift")
        items = tuple(_transition_mapping(item) for item in buffer._items)
        if (
            buffer._capacity != hp.replay_capacity
            or len(items) != min(transition_count, hp.replay_capacity)
            or buffer._cursor != transition_count % hp.replay_capacity
            or type(buffer._rng) is not random.Random
        ):
            raise ValueError("DDQN replay state does not match counters")
        rng_state = _plain_state_value(buffer._rng.getstate())
        replay = {
            "capacity": buffer._capacity, "size": len(items),
            "cursor": buffer._cursor, "items": items,
            "rng_state": rng_state,
            "content_sha256": _semantic_digest(items),
            "rng_state_sha256": _semantic_digest(rng_state),
        }
        model_spec = _model_mapping(learner.model_spec)
        hyperparameters = _hyperparameter_mapping(learner.hyperparameters)
        online = _plain_state_mapping(learner.online_network.state_dict())
        target = _plain_state_mapping(learner.target_network.state_dict())
        optimizer = _plain_state_mapping(learner._optimizer.state_dict())
        training = _training_metadata(
            transition_count=transition_count,
            per_graph_transition_counts=per_graph_transition_counts,
            environment_steps=learner.environment_steps,
            optimizer_steps=learner.optimizer_steps,
            learner_update_count=learner_update_count,
            last_loss=(
                None if learner.last_loss is None else float(learner.last_loss)
            ),
        )
        archive = {
            "schema_version": "family3_v2_ddqn_final_checkpoint_v0",
            "boundary_sha256": self._boundary_sha256,
            "method_id": method_id, "training_seed": training_seed,
            "attempt_number": attempt_number, "model_spec": model_spec,
            "hyperparameters": hyperparameters,
            "training_metadata": training,
            "online_state_dict": online, "target_state_dict": target,
            "optimizer_state_dict": optimizer, "replay_state": replay,
            "initial_state_hashes": initial,
        }
        semantic = _semantic_digest(_semantic_state_mapping(
            boundary_sha256=self._boundary_sha256,
            method_id=method_id, training_seed=training_seed,
            attempt_number=attempt_number, checkpoint_kind="masked_ddqn",
            training_metadata=training,
            algorithm_state={
                "model_spec": model_spec, "hyperparameters": hyperparameters,
                "online_state_dict": online,
                "target_state_dict": target,
                "optimizer_state_dict": optimizer, "replay_state": replay,
            },
            initial_state_hashes=initial,
        ))
        output = BytesIO()
        torch.save(archive, output)
        content = output.getvalue()
        decoded = torch.load(
            BytesIO(content), map_location="cpu", weights_only=True
        )
        fresh, replay_summary = self._ddqn_from_archive(decoded)
        fingerprint = _semantic_digest(_evaluation_fingerprint_mapping(
            boundary=self._boundary,
            reference_values=(
                method_id, training_seed, attempt_number, "masked_ddqn"
            ),
            learner=fresh, training_metadata=training,
            replay_summary=replay_summary,
            initial_state_hashes=initial,
        ))
        algorithm = {
            "model_spec": model_spec, "hyperparameters": hyperparameters,
            "online_state_sha256": _semantic_digest(online),
            "target_state_sha256": _semantic_digest(target),
            "optimizer_state_sha256": _semantic_digest(optimizer),
            "replay_capacity": replay["capacity"],
            "replay_size": replay["size"],
            "replay_cursor": replay["cursor"],
            "replay_content_sha256": replay["content_sha256"],
            "replay_rng_state_sha256": replay["rng_state_sha256"],
        }
        return (
            content, "masked_ddqn", training, algorithm,
            initial, semantic, fingerprint,
        )

    def _tabular_from_archive(
        self, archive: object,
    ) -> TabularQLearner:
        keys = (
            "schema_version", "boundary_sha256", "method_id",
            "training_seed", "attempt_number", "alpha_hex", "gamma_hex",
            "training_metadata", "q_rows", "initial_state_hashes",
        )
        if type(archive) is not dict or tuple(archive) != keys:
            raise ValueError("tabular checkpoint schema is malformed")
        method_id = archive["method_id"]
        if (
            archive["schema_version"]
            != "family3_v2_tabular_final_checkpoint_v0"
            or archive["boundary_sha256"] != self._boundary_sha256
            or type(method_id) is not str
            or not method_id.startswith("tabular_")
            or method_id not in self._boundary.trained_method_ids
            or type(archive["training_seed"]) is not int
            or archive["training_seed"] not in self._boundary.training_seeds
            or type(archive["attempt_number"]) is not int
            or type(archive["q_rows"]) is not list
            or type(archive["initial_state_hashes"]) is not list
        ):
            raise ValueError("tabular checkpoint identity is invalid")
        alpha = _decode_float_hex(archive["alpha_hex"], "alpha_hex")
        gamma = _decode_float_hex(archive["gamma_hex"], "gamma_hex")
        if (
            alpha != float(self._config.hyperparameters["tabular"]["alpha"])
            or gamma != _method_gamma(self._config, method_id)
        ):
            raise ValueError("tabular checkpoint hyperparameters mismatch")
        learner = TabularQLearner(alpha=alpha, gamma=gamma)
        prior: tuple[str, str] | None = None
        for row in archive["q_rows"]:
            if (
                type(row) is not list or len(row) != 3
                or type(row[0]) is not str or not row[0]
                or type(row[1]) is not str or not row[1]
            ):
                raise ValueError("tabular checkpoint Q row is malformed")
            coordinate = (row[0], row[1])
            if prior is not None and coordinate <= prior:
                raise ValueError("tabular checkpoint Q rows are not strict")
            learner.set_value(
                row[0], row[1], _decode_float_hex(row[2], "q_value")
            )
            prior = coordinate
        return learner

    def _ddqn_from_archive(
        self, archive: object,
    ) -> tuple[Family3V2MaskedDoubleDQN, dict[str, object]]:
        keys = (
            "schema_version", "boundary_sha256", "method_id",
            "training_seed", "attempt_number", "model_spec",
            "hyperparameters", "training_metadata", "online_state_dict",
            "target_state_dict", "optimizer_state_dict", "replay_state",
            "initial_state_hashes",
        )
        if type(archive) is not dict or tuple(archive) != keys:
            raise ValueError("DDQN checkpoint schema is malformed")
        method_id = archive["method_id"]
        training_seed = archive["training_seed"]
        if (
            archive["schema_version"]
            != "family3_v2_ddqn_final_checkpoint_v0"
            or archive["boundary_sha256"] != self._boundary_sha256
            or type(method_id) is not str
            or not method_id.startswith("masked_ddqn_")
            or method_id not in self._boundary.trained_method_ids
            or type(training_seed) is not int
            or training_seed not in self._boundary.training_seeds
            or type(archive["attempt_number"]) is not int
            or type(archive["model_spec"]) is not dict
            or tuple(archive["model_spec"])
            != ("state_dim", "candidate_dim", "max_candidates")
            or type(archive["hyperparameters"]) is not dict
            or tuple(archive["hyperparameters"]) != (
                "gamma", "learning_rate", "batch_size", "replay_capacity",
                "warmup_transitions", "optimize_every",
                "target_update_every", "gradient_clip",
            )
        ):
            raise ValueError("DDQN checkpoint identity is invalid")
        if archive["model_spec"] != _model_mapping(
            FAMILY3_V2_DDQN_MODEL_SPEC
        ):
            raise ValueError("DDQN checkpoint model specification mismatch")
        hp_values = archive["hyperparameters"]
        decoded_hp = DDQNHyperparameters(
            gamma=_decode_float_hex(hp_values["gamma"], "gamma"),
            learning_rate=_decode_float_hex(
                hp_values["learning_rate"], "learning_rate"
            ),
            batch_size=_exact_int(
                hp_values["batch_size"], "batch_size", minimum=1
            ),
            replay_capacity=_exact_int(
                hp_values["replay_capacity"], "replay_capacity", minimum=1
            ),
            warmup_transitions=_exact_int(
                hp_values["warmup_transitions"],
                "warmup_transitions", minimum=1,
            ),
            optimize_every=_exact_int(
                hp_values["optimize_every"], "optimize_every", minimum=1
            ),
            target_update_every=_exact_int(
                hp_values["target_update_every"],
                "target_update_every", minimum=1,
            ),
            gradient_clip=_decode_float_hex(
                hp_values["gradient_clip"], "gradient_clip"
            ),
        )
        if decoded_hp != _expected_ddqn_hyperparameters(
            self._config, method_id
        ):
            raise ValueError("DDQN checkpoint hyperparameters mismatch")
        training = archive["training_metadata"]
        if type(training) is not dict or tuple(training) != (
            "transition_count", "per_graph_transition_counts",
            "environment_steps", "optimizer_steps",
            "learner_update_count", "last_loss_hex",
            "rng_derivation_schema",
        ):
            raise ValueError("DDQN training metadata is malformed")
        for name in (
            "transition_count", "environment_steps", "optimizer_steps",
            "learner_update_count",
        ):
            _exact_int(training[name], name, minimum=0)
        if (
            training["rng_derivation_schema"]
            != "family3_v2_learner_rng_v0"
            or type(training["per_graph_transition_counts"]) is not list
        ):
            raise ValueError("DDQN training metadata values are invalid")
        replay = archive["replay_state"]
        if type(replay) is not dict or tuple(replay) != (
            "capacity", "size", "cursor", "items", "rng_state",
            "content_sha256", "rng_state_sha256",
        ):
            raise ValueError("DDQN replay archive is malformed")
        if type(replay["items"]) is not tuple:
            raise ValueError("DDQN replay items must be a tuple")
        transitions = tuple(
            _transition_from_mapping(item) for item in replay["items"]
        )
        if (
            type(replay["capacity"]) is not int
            or replay["capacity"] != decoded_hp.replay_capacity
            or type(replay["size"]) is not int
            or replay["size"] != len(transitions)
            or type(replay["cursor"]) is not int
            or replay["size"] != min(
                training["environment_steps"], replay["capacity"]
            )
            or replay["cursor"]
            != training["environment_steps"] % replay["capacity"]
            or replay["content_sha256"]
            != _semantic_digest(tuple(
                _transition_mapping(item) for item in transitions
            ))
            or replay["rng_state_sha256"]
            != _semantic_digest(replay["rng_state"])
        ):
            raise ValueError("DDQN replay archive does not verify")
        probe_rng = random.Random()
        try:
            probe_rng.setstate(replay["rng_state"])
        except (TypeError, ValueError) as error:
            raise ValueError("DDQN replay RNG state is invalid") from error
        learner = Family3V2MaskedDoubleDQN(
            rng_deriver=Family3V2LearnerRngDeriver(
                experiment_id=self._boundary.experiment_id,
                learner_family="masked_ddqn", base_seed=training_seed,
            ),
            hyperparameters=decoded_hp,
            model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
        )
        try:
            learner.online_network.load_state_dict(
                archive["online_state_dict"], strict=True
            )
            learner.target_network.load_state_dict(
                archive["target_state_dict"], strict=True
            )
            learner._optimizer.load_state_dict(
                archive["optimizer_state_dict"]
            )
        except (TypeError, ValueError, RuntimeError, KeyError) as error:
            raise ValueError("DDQN state dictionaries do not load strictly") from error
        learner.environment_steps = training["environment_steps"]
        learner.optimizer_steps = training["optimizer_steps"]
        learner.last_loss = (
            None if training["last_loss_hex"] is None
            else _decode_float_hex(
                training["last_loss_hex"], "last_loss_hex"
            )
        )
        if (
            learner.environment_steps != training["transition_count"]
            or learner.optimizer_steps != training["learner_update_count"]
        ):
            raise ValueError("DDQN training counters do not agree")
        summary = {
            "capacity": replay["capacity"], "size": replay["size"],
            "cursor": replay["cursor"],
            "content_sha256": replay["content_sha256"],
            "rng_state_sha256": replay["rng_state_sha256"],
        }
        if (
            len(learner._buffer._items) != 0
            or learner._buffer._cursor != 0
        ):
            raise ValueError("fresh evaluation replay is not empty")
        return learner, summary

    def _decode_payload(
        self, reference: FinalCheckpointRef, content: bytes,
    ) -> tuple[
        CheckpointLearner, dict[str, object], dict[str, object] | None,
        list[list[object]], str,
    ]:
        if reference.checkpoint_kind == "tabular_q":
            try:
                archive = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("tabular checkpoint is not strict JSON") from error
            if _canonical(archive) != content:
                raise ValueError("tabular checkpoint is noncanonical")
            learner = self._tabular_from_archive(archive)
            training = archive["training_metadata"]
            initial = archive["initial_state_hashes"]
            semantic = _semantic_digest(_semantic_state_mapping(
                boundary_sha256=self._boundary_sha256,
                method_id=reference.method_id,
                training_seed=reference.training_seed,
                attempt_number=reference.attempt_number,
                checkpoint_kind=reference.checkpoint_kind,
                training_metadata=training,
                algorithm_state={
                    "alpha_hex": archive["alpha_hex"],
                    "gamma_hex": archive["gamma_hex"],
                    "q_rows": archive["q_rows"],
                },
                initial_state_hashes=initial,
            ))
            return learner, training, None, initial, semantic
        try:
            archive = torch.load(
                BytesIO(content), map_location="cpu", weights_only=True
            )
        except Exception as error:
            raise ValueError("DDQN checkpoint cannot be loaded safely") from error
        learner, replay_summary = self._ddqn_from_archive(archive)
        semantic = _semantic_digest(_semantic_state_mapping(
            boundary_sha256=self._boundary_sha256,
            method_id=reference.method_id,
            training_seed=reference.training_seed,
            attempt_number=reference.attempt_number,
            checkpoint_kind=reference.checkpoint_kind,
            training_metadata=archive["training_metadata"],
            algorithm_state={
                "model_spec": archive["model_spec"],
                "hyperparameters": archive["hyperparameters"],
                "online_state_dict": archive["online_state_dict"],
                "target_state_dict": archive["target_state_dict"],
                "optimizer_state_dict": archive["optimizer_state_dict"],
                "replay_state": archive["replay_state"],
            },
            initial_state_hashes=archive["initial_state_hashes"],
        ))
        return (
            learner, archive["training_metadata"], replay_summary,
            archive["initial_state_hashes"], semantic,
        )

    def commit_final_checkpoint(
        self,
        method_id: str,
        training_seed: int,
        attempt_number: int,
        *,
        learner: CheckpointLearner,
        transition_count: int,
        per_graph_transition_counts: tuple[tuple[str, int], ...],
        learner_update_count: int,
        initial_state_hashes: tuple[tuple[str, str], ...],
        command: tuple[str, ...],
    ) -> FinalCheckpointRef:
        self._require_mutation()
        checked_command = self._command(command)
        coordinate = [method_id, training_seed, attempt_number]
        records = self._state_records()
        if (
            self._state() != "TRAINING_ATTEMPT_ACTIVE"
            or records[-1]["payload"]["active_attempt"] != coordinate
        ):
            raise ValueError("checkpoint does not match the active attempt")
        final_relative = self._final_ref_relative(method_id, training_seed)
        if (self._root / final_relative).exists():
            raise ValueError("training arm is already committed")
        payload_relative, manifest_relative = _checkpoint_paths(
            method_id, training_seed, attempt_number
        )
        attempt_relative = (
            f"training/{method_id}/{training_seed}/attempts/"
            f"{attempt_number:04d}/attempt.json"
        )
        (
            payload_bytes, kind, training, algorithm, initial,
            semantic, fingerprint,
        ) = self._encode_checkpoint(
            method_id, training_seed, attempt_number, learner,
            transition_count, per_graph_transition_counts,
            learner_update_count, initial_state_hashes,
        )
        self._publish_immutable(payload_relative, payload_bytes)
        self._fault("after_checkpoint_payload_publish", payload_relative)
        self._append_attempt_event(
            method_id, training_seed, attempt_number,
            event_type="CHECKPOINT_PAYLOAD_PUBLISHED",
            command=checked_command,
            artifact_refs=[_short_ref(self._root, payload_relative)],
            message=None,
        )
        prior = self._state_head()
        input_refs = [
            _artifact_ref(self._root, "attempt", attempt_relative),
            _artifact_ref(self._root, "payload", payload_relative),
        ]
        transaction = self._transaction(
            "CHECKPOINT_COMMIT", coordinate=coordinate,
            command=checked_command, input_refs=input_refs,
            input_values=[
                ["semantic_state_sha256", semantic],
                ["evaluation_fingerprint_sha256", fingerprint],
            ], prior_head=prior,
        )
        manifest = {
            "schema_version": "family3_v2_checkpoint_manifest_v0",
            "boundary_sha256": self._boundary_sha256,
            "method_id": method_id, "training_seed": training_seed,
            "attempt_number": attempt_number, "checkpoint_kind": kind,
            "payload_ref": _short_ref(self._root, payload_relative),
            "training_metadata": training,
            "algorithm_metadata": algorithm,
            "initial_state_hashes": initial,
            "semantic_state_sha256": semantic,
            "evaluation_fingerprint_sha256": fingerprint,
            "command": list(checked_command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
        }
        manifest_bytes = _canonical(manifest)
        self._publish_immutable(manifest_relative, manifest_bytes)
        self._fault("after_checkpoint_manifest_publish", manifest_relative)
        self._append_attempt_event(
            method_id, training_seed, attempt_number,
            event_type="CHECKPOINT_MANIFEST_PUBLISHED",
            command=checked_command,
            artifact_refs=[_short_ref(self._root, manifest_relative)],
            message=None,
        )
        reference = FinalCheckpointRef(
            schema_version="family3_v2_final_checkpoint_ref_v0",
            method_id=method_id, training_seed=training_seed,
            attempt_number=attempt_number, checkpoint_kind=kind,
            payload_relative_path=payload_relative,
            payload_sha256=_sha256_bytes(payload_bytes),
            payload_byte_size=len(payload_bytes),
            manifest_relative_path=manifest_relative,
            manifest_sha256=_sha256_bytes(manifest_bytes),
            manifest_byte_size=len(manifest_bytes),
            boundary_sha256=self._boundary_sha256,
            transition_count=transition_count,
            per_graph_transition_counts=per_graph_transition_counts,
            semantic_state_sha256=semantic,
            evaluation_fingerprint_sha256=fingerprint,
        )
        self._publish_immutable(
            final_relative, _canonical(_ref_mapping(reference))
        )
        self._fault("after_checkpoint_ref_publish", final_relative)
        event_head = self._append_attempt_event(
            method_id, training_seed, attempt_number,
            event_type="FINAL_CHECKPOINT_COMMITTED",
            command=checked_command,
            artifact_refs=[_short_ref(self._root, final_relative)],
            message=None,
        )
        refs = self._completed_refs()
        is_last = len(refs) == len(self._canonical_arms())
        self._append_state(
            event_type="CHECKPOINT_COMMIT",
            transaction_sha256=transaction,
            from_state="TRAINING_ATTEMPT_ACTIVE",
            to_state="ARM_COMMITTED", command=checked_command,
            completed_boundary=["ARM_COMMITTED", method_id, training_seed],
            artifacts=[
                _artifact_ref(self._root, "attempt", attempt_relative),
                _artifact_ref(
                    self._root, "checkpoint_payload", payload_relative
                ),
                _artifact_ref(
                    self._root, "checkpoint_manifest", manifest_relative
                ),
                _artifact_ref(
                    self._root, "final_checkpoint", final_relative
                ),
            ],
            output_paths=[
                payload_relative, manifest_relative, final_relative,
                self._attempt_event_relative(
                    method_id, training_seed, attempt_number
                ),
            ],
            ledger_heads=[[
                (
                    f"attempt_events/{method_id}/{training_seed}/"
                    f"{attempt_number:04d}"
                ),
                event_head,
            ]],
            active_attempt=None,
            next_action=(
                "PUBLISH_TRAINING_SEAL"
                if is_last else "BEGIN_NEXT_TRAINING_ATTEMPT"
            ),
        )
        if is_last:
            self._publish_training_seal(refs, checked_command)
        return reference

    def _publish_training_seal(
        self, refs: tuple[FinalCheckpointRef, ...],
        command: tuple[str, ...],
    ) -> None:
        if tuple(
            (reference.method_id, reference.training_seed)
            for reference in refs
        ) != self._canonical_arms():
            raise ValueError("checkpoint set is not the canonical complete set")
        checkpoints: list[list[object]] = []
        arms: list[list[object]] = []
        total = 0
        for reference in refs:
            final_relative = self._final_ref_relative(
                reference.method_id, reference.training_seed
            )
            final_content = _path_within(
                self._root, final_relative, final_file=True
            ).read_bytes()
            checkpoints.append([
                reference.method_id, reference.training_seed, final_relative,
                _sha256_bytes(final_content), len(final_content),
                reference.payload_sha256,
                reference.semantic_state_sha256,
                reference.evaluation_fingerprint_sha256,
            ])
            counts = [
                [graph_id, count]
                for graph_id, count
                in reference.per_graph_transition_counts
            ]
            arms.append([
                reference.method_id, reference.training_seed,
                reference.transition_count, counts,
            ])
            total += reference.transition_count
        checkpoint_set = {
            "schema_version": "family3_v2_checkpoint_set_manifest_v0",
            "boundary_sha256": self._boundary_sha256,
            "checkpoint_count": len(refs),
            "checkpoints": checkpoints,
        }
        budget = {
            "schema_version": "family3_v2_transition_budget_summary_v0",
            "boundary_sha256": self._boundary_sha256,
            "arm_count": len(refs), "arms": arms,
            "total_transition_count": total,
        }
        checkpoint_bytes = _canonical(checkpoint_set)
        budget_bytes = _canonical(budget)
        self._publish_immutable(
            "training/checkpoint_manifest.json", checkpoint_bytes
        )
        self._publish_immutable(
            "training/transition_budget_summary.json", budget_bytes
        )
        train_complete = {
            "schema_version": "family3_v2_train_complete_v0",
            "boundary_sha256": self._boundary_sha256,
            "checkpoint_manifest_sha256": _sha256_bytes(checkpoint_bytes),
            "transition_budget_summary_sha256": _sha256_bytes(budget_bytes),
            "completed_arm_count": len(refs),
            "completion_status": "TRAINING_COMPLETE",
        }
        self._publish_immutable(
            "training/train_complete.json", _canonical(train_complete)
        )
        transaction_refs = [
            _artifact_ref(
                self._root, "checkpoint_set_manifest",
                "training/checkpoint_manifest.json",
            ),
            _artifact_ref(
                self._root, "transition_budget_summary",
                "training/transition_budget_summary.json",
            ),
            _artifact_ref(
                self._root, "train_complete",
                "training/train_complete.json",
            ),
        ]
        transaction = self._transaction(
            "TRAINING_SEAL", coordinate=["training"], command=command,
            input_refs=transaction_refs,
            input_values=[
                ["completed_arm_count", len(refs)],
                ["completion_status", "TRAINING_COMPLETE"],
            ],
        )
        self._append_state(
            event_type="TRAINING_SEAL",
            transaction_sha256=transaction,
            from_state="ARM_COMMITTED", to_state="TRAINING_COMPLETE",
            command=command, completed_boundary=["TRAINING_COMPLETE"],
            artifacts=transaction_refs,
            output_paths=[
                "training/checkpoint_manifest.json",
                "training/transition_budget_summary.json",
                "training/train_complete.json",
            ],
            ledger_heads=[], active_attempt=None,
            next_action="RUN_NEXT_MISSING_VALIDATION_COORDINATE",
        )

    def _verified_checkpoint(
        self, reference: FinalCheckpointRef,
    ) -> tuple[
        CheckpointLearner, dict[str, object], dict[str, object] | None,
        list[list[object]],
    ]:
        if type(reference) is not FinalCheckpointRef:
            raise ValueError("reference has the wrong exact type")
        if (
            reference.boundary_sha256 != self._boundary_sha256
            or (
                reference.method_id, reference.training_seed
            ) not in self._canonical_arms()
        ):
            raise ValueError("checkpoint reference is outside this boundary")
        stored = self._load_ref_file(
            reference.method_id, reference.training_seed
        )
        if stored != reference:
            raise ValueError("checkpoint reference differs from its commit marker")
        payload_path = _path_within(
            self._root, reference.payload_relative_path, final_file=True
        )
        manifest_path = _path_within(
            self._root, reference.manifest_relative_path, final_file=True
        )
        payload = payload_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        if (
            len(payload) != reference.payload_byte_size
            or _sha256_bytes(payload) != reference.payload_sha256
            or len(manifest_bytes) != reference.manifest_byte_size
            or _sha256_bytes(manifest_bytes) != reference.manifest_sha256
        ):
            raise ValueError("checkpoint raw file identity mismatch")
        manifest = _read_exact_json(
            manifest_path,
            (
                "schema_version", "boundary_sha256", "method_id",
                "training_seed", "attempt_number", "checkpoint_kind",
                "payload_ref", "training_metadata", "algorithm_metadata",
                "initial_state_hashes", "semantic_state_sha256",
                "evaluation_fingerprint_sha256", "command",
                "prior_state_ledger_head_sha256", "transaction_sha256",
            ),
        )
        if (
            manifest["schema_version"]
            != "family3_v2_checkpoint_manifest_v0"
            or manifest["boundary_sha256"] != self._boundary_sha256
            or manifest["method_id"] != reference.method_id
            or manifest["training_seed"] != reference.training_seed
            or manifest["attempt_number"] != reference.attempt_number
            or manifest["checkpoint_kind"] != reference.checkpoint_kind
            or manifest["payload_ref"] != [
                reference.payload_relative_path, reference.payload_sha256,
                reference.payload_byte_size,
            ]
            or manifest["semantic_state_sha256"]
            != reference.semantic_state_sha256
            or manifest["evaluation_fingerprint_sha256"]
            != reference.evaluation_fingerprint_sha256
        ):
            raise ValueError("checkpoint manifest does not match its reference")
        learner, training, replay, initial, semantic = self._decode_payload(
            reference, payload
        )
        if (
            semantic != reference.semantic_state_sha256
            or training["transition_count"] != reference.transition_count
            or training["per_graph_transition_counts"]
            != [
                [graph_id, count]
                for graph_id, count
                in reference.per_graph_transition_counts
            ]
            or initial != manifest["initial_state_hashes"]
        ):
            raise ValueError("checkpoint semantic state does not verify")
        fingerprint = _semantic_digest(_evaluation_fingerprint_mapping(
            boundary=self._boundary,
            reference_values=(
                reference.method_id, reference.training_seed,
                reference.attempt_number, reference.checkpoint_kind,
            ),
            learner=learner, training_metadata=training,
            replay_summary=replay, initial_state_hashes=initial,
        ))
        if fingerprint != reference.evaluation_fingerprint_sha256:
            raise ValueError("checkpoint evaluation fingerprint mismatch")
        return learner, training, replay, initial

    def load_verified_final_checkpoint(
        self,
        reference: FinalCheckpointRef,
    ) -> CheckpointLearner:
        if not _runtime_matches(self._boundary):
            raise ValueError("checkpoint runtime boundary mismatch")
        learner, _, _, _ = self._verified_checkpoint(reference)
        return learner

    def evaluation_fingerprint(
        self,
        reference: FinalCheckpointRef,
        learner: CheckpointLearner,
    ) -> str:
        _, training, replay, initial = self._verified_checkpoint(reference)
        fingerprint = _semantic_digest(_evaluation_fingerprint_mapping(
            boundary=self._boundary,
            reference_values=(
                reference.method_id, reference.training_seed,
                reference.attempt_number, reference.checkpoint_kind,
            ),
            learner=learner, training_metadata=training,
            replay_summary=replay, initial_state_hashes=initial,
        ))
        if fingerprint != reference.evaluation_fingerprint_sha256:
            raise ValueError("evaluation learner state has mutated")
        return fingerprint

    def record_failure(
        self,
        failure_kind: str,
        failure_code: str,
        message: str,
        *,
        method_id: str | None = None,
        training_seed: int | None = None,
        attempt_number: int | None = None,
        command: tuple[str, ...],
        next_action: str,
    ) -> None:
        self._require_mutation()
        checked_command = self._command(command)
        for value, name in (
            (failure_kind, "failure_kind"), (failure_code, "failure_code"),
            (message, "message"), (next_action, "next_action"),
        ):
            _exact_str(value, name)
        coordinate_values = (method_id, training_seed, attempt_number)
        if failure_kind == "RESTARTABLE_ARM_FAILURE":
            if (
                self._state() != "TRAINING_ATTEMPT_ACTIVE"
                or any(value is None for value in coordinate_values)
                or next_action
                != "MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO"
            ):
                raise ValueError("restartable failure context is invalid")
            coordinate = [method_id, training_seed, attempt_number]
            if (
                self._state_records()[-1]["payload"]["active_attempt"]
                != coordinate
            ):
                raise ValueError("failure does not match the active attempt")
            assert isinstance(method_id, str)
            assert isinstance(training_seed, int)
            assert isinstance(attempt_number, int)
            relative = (
                f"training/{method_id}/{training_seed}/attempts/"
                f"{attempt_number:04d}/failure.json"
            )
            failure_number = attempt_number
        elif failure_kind == "TERMINAL_RUN_FAILURE":
            if not (
                all(value is None for value in coordinate_values)
                or all(value is not None for value in coordinate_values)
            ):
                raise ValueError("terminal failure coordinate is partially null")
            expected_next = (
                "NO_FURTHER_ACTION"
            )
            if next_action != expected_next:
                raise ValueError("terminal failure next action is invalid")
            failure_directory = self._root / "failures"
            failure_number = 1
            while (
                failure_directory / f"{failure_number:04d}.json"
            ).exists():
                failure_number += 1
            relative = f"failures/{failure_number:04d}.json"
            coordinate = (
                None if method_id is None
                else [method_id, training_seed, attempt_number]
            )
        else:
            raise ValueError("failure kind is not recognized")
        prior = self._state_head()
        transaction = self._transaction(
            "FAILURE", coordinate=coordinate, command=checked_command,
            input_refs=[], input_values=[
                ["failure_kind", failure_kind],
                ["failure_code", failure_code],
                ["message", message],
                ["next_action", next_action],
            ], prior_head=prior,
        )
        failure = {
            "schema_version": "family3_v2_failure_v0",
            "boundary_sha256": self._boundary_sha256,
            "failure_number": failure_number,
            "failure_kind": failure_kind,
            "failure_code": failure_code, "message": message,
            "method_id": method_id, "training_seed": training_seed,
            "attempt_number": attempt_number,
            "command": list(checked_command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
            "next_action": next_action,
        }
        self._publish_immutable(relative, _canonical(failure))
        if failure_kind == "RESTARTABLE_ARM_FAILURE":
            assert isinstance(method_id, str)
            assert isinstance(training_seed, int)
            assert isinstance(attempt_number, int)
            event_head = self._append_attempt_event(
                method_id, training_seed, attempt_number,
                event_type="ATTEMPT_FAILED", command=checked_command,
                artifact_refs=[_short_ref(self._root, relative)],
                message=message,
            )
            self._append_state(
                event_type="FAILURE", transaction_sha256=transaction,
                from_state="TRAINING_ATTEMPT_ACTIVE",
                to_state="TRAINING_INTERRUPTED", command=checked_command,
                completed_boundary=self._last_completed_boundary(),
                artifacts=[_artifact_ref(self._root, "failure", relative)],
                output_paths=[
                    relative,
                    self._attempt_event_relative(
                        method_id, training_seed, attempt_number
                    ),
                ],
                ledger_heads=[[
                    (
                        f"attempt_events/{method_id}/{training_seed}/"
                        f"{attempt_number:04d}"
                    ),
                    event_head,
                ]],
                active_attempt=None,
                next_action=next_action,
            )
            return
        self._commit_operational_failure(
            failure, relative, checked_command
        )

    def _expected_coordinates(
        self, phase: str,
    ) -> tuple[EvaluationCoordinate, ...]:
        if phase not in ("validation", "test"):
            raise ValueError("evaluation phase is invalid")
        graphs = (
            self._boundary.validation_graph_ids
            if phase == "validation" else self._boundary.test_graph_ids
        )
        seeds = tuple(self._config.evaluation["seeds"])
        return tuple(
            (method_id, seed, graph_id, condition, ordinal)
            for method_id in self._boundary.method_ids
            for seed in seeds
            for graph_id in graphs
            for condition in self._boundary.condition_ids
            for ordinal in range(self._boundary.episodes_per_evaluation_cell)
        )

    @staticmethod
    def _row_coordinate(row: EvaluationEpisodeRow) -> EvaluationCoordinate:
        return (
            row.method_id, row.evaluation_seed, row.graph_id,
            row.condition, row.episode_ordinal,
        )

    def _coordinate_rank(
        self, phase: str, coordinate: EvaluationCoordinate,
    ) -> int:
        graphs = (
            self._boundary.validation_graph_ids
            if phase == "validation" else self._boundary.test_graph_ids
        )
        seeds = tuple(self._config.evaluation["seeds"])
        method_id, seed, graph_id, condition, ordinal = coordinate
        try:
            indices = (
                self._boundary.method_ids.index(method_id),
                seeds.index(seed), graphs.index(graph_id),
                self._boundary.condition_ids.index(condition),
            )
        except ValueError as error:
            raise ValueError("evaluation coordinate is outside the universe") from error
        if (
            type(ordinal) is not int
            or ordinal < 0
            or ordinal >= self._boundary.episodes_per_evaluation_cell
        ):
            raise ValueError("evaluation ordinal is outside the universe")
        method_index, seed_index, graph_index, condition_index = indices
        width = self._boundary.episodes_per_evaluation_cell
        return (
            ((((method_index * len(seeds) + seed_index) * len(graphs)
               + graph_index) * len(self._boundary.condition_ids)
              + condition_index) * width)
            + ordinal
        )

    def _validate_row_authority(
        self, row: EvaluationEpisodeRow,
    ) -> EvaluationCoordinate:
        if type(row) is not EvaluationEpisodeRow:
            raise ValueError("row has the wrong exact type")
        coordinate = self._row_coordinate(row)
        self._coordinate_rank(row.phase, coordinate)
        expected_root = derive_family3_v2_eval_environment_seed(
            experiment_id=self._boundary.experiment_id,
            evaluation_seed=row.evaluation_seed,
            graph_id=row.graph_id,
            episode_ordinal=row.episode_ordinal,
        )
        if row.root_seed != expected_root:
            raise ValueError("evaluation root seed does not match its coordinate")
        return coordinate

    @staticmethod
    def _segment_relative(phase: str, segment_number: int) -> str:
        if segment_number == 0:
            return f"{phase}/rows.jsonl"
        return f"{phase}/rows.resume.{segment_number:04d}.jsonl"

    def _segment_numbers(self, phase: str) -> tuple[int, ...]:
        directory = self._root / phase
        if not directory.exists():
            return ()
        _reject_symlink_or_reparse(directory)
        numbers: list[int] = []
        if (directory / "rows.jsonl").exists():
            numbers.append(0)
        prefix = "rows.resume."
        suffix = ".jsonl"
        for path in directory.iterdir():
            name = path.name
            if name.startswith(prefix) and name.endswith(suffix):
                middle = name[len(prefix):-len(suffix)]
                if len(middle) != 4 or not middle.isdigit():
                    raise ValueError("evaluation recovery segment name is malformed")
                numbers.append(int(middle))
        numbers.sort()
        if numbers and numbers != list(range(numbers[-1] + 1)):
            raise ValueError("evaluation segment numbering has a gap")
        return tuple(numbers)

    def _read_rows_internal(
        self, phase: str, *, use_cache: bool,
    ) -> tuple[
        tuple[dict[str, object], ...],
        tuple[EvaluationEpisodeRow, ...],
        tuple[list[object], ...],
    ]:
        if phase not in ("validation", "test"):
            raise ValueError("evaluation phase is invalid")
        if use_cache and phase in self._row_cache:
            return self._row_cache[phase]
        all_records: list[dict[str, object]] = []
        seen: dict[EvaluationCoordinate, EvaluationEpisodeRow] = {}
        segment_refs: list[list[object]] = []
        previous = _ZERO_HASH
        sequence = 0
        keys = (
            "schema_version", "phase", "segment_number", "sequence",
            "boundary_sha256", "coordinate_key",
            "previous_record_sha256", "payload_sha256", "payload",
            "record_sha256",
        )
        for segment_number in self._segment_numbers(phase):
            relative = self._segment_relative(phase, segment_number)
            path = _path_within(self._root, relative, final_file=True)
            content = path.read_bytes()
            if not content or not content.endswith(b"\n") or b"\r" in content:
                raise ValueError("evaluation ledger has a corrupt tail")
            first_sequence = sequence
            last_rank: int | None = None
            row_count = 0
            for raw_line in content.splitlines():
                if not raw_line:
                    raise ValueError("evaluation ledger contains a blank line")
                try:
                    value = json.loads(raw_line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ValueError("evaluation ledger JSON is malformed") from error
                if (
                    type(value) is not dict
                    or tuple(value) != keys
                    or _canonical(value) != raw_line
                    or value["schema_version"]
                    != "family3_v2_evaluation_ledger_record_v0"
                    or value["phase"] != phase
                    or value["segment_number"] != segment_number
                    or value["sequence"] != sequence
                    or value["boundary_sha256"] != self._boundary_sha256
                    or value["previous_record_sha256"] != previous
                    or value["payload_sha256"]
                    != _sha256_bytes(_canonical(value["payload"]))
                ):
                    raise ValueError("evaluation ledger envelope is invalid")
                prefix_mapping = {
                    name: value[name] for name in keys[:-1]
                }
                if value["record_sha256"] != _sha256_bytes(
                    _canonical(prefix_mapping)
                ):
                    raise ValueError("evaluation ledger record hash is invalid")
                row = _row_from_mapping(value["payload"])
                coordinate = self._validate_row_authority(row)
                if (
                    type(value["coordinate_key"]) is not list
                    or value["coordinate_key"] != list(coordinate)
                ):
                    raise ValueError("evaluation coordinate key mismatch")
                rank = self._coordinate_rank(phase, coordinate)
                if last_rank is not None and rank <= last_rank:
                    raise ValueError("segment coordinates are not increasing")
                if coordinate in seen:
                    raise ValueError("evaluation ledger repeats a coordinate")
                seen[coordinate] = row
                last_rank = rank
                previous = value["record_sha256"]
                sequence += 1
                row_count += 1
                all_records.append(value)
            segment_refs.append([
                segment_number, relative, _sha256_bytes(content), len(content),
                first_sequence, sequence - 1, row_count,
            ])
        expected = self._expected_coordinates(phase)
        materialized = tuple(
            seen[coordinate] for coordinate in expected if coordinate in seen
        )
        result = (
            tuple(all_records), materialized, tuple(segment_refs)
        )
        self._row_cache[phase] = result
        self._row_seen[phase] = seen
        return result

    def append_evaluation_row(self, row: EvaluationEpisodeRow) -> None:
        self._require_mutation()
        coordinate = self._validate_row_authority(row)
        phase = row.phase
        state = self._state()
        allowed = (
            ("TRAINING_COMPLETE", "VALIDATION_IN_PROGRESS")
            if phase == "validation"
            else ("TEST_OPENED", "TEST_IN_PROGRESS")
        )
        if state not in allowed:
            raise ValueError("current state does not allow this evaluation row")
        if phase == "test":
            self._verified_start_marker()
        records, materialized, _ = self._read_rows_internal(
            phase, use_cache=True
        )
        seen = self._row_seen[phase]
        if coordinate in seen:
            if _row_mapping(seen[coordinate]) == _row_mapping(row):
                raise DuplicateCoordinateError(
                    "evaluation coordinate is already present"
                )
            raise ConflictingCoordinateError(
                "evaluation coordinate has conflicting payload"
            )
        rank = self._coordinate_rank(phase, coordinate)
        if not records:
            segment_number = 0
        else:
            segment_number = int(records[-1]["segment_number"])
            tail_coordinate = tuple(records[-1]["coordinate_key"])
            if rank <= self._coordinate_rank(
                phase, tail_coordinate  # type: ignore[arg-type]
            ):
                segment_number += 1
        relative = self._segment_relative(phase, segment_number)
        previous = (
            _ZERO_HASH if not records
            else str(records[-1]["record_sha256"])
        )
        payload = _row_mapping(row)
        prefix = {
            "schema_version": "family3_v2_evaluation_ledger_record_v0",
            "phase": phase, "segment_number": segment_number,
            "sequence": len(records),
            "boundary_sha256": self._boundary_sha256,
            "coordinate_key": list(coordinate),
            "previous_record_sha256": previous,
            "payload_sha256": _sha256_bytes(_canonical(payload)),
            "payload": payload,
        }
        record = {
            **prefix,
            "record_sha256": _sha256_bytes(_canonical(prefix)),
        }
        self._append_jsonl(relative, _canonical(record) + b"\n")
        seen[coordinate] = row
        self._row_cache[phase] = (
            records + (record,), (), ()
        )
        command = ("artifact-store:append-evaluation-row", phase)
        transaction = self._transaction(
            "EVALUATION_ROW_APPEND", coordinate=list(coordinate),
            command=command, input_refs=[],
            input_values=[
                ["phase", phase],
                ["segment_number", segment_number],
                ["sequence", len(records)],
                ["row_record_sha256", record["record_sha256"]],
            ],
        )
        to_state = (
            "VALIDATION_IN_PROGRESS"
            if phase == "validation" else "TEST_IN_PROGRESS"
        )
        self._append_state(
            event_type="EVALUATION_ROW_APPEND",
            transaction_sha256=transaction,
            from_state=state, to_state=to_state, command=command,
            completed_boundary=[
                "TRAINING_COMPLETE" if phase == "validation"
                else "TEST_OPENED"
            ],
            artifacts=[], output_paths=[relative],
            ledger_heads=[[
                f"{phase}_rows", record["record_sha256"]
            ]],
            active_attempt=None,
            next_action=(
                "RUN_NEXT_MISSING_VALIDATION_COORDINATE"
                if phase == "validation"
                else "RUN_NEXT_MISSING_TEST_COORDINATE"
            ),
        )

    def load_verified_rows(
        self,
        phase: str,
    ) -> tuple[EvaluationEpisodeRow, ...]:
        _, rows, _ = self._read_rows_internal(phase, use_cache=False)
        return rows

    def _rows_manifest(
        self, phase: str, *, completion_claimed: bool,
    ) -> tuple[dict[str, object], tuple[EvaluationEpisodeRow, ...]]:
        records, rows, segment_refs = self._read_rows_internal(
            phase, use_cache=False
        )
        coordinates = [list(self._row_coordinate(row)) for row in rows]
        manifest = {
            "schema_version": "family3_v2_evaluation_rows_manifest_v0",
            "phase": phase, "boundary_sha256": self._boundary_sha256,
            "expected_complete_row_count": len(
                self._expected_coordinates(phase)
            ),
            "observed_unique_row_count": len(rows),
            "segment_refs": list(segment_refs),
            "ledger_head_sha256": (
                _ZERO_HASH if not records
                else records[-1]["record_sha256"]
            ),
            "canonical_coordinate_set_sha256": _sha256_bytes(
                _canonical(coordinates)
            ),
            "completion_claimed": completion_claimed,
        }
        return manifest, rows

    def _verify_training_seals(
        self,
    ) -> tuple[
        tuple[FinalCheckpointRef, ...], dict[str, object], dict[str, object],
    ]:
        refs = self._completed_refs()
        if len(refs) != len(self._canonical_arms()):
            raise ValueError("the complete checkpoint set is absent")
        checkpoint_path = self._root / "training/checkpoint_manifest.json"
        budget_path = self._root / "training/transition_budget_summary.json"
        complete_path = self._root / "training/train_complete.json"
        checkpoint = _read_exact_json(
            checkpoint_path,
            (
                "schema_version", "boundary_sha256", "checkpoint_count",
                "checkpoints",
            ),
        )
        budget = _read_exact_json(
            budget_path,
            (
                "schema_version", "boundary_sha256", "arm_count", "arms",
                "total_transition_count",
            ),
        )
        complete = _read_exact_json(
            complete_path,
            (
                "schema_version", "boundary_sha256",
                "checkpoint_manifest_sha256",
                "transition_budget_summary_sha256", "completed_arm_count",
                "completion_status",
            ),
        )
        if (
            checkpoint["schema_version"]
            != "family3_v2_checkpoint_set_manifest_v0"
            or checkpoint["boundary_sha256"] != self._boundary_sha256
            or checkpoint["checkpoint_count"] != len(refs)
            or budget["schema_version"]
            != "family3_v2_transition_budget_summary_v0"
            or budget["boundary_sha256"] != self._boundary_sha256
            or budget["arm_count"] != len(refs)
            or complete != {
                "schema_version": "family3_v2_train_complete_v0",
                "boundary_sha256": self._boundary_sha256,
                "checkpoint_manifest_sha256": _sha256_bytes(
                    checkpoint_path.read_bytes()
                ),
                "transition_budget_summary_sha256": _sha256_bytes(
                    budget_path.read_bytes()
                ),
                "completed_arm_count": len(refs),
                "completion_status": "TRAINING_COMPLETE",
            }
        ):
            raise ValueError("training seal does not verify")
        return refs, checkpoint, complete

    def _phase_projection_bytes(
        self, phase: str, rows_manifest_sha256: str,
        result: ValidationGateResult | TestClassificationResult,
    ) -> tuple[bytes, bytes]:
        paired = {
            "schema_version": "family3_v2_paired_comparison_v0",
            "phase": phase, "boundary_sha256": self._boundary_sha256,
            "rows_manifest_sha256": rows_manifest_sha256,
            "cell_results": [
                _cell_mapping(cell) for cell in result.cell_results
            ],
        }
        phase_status = (
            result.status
            if type(result) is ValidationGateResult
            else result.classification
        )
        hard = {
            "schema_version": "family3_v2_hard_integrity_v0",
            "phase": phase, "boundary_sha256": self._boundary_sha256,
            "rows_manifest_sha256": rows_manifest_sha256,
            "hard_counts": _hard_mapping(result.hard_counts),
            "phase_status": phase_status,
        }
        return _canonical(paired), _canonical(hard)

    def write_validation_gate(
        self,
        result: ValidationGateResult,
        *,
        command: tuple[str, ...],
    ) -> None:
        self._require_mutation()
        checked_command = self._command(command)
        if type(result) is not ValidationGateResult:
            raise ValueError("validation result has the wrong exact type")
        state = self._state()
        if state not in ("TRAINING_COMPLETE", "VALIDATION_IN_PROGRESS"):
            raise ValueError("state does not allow validation classification")
        self._verify_training_seals()
        phase_complete = self._boundary.evidence_mode == "FORMAL"
        manifest, rows = self._rows_manifest(
            "validation", completion_claimed=phase_complete
        )
        expected = evaluate_validation_gate(
            self._config, rows, phase_complete=phase_complete
        )
        if result != expected:
            raise ValueError("validation result differs from Task 4")
        manifest_bytes = _canonical(manifest)
        result_bytes = _canonical(_validation_mapping(result))
        manifest_hash = _sha256_bytes(manifest_bytes)
        paired_bytes, hard_bytes = self._phase_projection_bytes(
            "validation", manifest_hash, result
        )
        self._publish_immutable(
            "validation/rows_manifest.json", manifest_bytes
        )
        self._publish_immutable("validation/result.json", result_bytes)
        self._fault(
            "after_validation_result_publish", "validation/result.json"
        )
        self._publish_immutable(
            "validation/paired_comparison.json", paired_bytes
        )
        self._publish_immutable(
            "validation/hard_integrity.json", hard_bytes
        )
        prior = self._state_head()
        input_refs = [
            _artifact_ref(
                self._root, "checkpoint_set_manifest",
                "training/checkpoint_manifest.json",
            ),
            _artifact_ref(
                self._root, "train_complete",
                "training/train_complete.json",
            ),
            _artifact_ref(
                self._root, "rows_manifest",
                "validation/rows_manifest.json",
            ),
            _artifact_ref(
                self._root, "result", "validation/result.json"
            ),
            _artifact_ref(
                self._root, "paired_comparison",
                "validation/paired_comparison.json",
            ),
            _artifact_ref(
                self._root, "hard_integrity",
                "validation/hard_integrity.json",
            ),
        ]
        transaction = self._transaction(
            "VALIDATION_GATE", coordinate=["validation"],
            command=checked_command, input_refs=input_refs,
            input_values=[
                ["status", result.status],
                ["qualifying_seed_ids", list(result.qualifying_seed_ids)],
            ], prior_head=prior,
        )
        gate = {
            "schema_version": "family3_v2_validation_gate_artifact_v0",
            "boundary_sha256": self._boundary_sha256,
            "rows_manifest_sha256": manifest_hash,
            "validation_result_sha256": _sha256_bytes(result_bytes),
            "paired_comparison_sha256": _sha256_bytes(paired_bytes),
            "hard_integrity_sha256": _sha256_bytes(hard_bytes),
            "status": result.status,
            "qualifying_seed_ids": list(result.qualifying_seed_ids),
            "command": list(checked_command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
        }
        self._publish_immutable(
            "validation/gate.json", _canonical(gate)
        )
        self._fault(
            "after_validation_gate_publish", "validation/gate.json"
        )
        artifacts = input_refs + [
            _artifact_ref(
                self._root, "validation_gate", "validation/gate.json"
            )
        ]
        records, _, _ = self._read_rows_internal(
            "validation", use_cache=False
        )
        self._append_state(
            event_type="VALIDATION_GATE",
            transaction_sha256=transaction,
            from_state=state, to_state="VALIDATION_CLASSIFIED",
            command=checked_command,
            completed_boundary=["VALIDATION_CLASSIFIED", result.status],
            artifacts=artifacts,
            output_paths=[
                "validation/rows_manifest.json",
                "validation/result.json",
                "validation/paired_comparison.json",
                "validation/hard_integrity.json",
                "validation/gate.json",
            ],
            ledger_heads=[[
                "validation_rows",
                _ZERO_HASH if not records
                else records[-1]["record_sha256"],
            ]],
            active_attempt=None,
            next_action=(
                "WRITE_TEST_PERMIT"
                if result.status == "READY_FOR_TEST"
                else "COMMIT_FINAL_VERDICT"
            ),
        )

    def _stored_validation(
        self,
    ) -> tuple[ValidationGateResult, dict[str, object]]:
        result_mapping = _read_exact_json(
            self._root / "validation/result.json",
            tuple(field.name for field in fields(ValidationGateResult)),
        )
        result = _validation_from_mapping(result_mapping)
        gate = _read_exact_json(
            self._root / "validation/gate.json",
            (
                "schema_version", "boundary_sha256",
                "rows_manifest_sha256", "validation_result_sha256",
                "paired_comparison_sha256", "hard_integrity_sha256",
                "status", "qualifying_seed_ids", "command",
                "prior_state_ledger_head_sha256", "transaction_sha256",
            ),
        )
        if (
            gate["schema_version"]
            != "family3_v2_validation_gate_artifact_v0"
            or gate["boundary_sha256"] != self._boundary_sha256
            or gate["validation_result_sha256"]
            != _sha256_bytes(
                (self._root / "validation/result.json").read_bytes()
            )
            or gate["status"] != result.status
            or gate["qualifying_seed_ids"]
            != list(result.qualifying_seed_ids)
        ):
            raise ValueError("stored validation gate does not verify")
        return result, gate

    def write_test_permit(
        self,
        result: ValidationGateResult,
        *,
        command: tuple[str, ...],
    ) -> None:
        self._require_mutation()
        checked_command = self._command(command)
        if self._boundary.evidence_mode != "FORMAL":
            raise ValueError("test permits are forbidden in smoke mode")
        if self._state() != "VALIDATION_CLASSIFIED":
            raise ValueError("state does not allow a test permit")
        stored, _ = self._stored_validation()
        if (
            type(result) is not ValidationGateResult
            or result != stored
            or result.status != "READY_FOR_TEST"
            or not result.phase_complete
        ):
            raise ValueError("permit requires exact READY_FOR_TEST evidence")
        refs, _, _ = self._verify_training_seals()
        prior = self._state_head()
        input_refs = [
            _artifact_ref(
                self._root, "checkpoint_set_manifest",
                "training/checkpoint_manifest.json",
            ),
            _artifact_ref(
                self._root, "validation_rows_manifest",
                "validation/rows_manifest.json",
            ),
            _artifact_ref(
                self._root, "validation_result",
                "validation/result.json",
            ),
            _artifact_ref(
                self._root, "validation_gate",
                "validation/gate.json",
            ),
        ]
        transaction = self._transaction(
            "TEST_PERMIT", coordinate=["test_permit"],
            command=checked_command, input_refs=input_refs,
            input_values=[
                ["certified_suite_sha256", self._boundary.certified_suite_sha256],
                [
                    "certified_final_verdict_sha256",
                    self._boundary.certified_final_verdict_sha256,
                ],
                ["qualifying_seed_ids", list(result.qualifying_seed_ids)],
            ], prior_head=prior,
        )
        final_hashes: list[list[object]] = []
        for reference in refs:
            relative = self._final_ref_relative(
                reference.method_id, reference.training_seed
            )
            content = (self._root / relative).read_bytes()
            final_hashes.append([
                reference.method_id, reference.training_seed,
                _sha256_bytes(content),
            ])
        permit = {
            "schema_version": "family3_v2_test_permit_v0",
            "boundary_sha256": self._boundary_sha256,
            "config_sha256": self._boundary.config_sha256,
            "source_manifest_sha256": self._boundary.source_manifest_sha256,
            "certified_dependency_manifest_sha256": (
                self._boundary.certified_dependency_manifest_sha256
            ),
            "certified_suite_sha256": self._boundary.certified_suite_sha256,
            "certified_final_verdict_sha256": (
                self._boundary.certified_final_verdict_sha256
            ),
            "checkpoint_manifest_sha256": input_refs[0][2],
            "final_checkpoint_file_hashes": final_hashes,
            "validation_rows_manifest_sha256": input_refs[1][2],
            "validation_result_sha256": input_refs[2][2],
            "validation_gate_sha256": input_refs[3][2],
            "qualifying_seed_ids": list(result.qualifying_seed_ids),
            "test_state": "UNOPENED",
            "command": list(checked_command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
        }
        self._publish_immutable("test_permit.json", _canonical(permit))
        self._fault("after_test_permit_publish", "test_permit.json")
        self._append_state(
            event_type="TEST_PERMIT", transaction_sha256=transaction,
            from_state="VALIDATION_CLASSIFIED",
            to_state="READY_FOR_TEST", command=checked_command,
            completed_boundary=["VALIDATION_CLASSIFIED", "READY_FOR_TEST"],
            artifacts=[
                _artifact_ref(
                    self._root, "test_permit", "test_permit.json"
                )
            ],
            output_paths=["test_permit.json"], ledger_heads=[],
            active_attempt=None, next_action="OPEN_TEST_ONCE",
        )

    def _verified_permit(self) -> dict[str, object]:
        permit = _read_exact_json(
            self._root / "test_permit.json",
            (
                "schema_version", "boundary_sha256", "config_sha256",
                "source_manifest_sha256",
                "certified_dependency_manifest_sha256",
                "certified_suite_sha256",
                "certified_final_verdict_sha256",
                "checkpoint_manifest_sha256",
                "final_checkpoint_file_hashes",
                "validation_rows_manifest_sha256",
                "validation_result_sha256", "validation_gate_sha256",
                "qualifying_seed_ids", "test_state", "command",
                "prior_state_ledger_head_sha256", "transaction_sha256",
            ),
        )
        result, _ = self._stored_validation()
        if (
            permit["schema_version"] != "family3_v2_test_permit_v0"
            or permit["boundary_sha256"] != self._boundary_sha256
            or permit["config_sha256"] != self._boundary.config_sha256
            or permit["source_manifest_sha256"]
            != self._boundary.source_manifest_sha256
            or permit["certified_dependency_manifest_sha256"]
            != self._boundary.certified_dependency_manifest_sha256
            or permit["certified_suite_sha256"]
            != self._boundary.certified_suite_sha256
            or permit["certified_final_verdict_sha256"]
            != self._boundary.certified_final_verdict_sha256
            or permit["checkpoint_manifest_sha256"]
            != _sha256_bytes(
                (self._root / "training/checkpoint_manifest.json").read_bytes()
            )
            or permit["validation_rows_manifest_sha256"]
            != _sha256_bytes(
                (self._root / "validation/rows_manifest.json").read_bytes()
            )
            or permit["validation_result_sha256"]
            != _sha256_bytes(
                (self._root / "validation/result.json").read_bytes()
            )
            or permit["validation_gate_sha256"]
            != _sha256_bytes(
                (self._root / "validation/gate.json").read_bytes()
            )
            or permit["qualifying_seed_ids"]
            != list(result.qualifying_seed_ids)
            or permit["test_state"] != "UNOPENED"
        ):
            raise ValueError("test permit does not verify")
        return permit

    def _unlock_records(self) -> tuple[dict[str, object], ...]:
        return self._records(
            "test/unlock_ledger.jsonl",
            "family3_v2_test_unlock_event_v0",
        )

    def _open_inputs(self) -> list[object]:
        return [
            _artifact_ref(
                self._root, "permit", "test_permit.json"
            ),
            _artifact_ref(
                self._root, "checkpoint_set_manifest",
                "training/checkpoint_manifest.json",
            ),
            _artifact_ref(
                self._root, "validation_gate",
                "validation/gate.json",
            ),
        ]

    def _publish_start_marker(
        self, *, permit: dict[str, object],
        transaction: str, unlock_head: str,
        command: tuple[str, ...], prior: str,
    ) -> None:
        marker = {
            "schema_version": "family3_v2_test_start_marker_v0",
            "boundary_sha256": self._boundary_sha256,
            "permit_sha256": _sha256_bytes(
                (self._root / "test_permit.json").read_bytes()
            ),
            "open_transaction_sha256": transaction,
            "unlock_ledger_head_sha256": unlock_head,
            "checkpoint_manifest_sha256": (
                permit["checkpoint_manifest_sha256"]
            ),
            "validation_gate_sha256": permit["validation_gate_sha256"],
            "qualifying_seed_ids": permit["qualifying_seed_ids"],
            "test_state": "OPENED",
            "command": list(command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
        }
        self._publish_immutable(
            "test/start_marker.json", _canonical(marker)
        )
        self._fault(
            "after_test_start_marker_publish", "test/start_marker.json"
        )

    def _verified_start_marker(self) -> dict[str, object]:
        marker = _read_exact_json(
            self._root / "test/start_marker.json",
            (
                "schema_version", "boundary_sha256", "permit_sha256",
                "open_transaction_sha256", "unlock_ledger_head_sha256",
                "checkpoint_manifest_sha256", "validation_gate_sha256",
                "qualifying_seed_ids", "test_state", "command",
                "prior_state_ledger_head_sha256", "transaction_sha256",
            ),
        )
        permit = self._verified_permit()
        unlock = self._unlock_records()
        if (
            not unlock
            or marker["schema_version"]
            != "family3_v2_test_start_marker_v0"
            or marker["boundary_sha256"] != self._boundary_sha256
            or marker["permit_sha256"]
            != _sha256_bytes(
                (self._root / "test_permit.json").read_bytes()
            )
            or marker["open_transaction_sha256"]
            != unlock[0]["payload"]["open_transaction_sha256"]
            or marker["unlock_ledger_head_sha256"]
            != unlock[0]["record_sha256"]
            or marker["checkpoint_manifest_sha256"]
            != permit["checkpoint_manifest_sha256"]
            or marker["validation_gate_sha256"]
            != permit["validation_gate_sha256"]
            or marker["qualifying_seed_ids"]
            != permit["qualifying_seed_ids"]
            or marker["test_state"] != "OPENED"
            or marker["transaction_sha256"]
            != marker["open_transaction_sha256"]
        ):
            raise ValueError("test start marker does not verify")
        return marker

    def open_test_once(
        self,
        *,
        resume: bool,
        command: tuple[str, ...],
    ) -> None:
        self._require_mutation()
        checked_command = self._command(command)
        if type(resume) is not bool:
            raise ValueError("resume must be an exact bool")
        if self._boundary.evidence_mode != "FORMAL":
            raise ValueError("test opening is forbidden in smoke mode")
        if (self._root / "test/result.json").exists():
            raise ValueError("test classification is already committed")
        permit = self._verified_permit()
        if resume:
            self._resume_test(permit, checked_command)
            return
        if self._state() != "READY_FOR_TEST":
            raise ValueError("fresh test open requires READY_FOR_TEST")
        if (
            (self._root / "test/start_marker.json").exists()
            or self._segment_numbers("test")
        ):
            raise ValueError("fresh test open requires sealed empty test state")
        prior = self._state_head()
        input_refs = self._open_inputs()
        transaction = self._transaction(
            "TEST_OPEN", coordinate=["test"], command=checked_command,
            input_refs=input_refs,
            input_values=[
                ["pre_open_test_ledger_head_sha256", _ZERO_HASH],
                ["qualifying_seed_ids", permit["qualifying_seed_ids"]],
            ], prior_head=prior,
        )
        unlock = self._unlock_records()
        if unlock:
            if (
                len(unlock) != 1
                or unlock[0]["payload"]["event_type"] != "OPEN"
                or unlock[0]["payload"]["transaction_sha256"]
                != transaction
                or unlock[0]["payload"]["command"]
                != list(checked_command)
                or unlock[0]["payload"]["prior_state_ledger_head_sha256"]
                != prior
            ):
                raise ValueError("orphan test-open event does not match retry")
            unlock_head = str(unlock[0]["record_sha256"])
        else:
            payload = {
                "event_type": "OPEN",
                "transaction_sha256": transaction,
                "open_transaction_sha256": transaction,
                "permit_sha256": input_refs[0][2],
                "checkpoint_manifest_sha256": input_refs[1][2],
                "validation_gate_sha256": input_refs[2][2],
                "qualifying_seed_ids": permit["qualifying_seed_ids"],
                "test_rows_ledger_head_sha256": _ZERO_HASH,
                "test_observed_row_count": 0,
                "test_missing_row_count": len(
                    self._expected_coordinates("test")
                ),
                "segment_refs": [],
                "command": list(checked_command),
                "prior_state_ledger_head_sha256": prior,
            }
            record = self._chain_record(
                "family3_v2_test_unlock_event_v0", 0, _ZERO_HASH, payload
            )
            self._append_jsonl(
                "test/unlock_ledger.jsonl", _canonical(record) + b"\n"
            )
            unlock_head = str(record["record_sha256"])
            self._fault(
                "after_test_open_event_fsync_before_marker",
                "test/unlock_ledger.jsonl",
            )
        self._publish_start_marker(
            permit=permit, transaction=transaction,
            unlock_head=unlock_head, command=checked_command, prior=prior,
        )
        self._append_state(
            event_type="TEST_OPEN", transaction_sha256=transaction,
            from_state="READY_FOR_TEST", to_state="TEST_OPENED",
            command=checked_command, completed_boundary=["TEST_OPENED"],
            artifacts=[
                _artifact_ref(
                    self._root, "test_permit", "test_permit.json"
                ),
                _artifact_ref(
                    self._root, "test_start_marker",
                    "test/start_marker.json",
                ),
            ],
            output_paths=[
                "test/unlock_ledger.jsonl", "test/start_marker.json"
            ],
            ledger_heads=[["test_unlock", unlock_head]],
            active_attempt=None,
            next_action="RUN_NEXT_MISSING_TEST_COORDINATE",
        )

    def _resume_test(
        self, permit: dict[str, object], command: tuple[str, ...],
    ) -> None:
        state = self._state()
        if state not in ("TEST_OPENED", "TEST_IN_PROGRESS"):
            raise ValueError("test resume requires an opened test")
        marker = self._verified_start_marker()
        records, rows, segment_refs = self._read_rows_internal(
            "test", use_cache=False
        )
        expected = self._expected_coordinates("test")
        present = {self._row_coordinate(row) for row in rows}
        missing_count = sum(
            coordinate not in present for coordinate in expected
        )
        prior = self._state_head()
        input_refs = [
            _artifact_ref(
                self._root, "permit", "test_permit.json"
            ),
            _artifact_ref(
                self._root, "start_marker", "test/start_marker.json"
            ),
            _artifact_ref(
                self._root, "checkpoint_set_manifest",
                "training/checkpoint_manifest.json",
            ),
            _artifact_ref(
                self._root, "validation_gate", "validation/gate.json"
            ),
        ]
        head = (
            _ZERO_HASH if not records
            else str(records[-1]["record_sha256"])
        )
        transaction = self._transaction(
            "TEST_RESUME", coordinate=["test"], command=command,
            input_refs=input_refs,
            input_values=[
                ["test_ledger_head_sha256", head],
                ["observed_row_count", len(rows)],
                ["missing_row_count", missing_count],
                ["segment_refs", list(segment_refs)],
            ], prior_head=prior,
        )
        unlock = self._unlock_records()
        previous = (
            _ZERO_HASH if not unlock
            else str(unlock[-1]["record_sha256"])
        )
        payload = {
            "event_type": "RESUME",
            "transaction_sha256": transaction,
            "open_transaction_sha256": marker["open_transaction_sha256"],
            "permit_sha256": input_refs[0][2],
            "checkpoint_manifest_sha256": input_refs[2][2],
            "validation_gate_sha256": input_refs[3][2],
            "qualifying_seed_ids": permit["qualifying_seed_ids"],
            "test_rows_ledger_head_sha256": head,
            "test_observed_row_count": len(rows),
            "test_missing_row_count": missing_count,
            "segment_refs": list(segment_refs),
            "command": list(command),
            "prior_state_ledger_head_sha256": prior,
        }
        unlock_record = self._chain_record(
            "family3_v2_test_unlock_event_v0",
            len(unlock), previous, payload,
        )
        self._append_jsonl(
            "test/unlock_ledger.jsonl",
            _canonical(unlock_record) + b"\n",
        )
        self._append_state(
            event_type="TEST_RESUME",
            transaction_sha256=transaction,
            from_state=state, to_state=state, command=command,
            completed_boundary=["TEST_OPENED"], artifacts=[],
            output_paths=["test/unlock_ledger.jsonl"],
            ledger_heads=[
                ["test_unlock", unlock_record["record_sha256"]],
                ["test_rows", head],
            ],
            active_attempt=None,
            next_action=(
                "COMMIT_FINAL_VERDICT"
                if missing_count == 0
                else "RUN_NEXT_MISSING_TEST_COORDINATE"
            ),
        )

    def missing_test_coordinates(
        self,
    ) -> tuple[EvaluationCoordinate, ...]:
        if self._boundary.evidence_mode != "FORMAL":
            raise ValueError("test coordinates are forbidden in smoke mode")
        if self._state() not in ("TEST_OPENED", "TEST_IN_PROGRESS"):
            raise ValueError("test coordinates require an opened test")
        self._verified_start_marker()
        if (self._root / "test/result.json").exists():
            raise ValueError("test classification is already committed")
        rows = self.load_verified_rows("test")
        present = {self._row_coordinate(row) for row in rows}
        return tuple(
            coordinate
            for coordinate in self._expected_coordinates("test")
            if coordinate not in present
        )

    @staticmethod
    def _null_ref(logical_name: str) -> list[object]:
        return [logical_name, None, None, None]

    def _optional_artifact_ref(
        self, logical_name: str, relative: str,
    ) -> list[object]:
        path = self._root / relative
        if not path.exists():
            return self._null_ref(logical_name)
        return _artifact_ref(self._root, logical_name, relative)

    def _publish_test_classification(
        self, result: TestClassificationResult,
        command: tuple[str, ...],
    ) -> None:
        state = self._state()
        if state not in ("TEST_OPENED", "TEST_IN_PROGRESS", "TEST_CLASSIFIED"):
            raise ValueError("state does not allow test classification")
        manifest, _ = self._rows_manifest(
            "test", completion_claimed=result.phase_complete
        )
        manifest_bytes = _canonical(manifest)
        result_bytes = _canonical(_test_mapping(result))
        manifest_hash = _sha256_bytes(manifest_bytes)
        paired_bytes, hard_bytes = self._phase_projection_bytes(
            "test", manifest_hash, result
        )
        if state == "TEST_CLASSIFIED":
            # The classification is already sealed; only the final verdict is
            # missing. Verify its bytes and ledger binding, never republish it.
            expected = (
                ("test_rows_manifest", "test/rows_manifest.json", manifest_bytes),
                ("test_result", "test/result.json", result_bytes),
                ("test_paired_comparison", "test/paired_comparison.json", paired_bytes),
                ("test_hard_integrity", "test/hard_integrity.json", hard_bytes),
            )
            refs = []
            for name, relative, content in expected:
                if _path_within(self._root, relative, final_file=True).read_bytes() != content:
                    raise ValueError("sealed test classification differs from verified rows")
                refs.append(_artifact_ref(self._root, name, relative))
            records, _, _ = self._read_rows_internal("test", use_cache=False)
            payload = self._state_records()[-1]["payload"]
            if (payload["event_type"] != "TEST_CLASSIFICATION"
                    or payload["completed_boundary"] != ["TEST_CLASSIFIED", result.classification]
                    or payload["artifacts"] != refs
                    or payload["ledger_heads"] != [["test_rows", _ZERO_HASH if not records else records[-1]["record_sha256"]]]):
                raise ValueError("sealed test classification ledger binding is invalid")
            return
        self._publish_immutable("test/rows_manifest.json", manifest_bytes)
        self._publish_immutable("test/result.json", result_bytes)
        self._fault("after_test_result_publish", "test/result.json")
        self._publish_immutable(
            "test/paired_comparison.json", paired_bytes
        )
        self._publish_immutable("test/hard_integrity.json", hard_bytes)
        prior = self._state_head()
        refs = [
            _artifact_ref(
                self._root, "start_marker", "test/start_marker.json"
            ),
            _artifact_ref(
                self._root, "test_rows_manifest",
                "test/rows_manifest.json",
            ),
            _artifact_ref(
                self._root, "test_result", "test/result.json"
            ),
            _artifact_ref(
                self._root, "test_paired_comparison",
                "test/paired_comparison.json",
            ),
            _artifact_ref(
                self._root, "test_hard_integrity",
                "test/hard_integrity.json",
            ),
        ]
        transaction = self._transaction(
            "TEST_CLASSIFICATION", coordinate=["test"], command=command,
            input_refs=refs,
            input_values=[
                ["phase_complete", result.phase_complete],
                ["classification", result.classification],
                ["observed_row_count", result.observed_row_count],
            ], prior_head=prior,
        )
        records, _, _ = self._read_rows_internal(
            "test", use_cache=False
        )
        self._append_state(
            event_type="TEST_CLASSIFICATION",
            transaction_sha256=transaction,
            from_state=state, to_state="TEST_CLASSIFIED",
            command=command,
            completed_boundary=[
                "TEST_CLASSIFIED", result.classification
            ],
            artifacts=refs[1:],
            output_paths=[
                "test/rows_manifest.json", "test/result.json",
                "test/paired_comparison.json",
                "test/hard_integrity.json",
            ],
            ledger_heads=[[
                "test_rows",
                _ZERO_HASH if not records
                else records[-1]["record_sha256"],
            ]],
            active_attempt=None, next_action="COMMIT_FINAL_VERDICT",
        )

    def commit_final_verdict(
        self,
        result: TestClassificationResult,
        *,
        command: tuple[str, ...],
    ) -> None:
        self._require_mutation()
        checked_command = self._command(command)
        if type(result) is not TestClassificationResult:
            raise ValueError("test result has the wrong exact type")
        validation, _ = self._stored_validation()
        permit_ids: tuple[int, ...] = ()
        opened = False
        rows: tuple[EvaluationEpisodeRow, ...] = ()
        if self._boundary.evidence_mode == "NON_EVIDENCE_SMOKE":
            if (
                validation.phase_complete
                or validation.status is not None
                or (self._root / "test_permit.json").exists()
                or (self._root / "test").exists()
            ):
                raise ValueError("smoke verdict evidence is invalid")
            expected = classify_test_result(
                self._config, (),
                validation_gate=validation, permitted_seed_ids=(),
                test_opened=False, phase_complete=False,
            )
            if result != expected or result.classification is not None:
                raise ValueError("smoke result differs from Task 4")
            run_status = "NON_EVIDENCE_SMOKE_COMPLETE"
            scientific: str | None = None
        else:
            if validation.status == "READY_FOR_TEST":
                permit = self._verified_permit()
                permit_ids = tuple(permit["qualifying_seed_ids"])
                opened = (self._root / "test/start_marker.json").exists()
                if opened:
                    self._verified_start_marker()
                    rows = self.load_verified_rows("test")
                expected = classify_test_result(
                    self._config, rows,
                    validation_gate=validation,
                    permitted_seed_ids=permit_ids,
                    test_opened=opened,
                    phase_complete=result.phase_complete,
                )
            elif validation.status in ("INVALID_RUN", "NO_TEST"):
                if (
                    (self._root / "test_permit.json").exists()
                    or (self._root / "test").exists()
                ):
                    raise ValueError("closed validation has test artifacts")
                expected = classify_test_result(
                    self._config, (),
                    validation_gate=validation, permitted_seed_ids=(),
                    test_opened=False, phase_complete=False,
                )
            else:
                raise ValueError("formal validation status is not terminal-ready")
            if result != expected:
                raise ValueError("test result differs from Task 4")
            if result.classification is None:
                return
            run_status = result.classification
            scientific = result.classification
            if opened:
                self._publish_test_classification(
                    result, checked_command
                )
        prior = self._state_head()
        refs = [
            _artifact_ref(
                self._root, "validation_gate", "validation/gate.json"
            ),
            self._optional_artifact_ref("permit", "test_permit.json"),
            self._optional_artifact_ref(
                "start_marker", "test/start_marker.json"
            ),
            self._optional_artifact_ref(
                "test_rows_manifest", "test/rows_manifest.json"
            ),
            self._optional_artifact_ref(
                "test_result", "test/result.json"
            ),
            self._optional_artifact_ref(
                "test_paired_comparison",
                "test/paired_comparison.json",
            ),
            self._optional_artifact_ref(
                "test_hard_integrity", "test/hard_integrity.json"
            ),
            self._null_ref("failure"),
        ]
        transaction = self._transaction(
            "FINAL_VERDICT", coordinate=["final_verdict"],
            command=checked_command, input_refs=refs,
            input_values=[
                ["run_status", run_status],
                ["scientific_classification", scientific],
                ["next_action", "NO_FURTHER_ACTION"],
            ], prior_head=prior,
        )
        verdict = {
            "schema_version": "family3_v2_pilot_final_verdict_v0",
            "boundary_sha256": self._boundary_sha256,
            "evidence_mode": self._boundary.evidence_mode,
            "run_status": run_status,
            "scientific_classification": scientific,
            "validation_gate_sha256": refs[0][2],
            "test_permit_sha256": refs[1][2],
            "test_start_marker_sha256": refs[2][2],
            "test_rows_manifest_sha256": refs[3][2],
            "test_result_sha256": refs[4][2],
            "test_paired_comparison_sha256": refs[5][2],
            "test_hard_integrity_sha256": refs[6][2],
            "failure_sha256": None,
            "command": list(checked_command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
            "next_action": "NO_FURTHER_ACTION",
        }
        self._publish_immutable(
            "final_verdict.json", _canonical(verdict)
        )
        self._fault(
            "after_final_verdict_publish", "final_verdict.json"
        )
        if run_status == "NON_EVIDENCE_SMOKE_COMPLETE":
            terminal_state = "FINAL_NON_EVIDENCE_SMOKE_COMPLETE"
        else:
            terminal_state = f"FINAL_{run_status}"
        self._append_state(
            event_type="FINAL_VERDICT",
            transaction_sha256=transaction,
            from_state=self._state(), to_state=terminal_state,
            command=checked_command,
            completed_boundary=["FINAL", run_status],
            artifacts=refs + [
                _artifact_ref(
                    self._root, "final_verdict", "final_verdict.json"
                )
            ],
            output_paths=["final_verdict.json"], ledger_heads=[],
            active_attempt=None, next_action="NO_FURTHER_ACTION",
        )

    def _commit_operational_failure(
        self, failure: dict[str, object], failure_relative: str,
        command: tuple[str, ...],
    ) -> None:
        prior = self._state_head()
        run_status = (
            "INVALID_RUN"
            if self._boundary.evidence_mode == "FORMAL"
            else "NON_EVIDENCE_SMOKE_FAILED"
        )
        scientific = (
            "INVALID_RUN"
            if self._boundary.evidence_mode == "FORMAL" else None
        )
        refs = [
            self._optional_artifact_ref(
                "validation_gate", "validation/gate.json"
            ),
            self._optional_artifact_ref("permit", "test_permit.json"),
            self._optional_artifact_ref(
                "start_marker", "test/start_marker.json"
            ),
            self._optional_artifact_ref(
                "test_rows_manifest", "test/rows_manifest.json"
            ),
            self._optional_artifact_ref(
                "test_result", "test/result.json"
            ),
            self._optional_artifact_ref(
                "test_paired_comparison",
                "test/paired_comparison.json",
            ),
            self._optional_artifact_ref(
                "test_hard_integrity", "test/hard_integrity.json"
            ),
            _artifact_ref(
                self._root, "failure", failure_relative
            ),
        ]
        transaction = self._transaction(
            "FINAL_VERDICT", coordinate=["final_verdict"],
            command=command, input_refs=refs,
            input_values=[
                ["run_status", run_status],
                ["scientific_classification", scientific],
                ["next_action", "NO_FURTHER_ACTION"],
            ], prior_head=prior,
        )
        verdict = {
            "schema_version": "family3_v2_pilot_final_verdict_v0",
            "boundary_sha256": self._boundary_sha256,
            "evidence_mode": self._boundary.evidence_mode,
            "run_status": run_status,
            "scientific_classification": scientific,
            "validation_gate_sha256": refs[0][2],
            "test_permit_sha256": refs[1][2],
            "test_start_marker_sha256": refs[2][2],
            "test_rows_manifest_sha256": refs[3][2],
            "test_result_sha256": refs[4][2],
            "test_paired_comparison_sha256": refs[5][2],
            "test_hard_integrity_sha256": refs[6][2],
            "failure_sha256": refs[7][2],
            "command": list(command),
            "prior_state_ledger_head_sha256": prior,
            "transaction_sha256": transaction,
            "next_action": "NO_FURTHER_ACTION",
        }
        self._publish_immutable(
            "final_verdict.json", _canonical(verdict)
        )
        self._fault(
            "after_final_verdict_publish", "final_verdict.json"
        )
        terminal = (
            "FINAL_INVALID_RUN"
            if self._boundary.evidence_mode == "FORMAL"
            else "FINAL_NON_EVIDENCE_SMOKE_FAILED"
        )
        self._append_state(
            event_type="FINAL_VERDICT",
            transaction_sha256=transaction,
            from_state=self._state(), to_state=terminal,
            command=command, completed_boundary=["FINAL", run_status],
            artifacts=refs + [
                _artifact_ref(
                    self._root, "final_verdict", "final_verdict.json"
                )
            ],
            output_paths=[failure_relative, "final_verdict.json"],
            ledger_heads=[], active_attempt=None,
            next_action="NO_FURTHER_ACTION",
        )


__all__ = [
    "PathLike",
    "EvaluationCoordinate",
    "CheckpointLearner",
    "DuplicateCoordinateError",
    "ConflictingCoordinateError",
    "PilotBoundary",
    "FinalCheckpointRef",
    "Family3V2PilotArtifactStore",
]
