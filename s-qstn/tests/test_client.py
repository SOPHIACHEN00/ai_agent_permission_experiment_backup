"""Exercise the copied spending guard and single-call adapter without a network."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqstn.client import respond
from sqstn.provider import CostLedger, atomic_json


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        atomic_json(self.root / 'state/budget.json', {'limit_usd':'5.00','jobs':{}})
        self.compiled = {'messages':[{'role':'user','content':'test permission'}], 'prompt_sha256':'fixture'}
        self.patchers = [patch.dict('os.environ', {'OPENROUTER_API_KEY':'unit-test-not-a-real-key'}),
                         patch('sqstn.client.model_metadata', return_value={})]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def response(self, *, finish='stop', raw='{"answer":"Yes, always share"}', cost=.000198):
        return {'model':'openai/o4-mini-2025-04-16', 'id':'unit-test',
                'choices':[{'finish_reason':finish,'message':{'content':raw}}],
                'usage':{'prompt_tokens':100,'completion_tokens':20,'cost':cost}}

    def test_valid_answer_saved_and_charged_once(self):
        with patch('sqstn.client.complete', return_value=self.response()) as caller:
            result = respond(self.compiled, self.root)
        self.assertEqual(caller.call_count, 1)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['answer'], 'Yes, always share')
        self.assertEqual(len(CostLedger(self.root/'state/budget.json').data['jobs']), 1)
        self.assertTrue((self.root/'outputs'/f"{result['job_id']}.json").is_file())
        self.assertFalse((self.root/'state/budget.lock').exists())

    def test_token_limit_failure_returns_error_and_next_call_can_continue(self):
        with patch('sqstn.client.complete', side_effect=[self.response(finish='length',raw=None),self.response()]) as caller:
            failed = respond(self.compiled, self.root)
            valid = respond(self.compiled, self.root)
        self.assertEqual(caller.call_count, 2)
        self.assertEqual(failed['status'], 'error')
        self.assertIsNone(failed['answer'])
        self.assertEqual(valid['status'], 'ok')
        self.assertFalse(failed['automatic_retries'])

    def test_network_failure_retains_reservation_without_retry(self):
        with patch('sqstn.client.complete', side_effect=OSError('fixture network unavailable')) as caller:
            result = respond(self.compiled, self.root)
        self.assertEqual(caller.call_count, 1)
        self.assertEqual(result['status'], 'error')
        job=CostLedger(self.root/'state/budget.json').data['jobs'][result['job_id']]
        self.assertEqual(job['status'], 'unknown_cost_full_reserve')

    def test_accounting_error_saves_response_and_blocks_further_calls(self):
        with patch('sqstn.client.complete', return_value=self.response(cost=1)):
            with self.assertRaises(RuntimeError):
                respond(self.compiled, self.root)
        records=list((self.root/'outputs').glob('*.json'))
        saved=json.loads(records[0].read_text(encoding='utf-8'))
        self.assertEqual(saved['status'], 'settlement_error')
        self.assertEqual(saved['response']['id'], 'unit-test')
        with patch('sqstn.client.complete') as caller, self.assertRaisesRegex(RuntimeError,'HALTED'):
            respond(self.compiled, self.root)
        caller.assert_not_called()

    def test_missing_ledger_never_creates_a_fresh_budget(self):
        (self.root/'state/budget.json').unlink()
        with patch('sqstn.client.complete') as caller, self.assertRaises(FileNotFoundError):
            respond(self.compiled, self.root)
        caller.assert_not_called()

    def test_snapshot_mismatch_prevents_paid_call(self):
        with patch('sqstn.client.model_metadata',side_effect=ValueError('snapshot mismatch')):
            with patch('sqstn.client.complete') as caller, self.assertRaises(ValueError):
                respond(self.compiled, self.root)
        caller.assert_not_called()
        self.assertEqual(CostLedger(self.root/'state/budget.json').data['jobs'], {})


if __name__ == '__main__':
    unittest.main()
