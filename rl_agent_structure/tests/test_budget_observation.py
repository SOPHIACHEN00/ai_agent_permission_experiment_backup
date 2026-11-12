"""Expose existing task-local runtime clocks; do not change their accounting."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent), str(ROOT / 'tests')]

from test_user_session import user_session, start
from personal_assistant.config import FUNCTIONAL_LIMITS
from personal_assistant.contracts.permission import ControllerAction as A, canonical_hash
from personal_assistant.learning.driver import LearningDriver
from personal_assistant.learning.transitions import PublicEpisodeContext, DecisionBoundary, EpisodeEnd
from personal_assistant.permissions.rule_policy import LeastScopeRulePolicy


def legacy_context():
    return PublicEpisodeContext(256, 32, 1, 2, 0, False, False, 0, 0, 128, 512)


class BudgetObservationTests(unittest.TestCase):
    def make_driver(self, **kwargs):
        user = user_session(run_id='budget-observation', **kwargs)
        session = start(user)
        return user, session, LearningDriver(user, None, lambda _: 0., training=False)

    def choose(self, driver, action):
        boundary = driver.advance()
        self.assertIsInstance(boundary, DecisionBoundary)
        candidate = next(c for c in boundary.view.candidates if c.valid and c.action == action)
        driver.step(candidate.candidate_id)
        return driver.advance()

    def test_legacy_all_absent_accepted_and_partial_presence_rejected(self):
        context = legacy_context()
        for name in ('control_steps_used', 'control_step_limit', 'release_steps_used', 'release_step_limit'):
            self.assertIsNone(getattr(context, name))
            with self.subTest(name=name), self.assertRaises(ValueError):
                replace(context, **{name: 1})

    def test_budget_values_are_typed_and_limits_positive(self):
        context = replace(legacy_context(), control_steps_used=0, control_step_limit=64,
                          release_steps_used=0, release_step_limit=32)
        for name in ('control_steps_used', 'control_step_limit', 'release_steps_used', 'release_step_limit'):
            for value in (-1, True, 1.5, '1'):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    replace(context, **{name: value})
        for name in ('control_step_limit', 'release_step_limit'):
            with self.assertRaises(ValueError): replace(context, **{name: 0})
        # Observation must represent cleanup clocks faithfully, even past a limit.
        advanced = replace(context, control_steps_used=66, release_steps_used=33)
        self.assertEqual(advanced.control_steps_used, 66)

    def test_actual_request_release_execute_counters_are_observed(self):
        _, session, driver = self.make_driver()
        first = driver.advance()
        self.assertEqual((first.context.control_steps_used, first.context.release_steps_used), (0, 0))
        for action, main_used, release_used in ((A.REQUEST, 1, 0), (A.RELEASE, 2, 1),
                                              (A.REQUEST, 3, 1), (A.EXECUTE, 4, 1)):
            boundary = self.choose(driver, action)
            self.assertIsInstance(boundary, DecisionBoundary)
            self.assertEqual((boundary.context.control_steps_used, boundary.context.release_steps_used),
                             (main_used, release_used))
            self.assertEqual(boundary.context.control_steps_used, session._logical_step)
            self.assertEqual(boundary.context.release_steps_used, session._release_steps)
            self.assertEqual(boundary.context.control_step_limit, session.max_control_steps)
            self.assertEqual(boundary.context.release_step_limit, session.limits.max_release_steps)
        self.assertEqual(session.adapter.invocation_count, 1)

    def test_next_query_resets_local_counters_not_global_decision_index(self):
        user, _, driver = self.make_driver()
        for _ in range(100):
            boundary = driver.advance()
            if isinstance(boundary, EpisodeEnd): break
            driver.step(LeastScopeRulePolicy().choose(boundary.view))
        else: self.fail('rule task did not finish')
        previous_global = user.position.decision_index
        self.assertGreater(previous_global, 0)
        start(user, 41)
        boundary = driver.advance()
        self.assertEqual((boundary.context.control_steps_used, boundary.context.release_steps_used), (0, 0))
        self.assertEqual(boundary.view.position.decision_index, previous_global)
        expected_token = canonical_hash((user.user_id, user.run_id, user.position.task_id,
                                         user.position.decision_index))
        self.assertEqual(boundary.token, expected_token)

    def test_exhausted_main_budget_stays_zero_during_cleanup(self):
        limits = replace(FUNCTIONAL_LIMITS, max_control_steps=1, max_release_steps=3)
        _, session, driver = self.make_driver(runtime_limits=limits)
        terminal_boundary = self.choose(driver, A.REQUEST)
        self.assertEqual(terminal_boundary.view.phase, 'task_end')
        self.assertEqual(terminal_boundary.context.control_steps_used, 1)
        self.assertEqual(max(0, terminal_boundary.context.control_step_limit
                             - terminal_boundary.context.control_steps_used), 0)
        cleanup_boundary = self.choose(driver, A.RELEASE)
        self.assertEqual(cleanup_boundary.view.phase, 'task_end')
        self.assertEqual((cleanup_boundary.context.control_steps_used, cleanup_boundary.context.release_steps_used), (2, 1))
        self.assertEqual(max(0, cleanup_boundary.context.control_step_limit
                             - cleanup_boundary.context.control_steps_used), 0)
        self.assertEqual(session.max_control_steps, 1)
        self.assertEqual(session._terminal, 'controller_limit')
        self.assertEqual(session.adapter.invocation_count, 0)


if __name__ == '__main__': unittest.main()
