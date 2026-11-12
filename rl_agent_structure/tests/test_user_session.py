import unittest
from helpers import binding, key_for
from personal_assistant.config import PermissionConfig
from personal_assistant.contracts.permission import PermissionChoice as C, ControllerAction as A
from personal_assistant.contracts.task import ControlView, AgentResult
from personal_assistant.interaction.human_channel import LocalHumanChannel, HumanReply
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from mock_tools.runtime import ReadWriteRuntime


def user_session(user='alice', n=3, **kwargs):
    from personal_assistant.execution.user_session import UserSession
    return UserSession(user, PermissionConfig(n), **kwargs)


def start(user, q=40, channel=None, task_id=None):
    b = binding(q)
    if channel is None:
        channel = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.ALLOW_REUSE),
                                    session_id=f'{user.run_id}-{task_id or f"q{q}"}')
    return user.start_task(task_id or f'q{q}', b, ScriptedPlanner(fixture_decisions(b.task)), channel, ReadWriteRuntime())


class UserSessionTests(unittest.TestCase):
    def test_wait_resume_does_not_advance_round(self):
        u = user_session(); channel = LocalHumanChannel(session_id='wait'); s = start(u, channel=channel)
        result = s.run()
        self.assertEqual(result.status, 'awaiting_human')
        position = u.position; messages = len(channel.snapshot()['messages'])
        for _ in range(3): self.assertEqual(s.advance().status, 'awaiting_human')
        self.assertEqual(u.position, position)
        self.assertEqual(len(channel.snapshot()['messages']), messages)
        self.assertEqual(s.adapter.invocation_count, 0)
        self.assertIs(u.start_task('q40', binding(40), None, None, None), s)

    def test_cross_query_reuse_keeps_history_separate(self):
        u = user_session(); first = start(u); r1 = first.run()
        self.assertTrue(r1.oracle_result['success'], r1.error)
        h = len(u.history.view())
        second = start(u, 41); r2 = second.run()
        self.assertTrue(r2.oracle_result['success'], r2.error)
        asked = [m['message']['requested_scope'] for m in r2.human_snapshot['messages']]
        self.assertFalse(any(a and a['tool'] == 'Weather' for a in asked))
        self.assertGreaterEqual(len(u.history.view()), h)
        self.assertEqual(u.position.round_index, 2)
        self.assertTrue(r2.ledger_replay_verified)

    def test_never_is_not_reasked_by_next_query_and_failure_is_retained(self):
        u = user_session()
        ch = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.DENY_PERSIST))
        r1 = start(u, channel=ch).run()
        self.assertFalse(r1.oracle_result['success'])
        r2 = start(u, 41).run()
        self.assertFalse(r2.oracle_result['success'])
        self.assertEqual(r2.prompts_used, 0)
        self.assertEqual(u.position.round_index, 2)

    def test_task_end_exposes_release_or_end_not_future_requests(self):
        u = user_session(); s = start(u)
        for _ in range(100):
            v = s.advance()
            self.assertIsInstance(v, ControlView)
            if v.phase == 'task_end': break
            progress = [c for c in v.candidates if c.valid and c.action in (A.EXECUTE, A.REQUEST)]
            chosen = min(progress, key=lambda c: (c.action != A.EXECUTE,
                         len((c.operation_scope or c.request_scope).data_attributes), c.candidate_id))
            s.dispatch_control(chosen.candidate_id)
        self.assertIsNone(v.pending)
        self.assertTrue(all(c.action in (A.RELEASE, A.END) for c in v.candidates if c.valid))
        active = [c for c in v.candidates if c.action == A.RELEASE and c.valid]
        self.assertTrue(active)
        s.dispatch_control(active[0].candidate_id)
        r = s.run()
        self.assertTrue(r.oracle_result['success'])
        self.assertEqual(u.position.round_index, 1)

    def test_invalid_policy_still_closes_failed_task_and_allows_next_query(self):
        class BrokenPolicy:
            def choose(self, view): return 'not-a-candidate'
        u = user_session(); u.policy = BrokenPolicy(); s = start(u)
        result = s.run()
        self.assertEqual(result.status, 'policy_error')
        self.assertTrue(s._closed)
        self.assertFalse(result.oracle_result['success'])
        self.assertEqual(start(u, 41).user_context.position.round_index, 2)

    def test_external_revocation_refreshes_observation_before_new_selection(self):
        u = user_session(); s = start(u)
        v = s.advance()
        c = next(c for c in v.candidates if c.action == A.REQUEST and c.valid)
        s.dispatch_control(c.candidate_id); before = s.advance()
        execute = next(c for c in before.candidates if c.action == A.EXECUTE and c.valid)
        u.ledger.disable(execute.authorization_ids[0], u.position)
        fresh = s.advance()
        self.assertFalse(any(c.action == A.EXECUTE and c.valid for c in fresh.candidates))
        self.assertEqual(s.adapter.invocation_count, 0)


if __name__ == '__main__': unittest.main()
