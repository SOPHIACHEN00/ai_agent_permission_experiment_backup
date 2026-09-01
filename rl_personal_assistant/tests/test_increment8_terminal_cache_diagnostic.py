"""Focused behavior tests for the terminal-cache-bypass exact diagnostic."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from pa_rl.increment8_terminal_cache_diagnostic import (
    NONTERMINAL_CACHE_SCHEMA_VERSION,
    TERMINAL_BYPASS_SOLVER_VERSION,
    NonterminalCacheExactValueSolver,
    NonterminalCacheRowLimitExceeded,
    build_parser,
    run_diagnostic_graph,
)
from pa_rl.increment8_value_solver import DiskBackedExactValueSolver


@dataclass(frozen=True, slots=True)
class _State:
    name: str
    terminated: bool = False
    reward: int = 0


@dataclass(frozen=True, slots=True)
class _Candidate:
    semantic_candidate_id: str
    mask_valid: bool = True


@dataclass(frozen=True, slots=True)
class _Transition:
    probability: Fraction
    next_state: _State


class _OneStepModel:
    ROOT = _State("root")
    WIN = _State("win", terminated=True, reward=1)
    LOSS = _State("loss", terminated=True, reward=0)

    def candidates(self, state: _State) -> tuple[_Candidate, ...]:
        return () if state.terminated else (_Candidate("act"),)

    def transition_distribution(
        self,
        state: _State,
        semantic_candidate_id: str,
    ) -> tuple[_Transition, ...]:
        if state != self.ROOT or semantic_candidate_id != "act":
            raise ValueError("unexpected transition request")
        return (
            _Transition(Fraction(3, 5), self.WIN),
            _Transition(Fraction(2, 5), self.LOSS),
        )


class _ChainModel:
    ROOT = _State("root")
    MIDDLE = _State("middle")
    WIN = _State("win", terminated=True, reward=1)

    def candidates(self, state: _State) -> tuple[_Candidate, ...]:
        return () if state.terminated else (_Candidate("advance"),)

    def transition_distribution(
        self,
        state: _State,
        semantic_candidate_id: str,
    ) -> tuple[_Transition, ...]:
        if semantic_candidate_id != "advance":
            raise ValueError("unexpected transition request")
        if state == self.ROOT:
            return (_Transition(Fraction(1), self.MIDDLE),)
        if state == self.MIDDLE:
            return (_Transition(Fraction(1), self.WIN),)
        raise ValueError("terminal states have no transitions")


class _KeyCountingSolver(NonterminalCacheExactValueSolver):
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.key_calls = 0
        super().__init__(*args, **kwargs)

    def _state_keys(self, state: object) -> tuple[bytes, bytes]:
        self.key_calls += 1
        return super()._state_keys(state)


class Increment8TerminalCacheDiagnosticTests(unittest.TestCase):
    def test_terminal_binary_reward_returns_without_key_or_cache_row(self) -> None:
        """Catches terminal keying, lookup/store, or ambiguous terminal accounting."""
        model = _OneStepModel()
        for reward in (0, 1):
            with self.subTest(reward=reward), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                cache_path = root / "values.sqlite3"
                checkpoint_path = root / "progress.json"
                with _KeyCountingSolver(
                    model,
                    cache_path=cache_path,
                    cache_signature="terminal_direct_v1",
                    nonterminal_cache_row_limit=1,
                    memory_cache_size=1,
                    checkpoint_path=checkpoint_path,
                    checkpoint_interval=1,
                ) as solver:
                    result = solver.solve(_State("terminal", True, reward))
                    self.assertEqual(solver.key_calls, 0)

                self.assertEqual(result.value, Fraction(reward))
                self.assertEqual(result.cached_nonterminal_states, 0)
                self.assertEqual(result.nonterminal_states_added, 0)
                self.assertEqual(result.terminal_returns, 1)
                with closing(sqlite3.connect(cache_path)) as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM nonterminal_exact_values"
                    ).fetchone()
                self.assertEqual(count, (0,))
                checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                self.assertEqual(checkpoint["cached_nonterminal_states"], 0)
                self.assertEqual(checkpoint["nonterminal_cache_row_limit"], 1)
                self.assertEqual(checkpoint["terminal_returns"], 1)
                self.assertNotIn("total_cached_states", checkpoint)
                self.assertNotIn("state_limit", checkpoint)

    def test_invalid_terminal_reward_fails_before_keying_and_stays_uncached(self) -> None:
        """Catches accepting or hashing a malformed terminal reward."""
        model = _OneStepModel()
        with tempfile.TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "values.sqlite3"
            with _KeyCountingSolver(
                model,
                cache_path=cache_path,
                cache_signature="invalid_terminal_v1",
                nonterminal_cache_row_limit=1,
                memory_cache_size=1,
            ) as solver:
                with self.assertRaisesRegex(ValueError, "integer 0 or 1"):
                    solver.solve(_State("bad", True, 2))
                self.assertEqual(solver.key_calls, 0)
            with closing(sqlite3.connect(cache_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM nonterminal_exact_values"
                ).fetchone()
            self.assertEqual(count, (0,))

    def test_only_nonterminal_states_consume_rows_and_result_is_exact(self) -> None:
        """Catches terminal rows leaking into the new accounting domain."""
        model = _OneStepModel()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with NonterminalCacheExactValueSolver(
                model,
                cache_path=root / "values.sqlite3",
                cache_signature="one_step_v1",
                nonterminal_cache_row_limit=1,
                memory_cache_size=1,
            ) as solver:
                result = solver.solve(model.ROOT)
            self.assertEqual(result.value, Fraction(3, 5))
            self.assertEqual(result.cached_nonterminal_states, 1)
            self.assertEqual(result.nonterminal_states_added, 1)
            self.assertEqual(result.terminal_returns, 2)
            self.assertEqual(result.value_calls, 3)

    def test_n_plus_one_distinct_nonterminal_row_is_rejected_exactly(self) -> None:
        """Catches an off-by-one cap or a cap that still counts terminal returns."""
        model = _ChainModel()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache_path = root / "values.sqlite3"
            checkpoint_path = root / "progress.json"
            with NonterminalCacheExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="chain_v1",
                nonterminal_cache_row_limit=1,
                memory_cache_size=1,
                checkpoint_path=checkpoint_path,
                checkpoint_interval=1,
            ) as solver:
                with self.assertRaises(NonterminalCacheRowLimitExceeded):
                    solver.solve(model.ROOT)
            with closing(sqlite3.connect(cache_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM nonterminal_exact_values"
                ).fetchone()
            self.assertEqual(count, (1,))
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["status"], "BLOCKED")
            self.assertEqual(checkpoint["cached_nonterminal_states"], 1)
            self.assertEqual(checkpoint["terminal_returns"], 1)

    def test_old_solver_database_is_rejected_without_schema_mutation(self) -> None:
        """Catches accidental reuse or migration of the old cache schema."""
        model = _OneStepModel()
        with tempfile.TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "old.sqlite3"
            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="same_text",
                state_limit=10,
                memory_cache_size=1,
            ):
                pass
            with self.assertRaisesRegex(ValueError, "solver version|schema"):
                NonterminalCacheExactValueSolver(
                    model,
                    cache_path=cache_path,
                    cache_signature="same_text",
                    nonterminal_cache_row_limit=10,
                    memory_cache_size=1,
                )
            with closing(sqlite3.connect(cache_path)) as connection:
                names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            self.assertNotIn("nonterminal_exact_values", names)

    def test_new_database_records_fresh_solver_and_schema_identity(self) -> None:
        """Catches unsigned evidence or reuse of the old solver identity."""
        with tempfile.TemporaryDirectory() as temporary:
            cache_path = Path(temporary) / "new.sqlite3"
            with NonterminalCacheExactValueSolver(
                _OneStepModel(),
                cache_path=cache_path,
                cache_signature="fresh_v1",
                nonterminal_cache_row_limit=1,
                memory_cache_size=1,
            ):
                pass
            with closing(sqlite3.connect(cache_path)) as connection:
                metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            self.assertEqual(metadata["solver_version"], TERMINAL_BYPASS_SOLVER_VERSION)
            self.assertEqual(metadata["schema_version"], NONTERMINAL_CACHE_SCHEMA_VERSION)
            self.assertEqual(metadata["accounting_domain"], "nonterminal_bellman_states")

    def test_runner_allows_only_ordered_controls_then_single_v4_candidate(self) -> None:
        """Catches parameter-search CLI surface or v4 execution without controls."""
        parser = build_parser()
        option_strings = {
            option for action in parser._actions for option in action.option_strings
        }
        self.assertTrue({"--graph-id", "--output-root"} <= option_strings)
        self.assertFalse(
            option_strings
            & {
                "--prompt",
                "--exposure",
                "--target",
                "--horizon",
                "--floor",
                "--seed",
                "--workers",
                "--resume",
            }
        )
        graph_action = next(
            action for action in parser._actions if "--graph-id" in action.option_strings
        )
        self.assertEqual(
            tuple(graph_action.choices),
            ("i8_s3_v5", "i8_s3_v3", "i8_s3_v4"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "control"):
                run_diagnostic_graph("i8_s3_v4", output_root)
            self.assertFalse((output_root / "graphs" / "i8_s3_v4").exists())


if __name__ == "__main__":
    unittest.main()
