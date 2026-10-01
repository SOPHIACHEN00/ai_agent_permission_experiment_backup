from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from pa_rl.family3_v2_exact_solver import (
    Family3V2ExactCacheError,
    Family3V2ExactValidationError,
    Family3V2ValueFirstExactSolver,
    MEMORY_LRU_CAPACITY,
    MAX_CACHED_NONTERMINAL_STATES,
    RSS_LIMIT_BYTES,
)


@dataclass(frozen=True)
class _Kernel:
    source_graph_id: str = "i8_f3v2_v0"


@dataclass(frozen=True)
class _State:
    name: str
    decision_index: int
    kernel: _Kernel = _Kernel()
    terminated: bool = False
    reward: int = 0


@dataclass(frozen=True)
class _Candidate:
    semantic_candidate_id: str
    mask_valid: bool = True


@dataclass(frozen=True)
class _Transition:
    probability: Fraction
    next_state: object


@dataclass(frozen=True)
class _TransitionWithMetadata:
    probability: object
    next_state: object
    terminated: bool
    reward: int


class _PoisonTerminal:
    terminated = True
    reward = 1

    def __getattribute__(self, name: str):
        if name in {"terminated", "reward", "__class__"}:
            return object.__getattribute__(self, name)
        raise AssertionError(f"terminal was touched through {name}")


class _ToyModel:
    def __init__(self, edges: dict[str, dict[str, tuple[_Transition, ...]]]) -> None:
        self.edges = edges
        self.calls = 0

    def candidates(self, state: _State) -> tuple[_Candidate, ...]:
        return tuple(_Candidate(action) for action in self.edges.get(state.name, {}))

    def transition_distribution(self, state: _State, action: str) -> tuple[_Transition, ...]:
        self.calls += 1
        return self.edges[state.name][action]


def _fingerprints() -> dict[str, str]:
    return {"src/pa_rl/family3_v2_model.py": "a" * 64}


