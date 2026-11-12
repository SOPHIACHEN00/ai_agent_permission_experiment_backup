"""Exercise real Agent/provider wiring with fake HTTP responses, never paid calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from helpers import ROOT, binding
from personal_assistant.contracts.permission import contract_json_round_trip
from personal_assistant.integration.online import OpenRouterTransport, load_client, load_policy, run_queries
from personal_assistant.planning.scripted import fixture_decisions


@unittest.skipUnless(all(importlib.util.find_spec(name) is not None for name in
                        ('qstn', 'pandas', 'sklearn', 'dotenv')), 'install requirements-online.txt')
class APIInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.budget_root = Path(self.temp.name)
        self.client = load_client(ROOT.parent / 's-qstn')
        self.client.initialize_budget(self.budget_root)
        self.key = 'unit-test-not-a-real-key'
        self.transport = OpenRouterTransport(self.budget_root, self.key)
        self.payloads = []

    def tearDown(self):
        self.temp.cleanup()

    def run_api(self, queries, *, answer='Yes, always share', policy=None, invalid_plan=False):
        decisions = iter(contract_json_round_trip(d) for q in queries for d in fixture_decisions(binding(q).task))

        def complete(payload, key):
            self.assertEqual(key, self.key)
            self.payloads.append(payload)
            if payload['response_format']['type'] == 'json_schema':
                data = {'answer': answer}
            else:
                data = next(decisions)
                if invalid_plan:
                    data['tool'] = 'undeclared_tool'
            return {'model': 'openai/o4-mini-2025-04-16',
                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(data)}}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'cost': .000198}}

        with patch('sqstn.client.model_metadata', return_value={}), patch('sqstn.client.complete', side_effect=complete):
            return run_queries(queries, user_id='alice', profile='persistent_granters', persist_rounds=3,
                               sqstn_root=ROOT.parent / 's-qstn', transport=self.transport,
                               policy=policy or load_policy('rule', user_id='alice'))

    def test_real_bridge_two_queries_share_budget_consent_and_tool_history(self):
        report = self.run_api([40, 41])
        self.assertEqual([t['status'] for t in report['tasks']], ['completed', 'completed'])
        for task in report['tasks']:
            self.assertTrue(task['result']['ledger_replay_verified'])
            self.assertTrue(task['result']['monitor_audit_verified'])
            self.assertEqual(task['metrics']['unauthorized_executed_field_instances'], 0)
            self.assertIsNone(task['reward'])
        self.assertEqual(report['optimizer_updates'], 0)
        self.assertFalse(report['training'])
        roles = {record['role'] for record in report['provider']['calls']}
        self.assertEqual(roles, {'planner', 'sqstn'})
        ledger = json.loads((self.budget_root / 'state/budget.json').read_text())
        self.assertEqual(len(ledger['jobs']), len(self.payloads))
        self.assertTrue(all(j['status'] == 'settled' for j in ledger['jobs'].values()))
        planner_prompts = [p['messages'][-1]['content'] for p in self.payloads
                           if p['response_format']['type'] == 'json_object']
        self.assertIn('tool_result', planner_prompts[-1])
        # Persistent consent observed in Q40 removes a repeated Weather question in Q41.
        messages = report['tasks'][1]['result']['human_snapshot']['messages']
        self.assertFalse(any(m['message']['requested_scope']['tool'] == 'Weather' for m in messages))
        self.assertNotIn(self.key, json.dumps(report))

    def test_denial_cannot_be_converted_to_execution_authority(self):
        report = self.run_api([40], answer='No, never share')
        task = report['tasks'][0]
        self.assertFalse(task['metrics']['task_success'])
        self.assertEqual(task['metrics']['unauthorized_executed_field_instances'], 0)
        self.assertTrue(task['result']['ledger_replay_verified'])

    def test_invalid_proposal_stays_behind_compiler_and_monitor(self):
        report = self.run_api([40], invalid_plan=True)
        task = report['tasks'][0]
        self.assertFalse(task['metrics']['task_success'])
        self.assertEqual(task['result']['tool_snapshot'].get('data_flows', []), [])
        self.assertEqual(task['metrics']['unauthorized_executed_field_instances'], 0)

    def test_manual_extension_waits_and_does_not_start_next_query(self):
        report = self.run_api([63, 40])
        self.assertEqual(len(report['tasks']), 1)
        self.assertEqual(report['tasks'][0]['status'], 'awaiting_human')
        self.assertIsNotNone(report['tasks'][0]['result']['awaiting_message_id'])
        self.assertTrue(all(r['role'] == 'planner' for r in report['provider']['calls']))

    def test_request_cap_is_shared_across_planner_and_sqstn(self):
        self.transport.max_model_calls = 1
        report = self.run_api([40, 41])
        self.assertEqual(len(self.payloads), 1)
        self.assertEqual(len(report['tasks']), 1)
        self.assertIn({'role': 'sqstn', 'reason': 'request_cap_reached'}, self.transport.failures)
        self.assertEqual(report['tasks'][0]['metrics']['unauthorized_executed_field_instances'], 0)

    def test_preview_never_loads_env_client_or_makes_network_request(self):
        spec = importlib.util.spec_from_file_location('api_cli_under_test', ROOT / 'run_online.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch.object(cli, 'load_client', side_effect=AssertionError('preview loaded client')), \
                patch('urllib.request.urlopen', side_effect=AssertionError('preview made network request')), \
                patch('builtins.print'):
            self.assertEqual(cli.main(['--queries', '40', '--user-id', 'alice', '--persist-rounds', '3']), 0)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'requires requirements-rl.txt')
    def test_restored_ddqn_is_frozen_and_cannot_restore_consent(self):
        import torch
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.checkpoint import save_checkpoint
        original = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu', training=True)
        path = self.budget_root / 'fixture.pt'
        save_checkpoint(original, path)
        policy = load_policy('ddqn', user_id='alice', checkpoint=path)
        self.assertFalse(policy.training)
        self.assertFalse(policy.learner.online_network.training)
        before = {k: v.clone() for k, v in policy.learner.online_network.state_dict().items()}
        # Fixed selection makes the inference test deterministic; the genuine
        # checkpoint/model is restored and must remain untouched.
        with patch.object(policy, 'select', side_effect=load_policy('rule', user_id='alice').select), \
                patch.object(policy, 'observe', side_effect=AssertionError('inference trained')):
            report = self.run_api([40], policy=policy)
        self.assertEqual(report['policy'], 'ddqn')
        self.assertEqual(report['tasks'][0]['status'], 'completed')
        self.assertTrue(any(c['role'] == 'sqstn' for c in report['provider']['calls']))
        self.assertTrue(all(torch.equal(before[k], v) for k, v in policy.learner.online_network.state_dict().items()))
        with self.assertRaises(ValueError):
            load_policy('ddqn', user_id='another-user', checkpoint=path)


if __name__ == '__main__':
    unittest.main()
