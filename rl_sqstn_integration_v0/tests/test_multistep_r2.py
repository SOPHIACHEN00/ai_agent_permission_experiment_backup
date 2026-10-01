import json
import tempfile
import unittest
from pathlib import Path

from rl_sqstn_integration_v0 import multistep_v1 as old
from rl_sqstn_integration_v0.adapter import AdapterFault
from rl_sqstn_integration_v0.live_api import LIVE_CONFIG
from rl_sqstn_integration_v0.tests import test_live_api


class RevisionTests(unittest.TestCase):
    def test_fourth_scope_history_is_retained_not_dropped(self):
        from rl_sqstn_integration_v0.multistep_r2 import enumerate_graph
        case = old.cases('train')[2]
        with self.assertRaises(AdapterFault):
            old.enumerate_graph(case, {}, lambda *_: '{"answer":"allow_reuse"}')
        cache = {}
        graph = enumerate_graph(case, cache, lambda *_: '{"answer":"allow_reuse"}')
        self.assertEqual(len(cache), 4)
        self.assertEqual(enumerate_graph(case, cache), graph)
        self.assertTrue(any(n['summary']['task_success'] for n in graph['nodes'].values()))

    def test_existing_nine_responses_keep_keys_and_complete_graphs(self):
        from rl_sqstn_integration_v0.multistep_r2 import enumerate_graph
        from rl_sqstn_integration_v0.collect_multistep_r2 import import_prior
        root = Path(__file__).resolve().parents[3]/'RL_Personal_Assistant_Design/experiments/2026-09-23_sqstn_rl_integration_v0/multistep_cache_pilot_v1/collection'
        cache, receipt = import_prior(root)
        self.assertEqual(len(cache), 9)
        self.assertEqual(receipt['cost_nusd'], 25931400)
        self.assertEqual(receipt['attempts'], 9)
        frozen = json.loads((root/'graphs_partial.json').read_text(encoding='utf-8'))
        for graph, case in zip(frozen, old.cases('train')):
            self.assertEqual(enumerate_graph(case, cache), graph)

    def test_total_attempts_and_spend_include_prior_calls(self):
        from rl_sqstn_integration_v0.collect_multistep_r2 import Campaign
        helper = test_live_api.LiveTests()
        with tempfile.TemporaryDirectory() as temp, helper.client(helper.success) as client:
            campaign = Campaign(client, Path(temp), prior_attempts=63, prior_cost_nusd=25931400)
            campaign('synthetic permission', LIVE_CONFIG)
            self.assertEqual(campaign.attempts, 64)
            self.assertEqual(campaign.accounted_nusd, 26129400)
            with self.assertRaises(AdapterFault):
                campaign('sixty-fifth must not send', LIVE_CONFIG)
        with tempfile.TemporaryDirectory() as temp, helper.client(helper.success) as client:
            campaign = Campaign(client, Path(temp), prior_attempts=9, prior_cost_nusd=3999999999)
            with self.assertRaises(AdapterFault):
                campaign('budget already reserved', LIVE_CONFIG)
            self.assertEqual(campaign.attempts, 9)


if __name__ == '__main__':
    unittest.main()
