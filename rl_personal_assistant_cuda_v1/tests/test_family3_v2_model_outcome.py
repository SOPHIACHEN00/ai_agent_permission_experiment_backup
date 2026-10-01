from __future__ import annotations

import unittest
from dataclasses import replace
from fractions import Fraction

from pa_rl.family3_v2_model import (
    Family3V2Model,
    Family3V2TerminationKind,
)
from pa_rl.family3_v2_outcome import (
    Family3V2OutcomeEvidence,
    evaluate_family3_v2_outcome,
)
from pa_rl.family3_v2_contracts import (
    ContinuationModeV2,
    FAMILY3_V2_CANDIDATE_ORDER,
    OfferWindowV2,
)
from pa_rl.family3_v2_suite import Family3V2KernelInput, build_family3_v2_suite


def _kernel(graph_index: int = 0) -> Family3V2KernelInput:
    return Family3V2KernelInput.from_graph(build_family3_v2_suite().graphs[graph_index])


def run_witness(graph_index: int, request_role: str, branch: str):
    """Choose the requested offer and a hand-selected first-effect branch."""
    model = Family3V2Model()
    state = model.initial_state(_kernel(graph_index))
    state = model.transition_distribution(state, request_role)[0].next_state
    transitions = model.transition_distribution(state, "execute_covering")
    wanted = ContinuationModeV2(branch)
    state = next(
        item.next_state
        for item in transitions
        if item.next_state.continuation_mode is wanted
    )
    while not state.terminated:
        state = model.transition_distribution(state, "execute_covering")[0].next_state
    return state