class Family3V2ExactSolverTests(unittest.TestCase):
    def _solver(self, directory: Path, model: _ToyModel, **kwargs):
        return Family3V2ValueFirstExactSolver(
            model,
            directory / "values.sqlite3",
            source_fingerprints=_fingerprints(),
            config_fingerprint="b" * 64,
            **kwargs,
        )

    def test_frozen_limits_and_exact_ordered_root_values(self) -> None:
        self.assertEqual(MAX_CACHED_NONTERMINAL_STATES, 250_000)
        self.assertEqual(MEMORY_LRU_CAPACITY, 4_096)
        self.assertEqual(RSS_LIMIT_BYTES, 512 * 1024 * 1024)
        root = _State("root", 0)
        model = _ToyModel({
            "root": {
                "request_narrow": (_Transition(Fraction(1), _State("lose", 1, terminated=True)),),
                "request_broader": (_Transition(Fraction(1), _State("win", 1, terminated=True, reward=1)),),
            }
        })
        with tempfile.TemporaryDirectory() as raw:
            result = self._solver(Path(raw), model).solve(root, ("request_broader", "request_narrow"))
        self.assertEqual(result.root_value, Fraction(1))
        self.assertEqual(result.root_q_values, (("request_broader", Fraction(1)), ("request_narrow", Fraction(0))))
        self.assertTrue(result.__dataclass_params__.frozen)
        self.assertFalse(hasattr(result, "__dict__"))

    def test_terminal_is_returned_before_any_key_or_cache_operation(self) -> None:
        root = _State("root", 0)
        model = _ToyModel({"root": {"request_narrow": (_Transition(Fraction(1), _PoisonTerminal()),)}})
        with tempfile.TemporaryDirectory() as raw:
            result = self._solver(Path(raw), model).solve(root, ("request_narrow",))
        self.assertEqual(result.root_value, Fraction(1))
        self.assertEqual(result.statistics.terminal_calls, 1)

    def test_root_qs_are_recomputed_on_resumed_root_hit(self) -> None:
        root = _State("root", 0)
        model = _ToyModel({"root": {"request_narrow": (_Transition(Fraction(1), _State("win", 1, terminated=True, reward=1)),)}})
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw)
            first = self._solver(path, model)
            first.solve(root, ("request_narrow",))
            first_calls = model.calls
            second = self._solver(path, model)
            again = second.solve(root, ("request_narrow",))
        self.assertEqual(again.root_q_values, (("request_narrow", Fraction(1)),))
        self.assertGreater(model.calls, first_calls)
        self.assertGreaterEqual(again.statistics.disk_hits, 1)

    def test_rejects_invalid_root_actions_probability_cycle_and_no_valid_action(self) -> None:
        root = _State("root", 0)
        terminal = _State("done", 1, terminated=True, reward=1)
        cases = (
            _ToyModel({"root": {"request_narrow": (_Transition(Fraction(2, 3), terminal),)}}),
            _ToyModel({"root": {"request_narrow": (_Transition(Fraction(1), root),)}}),
            _ToyModel({"root": {}}),
        )
        with tempfile.TemporaryDirectory() as raw:
            for index, model in enumerate(cases):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    self._solver(Path(raw) / str(index), model).solve(root, ("request_narrow",))

    def test_rejects_non_fraction_or_nonpositive_probability_and_invalid_terminal_reward_metadata(self) -> None:
        root = _State("root", 0)
        terminal = _State("done", 1, terminated=True, reward=1)
        cases = (
            (
                _TransitionWithMetadata(1, terminal, True, 1),
                "transition probability must be exact and positive",
            ),
            (
                _TransitionWithMetadata(Fraction(0), terminal, True, 1),
                "transition probability must be exact and positive",
            ),
            (
                _TransitionWithMetadata(Fraction(1), terminal, True, 0),
                "transition reward metadata disagrees",
            ),
        )
        with tempfile.TemporaryDirectory() as raw:
            for index, (transition, message) in enumerate(cases):
                model = _ToyModel({"root": {"request_narrow": (transition,)}})
                with self.subTest(index=index), self.assertRaisesRegex(
                    Family3V2ExactValidationError, message
                ):
                    self._solver(Path(raw) / str(index), model).solve(root, ("request_narrow",))

    def test_rejects_cache_signature_and_guard_mismatch(self) -> None:
        root = _State("root", 0)
        model = _ToyModel({"root": {"request_narrow": (_Transition(Fraction(1), _State("done", 1, terminated=True, reward=1)),)}})
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw)
            self._solver(path, model).solve(root, ("request_narrow",))
            with self.assertRaises(ValueError):
                Family3V2ValueFirstExactSolver(
                    model, path / "values.sqlite3", source_fingerprints=_fingerprints(),
                    config_fingerprint="c" * 64,
                ).solve(root, ("request_narrow",))
            with closing(sqlite3.connect(path / "values.sqlite3")) as connection:
                connection.execute("UPDATE nonterminal_exact_values SET guard_digest = '0' WHERE 1 = 1")
                connection.commit()
            with self.assertRaises(ValueError):
                self._solver(path, model).solve(root, ("request_narrow",))

    def test_rejects_value_table_with_missing_primary_key_and_without_rowid(self) -> None:
        root = _State("root", 0)
        terminal = _State("done", 1, terminated=True, reward=1)
        model = _ToyModel({"root": {"request_narrow": (_Transition(Fraction(1), terminal),)}})
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw)
            self._solver(path, model).solve(root, ("request_narrow",))
            with closing(sqlite3.connect(path / "values.sqlite3")) as connection:
                connection.execute("ALTER TABLE nonterminal_exact_values RENAME TO original_values")
                connection.execute(
                    "CREATE TABLE nonterminal_exact_values ("
                    "state_key TEXT NOT NULL, guard_digest TEXT NOT NULL, "
                    "value_numerator TEXT NOT NULL, value_denominator TEXT NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO nonterminal_exact_values SELECT * FROM original_values"
                )
                connection.execute("DROP TABLE original_values")
                connection.commit()
            with self.assertRaisesRegex(
                Family3V2ExactCacheError, "SQLite (?:column schema|canonical schema) mismatch"
            ):
                self._solver(path, model).solve(root, ("request_narrow",))

    def test_true_4096_entry_lru_moves_hits_to_mru_and_evicts_oldest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            solver = self._solver(Path(raw), _ToyModel({}))
            for index in range(MEMORY_LRU_CAPACITY):
                solver._remember(f"key-{index:04d}", f"guard-{index:04d}", Fraction(index))
            self.assertEqual(len(solver._memory), 4_096)
            self.assertEqual(solver._statistics().lru_peak_entry_count, 4_096)
            self.assertEqual(
                solver._lookup("key-0000", "guard-0000", record_statistics=True),
                Fraction(0),
            )
            self.assertEqual(next(reversed(solver._memory)), "key-0000")
            solver._remember("key-4096", "guard-4096", Fraction(4_096))
            self.assertEqual(len(solver._memory), 4_096)
            self.assertIn("key-0000", solver._memory)
            self.assertNotIn("key-0001", solver._memory)
            self.assertEqual(next(iter(solver._memory)), "key-0002")
            self.assertEqual(next(reversed(solver._memory)), "key-4096")
            self.assertEqual(solver._statistics().memory_hits, 1)

    def test_row_cap_and_rss_boundary_stop_before_insert(self) -> None:
        root = _State("root", 0)
        child = _State("child", 1)
        terminal = _State("done", 2, terminated=True, reward=1)
        model = _ToyModel({
            "root": {"request_narrow": (_Transition(Fraction(1), child),)},
            "child": {"execute_covering": (_Transition(Fraction(1), terminal),)},
        })
        with tempfile.TemporaryDirectory() as raw:
            with patch("pa_rl.family3_v2_exact_solver.MAX_CACHED_NONTERMINAL_STATES", 1):
                with self.assertRaises(ValueError):
                    self._solver(Path(raw) / "cap", model, rss_reader=lambda: 0).solve(root, ("request_narrow",))
            equal = self._solver(Path(raw) / "equal", model, rss_reader=lambda: RSS_LIMIT_BYTES)
            self.assertEqual(equal.solve(root, ("request_narrow",)).root_value, Fraction(1))
            over = self._solver(Path(raw) / "over", model, rss_reader=lambda: RSS_LIMIT_BYTES + 1)
            with self.assertRaises(ValueError):
                over.solve(root, ("request_narrow",))


if __name__ == "__main__":
    unittest.main()
