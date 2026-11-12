"""Four controller families must cause their advertised state transitions."""
import unittest
from test_user_session import user_session, start
from personal_assistant.contracts.permission import ControllerAction as A, PermissionChoice as C
from personal_assistant.interaction.human_channel import LocalHumanChannel, HumanReply


class FourActions(unittest.TestCase):
    def choose(self, s, action):
        v = s.advance()
        candidates = [c for c in v.candidates if c.action == action and c.valid]
        selected = min(candidates, key=lambda c: (len((c.request_scope or c.operation_scope).data_attributes)
                       if c.request_scope or c.operation_scope else 0, c.candidate_id))
        s.dispatch_control(selected.candidate_id)
        return selected

    def test_exactly_four_families(self):
        self.assertEqual(tuple(a.value for a in A), ('REQUEST', 'EXECUTE', 'RELEASE', 'END'))

    def test_release_preserves_consent_and_reactivation_does_not_reask(self):
        u = user_session(); s = start(u)
        self.choose(s, A.REQUEST); before = s.advance()
        self.assertTrue(any(c.action == A.EXECUTE and c.valid for c in before.candidates))
        records = u.ledger.records()
        history_count = len(u.history.view())
        message_count = len(s.channel.snapshot()['messages'])
        release = self.choose(s, A.RELEASE)
        self.assertEqual(u.ledger.records(), records)
        self.assertTrue(release.release_keys)
        self.assertFalse(set(release.release_keys) & s.gate.active_keys(u.ledger, u.position))
        self.choose(s, A.REQUEST); s.advance()
        self.assertEqual(len(u.history.view()), history_count)
        self.assertEqual(len(s.channel.snapshot()['messages']), message_count)
        self.choose(s, A.EXECUTE)
        self.assertEqual(s.adapter.invocation_count, 1)

    def test_end_is_not_an_unconditional_escape_from_a_possible_task(self):
        u = user_session(); s = start(u)
        self.assertFalse(any(c.action == A.END and c.valid for c in s.advance().candidates))
        deny = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', C.DENY_PERSIST))
        stopped = start(user_session('bob'), channel=deny)
        self.choose(stopped, A.REQUEST)
        view = stopped.advance()
        self.assertTrue(any(c.action == A.END and c.valid for c in view.candidates))
        result = stopped.run()
        self.assertFalse(result.oracle_result['success'])
        self.assertEqual(stopped.adapter.invocation_count, 0)


if __name__ == '__main__': unittest.main()
