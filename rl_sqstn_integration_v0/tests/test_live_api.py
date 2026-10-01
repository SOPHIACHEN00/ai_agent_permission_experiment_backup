"""Bounded transport tests: only HTTP is replaced; the real adapter still runs."""
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from openai import OpenAI

from rl_sqstn_integration_v0.adapter import AdapterFault
from rl_sqstn_integration_v0.live_api import LiveTransport, LIVE_CONFIG, make_episode
from rl_sqstn_integration_v0.policies import rule_action


class LiveTests(unittest.TestCase):
    def client(self, handler):
        return OpenAI(api_key='test-not-a-secret', base_url='https://api.openai.com/v1',
                      max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    def success(self, request):
        body = json.loads(request.content)
        self.assertEqual(body['model'], 'o4-mini')
        self.assertEqual(body['max_completion_tokens'], 4096)
        self.assertNotIn('temperature', body)
        self.assertNotIn('seed', body)
        return httpx.Response(200, json={
            'id': 'chatcmpl-test', 'object': 'chat.completion', 'created': 1,
            'model': 'o4-mini-2025-04-16', 'service_tier': 'default',
            'system_fingerprint': None,
            'choices': [{'index': 0, 'finish_reason': 'stop', 'logprobs': None,
                         'message': {'role': 'assistant', 'content': '{"answer":"allow_once"}',
                                     'refusal': None, 'annotations': []}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120,
                      'prompt_tokens_details': {'cached_tokens': 0, 'audio_tokens': 0},
                      'completion_tokens_details': {'reasoning_tokens': 10, 'audio_tokens': 0,
                                                    'accepted_prediction_tokens': 0,
                                                    'rejected_prediction_tokens': 0}}})

    def test_fifth_attempt_and_unaffordable_attempt_never_reach_http(self):
        calls = []
        def handler(request):
            calls.append(request)
            return self.success(request)
        with tempfile.TemporaryDirectory() as tmp, self.client(handler) as client:
            transport = LiveTransport(client, Path(tmp))
            for _ in range(4):
                self.assertEqual(transport('synthetic permission', LIVE_CONFIG), '{"answer":"allow_once"}')
            with self.assertRaises(AdapterFault):
                transport('fifth call', LIVE_CONFIG)
            self.assertEqual(len(calls), 4)
            self.assertEqual(transport.estimated_cost_nusd, 792000)
        with tempfile.TemporaryDirectory() as tmp, self.client(handler) as client:
            transport = LiveTransport(client, Path(tmp), budget_nusd=1)
            with self.assertRaises(AdapterFault):
                transport('cannot afford', LIVE_CONFIG)
            self.assertEqual(transport.attempts, 0)
            self.assertEqual(len(calls), 4)

    def test_http_failure_keeps_reservation_stops_and_redacts_error(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429, json={'error': {'message': 'sensitive-sentinel',
                                  'type': 'rate_limit_error', 'code': 'rate_limit_exceeded'}})
        with tempfile.TemporaryDirectory() as tmp, self.client(handler) as client:
            transport = LiveTransport(client, Path(tmp))
            for _ in range(2):
                with self.assertRaises(AdapterFault):
                    transport('synthetic permission', LIVE_CONFIG)
            self.assertEqual(len(calls), 1)
            self.assertEqual(transport.accounted_cost_nusd, 238022400)
            self.assertNotIn('sensitive-sentinel', (Path(tmp)/'attempts.jsonl').read_text())

    def test_live_authority_and_cache_only_replay_match_without_http(self):
        with tempfile.TemporaryDirectory() as tmp, self.client(self.success) as client:
            transport = LiveTransport(client, Path(tmp))
            cache = {}
            first = make_episode(1, cache, 'live', transport)
            frame = first.reset(1)
            live = [frame.as_mapping()]
            for _ in range(2):
                result = first.step(rule_action(frame))
                frame = result.frame
                live.append(frame.as_mapping())
            self.assertTrue(result.done)
            self.assertTrue(first.summary()['task_success'])
            self.assertEqual(first.summary()['committed_effects'], 1)
            self.assertEqual(first.summary()['unauthorized_effects'], 0)
            replay = make_episode(1, cache, 'cache_only')
            frame = replay.reset(1)
            replayed = [frame.as_mapping()]
            for _ in range(2):
                result = replay.step(rule_action(frame))
                frame = result.frame
                replayed.append(frame.as_mapping())
            self.assertEqual(live, replayed)
            self.assertEqual(transport.attempts, 1)
            self.assertEqual(replay.private_artifacts()['live_calls'], 0)


if __name__ == '__main__':
    unittest.main()
