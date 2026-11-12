"""Runtime accounting and authorization checks on original Wu tasks only."""
import unittest
from dataclasses import replace

from helpers import binding
from test_user_session import user_session, start
from personal_assistant.config import FUNCTIONAL_LIMITS
from personal_assistant.contracts.permission import ControllerAction as A, PermissionChoice as C
from personal_assistant.contracts.task import AgentResult
from personal_assistant.interaction.human_channel import LocalHumanChannel, HumanReply


class NoReleasePolicy:
    """Diagnostic policy: continue legal work, deliberately leave G enabled."""
    def choose(self, view):
        valid = [c for c in view.candidates if c.valid]
        execute = [c for c in valid if c.action == A.EXECUTE]
        requests = [c for c in valid if c.action == A.REQUEST]
        progress = execute or requests
        if progress:
            return min(progress, key=lambda c: (len((c.operation_scope or c.request_scope).data_attributes),
                                                c.candidate_id)).candidate_id
        return next(c.candidate_id for c in valid if c.action == A.END)


def choose_scope(session, action, *, contact=None, broad=False):
    view = session.advance()
    candidates = [c for c in view.candidates if c.valid and c.action == action]
    if contact is not None:
        candidates = [c for c in candidates if contact in (c.operation_scope or c.request_scope).data_attributes
                      and len((c.operation_scope or c.request_scope).data_attributes) == 11]
    choose = max if broad else min
    chosen = choose(candidates, key=lambda c: (len((c.operation_scope or c.request_scope).data_attributes), c.candidate_id))
    session.dispatch_control(chosen.candidate_id)
    return chosen


