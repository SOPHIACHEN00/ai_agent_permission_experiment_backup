"""Focused behavior tests for the Family-3 v2 literal suite and branch RNG."""

from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from fractions import Fraction
from unittest.mock import patch

from pa_rl.family3_v2_contracts import ContinuationModeV2
from pa_rl.family3_v2_rng import (
    continuation_from_residue,
    draw_family3_v2_branch_residue,
    residue_from_uint64s,
)
from pa_rl.family3_v2_suite import Family3V2KernelInput, _ROWS, build_family3_v2_suite
from pa_rl.scope_matching import ScopeRelation, covers, relation


_LITERAL_ROWS = (
    ("i8_f3v2_v0", "train", "c0_calendar", "agenda_summary", 4, 2, 1, 3, 9, 8),
    ("i8_f3v2_v1", "train", "c1_mail_archive", "status_notice", 1, 3, 1, 4, 12, 8),
    ("i8_f3v2_v2", "train", "c2_mail_send", "inbox_cleanup", 4, 3, 2, 4, 16, 8),
    ("i8_f3v2_v3", "train", "c3_report", "weekly_report", 1, 4, 2, 5, 12, 8),
    ("i8_f3v2_v4", "train", "c4_records", "approved_update", 4, 4, 3, 5, 30, 8),
    ("i8_f3v2_v5", "validation", "c0_calendar", "inbox_cleanup", 1, 5, 3, 6, 15, 9),
    ("i8_f3v2_v6", "validation", "c1_mail_archive", "weekly_report", 4, 5, 4, 6, 24, 9),
    ("i8_f3v2_v7", "test", "c2_mail_send", "approved_update", 1, 6, 4, 7, 24, 10),
    ("i8_f3v2_v8", "test", "c3_report", "agenda_summary", 4, 6, 5, 7, 21, 10),
    ("i8_f3v2_v9", "test", "c4_records", "status_notice", 1, 5, 3, 6, 30, 9),
)


class Family3V2SuiteRngTests(unittest.TestCase):
    def test_literal_suite_and_counterfactual(self) -> None:
        """A changed literal row or forecast swap must be observable at the kernel boundary."""
        suite = build_family3_v2_suite()
        literal_projection = tuple(
            (
                graph.graph_id,
                graph.split,
                graph.carrier_code,
                graph.purpose,
                graph.forecast_exact_probability.numerator,
                graph.e,
                graph.d,
                graph.target,
                graph.exposure_budget,
                graph.horizon,
            )
            for graph in suite.graphs
        )
        self.assertEqual(_ROWS, _LITERAL_ROWS)
        self.assertEqual(literal_projection, _ROWS)
        self.assertEqual(tuple(g.graph_id for g in suite.graphs), tuple(f"i8_f3v2_v{i}" for i in range(10)))
        self.assertEqual([g.split for g in suite.graphs], ["train"] * 5 + ["validation"] * 2 + ["test"] * 3)
        self.assertEqual([g.exposure_budget for g in suite.graphs], [9, 12, 16, 12, 30, 15, 24, 24, 21, 30])
        self.assertEqual([g.target for g in suite.graphs], [3, 4, 4, 5, 5, 6, 6, 7, 7, 6])
        for graph in suite.graphs:
            other = Family3V2KernelInput.from_graph(graph).forecast_counterfactual()
            self.assertEqual(other.branch_coupling_uid, graph.branch_coupling_uid)
            self.assertEqual(other.forecast_exact_probability, 1 - graph.forecast_exact_probability)

    def test_rejection_sampling_is_exactly_mod_five(self) -> None:
        """The rejection boundary and both forecast thresholds produce literal branches."""
        self.assertEqual(residue_from_uint64s(iter((2**64 - 1, 14))), 4)
        for residue in range(5):
            self.assertEqual(
                continuation_from_residue(Fraction(4, 5), Fraction(1, 5), residue),
                ContinuationModeV2.EXACT if residue < 4 else ContinuationModeV2.BROADER,
            )
            self.assertEqual(
                continuation_from_residue(Fraction(1, 5), Fraction(4, 5), residue),
                ContinuationModeV2.EXACT if residue < 1 else ContinuationModeV2.BROADER,
            )

    def test_counter_draw_records_the_accepted_payload_and_uint64(self) -> None:
        """A changed payload field, byte order, or attempt index changes the recorded evidence."""
        draw = draw_family3_v2_branch_residue(17, "a" * 64, 0)
        payload = '["i8_f3v2_branch_rng_v0",17,"' + ("a" * 64) + '",0,"continuation_branch",0,0]'
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        expected_uint64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        self.assertEqual(draw.payload, payload)
        self.assertEqual(draw.payload_sha256, hashlib.sha256(payload.encode("utf-8")).hexdigest())
        self.assertEqual(draw.attempt, 0)
        self.assertEqual(draw.accepted_uint64, expected_uint64)
        self.assertEqual(draw.residue, expected_uint64 % 5)

    def test_graph_validates_the_canonical_scope_coverage_relation(self) -> None:
        """A changed canonical coverage relation must make an otherwise literal graph invalid."""
        graph = build_family3_v2_suite().graphs[0]
        self.assertTrue(covers(graph.narrow_scope, graph.narrow_scope))
        self.assertTrue(covers(graph.broader_scope, graph.narrow_scope))
        self.assertFalse(covers(graph.narrow_scope, graph.broader_scope))
        self.assertEqual(relation(graph.narrow_scope, graph.narrow_scope), ScopeRelation.EXACT)
        self.assertEqual(relation(graph.broader_scope, graph.narrow_scope), ScopeRelation.NARROWER)
        self.assertEqual(relation(graph.narrow_scope, graph.broader_scope), ScopeRelation.BROADER)
        with patch("pa_rl.family3_v2_suite.covers", return_value=False, create=True):
            with self.assertRaises(ValueError):
                replace(graph)
        with patch("pa_rl.family3_v2_suite.relation", return_value=ScopeRelation.DISJOINT, create=True):
            with self.assertRaises(ValueError):
                replace(graph)

    def test_graph_and_kernel_reject_non_exact_or_inconsistent_integer_contracts(self) -> None:
        """Boolean/equality-equivalent integers and invalid derived kernels must fail closed."""
        graph = build_family3_v2_suite().graphs[0]
        for field_name in ("n", "b", "e", "d", "target", "prompt_budget", "exposure_budget", "horizon"):
            with self.subTest(contract="graph", field=field_name):
                with self.assertRaises(ValueError):
                    replace(graph, **{field_name: float(getattr(graph, field_name))})
        with self.assertRaises(ValueError):
            replace(graph, prompt_budget=True)

        kernel = Family3V2KernelInput.from_graph(graph)
        for field_name in ("e", "d", "target", "prompt_budget", "exposure_budget", "horizon"):
            with self.subTest(contract="kernel", field=field_name):
                with self.assertRaises(ValueError):
                    replace(kernel, **{field_name: float(getattr(kernel, field_name))})
        for replacement in (
            {"prompt_budget": True},
            {"d": kernel.e},
            {"exposure_budget": 0},
            {"horizon": 1},
            {"branch_coupling_uid": "A" * 64},
        ):
            with self.subTest(contract="kernel", replacement=replacement):
                with self.assertRaises(ValueError):
                    replace(kernel, **replacement)


if __name__ == "__main__":
    unittest.main()
