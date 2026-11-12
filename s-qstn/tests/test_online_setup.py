"""Environment, shared JSON transport and new-campaign setup without a network."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqstn.client import initialize_budget, load_api_key, request_json


class OnlineSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_env_precedence_and_no_process_mutation(self):
        (self.root / '.env').write_text('OPENROUTER_API_KEY=file-unit-test-key\n')
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(load_api_key(self.root), 'file-unit-test-key')
            self.assertNotIn('OPENROUTER_API_KEY', os.environ)
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'env-unit-test-key'}):
            self.assertEqual(load_api_key(self.root), 'env-unit-test-key')

    def test_example_or_missing_keys_are_rejected_before_network(self):
        initialize_budget(self.root)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            load_api_key(self.root)
        for key in ('', 'replace_with_your_openrouter_api_key', ' mock-key', '<your-key>'):
            with self.subTest(key=key), patch('sqstn.client.model_metadata') as metadata, \
                    patch('sqstn.client.complete') as complete, self.assertRaises(ValueError):
                request_json([], 'test', self.root, api_key=key)
            metadata.assert_not_called()
            complete.assert_not_called()

    def test_initialization_is_explicit_and_cannot_reset_an_existing_budget(self):
        path = initialize_budget(self.root)
        path.write_text('{"limit_usd":"5.00","jobs":{"previous":"keep"}}')
        previous = path.read_bytes()
        with self.assertRaises(FileExistsError):
            initialize_budget(self.root)
        self.assertEqual(path.read_bytes(), previous)

    def test_planner_json_is_duplicate_key_checked_and_failure_still_charged(self):
        initialize_budget(self.root)
        response = {'model': 'openai/o4-mini-2025-04-16',
                    'choices': [{'finish_reason': 'stop', 'message': {'content': '{"kind":"tool","kind":"finish"}'}}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}
        with patch('sqstn.client.model_metadata', return_value={}), \
                patch('sqstn.client.complete', return_value=response) as complete:
            result = request_json([], 'test', self.root, api_key='unit-test-key')
        self.assertEqual(complete.call_count, 1)
        self.assertEqual(result['status'], 'error')
        self.assertIsNone(result['data'])
        ledger = json.loads((self.root / 'state/budget.json').read_text())
        self.assertEqual(next(iter(ledger['jobs'].values()))['status'], 'settled')

    def test_provider_errors_never_echo_the_configured_key(self):
        initialize_budget(self.root)
        key = 'unit-test-sensitive-token'
        with patch('sqstn.client.model_metadata', return_value={}), \
                patch('sqstn.client.complete', side_effect=OSError('Bearer ' + key)):
            result = request_json([], 'test', self.root, api_key=key)
        self.assertNotIn(key, json.dumps(result))
        for path in (self.root / 'outputs').glob('*.json'):
            self.assertNotIn(key, path.read_text())


if __name__ == '__main__':
    unittest.main()
