from __future__ import annotations

import unittest
from dataclasses import dataclass
from fractions import Fraction

from pa_rl.family3_v2_exact_solver import Family3V2ValueFirstExactSolver  # RED anchor: solver must exist first.
from pa_rl.family3_v2_exact_reference import (
    TerminalFreeReferenceResult,
    enumerate_terminal_free_reference,
)


@dataclass(frozen=True)
class _Kernel:
    source_graph_id: str


@dataclass(frozen=True)
class _State:
    name: str
    decision_index: int
    kernel: _Kernel
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


class _PoisonTerminal:
    terminated = True
    reward = 1

    def __hash__(self):
        raise AssertionError("terminal was inserted into a state table")

    def __getattribute__(self, name: str):
        if name in {"terminated", "reward", "__class__", "__hash__"}:
            return object.__getattribute__(self, name)
        raise AssertionError(f"terminal was serialized through {name}")


class _Model:
    def __init__(self, edges):
        self.edges = edges

    def candidates(self, state):
        return tuple(_Candidate(key) for key in self.edges.get(state.name, {}))

    def transition_distribution(self, state, candidate_id):
        return self.edges[state.name][candidate_id]


class Family3V2ExactReferenceTests(unittest.TestCase):
    def test_result_rejects_non_tuple_root_q_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "caller-ordered tuple"):
            TerminalFreeReferenceResult(
                "i8_f3v2_v0", Fraction(1), [("a", Fraction(1))], 1, 1, 1, 1, 0
            )

    def test_result_rejects_empty_root_action_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty string"):
            TerminalFreeReferenceResult(
                "i8_f3v2_v0", Fraction(1), (("", Fraction(1)),), 1, 1, 1, 1, 0
            )

    def test_result_rejects_duplicate_root_action_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique"):
            TerminalFreeReferenceResult(
                "i8_f3v2_v0",
                Fraction(1),
                (("a", Fraction(1)), ("a", Fraction(0))),
                1,
                1,
                1,
                1,
                0,
            )

    def test_reference_is_terminal_free_and_preserves_root_order(self) -> None:
        kernel = _Kernel("i8_f3v2_v0")
        root = _State("root", 0, kernel)
        model = _Model({
            "root": {
                "request_narrow": (_Transition(Fraction(1), _PoisonTerminal()),),
                "request_broader": (_Transition(Fraction(1), _State("lose", 1, kernel, True, 0)),),
            }
        })
        result = enumerate_terminal_free_reference(model, root, ("request_broader", "request_narrow"))
        self.assertEqual(result.root_value, Fraction(1))
        self.assertEqual(result.root_q_values, (("request_broader", Fraction(0)), ("request_narrow", Fraction(1))))
        self.assertEqual(result.nonterminal_state_count, 1)
        self.assertEqual(result.terminal_leaf_count, 2)
        self.assertTrue(result.__dataclass_params__.frozen)
        self.assertFalse(hasattr(result, "__dict__"))

    def test_reference_rejects_wrong_graph_and_nonadvancing_or_invalid_transitions(self) -> None:
        unsupported = _State("root", 0, _Kernel("i8_f3v2_v2"))
        valid_terminal = _State("done", 1, unsupported.kernel, True, 1)
        nonadvancing = _State("child", 0, _Kernel("i8_f3v2_v0"))
        v0 = _State("root", 0, _Kernel("i8_f3v2_v0"))
        cases = (
            (_Model({"root": {"request_narrow": (_Transition(Fraction(1), valid_terminal),)}}), unsupported),
            (_Model({"root": {"request_narrow": (_Transition(Fraction(1), nonadvancing),)}}), v0),
            (_Model({"root": {"request_narrow": (_Transition(Fraction(2, 3), valid_terminal),)}}), v0),
            (_Model({"root": {}}), v0),
        )
        for model, state in cases:
            with self.subTest(state=state.kernel.source_graph_id), self.assertRaises(ValueError):
                enumerate_terminal_free_reference(model, state, ("request_narrow",))

    def test_reference_rejects_v0_or_v1_root_with_mixed_graph_nonterminal_child(self) -> None:
        for root_graph, child_graph in (
            ("i8_f3v2_v0", "i8_f3v2_v1"),
            ("i8_f3v2_v1", "i8_f3v2_v0"),
        ):
            root = _State("root", 0, _Kernel(root_graph))
            child = _State("child", 1, _Kernel(child_graph))
            terminal = _State("done", 2, _Kernel(child_graph), True, 1)
            model = _Model({
                "root": {"request_narrow": (_Transition(Fraction(1), child),)},
                "child": {"execute_covering": (_Transition(Fraction(1), terminal),)},
            })
            with self.subTest(root_graph=root_graph), self.assertRaisesRegex(
                ValueError, "same supported source graph"
            ):
                enumerate_terminal_free_reference(model, root, ("request_narrow",))


if __name__ == "__main__":
    unittest.main()
