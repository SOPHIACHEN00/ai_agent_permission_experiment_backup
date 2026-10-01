"""Capped exact Bellman solver for the frozen Family-3 v2 experiment."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any


MAX_CACHED_NONTERMINAL_STATES = 250_000
MEMORY_LRU_CAPACITY = 4_096
RSS_LIMIT_BYTES = 512 * 1024 * 1024

SOLVER_VERSION = "family3_v2_value_first_exact_solver_v0"
SQLITE_SCHEMA_VERSION = "family3_v2_nonterminal_exact_values_v0"
SERIALIZER_VERSION = "family3_v2_full_semantic_state_v0"
KEY_VERSION = "sha256_family3_v2_state_v0"
GUARD_VERSION = "blake2b256_family3_v2_state_guard_v0"
METADATA_VERSION = "family3_v2_exact_cache_metadata_v0"
ACCOUNTING_DOMAIN = "nonterminal_bellman_states"

_HEX_256 = re.compile(r"[0-9a-f]{64}\Z")
_CANONICAL_INTEGER = re.compile(r"(?:0|[1-9][0-9]*|-[1-9][0-9]*)\Z")


class Family3V2ExactSolverError(ValueError):
    """Base class for fail-closed exact-solver errors."""


class Family3V2ExactValidationError(Family3V2ExactSolverError):
    """Raised when a model, state, action, or transition is malformed."""


class Family3V2ExactCacheError(Family3V2ExactSolverError):
    """Raised when cache schema, metadata, keys, or values are incompatible."""


class Family3V2ExactCycleError(Family3V2ExactValidationError):
    """Raised when a reachable nonterminal Bellman cycle is detected."""


class Family3V2ExactResourceCapError(Family3V2ExactSolverError):
    """Raised before an insertion would violate a frozen resource limit."""

    def __init__(self, cap_name: str, limit: int, actual: int) -> None:
        self.cap_name = cap_name
        self.limit = limit
        self.actual = actual
        super().__init__(f"{cap_name} cap exceeded: limit={limit}, actual={actual}")


def _fraction_mapping(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise Family3V2ExactValidationError("exact value must be Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


@dataclass(frozen=True, slots=True)
class Family3V2ExactSolveStatistics:
    nonterminal_row_count: int
    new_nonterminal_row_count: int
    value_calls: int
    terminal_calls: int
    memory_hits: int
    disk_hits: int
    lru_peak_entry_count: int
    maximum_recursion_depth: int
    peak_rss_bytes: int
    current_rss_bytes: int

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field.name} must be a non-negative exact integer")
        if self.lru_peak_entry_count > MEMORY_LRU_CAPACITY:
            raise ValueError("reported LRU peak exceeds the frozen capacity")

    @property
    def row_count(self) -> int:
        return self.nonterminal_row_count

    @property
    def new_row_count(self) -> int:
        return self.new_nonterminal_row_count

    @property
    def lru_peak(self) -> int:
        return self.lru_peak_entry_count

    def as_mapping(self) -> dict[str, int]:
        return {
            "nonterminal_row_count": self.nonterminal_row_count,
            "new_nonterminal_row_count": self.new_nonterminal_row_count,
            "value_calls": self.value_calls,
            "terminal_calls": self.terminal_calls,
            "memory_hits": self.memory_hits,
            "disk_hits": self.disk_hits,
            "lru_peak_entry_count": self.lru_peak_entry_count,
            "maximum_recursion_depth": self.maximum_recursion_depth,
            "peak_rss_bytes": self.peak_rss_bytes,
            "current_rss_bytes": self.current_rss_bytes,
        }


@dataclass(frozen=True, slots=True)
class Family3V2ExactSolveResult:
    graph_id: str
    root_value: Fraction
    root_q_values: tuple[tuple[str, Fraction], ...]
    statistics: Family3V2ExactSolveStatistics

    def __post_init__(self) -> None:
        if type(self.graph_id) is not str or not self.graph_id:
            raise ValueError("graph_id must be a non-empty string")
        if type(self.root_value) is not Fraction:
            raise ValueError("root_value must be an exact Fraction")
        if not isinstance(self.root_q_values, tuple):
            raise ValueError("root_q_values must be a caller-ordered tuple")
        action_ids: list[str] = []
        for row in self.root_q_values:
            if (
                not isinstance(row, tuple)
                or len(row) != 2
                or type(row[0]) is not str
                or not row[0]
                or type(row[1]) is not Fraction
            ):
                raise ValueError("root Q rows must be (string, Fraction) pairs")
            action_ids.append(row[0])
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("root Q action IDs must be unique")
        if not isinstance(self.statistics, Family3V2ExactSolveStatistics):
            raise ValueError("statistics must be typed")

    def as_mapping(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "root_value": _fraction_mapping(self.root_value),
            "root_q_values": [
                {"action_id": action_id, "value": _fraction_mapping(value)}
                for action_id, value in self.root_q_values
            ],
            "statistics": self.statistics.as_mapping(),
        }


def _canonical_encode(value: object) -> object:
    if value is None or type(value) in {str, bool}:
        return value
    if type(value) is int:
        return value
    if type(value) is Fraction:
        return {
            "__fraction__": {
                "numerator": value.numerator,
                "denominator": value.denominator,
            }
        }
    if isinstance(value, Enum):
        return {
            "__enum__": f"{type(value).__module__}.{type(value).__qualname__}",
            "value": _canonical_encode(value.value),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__dataclass__": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": [
                [field.name, _canonical_encode(getattr(value, field.name))]
                for field in fields(value)
            ],
        }
    if isinstance(value, tuple):
        return {"__tuple__": [_canonical_encode(item) for item in value]}
    if isinstance(value, list):
        return [_canonical_encode(item) for item in value]
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise Family3V2ExactValidationError("canonical mappings require string keys")
        return {
            key: _canonical_encode(value[key])
            for key in sorted(value)
        }
    raise Family3V2ExactValidationError(
        f"unsupported semantic value type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            _canonical_encode(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        if isinstance(error, Family3V2ExactSolverError):
            raise
        raise Family3V2ExactValidationError("value is not canonically serializable") from error


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _guard_digest(data: bytes) -> str:
    return hashlib.blake2b(
        data,
        digest_size=32,
        person=b"f3v2-state-v0",
    ).hexdigest()


def _validate_sha256(name: str, value: object) -> str:
    if type(value) is not str or _HEX_256.fullmatch(value) is None:
        raise Family3V2ExactValidationError(f"{name} must be lowercase SHA-256")
    return value


def _canonical_source_fingerprints(
    source_fingerprints: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    if not isinstance(source_fingerprints, Mapping):
        raise Family3V2ExactValidationError("source_fingerprints must be a Mapping")
    try:
        items = tuple(source_fingerprints.items())
    except Exception as error:
        raise Family3V2ExactValidationError("source fingerprint mapping is unreadable") from error
    paths: list[str] = []
    canonical: list[tuple[str, str]] = []
    for path, digest in items:
        if type(path) is not str or not path:
            raise Family3V2ExactValidationError("source fingerprint paths must be non-empty strings")
        pure = PurePosixPath(path)
        if (
            pure.is_absolute()
            or path != pure.as_posix()
            or any(part in {"", ".", ".."} for part in pure.parts)
        ):
            raise Family3V2ExactValidationError("source fingerprint path is not canonical POSIX-relative")
        paths.append(path)
        canonical.append((path, _validate_sha256(f"source fingerprint for {path}", digest)))
    if not canonical or len(paths) != len(set(paths)):
        raise Family3V2ExactValidationError("source fingerprint paths must be nonempty and unique")
    return tuple(sorted(canonical))


def _default_rss_bytes() -> int:
    if sys.platform == "win32":
        from ctypes import wintypes

        size_t = ctypes.c_size_t

        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = (
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", size_t),
                ("WorkingSetSize", size_t),
                ("QuotaPeakPagedPoolUsage", size_t),
                ("QuotaPagedPoolUsage", size_t),
                ("QuotaPeakNonPagedPoolUsage", size_t),
                ("QuotaNonPagedPoolUsage", size_t),
                ("PagefileUsage", size_t),
                ("PeakPagefileUsage", size_t),
            )

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.GetCurrentProcess.argtypes = ()
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = (
                wintypes.HANDLE,
                ctypes.POINTER(_ProcessMemoryCounters),
                wintypes.DWORD,
            )
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            handle = kernel32.GetCurrentProcess()
            if not handle or not psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(counters), counters.cb
            ):
                raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
            value = counters.WorkingSetSize
        except Exception as error:
            raise Family3V2ExactResourceCapError("rss_reader_unavailable", RSS_LIMIT_BYTES, -1) from error
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/self/statm", "r", encoding="ascii") as handle:
                parts = handle.read().split()
            if len(parts) < 2 or re.fullmatch(r"[0-9]+", parts[1]) is None:
                raise ValueError("malformed resident-page count")
            resident_pages = int(parts[1])
            page_size = os.sysconf("SC_PAGE_SIZE")
            if type(page_size) is not int or page_size <= 0:
                raise ValueError("malformed page size")
            value = resident_pages * page_size
        except Exception as error:
            raise Family3V2ExactResourceCapError("rss_reader_unavailable", RSS_LIMIT_BYTES, -1) from error
    else:
        raise Family3V2ExactResourceCapError("rss_reader_unavailable", RSS_LIMIT_BYTES, -1)
    if type(value) is not int or value < 0:
        raise Family3V2ExactResourceCapError("rss_reader_invalid", RSS_LIMIT_BYTES, -1)
    return value


class Family3V2ValueFirstExactSolver:
    """Exact value-first solver with guarded SQLite and bounded memory caches."""

    def __init__(
        self,
        model: object,
        database_path: os.PathLike[str] | str,
        *,
        source_fingerprints: Mapping[str, str],
        config_fingerprint: str,
        rss_reader: Callable[[], int] | None = None,
        failure_hook: Callable[[str], None] | None = None,
    ) -> None:
        if not callable(getattr(model, "candidates", None)) or not callable(
            getattr(model, "transition_distribution", None)
        ):
            raise Family3V2ExactValidationError("model must expose candidates and transition_distribution")
        try:
            path = Path(database_path)
        except (TypeError, ValueError) as error:
            raise Family3V2ExactValidationError("database_path must be path-like") from error
        if not path.name:
            raise Family3V2ExactValidationError("database_path must name a file")
        if rss_reader is not None and not callable(rss_reader):
            raise Family3V2ExactValidationError("rss_reader must be callable")
        if failure_hook is not None and not callable(failure_hook):
            raise Family3V2ExactValidationError("failure_hook must be callable")
        self._model = model
        self._database_path = path
        self._source_fingerprints = _canonical_source_fingerprints(source_fingerprints)
        self._config_fingerprint = _validate_sha256("config_fingerprint", config_fingerprint)
        self._rss_reader = _default_rss_bytes if rss_reader is None else rss_reader
        self._failure_hook = failure_hook
        self._memory: OrderedDict[str, tuple[str, Fraction]] = OrderedDict()
        self._active: dict[str, str] = {}
        self._connection: sqlite3.Connection | None = None
        self._database_ready = False
        self._bound_metadata_bytes: bytes | None = None
        self._reset_statistics()

    def __enter__(self) -> Family3V2ValueFirstExactSolver:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._database_ready = False

    def _reset_statistics(self) -> None:
        self._value_calls = 0
        self._terminal_calls = 0
        self._memory_hits = 0
        self._disk_hits = 0
        self._new_rows = 0
        self._row_count = 0
        self._lru_peak = len(getattr(self, "_memory", ()))
        self._maximum_depth = 0
        self._peak_rss = 0
        self._current_rss = 0

    def _failpoint(self, stage: str) -> None:
        if self._failure_hook is not None:
            self._failure_hook(stage)

    @staticmethod
    def _terminal_flag(state: object) -> bool:
        try:
            terminated = state.terminated
        except Exception as error:
            raise Family3V2ExactValidationError("state must expose terminated") from error
        if type(terminated) is not bool:
            raise Family3V2ExactValidationError("state.terminated must be an exact bool")
        return terminated

    @staticmethod
    def _terminal_value(state: object) -> Fraction:
        try:
            reward = state.reward
        except Exception as error:
            raise Family3V2ExactValidationError("terminal state must expose reward") from error
        if type(reward) is not int or reward not in {0, 1}:
            raise Family3V2ExactValidationError("terminal reward must be an exact binary integer")
        return Fraction(reward)

    @staticmethod
    def _state_bytes(state: object) -> bytes:
        if not is_dataclass(state) or isinstance(state, type):
            raise Family3V2ExactValidationError("nonterminal state must be a dataclass instance")
        return _canonical_json_bytes({
            "serializer_version": SERIALIZER_VERSION,
            "state": state,
        })

    @staticmethod
    def _state_key_and_guard(state: object) -> tuple[str, str]:
        serialized = Family3V2ValueFirstExactSolver._state_bytes(state)
        return _sha256(KEY_VERSION.encode("ascii") + b"\0" + serialized), _guard_digest(serialized)

    def _expected_metadata(self, state: object) -> tuple[dict[str, object], bytes]:
        try:
            kernel = state.kernel
            graph_id = kernel.source_graph_id
        except Exception as error:
            raise Family3V2ExactValidationError("nonterminal state must expose kernel identity") from error
        if type(graph_id) is not str or not graph_id:
            raise Family3V2ExactValidationError("kernel source_graph_id must be non-empty")
        kernel_sha256 = _sha256(_canonical_json_bytes({
            "serializer_version": SERIALIZER_VERSION,
            "kernel": kernel,
        }))
        limits = {
            "max_cached_nonterminal_states": MAX_CACHED_NONTERMINAL_STATES,
            "memory_lru_capacity": MEMORY_LRU_CAPACITY,
            "rss_limit_bytes": RSS_LIMIT_BYTES,
        }
        compatibility = {
            "solver_version": SOLVER_VERSION,
            "sqlite_schema_version": SQLITE_SCHEMA_VERSION,
            "serializer_version": SERIALIZER_VERSION,
            "key_version": KEY_VERSION,
            "guard_version": GUARD_VERSION,
            "accounting_domain": ACCOUNTING_DOMAIN,
            "graph_id": graph_id,
            "kernel_sha256": kernel_sha256,
            "source_fingerprints": [list(item) for item in self._source_fingerprints],
            "config_fingerprint": self._config_fingerprint,
            "limits": limits,
        }
        metadata = {
            "metadata_version": METADATA_VERSION,
            **compatibility,
            "cache_signature": _sha256(_canonical_json_bytes(compatibility)),
        }
        return metadata, _canonical_json_bytes(metadata)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE metadata ("
            "singleton INTEGER NOT NULL PRIMARY KEY CHECK(singleton = 1), "
            "metadata_json TEXT NOT NULL, "
            "metadata_sha256 TEXT NOT NULL"
            ") WITHOUT ROWID"
        )
        connection.execute(
            "CREATE TABLE nonterminal_exact_values ("
            "state_key TEXT NOT NULL PRIMARY KEY, "
            "guard_digest TEXT NOT NULL, "
            "value_numerator TEXT NOT NULL, "
            "value_denominator TEXT NOT NULL"
            ") WITHOUT ROWID"
        )

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        objects = tuple(connection.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        ))
        expected_objects = (
            ("table", "metadata"),
            ("table", "nonterminal_exact_values"),
        )
        if objects != expected_objects:
            raise Family3V2ExactCacheError("SQLite application schema must contain exactly two tables")
        expected_columns = {
            "metadata": (
                ("singleton", "INTEGER", 1, 1),
                ("metadata_json", "TEXT", 1, 0),
                ("metadata_sha256", "TEXT", 1, 0),
            ),
            "nonterminal_exact_values": (
                ("state_key", "TEXT", 1, 1),
                ("guard_digest", "TEXT", 1, 0),
                ("value_numerator", "TEXT", 1, 0),
                ("value_denominator", "TEXT", 1, 0),
            ),
        }
        for table, expected in expected_columns.items():
            actual = tuple(
                (row[1], str(row[2]).upper(), int(row[3]), int(row[5]))
                for row in connection.execute(f"PRAGMA table_info({table})")
            )
            if actual != expected:
                raise Family3V2ExactCacheError(f"SQLite column schema mismatch for {table}")
        expected_sql = {
            "metadata": (
                "createtablemetadata(singletonintegernotnullprimarykeycheck(singleton=1),"
                "metadata_jsontextnotnull,metadata_sha256textnotnull)withoutrowid"
            ),
            "nonterminal_exact_values": (
                "createtablenonterminal_exact_values(state_keytextnotnullprimarykey,"
                "guard_digesttextnotnull,value_numeratortextnotnull,"
                "value_denominatortextnotnull)withoutrowid"
            ),
        }
        for table, expected in expected_sql.items():
            row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            if (
                row is None
                or type(row[0]) is not str
                or re.sub(r"\s+", "", row[0]).lower() != expected
            ):
                raise Family3V2ExactCacheError(f"SQLite canonical schema mismatch for {table}")

    def _ensure_database(self, state: object) -> None:
        metadata, metadata_bytes = self._expected_metadata(state)
        if self._bound_metadata_bytes is not None and metadata_bytes != self._bound_metadata_bytes:
            raise Family3V2ExactCacheError("solver instance cannot change graph or kernel identity")
        if self._database_ready:
            return
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        existed = self._database_path.exists()
        connection = sqlite3.connect(self._database_path)
        self._connection = connection
        try:
            if not existed:
                self._create_schema(connection)
                metadata_text = metadata_bytes.decode("utf-8")
                connection.execute(
                    "INSERT INTO metadata(singleton, metadata_json, metadata_sha256) VALUES(1, ?, ?)",
                    (metadata_text, _sha256(metadata_bytes)),
                )
                self._failpoint("before_metadata_commit")
                connection.commit()
            self._validate_schema(connection)
            rows = tuple(connection.execute(
                "SELECT singleton, metadata_json, metadata_sha256 FROM metadata"
            ))
            if len(rows) != 1 or rows[0][0] != 1:
                raise Family3V2ExactCacheError("metadata table must contain exactly its singleton")
            stored_text, stored_digest = rows[0][1], rows[0][2]
            if type(stored_text) is not str or type(stored_digest) is not str:
                raise Family3V2ExactCacheError("metadata values have invalid storage types")
            stored_bytes = stored_text.encode("utf-8")
            if _HEX_256.fullmatch(stored_digest) is None or _sha256(stored_bytes) != stored_digest:
                raise Family3V2ExactCacheError("metadata signature mismatch")
            try:
                parsed = json.loads(stored_text)
            except (TypeError, ValueError) as error:
                raise Family3V2ExactCacheError("metadata JSON is malformed") from error
            if _canonical_json_bytes(parsed) != stored_bytes or parsed != metadata:
                raise Family3V2ExactCacheError("cache metadata is incompatible")
            row_count = connection.execute(
                "SELECT COUNT(*) FROM nonterminal_exact_values"
            ).fetchone()[0]
            if type(row_count) is not int or row_count < 0:
                raise Family3V2ExactCacheError("cache row count is invalid")
            if row_count > MAX_CACHED_NONTERMINAL_STATES:
                raise Family3V2ExactResourceCapError(
                    "nonterminal_rows", MAX_CACHED_NONTERMINAL_STATES, row_count
                )
            self._row_count = row_count
            self._bound_metadata_bytes = metadata_bytes
            self._database_ready = True
        except Exception:
            connection.rollback()
            self.close()
            raise

    def _remember(self, key: str, guard: str, value: Fraction) -> None:
        if key in self._memory:
            del self._memory[key]
        self._memory[key] = (guard, value)
        if len(self._memory) > MEMORY_LRU_CAPACITY:
            self._memory.popitem(last=False)
        self._lru_peak = max(self._lru_peak, len(self._memory))

    @staticmethod
    def _parse_integer(text: object, *, positive: bool = False) -> int:
        if type(text) is not str or _CANONICAL_INTEGER.fullmatch(text) is None:
            raise Family3V2ExactCacheError("cached integer is not canonical decimal text")
        value = int(text)
        if positive and value <= 0:
            raise Family3V2ExactCacheError("cached denominator must be positive")
        return value

    def _lookup(self, key: str, guard: str, *, record_statistics: bool) -> Fraction | None:
        memory = self._memory.get(key)
        if memory is not None:
            stored_guard, value = memory
            if stored_guard != guard:
                raise Family3V2ExactCacheError("memory cache guard mismatch")
            self._memory.move_to_end(key)
            if record_statistics:
                self._memory_hits += 1
            return value
        if self._connection is None:
            raise Family3V2ExactCacheError("database is not open")
        row = self._connection.execute(
            "SELECT guard_digest, value_numerator, value_denominator "
            "FROM nonterminal_exact_values WHERE state_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        stored_guard, numerator_text, denominator_text = row
        if type(stored_guard) is not str or stored_guard != guard:
            raise Family3V2ExactCacheError("disk cache guard mismatch")
        numerator = self._parse_integer(numerator_text)
        denominator = self._parse_integer(denominator_text, positive=True)
        value = Fraction(numerator, denominator)
        if value.numerator != numerator or value.denominator != denominator:
            raise Family3V2ExactCacheError("cached Fraction is not reduced canonical form")
        self._remember(key, guard, value)
        if record_statistics:
            self._disk_hits += 1
        return value

    def _read_rss(self) -> int:
        try:
            value = self._rss_reader()
        except Family3V2ExactSolverError:
            raise
        except Exception as error:
            raise Family3V2ExactResourceCapError("rss_reader_unavailable", RSS_LIMIT_BYTES, -1) from error
        if type(value) is not int or value < 0:
            raise Family3V2ExactResourceCapError("rss_reader_invalid", RSS_LIMIT_BYTES, -1)
        self._current_rss = value
        self._peak_rss = max(self._peak_rss, value)
        return value

    def _insert(self, key: str, guard: str, value: Fraction) -> None:
        if self._connection is None:
            raise Family3V2ExactCacheError("database is not open")
        if self._row_count >= MAX_CACHED_NONTERMINAL_STATES:
            raise Family3V2ExactResourceCapError(
                "nonterminal_rows", MAX_CACHED_NONTERMINAL_STATES, self._row_count + 1
            )
        rss = self._read_rss()
        if rss > RSS_LIMIT_BYTES:
            raise Family3V2ExactResourceCapError("rss_bytes", RSS_LIMIT_BYTES, rss)
        self._failpoint("before_value_insert")
        try:
            self._connection.execute(
                "INSERT INTO nonterminal_exact_values("
                "state_key, guard_digest, value_numerator, value_denominator"
                ") VALUES(?, ?, ?, ?)",
                (key, guard, str(value.numerator), str(value.denominator)),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise Family3V2ExactCacheError("distinct nonterminal insertion collided") from error
        except Exception:
            self._connection.rollback()
            raise
        self._row_count += 1
        self._new_rows += 1
        self._remember(key, guard, value)

    def _candidate_rows(self, state: object) -> tuple[object, ...]:
        try:
            rows = self._model.candidates(state)
        except Exception as error:
            if isinstance(error, Family3V2ExactSolverError):
                raise
            raise Family3V2ExactValidationError("model candidate enumeration failed") from error
        if not isinstance(rows, tuple):
            raise Family3V2ExactValidationError("candidate catalog must be a tuple")
        identifiers: list[str] = []
        for row in rows:
            try:
                identifier = row.semantic_candidate_id
                valid = row.mask_valid
            except Exception as error:
                raise Family3V2ExactValidationError("candidate row is malformed") from error
            if type(identifier) is not str or not identifier or type(valid) is not bool:
                raise Family3V2ExactValidationError("candidate ID/mask is malformed")
            identifiers.append(identifier)
        if len(identifiers) != len(set(identifiers)):
            raise Family3V2ExactValidationError("candidate IDs must be unique")
        return rows

    def _action_value(
        self,
        state: object,
        action_id: str,
        *,
        record_statistics: bool,
    ) -> Fraction:
        try:
            distribution = self._model.transition_distribution(state, action_id)
        except Exception as error:
            if isinstance(error, Family3V2ExactSolverError):
                raise
            raise Family3V2ExactValidationError("model transition enumeration failed") from error
        if not isinstance(distribution, tuple) or not distribution:
            raise Family3V2ExactValidationError("transition distribution must be a nonempty tuple")
        probabilities: list[Fraction] = []
        successors: list[object] = []
        for transition in distribution:
            try:
                probability = transition.probability
                successor = transition.next_state
            except Exception as error:
                raise Family3V2ExactValidationError("transition row is malformed") from error
            if type(probability) is not Fraction or probability <= 0:
                raise Family3V2ExactValidationError("transition probability must be exact and positive")
            successor_terminal = self._terminal_flag(successor)
            if hasattr(transition, "terminated"):
                transition_terminal = transition.terminated
                if type(transition_terminal) is not bool or transition_terminal != successor_terminal:
                    raise Family3V2ExactValidationError("transition termination metadata disagrees")
            if hasattr(transition, "reward"):
                transition_reward = transition.reward
                if type(transition_reward) is not int or transition_reward not in {0, 1}:
                    raise Family3V2ExactValidationError("transition reward must be binary")
                try:
                    successor_reward = successor.reward
                except Exception as error:
                    raise Family3V2ExactValidationError("successor reward is missing") from error
                if type(successor_reward) is not int or transition_reward != successor_reward:
                    raise Family3V2ExactValidationError("transition reward metadata disagrees")
            probabilities.append(probability)
            successors.append(successor)
        if sum(probabilities, Fraction()) != Fraction(1):
            raise Family3V2ExactValidationError("transition probabilities must sum exactly to one")
        return sum(
            (
                probability * self._value(successor, record_statistics=record_statistics)
                for probability, successor in zip(probabilities, successors)
            ),
            Fraction(),
        )

    def _value(self, state: object, *, record_statistics: bool = True) -> Fraction:
        if record_statistics:
            self._value_calls += 1
        if self._terminal_flag(state):
            value = self._terminal_value(state)
            if record_statistics:
                self._terminal_calls += 1
            return value

        serialized = self._state_bytes(state)
        key = _sha256(KEY_VERSION.encode("ascii") + b"\0" + serialized)
        guard = _guard_digest(serialized)
        active_guard = self._active.get(key)
        if active_guard is not None:
            if active_guard == guard:
                raise Family3V2ExactCycleError("reachable nonterminal Bellman cycle")
            raise Family3V2ExactCacheError("primary key collision within active recursion")
        self._ensure_database(state)
        cached = self._lookup(key, guard, record_statistics=record_statistics)
        if cached is not None:
            return cached
        rows = self._candidate_rows(state)
        valid_ids = tuple(row.semantic_candidate_id for row in rows if row.mask_valid)
        if not valid_ids:
            raise Family3V2ExactValidationError("reachable nonterminal state has no valid action")
        self._active[key] = guard
        self._maximum_depth = max(self._maximum_depth, len(self._active))
        try:
            value = max(
                self._action_value(
                    state,
                    action_id,
                    record_statistics=record_statistics,
                )
                for action_id in valid_ids
            )
            self._insert(key, guard, value)
            return value
        finally:
            del self._active[key]

    def _statistics(self) -> Family3V2ExactSolveStatistics:
        return Family3V2ExactSolveStatistics(
            nonterminal_row_count=self._row_count,
            new_nonterminal_row_count=self._new_rows,
            value_calls=self._value_calls,
            terminal_calls=self._terminal_calls,
            memory_hits=self._memory_hits,
            disk_hits=self._disk_hits,
            lru_peak_entry_count=self._lru_peak,
            maximum_recursion_depth=self._maximum_depth,
            peak_rss_bytes=self._peak_rss,
            current_rss_bytes=self._current_rss,
        )

    def solve(
        self,
        initial_state: object,
        initial_action_ids: tuple[str, ...],
    ) -> Family3V2ExactSolveResult:
        self.close()
        self._reset_statistics()
        self._active.clear()
        if (
            not isinstance(initial_action_ids, tuple)
            or not initial_action_ids
            or any(type(item) is not str or not item for item in initial_action_ids)
            or len(initial_action_ids) != len(set(initial_action_ids))
        ):
            raise Family3V2ExactValidationError(
                "initial_action_ids must be a nonempty unique ordered tuple of strings"
            )
        if self._terminal_flag(initial_state):
            raise Family3V2ExactValidationError("solve requires a nonterminal root")
        root_rows = self._candidate_rows(initial_state)
        root_by_id = {row.semantic_candidate_id: row for row in root_rows}
        for action_id in initial_action_ids:
            row = root_by_id.get(action_id)
            if row is None or not row.mask_valid:
                raise Family3V2ExactValidationError(
                    "every requested root action must be present and mask-valid"
                )
        try:
            root_value = self._value(initial_state)
            root_q_values = tuple(
                (
                    action_id,
                    self._action_value(
                        initial_state,
                        action_id,
                        record_statistics=False,
                    ),
                )
                for action_id in initial_action_ids
            )
            try:
                graph_id = initial_state.kernel.source_graph_id
            except Exception as error:
                raise Family3V2ExactValidationError("root state lacks graph identity") from error
            return Family3V2ExactSolveResult(
                graph_id=graph_id,
                root_value=root_value,
                root_q_values=root_q_values,
                statistics=self._statistics(),
            )
        finally:
            self.close()


__all__ = [
    "ACCOUNTING_DOMAIN",
    "Family3V2ExactCacheError",
    "Family3V2ExactCycleError",
    "Family3V2ExactResourceCapError",
    "Family3V2ExactSolveResult",
    "Family3V2ExactSolveStatistics",
    "Family3V2ExactSolverError",
    "Family3V2ExactValidationError",
    "Family3V2ValueFirstExactSolver",
    "GUARD_VERSION",
    "KEY_VERSION",
    "MAX_CACHED_NONTERMINAL_STATES",
    "MEMORY_LRU_CAPACITY",
    "METADATA_VERSION",
    "RSS_LIMIT_BYTES",
    "SERIALIZER_VERSION",
    "SOLVER_VERSION",
    "SQLITE_SCHEMA_VERSION",
]
