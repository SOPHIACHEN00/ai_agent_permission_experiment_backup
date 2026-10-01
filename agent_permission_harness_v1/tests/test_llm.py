import importlib
import json
from pathlib import Path
import tempfile
import unittest


def wire():
    return {'kind': 'tool', 'tool': 'Cloud Drive', 'operation': 'read', 'resource': 'file',
            'requested_fields': ['title'], 'arguments_json': '{"record_id":"file"}',
            'answer': None, 'answer_status': None}


class LLMTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('agent_permission_harness_v1.llm')
        except ModuleNotFoundError:
            self.fail('generic bounded structured LLM transport is missing')

    def test_transport_uses_generic_schema_and_accounts_cost(self):
        m = self.module()
        requests = []
        def respond(payload):
            requests.append(payload)
            return {'model': 'o4-mini-2025-04-16', 'usage': {'prompt_tokens': 100, 'completion_tokens': 20},
                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(wire())}}]}
        with tempfile.TemporaryDirectory() as directory:
            t = m.StructuredChatTransport(Path(directory), requester=respond, budget_nusd=400_000_000)
            d = t.complete('Synthetic task only')
            self.assertEqual(d.arguments['record_id'], 'file')
            self.assertEqual(requests[0]['response_format']['json_schema']['schema']['additionalProperties'], False)
            self.assertFalse(requests[0]['store'])
            self.assertEqual(t.summary()['estimated_cost_usd'], 0.000198)
            with self.assertRaises(RuntimeError):
                t.complete('Cap prevents request')
            self.assertEqual(len(requests), 1)

    def test_failed_response_is_charged_and_not_retried(self):
        m = self.module()
        calls = []
        def respond(payload):
            calls.append(payload)
            bad = wire()
            bad['arguments_json'] = 'invalid'
            return {'model': 'o4-mini', 'usage': {'prompt_tokens': 100, 'completion_tokens': 20},
                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(bad)}}]}
        with tempfile.TemporaryDirectory() as directory:
            t = m.StructuredChatTransport(Path(directory), requester=respond)
            with self.assertRaises(RuntimeError):
                t.complete('synthetic')
            with self.assertRaises(RuntimeError):
                t.complete('no retry')
            self.assertEqual(len(calls), 1)
            self.assertEqual(t.summary()['automatic_retries'], 0)
            self.assertGreater(t.summary()['estimated_cost_usd'], 0)

    def test_wire_cannot_smuggle_permission_as_outer_field(self):
        m = self.module()
        bad = wire()
        bad['permission'] = 'allow_reuse'
        with self.assertRaises(ValueError):
            m.decode_wire(bad)
        bad = wire()
        bad['arguments_json'] = '[]'
        with self.assertRaises(ValueError):
            m.decode_wire(bad)


if __name__ == '__main__':
    unittest.main()
