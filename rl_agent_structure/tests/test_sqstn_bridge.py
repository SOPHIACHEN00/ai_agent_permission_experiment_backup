import unittest
import importlib.util
from helpers import ROOT, binding, key_for
from personal_assistant.interaction.history import UserHistory, ObservedAnswer
from personal_assistant.contracts.permission import PermissionChoice as C
from personal_assistant.contracts.persistence import RoundPosition


@unittest.skipUnless(
    all(importlib.util.find_spec(name) is not None for name in ('pandas', 'sklearn', 'qstn', 'jsonschema')),
    'install requirements-agent.txt and s-qstn/requirements.txt for bridge integration tests',
)
class SQSTNBridgeTests(unittest.TestCase):
    def bridge(self, history=None):
        from personal_assistant.interaction.sqstn_bridge import SQSTNBridge
        return SQSTNBridge(ROOT.parent / 's-qstn', 'alice', 'persistent_granters', history or UserHistory('alice'))

    def test_sqstn_memory_is_past_and_user_local(self):
        h = UserHistory('alice')
        h.append(ObservedAnswer('alice', 40, key_for(), C.ALLOW_REUSE, 'observed-1', 1))
        h.append(ObservedAnswer('alice', 40, key_for(), C.DENY_PERSIST, 'future-5', 5))
        b = self.bridge(h)
        e = b.compile_request(binding(41), key_for(41), RoundPosition('alice', 'q41', 2, 2), 3, before_event_index=2)
        self.assertEqual(e.status, 'ready')
        self.assertEqual(e.simulator_private_audit['memory_event_ids'], ['observed-1'])
        self.assertTrue(e.simulator_private_audit['memory_audit']['transition_audit'])
        text = '\n'.join(m['content'] for m in e.messages)
        self.assertIn(binding(41).task.goal, text)
        self.assertIn('Yes, always share', text)
        self.assertIn('3 task rounds', text)
        self.assertIn('Weather', text)
        self.assertIn('Trip location', text)
        self.assertNotIn('future-5', text)
        with self.assertRaises(ValueError): h.append(ObservedAnswer('bob', 40, key_for(user='bob'), C.ALLOW_ONCE, 'foreign', 6))

    def test_unknown_extension_manual_and_invalid_reply_never_authorizes(self):
        b = self.bridge()
        for q in (63, 64):
            w = binding(q)
            e = b.compile_request(w, w.keys_for('alice', f'q{q}')[0], RoundPosition('alice', f'q{q}', 1), 3)
            self.assertEqual(e.status, 'manual_confirmation_required')
            self.assertEqual(e.messages, ())
        e = b.compile_request(binding(40), key_for(), RoundPosition('alice', 'q40', 1), 3)
        with self.assertRaises(ValueError): b.parse_reply('{"clarification":"yes"}', e.request_id)
        with self.assertRaises(ValueError): b.parse_reply('{"answer":"No, never share","answer":"Yes, always share"}', e.request_id)
        answer = b.parse_reply('{"answer":"Yes, but ask me next time"}', e.request_id)
        self.assertEqual(answer.choice, C.ALLOW_ONCE)
        self.assertEqual(len(b.history.view()), 0)  # dispatcher, not parser, records a received/accepted answer
        with self.assertRaises(ValueError): b.parse_reply('{"answer":"Yes, always share"}', 'unknown')

    def test_prompt_adapter_connects_human_channel_to_actual_ledger(self):
        from personal_assistant.interaction.sqstn_bridge import SQSTNResponder
        from personal_assistant.interaction.human_channel import LocalHumanChannel
        from personal_assistant.contracts.permission import ControllerAction as A
        from test_user_session import user_session, start
        u = user_session()
        bridge = self.bridge(u.history)
        responder = SQSTNResponder(bridge, u, lambda envelope: '{"answer":"Yes, always share"}', response_source='explicit_fixture')
        channel = LocalHumanChannel(responder)
        s = start(u, channel=channel)
        v = s.advance(); request = next(c for c in v.candidates if c.action == A.REQUEST and c.valid)
        s.dispatch_control(request.candidate_id); v = s.advance()
        execute = next(c for c in v.candidates if c.action == A.EXECUTE and c.valid)
        s.dispatch_control(execute.candidate_id)
        self.assertEqual(s.adapter.invocation_count, 1)
        self.assertEqual(len(u.history.view()), 2)
        self.assertTrue(all(a.source == 'explicit_fixture' for a in u.history.view()))


if __name__ == '__main__': unittest.main()
