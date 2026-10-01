"""Replay saved actions, never rerun policy selection or train to improve scores."""
from copy import deepcopy
import importlib
import unittest

from agent_permission_harness_v1.learning_contracts import EpisodeConfig
from agent_permission_harness_v1.policy import LeastScopeRulePolicy
from agent_permission_harness_v1.run_ddqn_pilot import _run


class PilotReplayTests(unittest.TestCase):
    def test_saved_actions_reproduce_exact_result_and_exposure_and_reject_corruption(self):
        try:
            verifier = importlib.import_module('agent_permission_harness_v1.verify_pilot_replay')
        except ModuleNotFoundError:
            self.fail('saved-action replay verifier is missing')
        row = _run(LeastScopeRulePolicy(), 3, EpisodeConfig(3, 20),
                   {'seed': 17, 'split': 'train', 'arm': 'ddqn', 'episode': 0})
        self.assertTrue(verifier.verify_row(row)['match'])
        changed = deepcopy(row)
        changed['result']['human_snapshot']['messages'][0]['reply']['permission'] = 'deny_persist'
        self.assertFalse(verifier.verify_row(changed)['match'])
        changed = deepcopy(row)
        changed['exposure_used'] += 1
        self.assertFalse(verifier.verify_row(changed)['match'])


if __name__ == '__main__':
    unittest.main()