class Family3V2ModelOutcomeTests(unittest.TestCase):
    def test_reset_catalog_and_branch_are_literal_and_unrealized(self) -> None:
        """A missing row, wrong reset mask, or early future queue must fail."""
        model = Family3V2Model()
        state = model.initial_state(_kernel())
        candidates = model.candidates(state)
        self.assertEqual(tuple(row.role for row in candidates), FAMILY3_V2_CANDIDATE_ORDER)
        self.assertEqual(len(candidates), 7)
        self.assertEqual(
            tuple(row.mask_valid for row in candidates),
            (True, True, False, False, False, True, True),
        )
        self.assertEqual(state.queued_tasks, ())
        self.assertIs(state.continuation_mode, ContinuationModeV2.UNREALIZED)
        self.assertEqual(state.effect_index, 0)

    def test_verified_grant_closes_offer_and_disable_hits_nonemitted_guard(self) -> None:
        """Reopening the one-use offer or emitting a doomed state must fail."""
        model = Family3V2Model()
        requested = model.transition_distribution(
            model.initial_state(_kernel()), "request_narrow"
        )[0].next_state
        self.assertIs(requested.offer.offer_window, OfferWindowV2.CLOSED)
        by_role = {row.role.value: row for row in model.candidates(requested)}
        self.assertEqual(by_role["request_narrow"].invalid_reason, "offer_window_closed")
        self.assertEqual(by_role["request_broader"].invalid_reason, "offer_window_closed")
        self.assertEqual(by_role["refresh_closed"].invalid_reason, "offer_window_closed")

        disabled = model.transition_distribution(requested, "disable_active")[0]
        self.assertTrue(disabled.terminated)
        self.assertEqual(disabled.next_state.failure_reason, "irreversible_no_coverage")
        self.assertIs(disabled.next_state.offer.offer_window, OfferWindowV2.CLOSED)
        self.assertEqual(disabled.next_mask, ())
        guard = disabled.next_state.nonemitted_guard_catalog
        self.assertEqual(len(guard), 7)
        self.assertTrue(all(not row.emitted for row in guard))
        self.assertEqual(
            {row.role.value: row.invalid_reason for row in guard}["request_narrow"],
            "offer_window_closed",
        )

    def test_all_four_construction_witnesses_hold_for_every_graph(self) -> None:
        """Wrong coverage or exposure timing must break a literal witness cell."""
        for graph_index, graph in enumerate(build_family3_v2_suite().graphs):
            with self.subTest(graph=graph.graph_id):
                narrow_exact = run_witness(graph_index, "request_narrow", "exact")
                narrow_broader = run_witness(graph_index, "request_narrow", "broader")
                broader_exact = run_witness(graph_index, "request_broader", "exact")
                broader_broader = run_witness(graph_index, "request_broader", "broader")
                self.assertTrue(narrow_exact.success)
                self.assertEqual(narrow_exact.exposure_used, (graph.e + 2) * graph.n)
                self.assertEqual(narrow_broader.failure_reason, "irreversible_no_coverage")
                self.assertEqual(broader_exact.failure_reason, "exposure_budget_exceeded")
                self.assertTrue(broader_broader.success)
                self.assertEqual(broader_broader.exposure_used, (graph.d + 2) * graph.b)

    def test_first_execute_is_the_only_stochastic_transition(self) -> None:
        """Wrong probabilities or later branch redraws must fail exact-kernel checks."""
        model = Family3V2Model()
        state = model.transition_distribution(
            model.initial_state(_kernel()), "request_narrow"
        )[0].next_state
        transitions = model.transition_distribution(state, "execute_covering")
        self.assertEqual(tuple(item.probability for item in transitions), (Fraction(4, 5), Fraction(1, 5)))
        self.assertEqual(
            tuple(item.next_state.continuation_mode for item in transitions),
            (ContinuationModeV2.EXACT, ContinuationModeV2.BROADER),
        )
        exact = model.transition_from_residue(state, "execute_covering", 0)
        broader = model.transition_from_residue(state, "execute_covering", 4)
        self.assertIs(exact.next_state.continuation_mode, ContinuationModeV2.EXACT)
        self.assertIs(broader.next_state.continuation_mode, ContinuationModeV2.BROADER)
        if not exact.terminated:
            later = model.transition_distribution(exact.next_state, "execute_covering")
            self.assertEqual(tuple(item.probability for item in later), (Fraction(1),))

    def test_invalid_action_has_no_authority_resource_effect_or_branch_side_effect(self) -> None:
        """Dispatching a masked execute must not partially mutate trusted state."""
        model = Family3V2Model()
        state = model.initial_state(_kernel())
        failed = model.transition_distribution(state, "execute_covering")[0].next_state
        self.assertEqual(failed.failure_reason, "no_covering_authorization")
        self.assertEqual(failed.invalid_actions, 1)
        self.assertEqual(failed.prompts_used, state.prompts_used)
        self.assertEqual(failed.exposure_used, state.exposure_used)
        self.assertEqual(failed.authorization, state.authorization)
        self.assertEqual(failed.effect_index, state.effect_index)
        self.assertEqual(failed.continuation_mode, state.continuation_mode)
        self.assertEqual(failed.queued_tasks, state.queued_tasks)

    def test_exposure_failure_beats_same_step_natural_completion(self) -> None:
        """Checking completion before post-action exposure would reward the wrong witness."""
        state = run_witness(0, "request_broader", "exact")
        self.assertGreaterEqual(state.accumulated_utility, state.kernel.target)
        self.assertIsNone(state.current_task)
        self.assertEqual(state.failure_reason, "exposure_budget_exceeded")
        self.assertFalse(state.success)

    def test_natural_completion_on_last_decision_beats_horizon(self) -> None:
        """A valid final decision at index horizon-1 must not be truncated."""
        model = Family3V2Model()
        state = model.transition_distribution(
            model.initial_state(_kernel()), "request_narrow"
        )[0].next_state
        state = model.transition_from_residue(state, "execute_covering", 0).next_state
        state = replace(
            state,
            decision_index=state.kernel.horizon - 1,
            current_task=replace(state.current_task, utility=state.kernel.target - state.accumulated_utility),
            queued_tasks=(),
            exposure_used=0,
        )
        completed = model.transition_distribution(state, "execute_covering")[0]
        self.assertTrue(completed.terminated)
        self.assertFalse(completed.truncated)
        self.assertEqual(completed.reward, 1)
        self.assertIs(completed.next_state.termination_kind, Family3V2TerminationKind.NATURAL_COMPLETION)

    def test_only_natural_completion_can_receive_reward_one(self) -> None:
        """Accepting horizon or policy terminal closure would weaken the binary contract."""
        base = Family3V2OutcomeEvidence(
            closed=True,
            termination_kind=Family3V2TerminationKind.NATURAL_COMPLETION,
            accumulated_utility=3,
            utility_target=3,
            pending_required_task_count=0,
            prompts_used=1,
            prompt_budget=1,
            exposure_used=9,
            exposure_budget=9,
            invalid_actions=0,
            unauthorized_committed_effects=0,
            monitor_blocked_attempts=0,
        )
        self.assertEqual(evaluate_family3_v2_outcome(base).reward, 1)
        for kind in Family3V2TerminationKind:
            if kind in {Family3V2TerminationKind.IN_PROGRESS, Family3V2TerminationKind.NATURAL_COMPLETION}:
                continue
            with self.subTest(kind=kind):
                result = evaluate_family3_v2_outcome(replace(base, termination_kind=kind))
                self.assertEqual(result.reward, 0)
                self.assertFalse(result.success)

    def test_open_outcome_evidence_returns_a_nonterminal_zero_result(self) -> None:
        """Rejecting valid open evidence would break the evaluator's public return path."""
        result = evaluate_family3_v2_outcome(Family3V2OutcomeEvidence(
            closed=False,
            termination_kind=Family3V2TerminationKind.IN_PROGRESS,
            accumulated_utility=0,
            utility_target=3,
            pending_required_task_count=1,
            prompts_used=0,
            prompt_budget=1,
            exposure_used=0,
            exposure_budget=9,
            invalid_actions=0,
            unauthorized_committed_effects=0,
            monitor_blocked_attempts=0,
        ))
        self.assertFalse(result.terminal)
        self.assertEqual(result.reward, 0)
        self.assertFalse(result.success)
        self.assertEqual(result.failed_constraints, ())

    def test_public_integrity_failure_transition_owns_terminal_closure(self) -> None:
        """Removing the public model-owned anomaly transition must break mediation closure."""
        model = Family3V2Model()
        state = model.initial_state(_kernel())
        transition = model.transition_integrity_failure(state, "injected_integrity_failure")
        self.assertEqual(transition.next_state.failure_reason, "injected_integrity_failure")
        self.assertIs(transition.next_state.termination_kind, Family3V2TerminationKind.IRREVERSIBLE_FAILURE)
        self.assertEqual(transition.reward, 0)
        self.assertTrue(transition.terminated)
        self.assertFalse(transition.truncated)
        self.assertEqual(transition.next_mask, ())
        with self.assertRaises(ValueError):
            model.transition_integrity_failure(state, "")
        with self.assertRaises(ValueError):
            model.transition_integrity_failure(transition.next_state, "second_failure")


if __name__ == "__main__":
    unittest.main()
