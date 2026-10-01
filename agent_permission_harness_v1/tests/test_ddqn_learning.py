"""Native DDQN optimization, frozen evaluation and portable checkpoint contracts."""
import copy
import importlib
from pathlib import Path
import tempfile
import unittest

import torch
from pa_rl.contracts import ControllerAction as A
from pa_rl.ddqn import DDQNHyperparameters, MaskedDoubleDQN
from agent_permission_harness_v1.ddqn_features import FEATURE_SCHEMA
import test_learning_environment as support
from test_learning_environment import select


class DDQNLearningTests(unittest.TestCase):
    def make_policy(self, **kwargs):
        try:
            module = importlib.import_module('agent_permission_harness_v1.ddqn_policy')
        except ModuleNotFoundError:
            self.fail('native DDQN permission policy is missing')
        hyper = DDQNHyperparameters(gamma=1, batch_size=1, warmup_transitions=1,
            optimize_every=1, target_update_every=2, replay_capacity=16)
        return module.DDQNPermissionPolicy(seed=17, hyperparameters=hyper, **kwargs)

    def environment(self):
        return support.LearningEnvironmentTests().environment()

    def test_selection_is_legal_and_training_updates_native_network(self):
        policy = self.make_policy(device='cpu')
        self.assertIsInstance(policy.learner, MaskedDoubleDQN)
        env, boundary = self.environment(), None
        boundary = env.start()
        for epsilon in (0, 1):
            chosen = policy.select(boundary, epsilon=epsilon)
            self.assertTrue(any(c.candidate_id == chosen and c.valid for c in boundary.view.candidates))
        before = copy.deepcopy(policy.learner.online_network.state_dict())
        transition = env.step(select(boundary, A.REQUEST_AUTHORIZATION, 2), decision_token=boundary.token)
        self.assertTrue(policy.observe(transition))
        self.assertEqual(policy.learner.optimizer_steps, 1)
        self.assertEqual(policy.learner.replay_size, 1)
        self.assertTrue(any(not torch.equal(value, policy.learner.online_network.state_dict()[name]) for name, value in before.items()))
        self.assertFalse(policy.observe(transition))
        self.assertEqual(policy.learner.replay_size, 1)

    def test_frozen_selection_does_not_mutate_training_or_rng(self):
        policy = self.make_policy(device='cpu', training=False)
        boundary = self.environment().start()
        weights = copy.deepcopy(policy.learner.online_network.state_dict())
        rng = policy.learner._rng.getstate()
        for _ in range(3):
            policy.select(boundary)
        self.assertEqual(policy.learner._rng.getstate(), rng)
        self.assertEqual(policy.learner.environment_steps, 0)
        self.assertEqual(policy.learner.replay_size, 0)
        self.assertTrue(all(torch.equal(value, policy.learner.online_network.state_dict()[name]) for name, value in weights.items()))
        with self.assertRaises(ValueError):
            policy.select(boundary, epsilon=.1)
        with self.assertRaises(ValueError):
            policy.observe(None)

    def test_terminal_transition_has_no_bootstrap_successor(self):
        policy, env = self.make_policy(device='cpu'), self.environment()
        boundary = env.start()
        for action, width in ((A.REQUEST_AUTHORIZATION, 2), (A.EXECUTE_WITH_AUTHORIZATION, 1), (A.EXECUTE_WITH_AUTHORIZATION, 2)):
            transition = env.step(select(boundary, action, width), decision_token=boundary.token)
            policy.observe(transition)
            boundary = transition.next_decision
        self.assertEqual(transition.reward, 1)
        item = policy.learner._buffer._items[-1]
        self.assertTrue(item.done)
        self.assertFalse(item.next_mask.any())
        self.assertEqual(float(item.reward), 1)

    def test_checkpoint_roundtrip_is_frozen_and_rejects_legacy_schema(self):
        policy = self.make_policy(device='cpu')
        checkpoints = importlib.import_module('agent_permission_harness_v1.learning_checkpoints')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'final.pt'
            checkpoints.save_checkpoint(policy, path, metadata={'split': 'train-only'})
            loaded = checkpoints.load_checkpoint(path, device='cpu')
            self.assertFalse(loaded.training)
            self.assertEqual(loaded.schema_version, FEATURE_SCHEMA)
            self.assertTrue(all(torch.equal(t, loaded.learner.online_network.state_dict()[key])
                                for key, t in policy.learner.online_network.state_dict().items()))
            self.assertEqual(loaded.learner.replay_size, 0)
            payload = torch.load(path, weights_only=True)
            payload['feature_schema'] = 'family3_v2'
            invalid = Path(directory) / 'legacy.pt'
            torch.save(payload, invalid)
            with self.assertRaises(ValueError):
                checkpoints.load_checkpoint(invalid, device='cpu')
            with self.assertRaises(FileExistsError):
                checkpoints.save_checkpoint(policy, path)

    @unittest.skipUnless(torch.cuda.is_available(), 'CUDA unavailable on execution host')
    def test_cuda_optimization_and_cpu_checkpoint_portability(self):
        policy = self.make_policy(device='cuda:0')
        env = self.environment()
        boundary = env.start()
        chosen = policy.select(boundary)
        self.assertIn(chosen, [c.candidate_id for c in boundary.view.candidates if c.valid])
        transition = env.step(select(boundary, A.REQUEST_AUTHORIZATION, 2), decision_token=boundary.token)
        policy.observe(transition)
        self.assertEqual(policy.learner.optimizer_steps, 1)
        parameters = list(policy.learner.online_network.parameters())
        self.assertTrue(all(p.is_cuda and p.grad is not None and p.grad.is_cuda for p in parameters))
        self.assertTrue(all(item.state.device.type == 'cpu' for item in policy.learner._buffer._items))
        checkpoints = importlib.import_module('agent_permission_harness_v1.learning_checkpoints')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cuda.pt'
            checkpoints.save_checkpoint(policy, path)
            loaded = checkpoints.load_checkpoint(path, device='cpu')
            encoded = policy.encoder.encode(boundary)
            with torch.no_grad():
                cpu_q = loaded.learner.online_network(encoded.state[None], encoded.candidate_features[None])
                cuda_q = policy.learner.online_network(encoded.state[None], encoded.candidate_features[None])
            self.assertTrue(torch.allclose(cpu_q, cuda_q, atol=1e-5, rtol=1e-5))


if __name__ == '__main__':
    unittest.main()
