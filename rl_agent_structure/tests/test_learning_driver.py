import unittest
from test_user_session import user_session, start
from personal_assistant.learning.transitions import EpisodeEnd, HumanWait
from personal_assistant.permissions.rule_policy import LeastScopeRulePolicy
from personal_assistant.interaction.human_channel import LocalHumanChannel


class Collector:
    def __init__(self):
        self.transitions = []
    def select(self, boundary, **kwargs):
        return LeastScopeRulePolicy().choose(boundary.view)
    def observe(self, transition):
        self.transitions.append(transition)


class DriverTests(unittest.TestCase):
    def driver(self, user, learner, training=True):
        from personal_assistant.learning.driver import LearningDriver
        return LearningDriver(user, learner,
            lambda delta: delta.success - delta.failure - .1 * delta.extra_question,
            training=training, episode_mode='query')

    def run_task(self, driver, policy):
        for _ in range(500):
            boundary = driver.advance()
            if isinstance(boundary, EpisodeEnd):
                return boundary
            driver.step(policy.select(boundary))
        self.fail('no task end')

    def test_query_end_is_terminal_but_user_history_persists(self):
        user = user_session()
        start(user)
        learner = Collector()
        driver = self.driver(user, learner)
        end = self.run_task(driver, learner)
        self.assertTrue(end.terminated)
        self.assertIsNone(driver.pending_transition)
        self.assertTrue(learner.transitions[-1].done)
        self.assertIsNone(learner.transitions[-1].next_decision)
        count = len(learner.transitions)
        history = len(user.history.view())
        driver.advance()
        self.assertEqual(len(learner.transitions), count)
        start(user, 41)
        self.run_task(driver, learner)
        driver.finish_sequence()
        driver.finish_sequence()
        self.assertGreaterEqual(len(user.history.view()), history)
        self.assertEqual(sum(t.done for t in learner.transitions), 2)
        self.assertEqual(len({t.transition_id for t in learner.transitions}), len(learner.transitions))
        for transition in learner.transitions:
            if not transition.done:
                self.assertEqual(transition.pre_decision.view.position.task_id,
                                 transition.next_decision.view.position.task_id)

    def test_wait_has_no_fake_feedback_and_freeze_has_no_observe(self):
        user = user_session()
        start(user, channel=LocalHumanChannel())
        learner = Collector()
        driver = self.driver(user, learner)
        boundary = driver.advance()
        result = driver.step(learner.select(boundary))
        self.assertIsInstance(result, HumanWait)
        for _ in range(3):
            driver.advance()
        self.assertEqual(learner.transitions, [])
        with self.assertRaises(ValueError):
            driver.finish_sequence()

        other = user_session('bob')
        start(other)
        frozen = Collector()
        d2 = self.driver(other, frozen, False)
        self.run_task(d2, frozen)
        d2.finish_sequence()
        self.assertEqual(frozen.transitions, [])

    def test_failed_audit_prevents_delivery_to_replay(self):
        from dataclasses import replace
        from unittest.mock import patch
        from personal_assistant.learning.outcomes import task_metrics
        for failed_flag in ('ledger_replay_verified', 'monitor_audit_verified'):
            with self.subTest(failed_flag=failed_flag):
                user = user_session()
                session = start(user)
                learner = Collector()
                driver = self.driver(user, learner)
                real_result = session._result
                def broken_result(status):
                    return replace(real_result(status), **{failed_flag: False})
                with patch.object(session, '_result', side_effect=broken_result):
                    end = self.run_task(driver, learner)
                    metrics = task_metrics(session)
                    self.assertFalse(metrics['authorization_evidence_complete'])
                    self.assertFalse(metrics['data_metrics_scorable'])
                    self.assertTrue(end.integrity_failures)
                    self.assertEqual(learner.transitions, [])

    def test_raw_costs_sum_to_one_query_reward(self):
        from personal_assistant.learning.outcomes import RewardWeights, compute_reward, task_metrics, MetricDelta
        from personal_assistant.learning.driver import LearningDriver
        user = user_session()
        session = start(user)
        learner = Collector()
        weights = RewardWeights(1, 1, .2, .3, .1, .05)  # arithmetic fixture, not experiment prices
        driver = LearningDriver(user, learner, lambda d: compute_reward(d, weights), training=True)
        self.run_task(driver, learner)
        m = task_metrics(session)
        expected = compute_reward(MetricDelta(m['task_success'], m['task_failure'],
            m['extra_read_instances'], m['extra_write_instances'],
            m['extra_permission_messages'], m['idle_gate_key_checkpoints']), weights)
        self.assertAlmostEqual(sum(t.reward for t in learner.transitions), expected)

    def test_unknown_effect_stays_reportable_but_not_a_fake_terminal_sample(self):
        from helpers import binding
        from mock_tools.runtime import ReadWriteRuntime
        from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
        from personal_assistant.interaction.human_channel import HumanReply
        from personal_assistant.contracts.permission import PermissionChoice as C
        class UncertainTool(ReadWriteRuntime):
            def prepare_io_effect(self, *args, **kwargs):
                raise RuntimeError('effect status cannot be confirmed')
        user = user_session()
        task = binding(40)
        channel = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.ALLOW_REUSE))
        user.start_task('uncertain40', task, ScriptedPlanner(fixture_decisions(task.task)),
                        channel, UncertainTool())
        learner = Collector()
        driver = self.driver(user, learner)
        end = self.run_task(driver, learner)
        self.assertTrue(end.integrity_failures)
        self.assertFalse(end.terminated)
        self.assertTrue(end.truncated)
        self.assertFalse(any(t.done for t in learner.transitions))
        self.assertIsNotNone(driver.unresolved_transition)
        with self.assertRaises(ValueError):
            driver.finish_sequence()
        next_task = binding(41)
        user.start_task('after-uncertain41', next_task,
            ScriptedPlanner(fixture_decisions(next_task.task)),
            LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.ALLOW_REUSE)),
            ReadWriteRuntime())
        with self.assertRaisesRegex(ValueError, 'unresolved query'):
            driver.advance()


if __name__ == '__main__':
    unittest.main()
