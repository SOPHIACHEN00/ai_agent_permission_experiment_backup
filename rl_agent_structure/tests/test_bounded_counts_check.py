"""Protocol and full/cached audit checks; actual optimizer training stays on server."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT.parent), str(ROOT/'tests')]

from rl_testing.bounded_counts_check import MODES, TRAIN_TASKS, EVALUATION_GROUPS, prefix_matches
from rl_testing.audit_cache_check import audit_cache_check
from test_online_check import config


class BoundedProtocolTests(unittest.TestCase):
    def test_one_factor_protocol_and_cli_gate(self):
        self.assertEqual(MODES, ('raw_v1', 'bounded_ratio_v1'))
        self.assertEqual(3 + len(MODES)*TRAIN_TASKS + len(EVALUATION_GROUPS)*3 + 3, 60)
        result = subprocess.run([sys.executable, '-B', str(ROOT/'rl_testing/bounded_counts_check.py'),
            '--config', 'missing', '--reference-prefix', 'missing', '--output', 'missing'],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--allow-training required', result.stderr)
        self.assertNotIn('No module named', result.stderr)

    def test_prefix_gate_checks_every_query_and_metric(self):
        rows = [{'query_id': q, 'status': 'completed', 'return': 1., 'epsilon': .3,
                 'metrics': {'task_success': 1, 'permission_messages': 1}} for q in (40,41,55)*5]
        self.assertTrue(prefix_matches(rows, deepcopy(rows)))
        wrong = deepcopy(rows); wrong[7]['metrics']['permission_messages'] = 2
        self.assertFalse(prefix_matches(rows, wrong))
        self.assertFalse(prefix_matches(rows[:-1], rows))

    def test_full_and_cached_execution_are_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            result = audit_cache_check(config(), Path(folder)/'audit', deadline=time.monotonic()+60)
            self.assertEqual(result['task_count'], 6)
            self.assertTrue(all(result['equivalence'].values()))
            self.assertEqual(result['verification_stats']['full']['cache_hits'], 0)
            self.assertGreater(result['verification_stats']['cache']['cache_hits'], 0)
            self.assertEqual(len(result['timing_batches']), 4)
            self.assertTrue(all(row['seconds'] > 0 for row in result['timing_batches']))


@unittest.skipUnless(importlib.util.find_spec('torch'), 'server Torch check required')
class FrozenRepresentationTests(unittest.TestCase):
    def test_frozen_copy_keeps_representation_and_parameters(self):
        from rl_testing.torch_checks import _policy, _frozen_copy, _network_digest, _checkpoint_signature
        for mode in MODES:
            source = _policy(config(), None, count_representation=mode)
            before = _checkpoint_signature(source)
            frozen = _frozen_copy(config(), source)
            self.assertEqual(frozen.count_representation, mode)
            self.assertEqual(frozen.schema_version, source.schema_version)
            self.assertFalse(frozen.training)
            self.assertEqual(_network_digest(source.learner.online_network), _network_digest(frozen.learner.online_network))
            self.assertEqual(_checkpoint_signature(source), before)


if __name__ == '__main__': unittest.main()
