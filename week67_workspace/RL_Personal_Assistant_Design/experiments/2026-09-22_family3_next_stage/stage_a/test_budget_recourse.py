"""Small behavior group; hand-derived expectations, no learned-policy tests."""
from __future__ import annotations

import importlib
import unittest
from dataclasses import replace
from fractions import Fraction as F


class BudgetRecourseTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.m = importlib.import_module("budget_recourse")
            self.e = importlib.import_module("budget_recourse_env")
        except ModuleNotFoundError as error:
            self.fail(f"Approved budget-recourse feature is not implemented: {error.name}")

    def root(self, prompts: int = 2):
        return self.m.State(n1=1, n2=1, forecast=F(1, 5), future_high=F(1, 2),
                            exposure=9, prompts=prompts)

    def test_prompt_budget_reverses_optimal_first_action(self) -> None:
        # Catches ignoring future prompt consumption or failing to include recourse.
        solver = self.m.Solver()
        for prompts, narrow, broad in ((2, F(1, 5), F(1, 2)), (3, F(3, 5), F(1, 2))):
            q = solver.q_values(self.root(prompts))
            self.assertEqual(q["request_narrow"], narrow)
            self.assertEqual(q["request_broader"], broad)

    def test_last_stage_budget_changes_completion_value(self) -> None:
        # Catches budget checked only at request, not before every effect.
        solver = self.m.Solver()
        state = replace(self.root(), stage=2, prompts=1, exposure=3)
        self.assertEqual(solver.value(state), F(1, 5))
        self.assertEqual(solver.value(replace(state, exposure=6)), F(1))

    def test_strong_and_myopic_rules_use_the_specified_horizons(self) -> None:
        # Catches accidentally giving the local rule full-horizon DP labels.
        solver = self.m.Solver()
        self.assertEqual(solver.policy_value("current_task_rule", self.root()), F(1, 5))
        self.assertEqual(solver.policy_value("reservation_rule", self.root()), F(1, 2))
        self.assertEqual(solver.policy_value("reservation_rule", self.root(3)), F(3, 5))
        self.assertEqual(solver.policy_value("forecast_transfer_rule", self.root()), F(2, 5))

    def test_real_consent_costs_and_invalid_execution_are_nonvacuous(self) -> None:
        # Catches automatic scope escalation, missing issuance charges or unsafe effects.
        env = self.e.Environment(self.root(3), self.e.Tape(2, False, 1))
        before = env.snapshot()
        with self.assertRaises(ValueError):
            env.step("execute_covering")
        self.assertEqual(env.snapshot(), before)
        env.step("request_narrow")
        env.step("execute_covering")
        self.assertEqual((env.state.exposure, env.state.prompts, env.effect_count), (7, 2, 1))
        self.assertNotIn("execute_covering", self.m.legal_actions(env.state))
        before = env.snapshot()
        with self.assertRaises(ValueError):
            env.step("execute_covering")
        self.assertEqual(env.snapshot(), before)
        env.step("request_broader")
        self.assertEqual(env.consent_count, 2)
        env.step("execute_covering")
        self.assertEqual((env.state.stage, env.state.exposure, env.state.prompts), (2, 3, 1))
        self.assertEqual(env.active_grant_count, 0)
        env.step("request_narrow")
        env.step("execute_covering")
        env.step("execute_covering")
        self.assertEqual((env.state.status, env.effect_count, env.state.exposure), ("success", 4, 0))

    def test_forecast_hidden_until_boundary_and_disable_cannot_reopen(self) -> None:
        # Catches leaking private future draws or obtaining a fresh request after revocation.
        left = self.e.Environment(self.root(3), self.e.Tape(1, False, 1))
        right = self.e.Environment(self.root(3), self.e.Tape(2, True, 2))
        self.assertEqual(left.observation(), right.observation())
        left.step("request_narrow")
        left.step("disable")
        self.assertEqual(set(self.m.legal_actions(left.state)), {"deny", "escalate"})
        self.assertEqual(left.active_grant_count, 0)
        self.assertNotIn("request_refresh", self.m.legal_actions(right.state))

    def test_structural_solver_honors_its_resource_cap(self) -> None:
        # Catches an unbounded memo table; this intentional negative is not a failed run.
        solver = self.m.Solver(self.m.Budget(max_states=1))
        with self.assertRaises(self.m.ResourceLimit):
            solver.value(self.root())


if __name__ == "__main__":
    unittest.main()
