from __future__ import annotations

import tempfile
import unittest
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from pa_rl.increment8_value_solver import (
    DiskBackedExactValueSolver,
    ExactStateLimitExceeded,
)


@dataclass(frozen=True, slots=True)
class _TinyState:
    name: str
    terminated: bool = False
    reward: int = 0


@dataclass(frozen=True, slots=True)
class _TinyCandidate:
    semantic_candidate_id: str
    mask_valid: bool = True


@dataclass(frozen=True, slots=True)
class _TinyTransition:
    probability: Fraction
    next_state: _TinyState


class _TinyExactModel:
    ROOT = _TinyState("root")
    WIN = _TinyState("win", terminated=True, reward=1)
    LOSS = _TinyState("loss", terminated=True, reward=0)

    def candidates(self, state: _TinyState) -> tuple[_TinyCandidate, ...]:
        if state.terminated:
            return ()
        return (_TinyCandidate("one_third"), _TinyCandidate("three_fifths"))

    def transition_distribution(
        self,
        state: _TinyState,
        semantic_candidate_id: str,
    ) -> tuple[_TinyTransition, ...]:
        if state != self.ROOT:
            raise ValueError("only the root has transitions")
        if semantic_candidate_id == "one_third":
            return (
                _TinyTransition(Fraction(1, 3), self.WIN),
                _TinyTransition(Fraction(2, 3), self.LOSS),
            )
        if semantic_candidate_id == "three_fifths":
            return (
                _TinyTransition(Fraction(3, 5), self.WIN),
                _TinyTransition(Fraction(2, 5), self.LOSS),
            )
        raise ValueError("unknown candidate")


class Increment8ValueSolverTests(unittest.TestCase):
    def test_exact_value_is_fraction_and_resumes_from_bounded_cache(self) -> None:
        model = _TinyExactModel()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cache_path = root / "values.sqlite3"
            checkpoint_path = root / "progress.json"

            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="tiny_exact_kernel_v1",
                state_limit=10,
                memory_cache_size=1,
                checkpoint_path=checkpoint_path,
                checkpoint_interval=1,
            ) as solver:
                first = solver.solve(model.ROOT)

            self.assertEqual(first.value, Fraction(3, 5))
            self.assertIs(type(first.value), Fraction)
            self.assertEqual(first.total_cached_states, 3)
            self.assertEqual(first.states_added, 3)
            self.assertLessEqual(first.peak_memory_cache_entries, 1)
            self.assertTrue(checkpoint_path.is_file())

            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="tiny_exact_kernel_v1",
                state_limit=10,
                memory_cache_size=1,
            ) as solver:
                resumed = solver.solve(model.ROOT)

            self.assertEqual(resumed.value, Fraction(3, 5))
            self.assertEqual(resumed.states_added, 0)
            self.assertGreaterEqual(resumed.disk_cache_hits, 1)

    def test_cache_signature_mismatch_is_rejected(self) -> None:
        model = _TinyExactModel()
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "values.sqlite3"
            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="first_kernel",
                state_limit=10,
                memory_cache_size=1,
            ):
                pass

            with self.assertRaisesRegex(ValueError, "cache signature"):
                DiskBackedExactValueSolver(
                    model,
                    cache_path=cache_path,
                    cache_signature="different_kernel",
                    state_limit=10,
                    memory_cache_size=1,
                )

    def test_unsigned_or_wrong_version_cache_is_rejected(self) -> None:
        model = _TinyExactModel()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            unsigned_path = root / "unsigned.sqlite3"
            with DiskBackedExactValueSolver(
                model,
                cache_path=unsigned_path,
                cache_signature="signed_kernel",
                state_limit=10,
                memory_cache_size=1,
            ) as solver:
                solver.solve(model.ROOT)
            with closing(sqlite3.connect(unsigned_path)) as connection:
                connection.execute("DELETE FROM metadata")
                connection.commit()
            with self.assertRaisesRegex(ValueError, "unsigned non-empty"):
                DiskBackedExactValueSolver(
                    model,
                    cache_path=unsigned_path,
                    cache_signature="signed_kernel",
                    state_limit=10,
                    memory_cache_size=1,
                )

            wrong_version_path = root / "wrong_version.sqlite3"
            with DiskBackedExactValueSolver(
                model,
                cache_path=wrong_version_path,
                cache_signature="signed_kernel",
                state_limit=10,
                memory_cache_size=1,
            ):
                pass
            with closing(sqlite3.connect(wrong_version_path)) as connection:
                connection.execute(
                    "UPDATE metadata SET value = 'wrong' WHERE key = 'solver_version'"
                )
                connection.commit()
            with self.assertRaisesRegex(ValueError, "solver version"):
                DiskBackedExactValueSolver(
                    model,
                    cache_path=wrong_version_path,
                    cache_signature="signed_kernel",
                    state_limit=10,
                    memory_cache_size=1,
                )

            wrong_schema_path = root / "wrong_schema.sqlite3"
            with DiskBackedExactValueSolver(
                model,
                cache_path=wrong_schema_path,
                cache_signature="signed_kernel",
                state_limit=10,
                memory_cache_size=1,
            ):
                pass
            with closing(sqlite3.connect(wrong_schema_path)) as connection:
                connection.execute(
                    "UPDATE metadata SET value = 'wrong' WHERE key = 'schema_version'"
                )
                connection.commit()
            with self.assertRaisesRegex(ValueError, "schema version"):
                DiskBackedExactValueSolver(
                    model,
                    cache_path=wrong_schema_path,
                    cache_signature="signed_kernel",
                    state_limit=10,
                    memory_cache_size=1,
                )

    def test_state_limit_blocks_before_n_plus_one_and_resumes(self) -> None:
        model = _TinyExactModel()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cache_path = root / "limited.sqlite3"
            checkpoint_path = root / "progress.json"
            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="limited_kernel",
                state_limit=2,
                memory_cache_size=1,
                checkpoint_path=checkpoint_path,
                checkpoint_interval=1,
            ) as solver:
                with self.assertRaises(ExactStateLimitExceeded):
                    solver.solve(model.ROOT)
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["status"], "BLOCKED")
            self.assertEqual(checkpoint["total_cached_states"], 2)

            with DiskBackedExactValueSolver(
                model,
                cache_path=cache_path,
                cache_signature="limited_kernel",
                state_limit=3,
                memory_cache_size=1,
            ) as solver:
                resumed = solver.solve(model.ROOT)
            self.assertEqual(resumed.value, Fraction(3, 5))
            self.assertEqual(resumed.total_cached_states, 3)
            self.assertEqual(resumed.states_added, 1)


if __name__ == "__main__":
    unittest.main()
