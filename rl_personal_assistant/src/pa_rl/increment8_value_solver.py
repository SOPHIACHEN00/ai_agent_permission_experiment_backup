"""Disk-backed exact Bellman solver for the fixed Increment 8 v1 calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import platform
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Protocol

from .contracts import canonical_hash
from .increment8_model import (
    LifecycleModel,
    LifecycleState,
    LifecycleTask,
    WorkloadBranch,
    _carrier_index,
    _shift,
)
from .increment8_suite import (
    INCREMENT8_SUITE_VERSION,
    LifecycleGraphSpec,
    LikelihoodLevel,
    _CARRIERS,
    build_increment8_suite,
)


VALUE_SOLVER_VERSION = "disk_backed_value_first_exact_dp_v1"
VALUE_CACHE_SCHEMA_VERSION = "exact_value_cache_v1"
S3_V9_CALIBRATION_VERSION = "increment8_v1_s3_v9_exposure_plus8_v1"
S3_V9_ORACLE_FLOOR = Fraction(3, 5)
S3_V9_STATE_LIMIT = 1_000_000
S3_V9_MEMORY_CACHE_SIZE = 4_096
S3_V9_CHECKPOINT_INTERVAL = 1_000
_PICKLE_PROTOCOL = 5


class _CandidateLike(Protocol):
    semantic_candidate_id: str
    mask_valid: bool


class _TransitionLike(Protocol):
    probability: Fraction
    next_state: object


class _ExactModelLike(Protocol):
    def candidates(self, state: object) -> tuple[_CandidateLike, ...]: ...

    def transition_distribution(
        self,
        state: object,
        semantic_candidate_id: str,
    ) -> tuple[_TransitionLike, ...]: ...


class ExactStateLimitExceeded(RuntimeError):
    """Raised before the disk cache can exceed the declared state ceiling."""


@dataclass(frozen=True, slots=True)
class ExactValueResult:
    value: Fraction
    total_cached_states: int
    states_added: int
    memory_cache_hits: int
    disk_cache_hits: int
    peak_memory_cache_entries: int
    max_recursion_depth: int


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class DiskBackedExactValueSolver:
    """Compute an undiscounted exact Bellman value without retaining the graph.

    Solved values live in a signature-bound SQLite cache. Only a fixed-size
    in-memory LRU, the current recursion stack, and one action's successors are
    retained in RAM.
    """

    def __init__(
        self,
        model: _ExactModelLike,
        *,
        cache_path: Path,
        cache_signature: str,
        state_limit: int,
        memory_cache_size: int,
        checkpoint_path: Path | None = None,
        checkpoint_interval: int = 1_000,
    ) -> None:
        if not isinstance(cache_signature, str) or not cache_signature:
            raise ValueError("cache signature must be non-empty text")
        for name, value in (
            ("state_limit", state_limit),
            ("memory_cache_size", memory_cache_size),
            ("checkpoint_interval", checkpoint_interval),
        ):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be an exact positive integer")
        if not isinstance(cache_path, Path):
            raise ValueError("cache_path must be pathlib.Path")
        if checkpoint_path is not None and not isinstance(checkpoint_path, Path):
            raise ValueError("checkpoint_path must be pathlib.Path or None")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._model = model
        self._cache_path = cache_path
        self._cache_signature = cache_signature
        self._state_limit = state_limit
        self._memory_cache_size = memory_cache_size
        self._checkpoint_path = checkpoint_path
        self._checkpoint_interval = checkpoint_interval
        self._connection = sqlite3.connect(cache_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._connection.execute("PRAGMA temp_store=FILE")
        self._connection.execute("PRAGMA cache_size=-8192")
        self._connection.execute("PRAGMA wal_autocheckpoint=1000")
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exact_values (
                state_key BLOB PRIMARY KEY,
                guard_key BLOB NOT NULL,
                numerator TEXT NOT NULL,
                denominator TEXT NOT NULL
            ) WITHOUT ROWID
            """
        )
        existing = self._connection.execute(
            "SELECT value FROM metadata WHERE key = 'cache_signature'"
        ).fetchone()
        existing_value_count = self._count_rows()
        if existing is None:
            if existing_value_count != 0:
                self._connection.close()
                raise ValueError(
                    "unsigned non-empty exact value cache is not trusted"
                )
            self._connection.execute(
                "INSERT INTO metadata(key, value) VALUES('cache_signature', ?)",
                (cache_signature,),
            )
            self._connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('solver_version', ?)",
                (VALUE_SOLVER_VERSION,),
            )
            self._connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
                (VALUE_CACHE_SCHEMA_VERSION,),
            )
            self._connection.commit()
        else:
            if existing[0] != cache_signature:
                self._connection.close()
                raise ValueError(
                    "cache signature does not match the requested exact kernel"
                )
            stored_solver_version = self._connection.execute(
                "SELECT value FROM metadata WHERE key = 'solver_version'"
            ).fetchone()
            if (
                stored_solver_version is None
                or stored_solver_version[0] != VALUE_SOLVER_VERSION
            ):
                self._connection.close()
                raise ValueError("cache solver version is missing or incompatible")
            stored_schema_version = self._connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if (
                stored_schema_version is None
                or stored_schema_version[0] != VALUE_CACHE_SCHEMA_VERSION
            ):
                self._connection.close()
                raise ValueError("cache schema version is missing or incompatible")

        self._initial_cached_states = existing_value_count
        if self._initial_cached_states > state_limit:
            self._connection.close()
            raise ExactStateLimitExceeded(
                "existing exact cache exceeds the declared state limit"
            )
        self._total_cached_states = self._initial_cached_states
        self._states_added = 0
        self._memory_cache_hits = 0
        self._disk_cache_hits = 0
        self._pending_writes = 0
        self._memory_cache: OrderedDict[bytes, tuple[bytes, Fraction]] = OrderedDict()
        self._active_keys: set[bytes] = set()
        self._peak_memory_cache_entries = 0
        self._max_recursion_depth = 0
        self._closed = False
        self._last_status = "READY"

    def __enter__(self) -> "DiskBackedExactValueSolver":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._connection.commit()
        self._connection.close()
        self._closed = True

    def _count_rows(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) FROM exact_values").fetchone()
        assert row is not None
        return int(row[0])

    @staticmethod
    def _state_keys(state: object) -> tuple[bytes, bytes]:
        serialized = pickle.dumps(state, protocol=_PICKLE_PROTOCOL)
        return (
            hashlib.sha256(serialized).digest(),
            hashlib.blake2b(serialized, digest_size=16).digest(),
        )

    def _remember(self, state_key: bytes, guard_key: bytes, value: Fraction) -> None:
        self._memory_cache[state_key] = (guard_key, value)
        self._memory_cache.move_to_end(state_key)
        while len(self._memory_cache) > self._memory_cache_size:
            self._memory_cache.popitem(last=False)
        self._peak_memory_cache_entries = max(
            self._peak_memory_cache_entries,
            len(self._memory_cache),
        )

    def _lookup(self, state_key: bytes, guard_key: bytes) -> Fraction | None:
        memory = self._memory_cache.get(state_key)
        if memory is not None:
            if memory[0] != guard_key:
                raise RuntimeError("exact state-key collision detected in memory cache")
            self._memory_cache_hits += 1
            self._memory_cache.move_to_end(state_key)
            return memory[1]
        row = self._connection.execute(
            "SELECT guard_key, numerator, denominator FROM exact_values WHERE state_key = ?",
            (state_key,),
        ).fetchone()
        if row is None:
            return None
        stored_guard = bytes(row[0])
        if stored_guard != guard_key:
            raise RuntimeError("exact state-key collision detected in disk cache")
        value = Fraction(int(row[1]), int(row[2]))
        self._disk_cache_hits += 1
        self._remember(state_key, guard_key, value)
        return value

    def _store(self, state_key: bytes, guard_key: bytes, value: Fraction) -> None:
        if self._total_cached_states >= self._state_limit:
            raise ExactStateLimitExceeded(
                f"exact value state limit reached ({self._state_limit})"
            )
        cursor = self._connection.execute(
            """
            INSERT INTO exact_values(state_key, guard_key, numerator, denominator)
            VALUES(?, ?, ?, ?)
            """,
            (
                state_key,
                guard_key,
                str(value.numerator),
                str(value.denominator),
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("exact value cache insert did not add one state")
        self._total_cached_states += 1
        self._states_added += 1
        self._pending_writes += 1
        self._remember(state_key, guard_key, value)
        if self._pending_writes >= self._checkpoint_interval:
            self._flush("IN_PROGRESS")

    def _checkpoint_mapping(self, status: str) -> dict[str, object]:
        return {
            "solver_version": VALUE_SOLVER_VERSION,
            "cache_signature": self._cache_signature,
            "status": status,
            "updated_at": _utc_now(),
            "cache_path": str(self._cache_path.resolve()),
            "state_limit": self._state_limit,
            "memory_cache_size": self._memory_cache_size,
            "total_cached_states": self._total_cached_states,
            "states_added_this_process": self._states_added,
            "memory_cache_hits": self._memory_cache_hits,
            "disk_cache_hits": self._disk_cache_hits,
            "peak_memory_cache_entries": self._peak_memory_cache_entries,
            "max_recursion_depth": self._max_recursion_depth,
        }

    def _flush(self, status: str) -> None:
        self._connection.commit()
        self._pending_writes = 0
        self._last_status = status
        if self._checkpoint_path is not None:
            _atomic_json(self._checkpoint_path, self._checkpoint_mapping(status))

    def _value(self, state: object, depth: int) -> Fraction:
        state_key, guard_key = self._state_keys(state)
        cached = self._lookup(state_key, guard_key)
        if cached is not None:
            return cached
        if state_key in self._active_keys:
            raise ValueError("exact value solver requires an acyclic state graph")
        self._active_keys.add(state_key)
        self._max_recursion_depth = max(self._max_recursion_depth, depth)
        try:
            terminated = getattr(state, "terminated", None)
            if type(terminated) is not bool:
                raise ValueError("exact state must expose a boolean terminated property")
            if terminated:
                reward = getattr(state, "reward", None)
                if type(reward) is not int or reward not in {0, 1}:
                    raise ValueError("terminal exact reward must be the integer 0 or 1")
                result = Fraction(reward)
            else:
                action_values: list[Fraction] = []
                for candidate in self._model.candidates(state):
                    if type(candidate.mask_valid) is not bool:
                        raise ValueError("candidate mask flag must be boolean")
                    if not candidate.mask_valid:
                        continue
                    semantic_id = candidate.semantic_candidate_id
                    if not isinstance(semantic_id, str) or not semantic_id:
                        raise ValueError("candidate semantic ID must be non-empty text")
                    transitions = self._model.transition_distribution(
                        state,
                        semantic_id,
                    )
                    if not isinstance(transitions, tuple) or not transitions:
                        raise ValueError("valid action must have a non-empty transition tuple")
                    probability_sum = Fraction()
                    action_value = Fraction()
                    for transition in transitions:
                        probability = transition.probability
                        if not isinstance(probability, Fraction) or probability <= 0:
                            raise ValueError("exact transition probability must be positive Fraction")
                        probability_sum += probability
                        action_value += probability * self._value(
                            transition.next_state,
                            depth + 1,
                        )
                    if probability_sum != 1:
                        raise ValueError("exact transition probabilities must sum to one")
                    action_values.append(action_value)
                if not action_values:
                    raise ValueError("reachable nonterminal state has no valid candidate")
                result = max(action_values)
            self._store(state_key, guard_key, result)
            return result
        finally:
            self._active_keys.remove(state_key)

    def solve(self, initial_state: object) -> ExactValueResult:
        if self._closed:
            raise ValueError("exact value solver is closed")
        try:
            value = self._value(initial_state, 1)
        except BaseException:
            self._flush("BLOCKED")
            raise
        self._flush("SOLVED")
        return ExactValueResult(
            value=value,
            total_cached_states=self._total_cached_states,
            states_added=self._states_added,
            memory_cache_hits=self._memory_cache_hits,
            disk_cache_hits=self._disk_cache_hits,
            peak_memory_cache_entries=self._peak_memory_cache_entries,
            max_recursion_depth=self._max_recursion_depth,
        )


class _ClockFixedCalibrationModel(LifecycleModel):
    """Calibration-only v0 model with the approved committed-effect clock fix."""

    @staticmethod
    def _next_task(
        state: LifecycleState,
        branch: WorkloadBranch,
    ) -> tuple[LifecycleTask, LikelihoodLevel, LikelihoodLevel]:
        current = state.task
        next_workload_transition_index = len(state.credited_task_ordinals) + 1
        if current.ordinal != next_workload_transition_index:
            raise ValueError("calibration workload-index invariant is violated")
        if branch is WorkloadBranch.EXACT:
            scope = current.scope
            utility = current.utility
            sensitivity = current.sensitivity
            reuse = _shift(state.reuse_likelihood, 1)
            scope_change = _shift(state.scope_change_likelihood, -1)
        elif branch is WorkloadBranch.BROADER:
            carrier = _CARRIERS[_carrier_index(current.scope)]
            scope = carrier.scope(current.scope.purpose, broader=True)
            utility = min(3, current.utility + 1)
            sensitivity = min(3, current.sensitivity + 1)
            reuse = _shift(state.reuse_likelihood, -1)
            scope_change = _shift(state.scope_change_likelihood, 1)
        else:
            carrier = _CARRIERS[
                (_carrier_index(current.scope) + 1) % len(_CARRIERS)
            ]
            scope = carrier.scope(current.scope.purpose)
            utility = 1 + (
                (current.utility + next_workload_transition_index) % 3
            )
            sensitivity = carrier.sensitivity
            reuse = LikelihoodLevel.MEDIUM
            scope_change = LikelihoodLevel.HIGH
        return (
            LifecycleTask(state.next_task_ordinal, scope, utility, sensitivity),
            reuse,
            scope_change,
        )


def _fixed_s3_v9_graph() -> LifecycleGraphSpec:
    suite = build_increment8_suite()
    graph = next(
        member.graph
        for member in suite.members
        if member.graph.graph_id == "i8_s3_v9"
    )
    expected = (graph.prompt_budget, graph.exposure_budget, graph.utility_target, graph.horizon)
    if expected != (3, 16, 7, 12):
        raise ValueError("frozen v0 s3_v9 parameters changed unexpectedly")
    return replace(graph, exposure_budget=24)


def _calibration_signature(graph: LifecycleGraphSpec) -> str:
    source_directory = Path(__file__).resolve().parent
    return canonical_hash(
        {
            "solver_version": VALUE_SOLVER_VERSION,
            "calibration_version": S3_V9_CALIBRATION_VERSION,
            "base_suite_version": INCREMENT8_SUITE_VERSION,
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "pickle_protocol": _PICKLE_PROTOCOL,
            "source_sha256": {
                "solver": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "model": hashlib.sha256(
                    (source_directory / "increment8_model.py").read_bytes()
                ).hexdigest(),
                "suite": hashlib.sha256(
                    (source_directory / "increment8_suite.py").read_bytes()
                ).hexdigest(),
                "outcome": hashlib.sha256(
                    (source_directory / "increment8_outcome.py").read_bytes()
                ).hexdigest(),
                "contracts": hashlib.sha256(
                    (source_directory / "contracts.py").read_bytes()
                ).hexdigest(),
                "scope_matching": hashlib.sha256(
                    (source_directory / "scope_matching.py").read_bytes()
                ).hexdigest(),
            },
            "clock_semantics": "next_committed_effect_index",
            "family_formula": "family3_exposure_v1_equals_v0_plus_8",
            "graph": graph.as_mapping(),
            "oracle_floor": {
                "numerator": S3_V9_ORACLE_FLOOR.numerator,
                "denominator": S3_V9_ORACLE_FLOOR.denominator,
            },
        }
    )


def run_fixed_s3_v9_calibration(output_directory: Path) -> dict[str, object]:
    if not isinstance(output_directory, Path):
        raise ValueError("output_directory must be pathlib.Path")
    output_directory.mkdir(parents=True, exist_ok=True)
    graph = _fixed_s3_v9_graph()
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

    status = (
        "CERTIFIED_PASS"
        if result.value >= S3_V9_ORACLE_FLOOR
        else "CERTIFIED_FAIL"
    )
    certificate: dict[str, object] = {
        "calibration_version": S3_V9_CALIBRATION_VERSION,
        "solver_version": VALUE_SOLVER_VERSION,
        "status": status,
        "completed_at": _utc_now(),
        "cache_signature": signature,
        "base_suite_version": INCREMENT8_SUITE_VERSION,
        "graph_id": graph.graph_id,
        "graph_hash": canonical_hash(graph.as_mapping()),
        "clock_semantics": "next_committed_effect_index",
        "parameter_change": {
            "family": 3,
            "prompt_budget": 3,
            "exposure_budget_v0": 16,
            "exposure_budget_candidate": 24,
            "utility_target": 7,
            "horizon": 12,
        },
        "oracle_value": {
            "numerator": result.value.numerator,
            "denominator": result.value.denominator,
        },
        "oracle_floor": {
            "numerator": S3_V9_ORACLE_FLOOR.numerator,
            "denominator": S3_V9_ORACLE_FLOOR.denominator,
        },
        "threshold_pass": result.value >= S3_V9_ORACLE_FLOOR,
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
        description="Resume or run the single frozen Increment 8 s3_v9 exact calibration."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/increment8_v1_s3_v9_calibration"),
    )
    arguments = parser.parse_args(argv)
    certificate = run_fixed_s3_v9_calibration(arguments.output)
    print(json.dumps(certificate, ensure_ascii=False, sort_keys=True))
    return 0 if certificate["status"] == "CERTIFIED_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DiskBackedExactValueSolver",
    "ExactStateLimitExceeded",
    "ExactValueResult",
    "run_fixed_s3_v9_calibration",
]
