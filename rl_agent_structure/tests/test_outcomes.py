import copy
import unittest
from types import SimpleNamespace
from test_user_session import user_session, start
from personal_assistant.contracts.permission import ControllerAction as A


class OutcomeTests(unittest.TestCase):
    def test_explicit_six_price_reward_and_failure(self):
        from personal_assistant.learning.outcomes import MetricDelta, RewardWeights, compute_reward
        weights = RewardWeights(1, 1, .2, .3, .1, .05)
        self.assertAlmostEqual(compute_reward(MetricDelta(success=1, extra_question=2), weights), .8)
        self.assertAlmostEqual(compute_reward(MetricDelta(failure=1, retention=2), weights), -1.1)
        with self.assertRaises(ValueError):
            RewardWeights(1, 1, 0, 0, float('nan'), 0)
        with self.assertRaises(ValueError):
            MetricDelta(success=1, failure=1)

    def test_q40_complete_coverage_has_fixed_denominators_and_c_is_not_g(self):
        from personal_assistant.learning.outcomes import task_metrics
        user = user_session()
        session = start(user)
        result = session.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        metrics = task_metrics(session)
        self.assertEqual(metrics['task_success'], 1)
        self.assertEqual(metrics['task_failure'], 0)
        self.assertEqual(metrics['extra_read_instances'], 0)
        self.assertEqual(metrics['extra_write_instances'], 0)
        self.assertEqual(metrics['necessary_opportunities_write'], 4)
        self.assertEqual(metrics['unnecessary_opportunities_write'], 2)
        self.assertEqual(metrics['pp_write'], 1)
        self.assertEqual(metrics['hs_write'], 1)
        self.assertEqual(metrics['ad_write'], 1)
        self.assertIsNone(metrics['pp_read'])
        self.assertGreater(metrics['active_consent_items_after_task'], 0)
        self.assertEqual(metrics['active_gate_items_before_cleanup'], 0)
        self.assertEqual(metrics['idle_gate_key_checkpoints'], 0)
        self.assertEqual(metrics['authorization_violations'], 0)
        self.assertEqual(metrics['unverifiable_authorization_field_instances'], 0)

    def test_empty_execution_and_unknown_effect_do_not_earn_task_success(self):
        from personal_assistant.learning.outcomes import data_usage_metrics
        session = start(user_session())
        snapshot = session.store.snapshot()
        metrics = data_usage_metrics(session.task, snapshot)
        self.assertEqual(metrics['hs_write'], 0)
        self.assertEqual(metrics['ad_write'], 0)
        self.assertEqual(metrics['pp_write'], 1)
        unknown = data_usage_metrics(session.task, snapshot, complete_evidence=False)
        self.assertIsNone(unknown['pp_write'])
        self.assertIsNone(unknown['hs_write'])
        self.assertFalse(unknown['data_metrics_scorable'])

    def test_wide_receipts_count_instances_but_log_duplicates_do_not(self):
        from personal_assistant.learning.outcomes import task_metrics, data_usage_metrics
        session = start(user_session())
        view = session.advance()
        request = max((c for c in view.candidates if c.action == A.REQUEST and c.valid),
                      key=lambda c: len(c.request_scope.data_attributes))
        session.dispatch_control(request.candidate_id)
        view = session.advance()
        execute = max((c for c in view.candidates if c.action == A.EXECUTE and c.valid),
                      key=lambda c: len(c.operation_scope.data_attributes))
        session.dispatch_control(execute.candidate_id)
        snapshot = session.store.snapshot()
        before = task_metrics(session)
        self.assertEqual(before['extra_write_instances'], 2)
        duplicated = copy.deepcopy(snapshot)
        duplicated['data_flows'] += copy.deepcopy(snapshot['data_flows'])
        deduped = data_usage_metrics(session.task, duplicated)
        self.assertEqual(deduped['extra_write_instances'], 2)
        repeated = copy.deepcopy(snapshot)
        repeated['data_flows'] += [{**f, 'effect_id': 'another-real-effect'} for f in snapshot['data_flows']]
        counts = data_usage_metrics(session.task, repeated)
        self.assertEqual(counts['extra_write_instances'], 4)
        self.assertEqual(counts['unnecessary_used_write'], 2)
        self.assertEqual(counts['pp_write'], deduped['pp_write'])

    def test_blocked_attempt_is_not_an_executed_violation(self):
        from personal_assistant.learning.outcomes import _authorization_counts
        blocked = SimpleNamespace(payload={'disposition': 'blocked', 'task_step_id': 's',
                                          'tool_effect_status': None})
        self.assertEqual(_authorization_counts((), (blocked,)), (0, 0))
        flow = {'step_id': 's', 'field': 'x', 'effect_id': 'e'}
        self.assertEqual(_authorization_counts((flow,), (blocked,)), (0, 1))
        bad = SimpleNamespace(payload={'tool_effect_status': 'committed', 'tool_effect_id': 'e',
                                      'task_step_id': 's', 'pre_execution_authorized': False, 'checks': {}})
        self.assertEqual(_authorization_counts((flow,), (bad,)), (1, 0))

    def test_receipt_must_match_the_authorized_recipient_and_fields(self):
        from personal_assistant.learning.outcomes import _authorization_counts
        proof = SimpleNamespace(payload={'tool_effect_status': 'committed', 'tool_effect_id': 'e',
            'task_step_id': 's', 'pre_execution_authorized': True, 'checks': {},
            'tool': 'Weather', 'recipient': 'Weather', 'operation': 'update',
            'authorized_fields': ['Trip location']})
        flow = {'effect_id': 'e', 'step_id': 's', 'field': 'Trip location',
                'tool': 'Weather', 'recipient': 'Weather', 'direction': 'write'}
        self.assertEqual(_authorization_counts((flow,), (proof,)), (0, 0))
        self.assertEqual(_authorization_counts(({**flow, 'recipient': 'unapproved'},), (proof,)), (1, 0))
        self.assertEqual(_authorization_counts(({**flow, 'field': 'unapproved'},), (proof,)), (1, 0))

    def test_q55_both_contacts_are_one_extra_disclosure(self):
        from personal_assistant.learning.outcomes import task_metrics
        session = start(user_session(), 55)
        view = session.advance()
        request = max((c for c in view.candidates if c.action == A.REQUEST and c.valid),
                      key=lambda c: len(c.request_scope.data_attributes))
        session.dispatch_control(request.candidate_id)
        view = session.advance()
        execute = max((c for c in view.candidates if c.action == A.EXECUTE and c.valid),
                      key=lambda c: len(c.operation_scope.data_attributes))
        session.dispatch_control(execute.candidate_id)
        session.run()
        metrics = task_metrics(session)
        self.assertEqual(metrics['task_success'], 1)
        self.assertEqual(metrics['extra_write_instances'], 1)
        self.assertEqual(metrics['extra_permission_messages'], 1)
        self.assertEqual(metrics['necessary_opportunities_write'], 11)
        self.assertEqual(metrics['unnecessary_opportunities_write'], 1)
        self.assertEqual(metrics['necessary_used_write'], 11)
        self.assertEqual(metrics['unnecessary_used_write'], 1)


if __name__ == '__main__':
    unittest.main()
