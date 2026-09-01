"""Focused contract tests for the fixed-formula v1 exact-preflight runner."""

from __future__ import annotations

import json
import hashlib
import platform
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from pa_rl.contracts import canonical_hash
from pa_rl.increment8_v1_preflight import (
    CALIBRATION_VERSION,
    ORACLE_FLOOR,
    build_parser,
    build_v1_strategic_graphs,
    write_phase_summary,
)
from pa_rl.increment8_suite import INCREMENT8_SUITE_VERSION, build_increment8_suite
from pa_rl.increment8_value_solver import VALUE_SOLVER_VERSION


class Increment8V1PreflightTests(unittest.TestCase):
    @staticmethod
    def _expected_source_hashes() -> dict[str, str]:
        source_directory = Path(__file__).resolve().parents[1] / "src" / "pa_rl"
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

    @classmethod
    def _expected_signature(cls, graph: object) -> str:
        return canonical_hash(
            {
                "solver_version": VALUE_SOLVER_VERSION,
                "calibration_version": CALIBRATION_VERSION,
                "base_suite_version": INCREMENT8_SUITE_VERSION,
                "python_implementation": platform.python_implementation(),
                "python_version": platform.python_version(),
                "pickle_protocol": 5,
                "source_sha256": cls._expected_source_hashes(),
                "clock_semantics": "next_committed_effect_index",
                "family_formula": {
                    "exposure_budget": "exposure_v1=exposure_v0+8",
                    "utility_target": "target_v1=max(4,target_v0-1)",
                },
                "graph": graph.as_mapping(),
                "oracle_floor": {"numerator": 3, "denominator": 5},
            }
        )

    @staticmethod
    def _write_certificate(
        output_root: Path,
        graph_id: str,
        value: Fraction,
        *,
        graph_hash: str | None = None,
    ) -> None:
        graphs = {graph.graph_id: graph for graph in build_v1_strategic_graphs()}
        v0_by_id = {
            member.graph.graph_id: member.graph
            for member in build_increment8_suite().members
        }
        graph = graphs[graph_id]
        v0 = v0_by_id[graph_id]
        certificate = {
            "calibration_version": CALIBRATION_VERSION,
            "solver_version": VALUE_SOLVER_VERSION,
            "status": "CERTIFIED_PASS" if value >= ORACLE_FLOOR else "CERTIFIED_FAIL",
            "graph_id": graph_id,
            "graph": graph.as_mapping(),
            "graph_hash": graph_hash or canonical_hash(graph.as_mapping()),
            "base_suite_version": INCREMENT8_SUITE_VERSION,
            "source_sha256": Increment8V1PreflightTests._expected_source_hashes(),
            "cache_signature": Increment8V1PreflightTests._expected_signature(graph),
            "clock_semantics": "next_committed_effect_index",
            "family_formula": {
                "exposure_budget": "exposure_v1=exposure_v0+8",
                "utility_target": "target_v1=max(4,target_v0-1)",
            },
            "parameter_change": {
                "family": graph.family_index,
                "prompt_budget_v0": v0.prompt_budget,
                "prompt_budget_candidate": graph.prompt_budget,
                "exposure_budget_v0": v0.exposure_budget,
                "exposure_budget_candidate": graph.exposure_budget,
                "utility_target_v0": v0.utility_target,
                "utility_target_candidate": graph.utility_target,
                "horizon_v0": v0.horizon,
                "horizon_candidate": graph.horizon,
            },
            "oracle_value": {"numerator": value.numerator, "denominator": value.denominator},
            "oracle_floor": {"numerator": 3, "denominator": 5},
            "threshold_pass": value >= ORACLE_FLOOR,
            "solver_evidence": {
                "state_limit": 1_000_000,
                "memory_cache_size": 4_096,
                "checkpoint_interval": 1_000,
                "total_cached_states": 1,
                "states_added_this_process": 1,
                "memory_cache_hits": 0,
                "disk_cache_hits": 0,
                "peak_memory_cache_entries": 1,
                "max_recursion_depth": 1,
            },
        }
        path = output_root / "graphs" / graph_id / "certificate.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(certificate), encoding="utf-8")

    def test_builds_all_strategic_graphs_with_only_literal_family3_changes(self) -> None:
        """Catches a wrong v1 formula or an unintended family 0--2 rewrite."""
        v0_by_id = {
            member.graph.graph_id: member.graph
            for member in build_increment8_suite().members
        }
        graphs = build_v1_strategic_graphs()
        self.assertEqual(
            tuple(graph.graph_id for graph in graphs),
            tuple(f"i8_s{family}_v{variant}" for family in range(4) for variant in range(10)),
        )
        self.assertEqual(len(graphs), 40)

        family3_pairs = {
            graph.graph_id: (graph.exposure_budget, graph.utility_target)
            for graph in graphs
            if graph.family_index == 3
        }
        self.assertEqual(
            family3_pairs,
            {
                "i8_s3_v0": (24, 4),
                "i8_s3_v1": (22, 4),
                "i8_s3_v2": (26, 4),
                "i8_s3_v3": (24, 5),
                "i8_s3_v4": (28, 5),
                "i8_s3_v5": (18, 4),
                "i8_s3_v6": (20, 4),
                "i8_s3_v7": (18, 4),
                "i8_s3_v8": (22, 5),
                "i8_s3_v9": (24, 6),
            },
        )
        self.assertEqual(
            {graph.graph_id: graph for graph in graphs if graph.family_index != 3},
            {
                graph_id: v0_by_id[graph_id]
                for graph_id in tuple(f"i8_s{family}_v{variant}" for family in range(3) for variant in range(10))
            },
        )

    def test_writes_exact_sorted_family3_summary_from_real_certificates(self) -> None:
        """Catches incorrect cardinality, ordering, or fraction aggregation."""
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            values = {
                "i8_s3_v0": Fraction(3, 5),
                "i8_s3_v1": Fraction(4, 5),
                "i8_s3_v2": Fraction(7, 10),
                "i8_s3_v3": Fraction(1, 2),
                "i8_s3_v4": Fraction(3, 5),
                "i8_s3_v5": Fraction(9, 10),
                "i8_s3_v6": Fraction(2, 5),
                "i8_s3_v7": Fraction(3, 5),
                "i8_s3_v8": Fraction(1, 1),
                "i8_s3_v9": Fraction(3, 5),
            }
            for graph_id, value in reversed(tuple(values.items())):
                self._write_certificate(output_root, graph_id, value)

            summary = write_phase_summary(output_root, "family3")
            self.assertEqual(summary["graph_count"], 10)
            self.assertEqual(summary["pass_count"], 8)
            self.assertEqual(summary["fail_count"], 2)
            self.assertEqual(summary["status"], "CERTIFIED_FAIL")
            self.assertEqual(summary["macro_mean"], {"numerator": 67, "denominator": 100})
            self.assertEqual(summary["minimum_value"], {"numerator": 2, "denominator": 5})
            self.assertEqual(summary["minimum_graph_id"], "i8_s3_v6")
            self.assertEqual(
                [row["graph_id"] for row in summary["graphs"]],
                sorted(values),
            )
            self.assertEqual(
                json.loads((output_root / "family3_summary.json").read_text(encoding="utf-8")),
                summary,
            )

    def test_rejects_missing_or_inconsistent_family3_certificate(self) -> None:
        """Catches acceptance of incomplete or self-contradictory evidence."""
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "expected complete certificates"):
                write_phase_summary(output_root, "family3")

            for variant in range(10):
                self._write_certificate(output_root, f"i8_s3_v{variant}", Fraction(1))
            self._write_certificate(output_root, "i8_s3_v0", Fraction(1), graph_hash="wrong")
            with self.assertRaisesRegex(ValueError, "graph hash"):
                write_phase_summary(output_root, "family3")

    def test_rejects_unbound_certificate_fields(self) -> None:
        """Catches summary acceptance when solver and source bindings are absent or forged."""
        mutations = {
            "solver_version": None,
            "base_suite_version": "wrong",
            "source_sha256": {},
            "cache_signature": "wrong",
            "graph": {},
            "solver_evidence": {"state_limit": 1},
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                output_root = Path(temporary)
                for variant in range(10):
                    self._write_certificate(output_root, f"i8_s3_v{variant}", Fraction(1))
                path = output_root / "graphs" / "i8_s3_v0" / "certificate.json"
                certificate = json.loads(path.read_text(encoding="utf-8"))
                certificate[field] = replacement
                path.write_text(json.dumps(certificate), encoding="utf-8")
                with self.assertRaises(ValueError):
                    write_phase_summary(output_root, "family3")

    def test_accepts_zero_recursion_depth_from_a_fully_resumed_certificate(self) -> None:
        """Catches rejection when the initial state is returned directly from disk cache."""
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            for variant in range(10):
                self._write_certificate(output_root, f"i8_s3_v{variant}", Fraction(1))
            path = output_root / "graphs" / "i8_s3_v0" / "certificate.json"
            certificate = json.loads(path.read_text(encoding="utf-8"))
            certificate["solver_evidence"]["max_recursion_depth"] = 0
            path.write_text(json.dumps(certificate), encoding="utf-8")
            self.assertEqual(write_phase_summary(output_root, "family3")["status"], "CERTIFIED_PASS")

    def test_writes_and_requires_complete_strategic_summary(self) -> None:
        """Catches acceptance of a partial or extra 40-graph strategic certificate set."""
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            graph_ids = tuple(graph.graph_id for graph in build_v1_strategic_graphs())
            for graph_id in graph_ids:
                self._write_certificate(output_root, graph_id, Fraction(1))
            summary = write_phase_summary(output_root, "strategic")
            self.assertEqual(summary["graph_count"], 40)
            self.assertEqual(summary["status"], "CERTIFIED_PASS")
            self.assertEqual([row["graph_id"] for row in summary["graphs"]], list(graph_ids))

            (output_root / "graphs" / "i8_s0_v0" / "certificate.json").unlink()
            with self.assertRaisesRegex(ValueError, "expected complete certificates"):
                write_phase_summary(output_root, "strategic")

            self._write_certificate(output_root, "i8_s0_v0", Fraction(1))
            extra = output_root / "graphs" / "i8_extra" / "certificate.json"
            extra.parent.mkdir(parents=True)
            extra.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected complete certificates"):
                write_phase_summary(output_root, "strategic")

    def test_parser_does_not_expose_scientific_parameter_overrides(self) -> None:
        """Catches accidental CLI access to formula-defining controls."""
        parser = build_parser()
        option_strings = {option for action in parser._actions for option in action.option_strings}
        self.assertTrue({"--graph-id", "--summary", "--output-root"} <= option_strings)
        self.assertFalse(
            option_strings
            & {"--prompt", "--exposure", "--target", "--horizon", "--floor", "--seed", "--workers"}
        )


if __name__ == "__main__":
    unittest.main()
