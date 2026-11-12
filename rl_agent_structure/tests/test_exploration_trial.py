"""No-Torch checks for the pure online exploration experiment boundary."""
from dataclasses import asdict
import random
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

from helpers import ROOT
import sys
sys.path.insert(0, str(ROOT))
from rl_testing.exploration_trial import ARMS, SEEDS, protocol_config, main
from rl_testing.exploration_trace import ExplorationLog, ExplorationTrace
from personal_assistant.contracts.permission import ControllerAction as A


class ListValue:
    def __init__(self, values): self.values = values
    def tolist(self): return self.values


class ExplorationProtocolTests(unittest.TestCase):
    def test_pair_configuration_only_changes_exploration(self):
        for seed in SEEDS:
            configs = [asdict(protocol_config(seed, arm, 'cpu')) for arm in ARMS]
            for config in configs:
                self.assertFalse(config['public_effects'])
                self.assertEqual(config['retention_weight'], 0)
                self.assertEqual(config['queries'], (40,41,55))
                self.assertEqual(config['cycles'], 20)
                self.assertEqual(config['n_steps'], 1)
                config.pop('exploration')
            self.assertEqual(*configs)

    def test_protocol_retains_original_reward_and_limits(self):
        config = protocol_config(3,'candidate','cpu')
        config.validate()
        self.assertEqual(config.reward_weights,dict(success=1.,failure=1.,extra_read=.01,
                         extra_write=.01,extra_question=.01,retention=.001))
        self.assertEqual(config.runtime_limits['max_control_steps'],64)
        self.assertEqual(config.runtime_limits['max_release_steps'],32)
        self.assertEqual(config.hyperparameters['batch_size'],2)
        self.assertEqual(config.hyperparameters['replay_capacity'],128)
        self.assertEqual(config.epsilon(1),.3)
        self.assertAlmostEqual(config.epsilon(60),.05)

    def test_unapproved_seed_or_mode_is_rejected(self):
        for seed, arm in ((5,'candidate'),(3,'teacher')):
            with self.assertRaises(ValueError): protocol_config(seed,arm,'cpu')

    def test_training_requires_opt_in_before_torch_import(self):
        with self.assertRaises(SystemExit) as caught:
            main(['--output','unused','--seed','3','--device','cpu'])
        self.assertEqual(caught.exception.code,2)

    def test_trace_delegates_both_modes_and_preserves_rng(self):
        for mode in ARMS:
            with self.subTest(mode=mode):
                candidates = tuple(N(candidate_id=f'c{i}',action=action,valid=True,
                                     request_scope=None,operation_scope=None,release_keys=())
                                   for i,action in enumerate((A.EXECUTE,A.RELEASE)))
                encoded = N(candidate_ids=('c0','c1'),mask=ListValue([True,True]),
                            state=ListValue([0.]*22),validate=lambda:None)
                calls=[]; rng=random.Random(7)
                base=N(training=True,budget_representation='remaining_ratio_v1',
                       enhancements=N(exploration=mode),learner=N(_rng=rng),
                       encoder=N(encode=lambda boundary:encoded))
                base.select=lambda boundary,**kwargs: calls.append(kwargs) or 'c0'
                boundary=N(token='token',view=N(candidates=candidates,position=N(task_id='task'),
                           logical_step=0,phase='control'),context=N(control_steps_used=0,
                           control_step_limit=64,release_steps_used=0,release_step_limit=32))
                log=ExplorationLog(protocol_config(3,mode,'cpu'))
                trace=ExplorationTrace(base,log); before=rng.getstate()
                with patch('rl_testing.exploration_trace._score_candidates',return_value=[.2,.1]):
                    self.assertEqual(trace.select(boundary,epsilon=.3),'c0')
                self.assertEqual(calls,[{'epsilon':.3}])
                self.assertEqual(before,rng.getstate())
                self.assertEqual(log.action_scores[0]['exploration_mode'],mode)
                self.assertTrue(log.action_scores[0]['execute_legal'])


if __name__=='__main__':
    unittest.main()
