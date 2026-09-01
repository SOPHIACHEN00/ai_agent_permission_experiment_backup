"""Isolated exact-DP diagnostic that never caches terminal states.

This module intentionally leaves the frozen Increment 8 solver and its caches
untouched.  Its numeric row limit applies only to distinct nonterminal Bellman
states; terminal rewards are validated and returned before key construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import platform
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Protocol

from .contracts import canonical_hash
from .increment8_suite import INCREMENT8_SUITE_VERSION, LifecycleGraphSpec
from .increment8_v1_preflight import (
    CLOCK_SEMANTICS,
    FAMILY_FORMULA,
    ORACLE_FLOOR,
    build_v1_strategic_graphs,
)
from .increment8_value_solver import _ClockFixedCalibrationModel, _PICKLE_PROTOCOL


TERMINAL_BYPASS_SOLVER_VERSION = "disk_backed_nonterminal_cache_exact_dp_v1"
NONTERMINAL_CACHE_SCHEMA_VERSION = "nonterminal_exact_value_cache_v1"
TERMINAL_CACHE_DIAGNOSTIC_VERSION = (
    "increment8_v1_terminal_cache_bypass_diagnostic_v1"
)
ACCOUNTING_DOMAIN = "nonterminal_bellman_states"
NONTERMINAL_CACHE_ROW_LIMIT = 1_000_000
MEMORY_CACHE_SIZE = 4_096
CHECKPOINT_INTERVAL = 1_000
_ALLOWED_GRAPH_IDS = ("i8_s3_v5", "i8_s3_v3", "i8_s3_v4")
_CONTROL_VALUES = {
    "i8_s3_v5": Fraction(1),
    "i8_s3_v3": Fraction(13, 25),
}


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


class NonterminalCacheRowLimitExceeded(RuntimeError):
    """Raised before the cache can exceed its nonterminal-row limit."""


@dataclass(frozen=True, slots=True)
class NonterminalExactValueResult:
    value: Fraction
    cached_nonterminal_states: int
    nonterminal_states_added: int
    terminal_returns: int
    value_calls: int
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


class NonterminalCacheExactValueSolver:
    """Disk-backed exact Bellman solver with terminal-cache bypass."""

    def __init__(
        self,
        model: _ExactModelLike,
        *,
        cache_path: Path,
        cache_signature: str,
        nonterminal_cache_row_limit: int,
        memory_cache_size: int,
        checkpoint_path: Path | None = None,
        checkpoint_interval: int = 1_000,
    ) -> None:
        if not isinstance(cache_signature, str) or not cache_signature:
            raise ValueError("cache signature must be non-empty text")
        for name, value in (
            ("nonterminal_cache_row_limit", nonterminal_cache_row_limit),
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
        existing_database = cache_path.is_file() and cache_path.stat().st_size > 0
        connection = sqlite3.connect(cache_path)
        try:
            if existing_database:
                self._validate_existing_database(connection, cache_signature)
            else:
                self._create_database(connection, cache_signature)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA temp_store=FILE")
            connection.execute("PRAGMA cache_size=-8192")
            connection.execute("PRAGMA wal_autocheckpoint=1000")
            existing_row_count = self._count_rows(connection)
        except BaseException:
            connection.close()
            raise

        if existing_row_count > nonterminal_cache_row_limit:
            connection.close()
            raise NonterminalCacheRowLimitExceeded(
                "existing nonterminal cache exceeds the declared row limit"
            )
        self._model = model
        self._cache_path = cache_path
        self._cache_signature = cache_signature
        self._nonterminal_cache_row_limit = nonterminal_cache_row_limit
        self._memory_cache_size = memory_cache_size
        self._checkpoint_path = checkpoint_path
        self._checkpoint_interval = checkpoint_interval
        self._connection = connection
        self._cached_nonterminal_states = existing_row_count
        self._nonterminal_states_added = 0
        self._terminal_returns = 0
        self._value_calls = 0
        self._memory_cache_hits = 0
        self._disk_cache_hits = 0
        self._pending_writes = 0
        self._memory_cache: OrderedDict[bytes, tuple[bytes, Fraction]] = OrderedDict()
        self._active_keys: set[bytes] = set()
        self._peak_memory_cache_entries = 0
        self._max_recursion_depth = 0
        self._closed = False

    @staticmethod
    def _metadata(connection: sqlite3.Connection) -> dict[str, str]:
        return dict(connection.execute("SELECT key, value FROM metadata"))

    @classmethod
    def _validate_existing_database(
        cls,
        connection: sqlite3.Connection,
        cache_signature: str,
    ) -> None:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not {"metadata", "nonterminal_exact_values"} <= table_names:
            raise ValueError("cache schema is missing or incompatible")
        metadata = cls._metadata(connection)
        if metadata.get("cache_signature") != cache_signature:
            raise ValueError(
                "cache signature does not match the requested exact kernel"
            )
        if metadata.get("solver_version") != TERMINAL_BYPASS_SOLVER_VERSION:
            raise ValueError("cache solver version is missing or incompatible")
        if metadata.get("schema_version") != NONTERMINAL_CACHE_SCHEMA_VERSION:
            raise ValueError("cache schema version is missing or incompatible")
        if metadata.get("accounting_domain") != ACCOUNTING_DOMAIN:
            raise ValueError("cache accounting domain is missing or incompatible")

    @staticmethod
    def _create_database(
        connection: sqlite3.Connection,
        cache_signature: str,
    ) -> None:
        connection.execute(
            "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            """
            CREATE TABLE nonterminal_exact_values (
                state_key BLOB PRIMARY KEY,
                guard_key BLOB NOT NULL,
                numerator TEXT NOT NULL,
                denominator TEXT NOT NULL
            ) WITHOUT ROWID
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES(?, ?)",
            (
                ("cache_signature", cache_signature),
                ("solver_version", TERMINAL_BYPASS_SOLVER_VERSION),
                ("schema_version", NONTERMINAL_CACHE_SCHEMA_VERSION),
                ("accounting_domain", ACCOUNTING_DOMAIN),
            ),
        )
        connection.commit()

    @staticmethod
    def _count_rows(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT COUNT(*) FROM nonterminal_exact_values"
        ).fetchone()
        assert row is not None
        return int(row[0])

    def __enter__(self) -> "NonterminalCacheExactValueSolver":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._connection.commit()
        self._connection.close()
        self._closed = True

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
            """
            SELECT guard_key, numerator, denominator
            FROM nonterminal_exact_values
            WHERE state_key = ?
            """,
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
        if self._cached_nonterminal_states >= self._nonterminal_cache_row_limit:
            raise NonterminalCacheRowLimitExceeded(
                "nonterminal exact-value cache row limit reached "
                f"({self._nonterminal_cache_row_limit})"
            )
        cursor = self._connection.execute(
            """
            INSERT INTO nonterminal_exact_values(
                state_key, guard_key, numerator, denominator
            ) VALUES(?, ?, ?, ?)
            """,
            (
                state_key,
                guard_key,
                str(value.numerator),
                str(value.denominator),
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("nonterminal exact-value insert did not add one row")
        self._cached_nonterminal_states += 1
        self._nonterminal_states_added += 1
        self._pending_writes += 1
        self._remember(state_key, guard_key, value)
        if self._pending_writes >= self._checkpoint_interval:
            self._flush("IN_PROGRESS")

    def _checkpoint_mapping(self, status: str) -> dict[str, object]:
        return {
            "solver_version": TERMINAL_BYPASS_SOLVER_VERSION,
            "schema_version": NONTERMINAL_CACHE_SCHEMA_VERSION,
            "accounting_domain": ACCOUNTING_DOMAIN,
            "cache_signature": self._cache_signature,
            "status": status,
            "updated_at": _utc_now(),
            "cache_path": str(self._cache_path.resolve()),
            "nonterminal_cache_row_limit": self._nonterminal_cache_row_limit,
            "memory_cache_size": self._memory_cache_size,
            "cached_nonterminal_states": self._cached_nonterminal_states,
            "nonterminal_states_added_this_process": self._nonterminal_states_added,
            "terminal_returns": self._terminal_returns,
            "value_calls": self._value_calls,
            "memory_cache_hits": self._memory_cache_hits,
            "disk_cache_hits": self._disk_cache_hits,
            "peak_memory_cache_entries": self._peak_memory_cache_entries,
            "max_recursion_depth": self._max_recursion_depth,
        }

    def _flush(self, status: str) -> None:
        self._connection.commit()
        self._pending_writes = 0
        if self._checkpoint_path is not None:
            _atomic_json(self._checkpoint_path, self._checkpoint_mapping(status))

    def _value(self, state: object, depth: int) -> Fraction:
        self._value_calls += 1
        self._max_recursion_depth = max(self._max_recursion_depth, depth)

        terminated = getattr(state, "terminated", None)
        if type(terminated) is not bool:
            raise ValueError("exact state must expose a boolean terminated property")
        if terminated:
            reward = getattr(state, "reward", None)
            if type(reward) is not int or reward not in {0, 1}:
                raise ValueError("terminal exact reward must be the integer 0 or 1")
            self._terminal_returns += 1
            return Fraction(reward)

        state_key, guard_key = self._state_keys(state)
        cached = self._lookup(state_key, guard_key)
        if cached is not None:
            return cached
        if state_key in self._active_keys:
            raise ValueError("exact value solver requires an acyclic state graph")
        self._active_keys.add(state_key)
        try:
            action_values: list[Fraction] = []
            for candidate in self._model.candidates(state):
                if type(candidate.mask_valid) is not bool:
                    raise ValueError("candidate mask flag must be boolean")
                if not candidate.mask_valid:
                    continue
                semantic_id = candidate.semantic_candidate_id
                if not isinstance(semantic_id, str) or not semantic_id:
                    raise ValueError("candidate semantic ID must be non-empty text")
                transitions = self._model.transition_distribution(state, semantic_id)
                if not isinstance(transitions, tuple) or not transitions:
                    raise ValueError(
                        "valid action must have a non-empty transition tuple"
                    )
                probability_sum = Fraction()
                action_value = Fraction()
                for transition in transitions:
                    probability = transition.probability
                    if not isinstance(probability, Fraction) or probability <= 0:
                        raise ValueError(
                            "exact transition probability must be positive Fraction"
                        )
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

    def solve(self, initial_state: object) -> NonterminalExactValueResult:
        if self._closed:
            raise ValueError("exact value solver is closed")
        try:
            value = self._value(initial_state, 1)
        except BaseException:
            self._flush("BLOCKED")
            raise
        self._flush("SOLVED")
        return NonterminalExactValueResult(
            value=value,
            cached_nonterminal_states=self._cached_nonterminal_states,
            nonterminal_states_added=self._nonterminal_states_added,
            terminal_returns=self._terminal_returns,
            value_calls=self._value_calls,
            memory_cache_hits=self._memory_cache_hits,
            disk_cache_hits=self._disk_cache_hits,
            peak_memory_cache_entries=self._peak_memory_cache_entries,
            max_recursion_depth=self._max_recursion_depth,
        )


def _fraction_mapping(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _json_compatible(value: object) -> object:
    return json.loads(json.dumps(value))


def _source_hashes() -> dict[str, str]:
    source_directory = Path(__file__).resolve().parent
    names = (
        "increment8_terminal_cache_diagnostic.py",
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
            "diagnostic_version": TERMINAL_CACHE_DIAGNOSTIC_VERSION,
            "solver_version": TERMINAL_BYPASS_SOLVER_VERSION,
            "schema_version": NONTERMINAL_CACHE_SCHEMA_VERSION,
            "accounting_domain": ACCOUNTING_DOMAIN,
            "nonterminal_cache_row_limit": NONTERMINAL_CACHE_ROW_LIMIT,
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


def _graphs() -> dict[str, LifecycleGraphSpec]:
    graphs = {
        graph.graph_id: graph
        for graph in build_v1_strategic_graphs()
        if graph.graph_id in _ALLOWED_GRAPH_IDS
    }
    if tuple(graph_id for graph_id in _ALLOWED_GRAPH_IDS if graph_id in graphs) != (
        _ALLOWED_GRAPH_IDS
    ):
        raise ValueError("frozen terminal-cache diagnostic graph set changed")
    return graphs


def _validate_evidence(value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError("control certificate solver evidence is invalid")
    fixed = {
        "nonterminal_cache_row_limit": NONTERMINAL_CACHE_ROW_LIMIT,
        "memory_cache_size": MEMORY_CACHE_SIZE,
        "checkpoint_interval": CHECKPOINT_INTERVAL,
    }
    for name, expected in fixed.items():
        if value.get(name) != expected:
            raise ValueError(f"control certificate {name} is incompatible")
    measured = (
        "cached_nonterminal_states",
        "nonterminal_states_added_this_process",
        "terminal_returns",
        "value_calls",
        "memory_cache_hits",
        "disk_cache_hits",
        "peak_memory_cache_entries",
        "max_recursion_depth",
    )
    for name in measured:
        measured_value = value.get(name)
        if type(measured_value) is not int or measured_value < 0:
            raise ValueError(f"control certificate {name} is invalid")
    if value["cached_nonterminal_states"] > NONTERMINAL_CACHE_ROW_LIMIT:
        raise ValueError("control certificate exceeds the nonterminal row limit")
    if (
        value["nonterminal_states_added_this_process"]
        > value["cached_nonterminal_states"]
    ):
        raise ValueError("control certificate has impossible nonterminal row counts")
    if value["peak_memory_cache_entries"] > MEMORY_CACHE_SIZE:
        raise ValueError("control certificate exceeds the memory cache size")


def _read_fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a fraction mapping")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        raise ValueError(f"{name} must contain an integer nonzero-denominator fraction")
    return Fraction(numerator, denominator)


def _validate_control_certificate(
    output_root: Path,
    graph_id: str,
) -> dict[str, object]:
    path = output_root / "graphs" / graph_id / "certificate.json"
    if not path.is_file():
        raise ValueError(f"required control certificate is missing: {graph_id}")
    try:
        certificate = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"required control certificate is invalid: {graph_id}") from error
    if not isinstance(certificate, dict):
        raise ValueError(f"required control certificate is invalid: {graph_id}")
    graph = _graphs()[graph_id]
    expected_value = _CONTROL_VALUES[graph_id]
    expected_fields: dict[str, object] = {
        "diagnostic_version": TERMINAL_CACHE_DIAGNOSTIC_VERSION,
        "solver_version": TERMINAL_BYPASS_SOLVER_VERSION,
        "schema_version": NONTERMINAL_CACHE_SCHEMA_VERSION,
        "accounting_domain": ACCOUNTING_DOMAIN,
        "base_suite_version": INCREMENT8_SUITE_VERSION,
        "source_sha256": _source_hashes(),
        "graph_id": graph_id,
        "graph": _json_compatible(graph.as_mapping()),
        "graph_hash": canonical_hash(graph.as_mapping()),
        "cache_signature": _signature(graph),
        "clock_semantics": CLOCK_SEMANTICS,
        "family_formula": FAMILY_FORMULA,
        "oracle_floor": _fraction_mapping(ORACLE_FLOOR),
        "control_expected_value": _fraction_mapping(expected_value),
        "control_match": True,
        "status": "CONTROL_MATCH",
    }
    for name, expected in expected_fields.items():
        if certificate.get(name) != expected:
            raise ValueError(f"required control certificate {name} is incompatible")
    if _read_fraction(certificate.get("oracle_value"), "oracle_value") != expected_value:
        raise ValueError(f"required control value is incompatible: {graph_id}")
    _validate_evidence(certificate.get("solver_evidence"))
    return certificate


def _gate_requested_graph(graph_id: str, output_root: Path) -> None:
    if graph_id == "i8_s3_v3":
        _validate_control_certificate(output_root, "i8_s3_v5")
    elif graph_id == "i8_s3_v4":
        _validate_control_certificate(output_root, "i8_s3_v5")
        _validate_control_certificate(output_root, "i8_s3_v3")


def run_diagnostic_graph(graph_id: str, output_root: Path) -> dict[str, object]:
    """Run one eligible graph, enforcing v5 -> v3 -> one-shot v4 ordering."""
    if graph_id not in _ALLOWED_GRAPH_IDS:
        raise ValueError("graph_id is outside the bounded diagnostic set")
    if not isinstance(output_root, Path):
        raise ValueError("output_root must be pathlib.Path")
    _gate_requested_graph(graph_id, output_root)
    graphs = _graphs()
    graph = graphs[graph_id]
    graph_directory = output_root / "graphs" / graph_id
    certificate_path = graph_directory / "certificate.json"

    if graph_id in _CONTROL_VALUES and certificate_path.is_file():
        return _validate_control_certificate(output_root, graph_id)
    if graph_id == "i8_s3_v4" and graph_directory.exists():
        raise ValueError("i8_s3_v4 is a single-attempt diagnostic and cannot resume")

    signature = _signature(graph)
    model = _ClockFixedCalibrationModel()
    with NonterminalCacheExactValueSolver(
        model,
        cache_path=graph_directory / "nonterminal_value_cache.sqlite3",
        cache_signature=signature,
        nonterminal_cache_row_limit=NONTERMINAL_CACHE_ROW_LIMIT,
        memory_cache_size=MEMORY_CACHE_SIZE,
        checkpoint_path=graph_directory / "progress_checkpoint.json",
        checkpoint_interval=CHECKPOINT_INTERVAL,
    ) as solver:
        result = solver.solve(model.initial_state(graph))

    control_expected = _CONTROL_VALUES.get(graph_id)
    control_match = (
        result.value == control_expected if control_expected is not None else None
    )
    if control_expected is None:
        status = "CERTIFIED_VALUE"
    else:
        status = "CONTROL_MATCH" if control_match else "CONTROL_MISMATCH"
    certificate: dict[str, object] = {
        "diagnostic_version": TERMINAL_CACHE_DIAGNOSTIC_VERSION,
        "solver_version": TERMINAL_BYPASS_SOLVER_VERSION,
        "schema_version": NONTERMINAL_CACHE_SCHEMA_VERSION,
        "accounting_domain": ACCOUNTING_DOMAIN,
        "status": status,
        "completed_at": _utc_now(),
        "cache_signature": signature,
        "base_suite_version": INCREMENT8_SUITE_VERSION,
        "source_sha256": _source_hashes(),
        "graph_id": graph_id,
        "graph": graph.as_mapping(),
        "graph_hash": canonical_hash(graph.as_mapping()),
        "clock_semantics": CLOCK_SEMANTICS,
        "family_formula": FAMILY_FORMULA,
        "oracle_value": _fraction_mapping(result.value),
        "oracle_floor": _fraction_mapping(ORACLE_FLOOR),
        "threshold_pass": result.value >= ORACLE_FLOOR,
        "control_expected_value": (
            _fraction_mapping(control_expected)
            if control_expected is not None
            else None
        ),
        "control_match": control_match,
        "solver_evidence": {
            "nonterminal_cache_row_limit": NONTERMINAL_CACHE_ROW_LIMIT,
            "memory_cache_size": MEMORY_CACHE_SIZE,
            "checkpoint_interval": CHECKPOINT_INTERVAL,
            "cached_nonterminal_states": result.cached_nonterminal_states,
            "nonterminal_states_added_this_process": (
                result.nonterminal_states_added
            ),
            "terminal_returns": result.terminal_returns,
            "value_calls": result.value_calls,
            "memory_cache_hits": result.memory_cache_hits,
            "disk_cache_hits": result.disk_cache_hits,
            "peak_memory_cache_entries": result.peak_memory_cache_entries,
            "max_recursion_depth": result.max_recursion_depth,
        },
    }
    _atomic_json(certificate_path, certificate)
    return certificate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded Increment 8 terminal-cache-bypass diagnostic."
    )
    parser.add_argument("--graph-id", required=True, choices=_ALLOWED_GRAPH_IDS)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = run_diagnostic_graph(arguments.graph_id, arguments.output_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] != "CONTROL_MISMATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NONTERMINAL_CACHE_SCHEMA_VERSION",
    "TERMINAL_BYPASS_SOLVER_VERSION",
    "NonterminalCacheExactValueSolver",
    "NonterminalCacheRowLimitExceeded",
    "NonterminalExactValueResult",
    "build_parser",
    "run_diagnostic_graph",
]
