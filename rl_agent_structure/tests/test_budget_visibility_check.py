"""Budget experiment accounting and frozen-copy contract; optimizer runs on server only."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT.parent), str(ROOT/'tests')]
from rl_testing.budget_visibility_check import (MODES, TRAIN_TASKS, EVALUATION_GROUPS,
                                                execution_budget_diagnostics)
from test_online_check import config


class BudgetProtocolTests(unittest.TestCase):
    def test_matched_protocol_and_explicit_training_gate(self):
        self.assertEqual(MODES, ('masked_v1', 'remaining_ratio_v1'))
        self.assertEqual(3 + len(MODES)*TRAIN_TASKS + len(EVALUATION_GROUPS)*3, 57)
        result = subprocess.run([sys.executable, '-B', str(ROOT/'rl_testing/budget_visibility_check.py'),
            '--config', 'missing', '--output', 'missing'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--allow-training required', result.stderr)
        self.assertNotIn('No module named', result.stderr)

    def test_success_after_release_exhaustion_is_not_autonomous_progress(self):
        task = {'task_id': 'task', 'query_id': 55, 'status': 'completed',
                'metrics': {'task_success': 1, 'active_gate_items_before_cleanup': 11}}
        trace = {'task_id': 'task', 'selected_action': 'EXECUTE', 'global_decision': 46,
                 'runtime_budgets': {'control_steps_used': 46, 'control_step_limit': 64,
                                     'release_steps_used': 32, 'release_step_limit': 32},
                 'candidates': [{'action': 'RELEASE', 'valid': False}]}
        row = execution_budget_diagnostics(SimpleNamespace(tasks=[task]), [trace])[0]
        self.assertEqual(row['task_success'], 1)
        self.assertFalse(row['first_execute_before_release_limit'])
        self.assertEqual(row['executions'][0]['legal_release_candidates'], 0)
        trace['runtime_budgets']['release_steps_used'] = 2
        trace['candidates'][0]['valid'] = True
        row = execution_budget_diagnostics(SimpleNamespace(tasks=[task]), [trace])[0]
        self.assertTrue(row['first_execute_before_release_limit'])
        self.assertEqual(row['executions'][0]['legal_release_candidates'], 1)
        row = execution_budget_diagnostics(SimpleNamespace(tasks=[task]), [])[0]
        self.assertIsNone(row['first_execute_before_release_limit'])


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Torch checkpoint/frozen checks require server')
class FrozenBudgetTests(unittest.TestCase):
    def test_equal_capacity_and_freezing_preserve_budget_mode(self):
        from rl_testing.torch_checks import _policy, _frozen_copy, _checkpoint_signature, _network_digest
        digests = []
        for mode in MODES:
            source = _policy(config(), None, count_representation='bounded_ratio_v1', budget_representation=mode)
            before = _checkpoint_signature(source)
            frozen = _frozen_copy(config(), source)
            self.assertEqual(frozen.budget_representation, mode)
            self.assertEqual(frozen.learner.model_spec.state_dim, 22)
            self.assertFalse(frozen.training)
            self.assertEqual(source.schema_version, frozen.schema_version)
            self.assertEqual(_network_digest(source.learner.online_network), _network_digest(frozen.learner.online_network))
            self.assertEqual(before, _checkpoint_signature(source))
            digests.append(_network_digest(source.learner.online_network))
        self.assertEqual(digests[0], digests[1])


if __name__ == '__main__': unittest.main()