class FourActionRuntimeTests(unittest.TestCase):
    def test_q55_final_checkpoint_counts_before_cleanup_and_does_not_duplicate(self):
        u = user_session(policy=NoReleasePolicy()); s = start(u, 55)
        result = s.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(s.idle_gate_key_checkpoints, 11)
        self.assertEqual(len(s.terminal_active_gate_keys), 11)
        self.assertEqual(s.gate.active_keys(u.ledger, u.position), frozenset())
        self.assertEqual(sum(r.allows and r.status.value == 'active' for r in u.ledger.records()), 11)
        for _ in range(3): self.assertIsInstance(s.advance(), AgentResult)
        self.assertEqual(s.idle_gate_key_checkpoints, 11)
        self.assertEqual(len(s.terminal_active_gate_keys), 11)

    def test_rule_has_release_opportunity_and_preserves_always_consent(self):
        u = user_session(); s = start(u, 55); result = s.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(s.idle_gate_key_checkpoints, 0)
        self.assertEqual(len(s.terminal_active_gate_keys), 0)
        self.assertTrue(any(item['selected']['action'] == 'RELEASE' for item in result.controller_trace))
        self.assertEqual(sum(r.allows and r.status.value == 'active' for r in u.ledger.records()), 11)

    def test_q55_second_contact_question_is_extra_but_denial_is_not(self):
        def human(message):
            choice = C.DENY_PERSIST if message.requested_scope.data_attributes == ('Phone number',) else C.ALLOW_REUSE
            return HumanReply(message.message_id, 'permission', choice)
        u = user_session(); s = start(u, 55, channel=LocalHumanChannel(human))
        choose_scope(s, A.REQUEST, contact='Phone number')
        s.advance()
        self.assertEqual(s.extra_permission_messages, 0)
        choose_scope(s, A.REQUEST, contact='Email address')
        result = s.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(s.extra_permission_messages, 1)
        self.assertEqual(result.prompts_used, 12)
        self.assertNotIn('Phone number', result.tool_snapshot['outbox'][0]['data'])

    def test_q55_first_contact_and_user_required_once_confirmation_are_not_extra(self):
        u = user_session()
        channel = LocalHumanChannel(lambda message: HumanReply(message.message_id, 'permission', C.ALLOW_ONCE))
        first = start(u, 55, channel=channel, task_id='q55-first')
        choose_scope(first, A.REQUEST, contact='Email address')
        self.assertTrue(first.run().oracle_result['success'])
        self.assertEqual(first.extra_permission_messages, 0)
        again = start(u, 55, task_id='q55-again', channel=LocalHumanChannel(
            lambda message: HumanReply(message.message_id, 'permission', C.ALLOW_ONCE)))
        choose_scope(again, A.REQUEST, contact='Email address')
        result = again.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(result.prompts_used, 11)
        self.assertEqual(again.extra_permission_messages, 0)

    def test_terminal_policy_must_keep_partial_failed_tasks_in_results(self):
        limits = replace(FUNCTIONAL_LIMITS, max_permission_messages=1)
        u = user_session(runtime_limits=limits); s = start(u)
        result = s.run()
        self.assertFalse(result.oracle_result['success'])
        self.assertTrue(s._closed)
        self.assertEqual(result.prompts_used, 1)
        self.assertEqual(s.adapter.invocation_count, 0)
        self.assertEqual(result.tool_snapshot['data_flows'], [])
        self.assertIsNotNone(s.terminal_active_gate_keys)
        self.assertEqual(s.gate.active_keys(u.ledger, u.position), frozenset())

    def test_read_write_budgets_stop_actual_effects_not_only_reported_numbers(self):
        for query_id, limit in ((55, {'max_write_instances': 1}), (59, {'max_read_instances': 1})):
            with self.subTest(query_id=query_id):
                u = user_session(runtime_limits=replace(FUNCTIONAL_LIMITS, **limit))
                s = start(u, query_id); result = s.run()
                self.assertFalse(result.oracle_result['success'])
                self.assertTrue(s._closed)
                direction = 'write' if 'max_write_instances' in limit else 'read'
                self.assertLessEqual(sum(flow['direction'] == direction for flow in result.tool_snapshot['data_flows']), 1)

    def test_permission_expiry_requires_new_actual_answer_and_new_task_gates(self):
        u = user_session(n=1)
        first = start(u, 55, task_id='first55'); first_result = first.run()
        self.assertTrue(first_result.oracle_result['success'])
        old_gate = first.gate
        second = start(u, 55, task_id='second55')
        self.assertIsNot(second.gate, old_gate)
        view = second.advance()
        self.assertFalse(any(c.action == A.EXECUTE and c.valid for c in view.candidates))
        result = second.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(result.prompts_used, 11)
        self.assertEqual(second.extra_permission_messages, 0)

    def test_checkpoint_budget_reserves_one_terminal_check_without_clipping(self):
        u = user_session(policy=NoReleasePolicy(), runtime_limits=replace(FUNCTIONAL_LIMITS, max_checkpoints=1))
        s = start(u, 40); result = s.run()
        self.assertFalse(result.oracle_result['success'])
        self.assertEqual(result.status, 'checkpoint_limit')
        self.assertEqual(s.adapter.invocation_count, 1)
        self.assertEqual(len(s.checkpoint_events), 1)
        event = s.checkpoint_events[0]
        self.assertTrue(event['terminal'])
        self.assertEqual(event['idle_count'], len(s.terminal_active_gate_keys))
        self.assertEqual(s.idle_gate_key_checkpoints, event['idle_count'])

    def test_observed_contact_history_guides_rule_without_becoming_authority(self):
        def human(message):
            choice = C.DENY_REASK if message.requested_scope.data_attributes == ('Phone number',) else C.ALLOW_ONCE
            return HumanReply(message.message_id, 'permission', choice)
        u = user_session(n=1)
        previous = start(u, 55, task_id='observed55', channel=LocalHumanChannel(human))
        choose_scope(previous, A.REQUEST, contact='Phone number')
        previous.advance()
        choose_scope(previous, A.REQUEST, contact='Email address')
        self.assertTrue(previous.run().oracle_result['success'])
        current = start(u, 55, task_id='later55')
        view = current.advance()
        self.assertFalse(any(c.action == A.EXECUTE and c.valid for c in view.candidates))
        chosen = next(c for c in view.candidates if c.candidate_id == current.policy.choose(view))
        self.assertEqual(chosen.action, A.REQUEST)
        self.assertIn('Email address', chosen.request_scope.data_attributes)
        self.assertNotIn('Phone number', chosen.request_scope.data_attributes)
        self.assertEqual(len(current.channel.snapshot()['messages']), 0)

    def test_unknown_tool_effect_remains_unknown_and_does_not_become_success(self):
        from mock_tools.runtime import ReadWriteRuntime
        from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
        class FaultyTool(ReadWriteRuntime):
            def prepare_io_effect(self, *args, **kwargs):
                raise RuntimeError('effect cannot be reconciled')
        u = user_session(); b = binding(55)
        channel = LocalHumanChannel(lambda message: HumanReply(message.message_id, 'permission', C.ALLOW_REUSE))
        s = u.start_task('unknown55', b, ScriptedPlanner(fixture_decisions(b.task)), channel, FaultyTool())
        result = s.run()
        self.assertTrue(s._closed)
        self.assertFalse(result.oracle_result['success'])
        self.assertTrue(result.oracle_result['task_facts']['has_unknown_effect'])
        self.assertTrue(any(r.status.value == 'reconciliation_required' for r in u.ledger.records()))
        self.assertEqual(s.gate.active_keys(u.ledger, u.position), frozenset())

    def test_gate_capacity_failure_is_not_reported_as_user_denial(self):
        u = user_session(runtime_limits=replace(FUNCTIONAL_LIMITS, max_active_gates=1))
        s = start(u, 55)
        ends = [c for c in s.advance().candidates if c.action == A.END and c.valid]
        self.assertEqual([c.reason_code for c in ends], ['gate_limit'])
        result = s.run()
        self.assertEqual(result.status, 'gate_limit')
        self.assertFalse(result.oracle_result['success'])
        self.assertEqual(result.prompts_used, 0)
        self.assertEqual(len(u.history.view()), 0)
        self.assertEqual(s.adapter.invocation_count, 0)

    def test_release_can_make_room_so_end_cannot_abandon_a_feasible_next_step(self):
        u = user_session(runtime_limits=replace(FUNCTIONAL_LIMITS, max_active_gates=2))
        s = start(u, 40)
        choose_scope(s, A.REQUEST)
        s.advance()
        choose_scope(s, A.EXECUTE)
        for remaining in (2, 1):
            view = s.advance()
            self.assertEqual(len(s.gate.active_keys(u.ledger, u.position)), remaining)
            self.assertFalse(any(c.action == A.END and c.valid for c in view.candidates))
            self.assertFalse(any(c.action == A.REQUEST and c.valid for c in view.candidates))
            release = next(c for c in view.candidates if c.action == A.RELEASE and c.valid)
            s.dispatch_control(release.candidate_id)
        view = s.advance()
        self.assertTrue(any(c.action == A.REQUEST and c.valid for c in view.candidates))
        result = s.run()
        self.assertTrue(result.oracle_result['success'], result.error)
        self.assertEqual(s.adapter.invocation_count, 2)
        self.assertEqual(s.idle_gate_key_checkpoints, 0)


if __name__ == '__main__': unittest.main()
