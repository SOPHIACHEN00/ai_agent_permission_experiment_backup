import tempfile
from copy import deepcopy
import unittest
from unittest.mock import patch
from pathlib import Path

from rl_sqstn_integration_v0.adapter import AdapterFault
from rl_sqstn_integration_v0.multistep_v1 import cases, enumerate_graph, coverage, frame_from_mapping
from rl_sqstn_integration_v0.collect_multistep import Campaign
from rl_sqstn_integration_v0.tests.test_live_api import LiveTests


class MultistepTests(unittest.TestCase):
    def test_output_failure_reconciles_successful_call_only_once(self):
        helper = LiveTests()
        with tempfile.TemporaryDirectory() as temp, helper.client(helper.success) as client:
            campaign = Campaign(client, Path(temp))
            with patch('builtins.print', side_effect=BrokenPipeError), self.assertRaises(AdapterFault):
                campaign('synthetic permission', {'approved': True, 'model': 'o4-mini',
                         'temperature': None, 'seed': None, 'max_calls': 4})
            self.assertEqual(campaign.accounted_nusd, 198000)
            self.assertEqual(campaign.estimated_nusd, 198000)
            self.assertTrue(campaign.failed)
            with self.assertRaises(AdapterFault):
                campaign('must not retry', {})
            self.assertEqual(campaign.attempts, 1)

    def test_refresh_coverage_requires_the_same_intervened_history(self):
        cache = {}
        graph = enumerate_graph(cases('train')[3], cache, lambda *_: '{"answer":"allow_reuse"}')
        self.assertTrue(coverage([graph], cache)['gates']['train_forced_disable_then_refresh'])
        missing_proof = deepcopy(graph)
        for node in missing_proof['nodes'].values():
            node['request_links'] = []
        self.assertFalse(coverage([missing_proof], cache)['gates']['train_forced_disable_then_refresh'])

    def test_complete_tree_preserves_history_and_replays_without_network(self):
        cache, calls = {}, []
        def answer(prompt, config):
            calls.append(prompt)
            return '{"answer":"allow_reuse"}'
        graph = enumerate_graph(cases('train')[0], cache, answer)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(cache), 3)
        self.assertTrue(any(n['summary']['task_success'] for n in graph['nodes'].values()))
        for node in graph['nodes'].values():
            frame = frame_from_mapping(node['frame'])
            self.assertEqual(set(node['edges']), {str(i) for i, flag in enumerate(frame.observation.action_mask) if flag})
            self.assertLessEqual(len(frame.answers), 2)
        self.assertEqual(enumerate_graph(cases('train')[0], cache), graph)
        self.assertEqual(len(calls), 3)
        with self.assertRaises(AdapterFault):
            enumerate_graph(cases('train')[0], {})

    def test_consumption_forced_disable_and_denial_are_distinct(self):
        once = enumerate_graph(cases('train')[1], {}, lambda *_: '{"answer":"allow_once"}')
        self.assertTrue(any(n['summary']['task_success'] and len(n['frame']['permission_answers']) == 2
                            for n in once['nodes'].values()))
        forced = enumerate_graph(cases('train')[3], {}, lambda *_: '{"answer":"allow_reuse"}')
        self.assertTrue(any(n['summary']['task_success'] and n['summary']['protocol_disables'] == 1
                            and len(n['frame']['permission_answers']) == 2 for n in forced['nodes'].values()))
        denied = enumerate_graph(cases('train')[2], {}, lambda *_: '{"answer":"deny_persist"}')
        self.assertFalse(any(n['summary']['task_success'] for n in denied['nodes'].values()))
        self.assertTrue(all(n['summary']['committed_effects'] == 0 for n in denied['nodes'].values()))
        self.assertFalse(coverage([denied], {})['passed'])

    def test_global_twenty_fifth_call_and_budget_exhaustion_do_not_send(self):
        helper = LiveTests()
        with tempfile.TemporaryDirectory() as temp, helper.client(helper.success) as client:
            campaign = Campaign(client, Path(temp))
            for _ in range(24):
                campaign('synthetic permission', {'approved': True, 'model': 'o4-mini',
                         'temperature': None, 'seed': None, 'max_calls': 4})
            with self.assertRaises(AdapterFault):
                campaign('too many', {})
            self.assertEqual(campaign.attempts, 24)
            self.assertEqual(campaign.accounted_nusd, 4752000)
        with tempfile.TemporaryDirectory() as temp, helper.client(helper.success) as client:
            campaign = Campaign(client, Path(temp), budget_nusd=1)
            with self.assertRaises(AdapterFault):
                campaign('too costly', {})
            self.assertEqual(campaign.attempts, 0)


if __name__ == '__main__':
    unittest.main()
