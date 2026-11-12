import importlib.util
import unittest
from helpers import ROOT


@unittest.skipUnless(importlib.util.find_spec('torch'), 'torch unavailable: real DDQN/CUDA requires server verification')
class TorchTests(unittest.TestCase):
    def test_four_action_policy_rejects_discounting_even_for_one_step(self):
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.ddqn import DDQNHyperparameters
        from personal_assistant.learning.enhancements import EnhancementConfig
        for n_steps in (1, 3):
            with self.subTest(n_steps=n_steps), self.assertRaisesRegex(ValueError, 'gamma=1'):
                DDQNPermissionPolicy(seed=3, user_id='alice', training=False, device='cpu',
                    hyperparameters=DDQNHyperparameters(gamma=.99),
                    enhancements=EnhancementConfig(n_steps=n_steps))

    def test_retention_formula_mask_and_cpu_cuda(self):
        import torch
        from personal_assistant.learning.retention import retention_loss, family_weights
        for device in ['cpu'] + (['cuda:0'] if torch.cuda.is_available() else []):
            q = torch.tensor([[0., .2, 999.], [.4, 0., 999.]], device=device)
            mask = torch.tensor([[True, True, False]]*2, device=device)
            action = torch.tensor([0, 1], device=device)
            loss = retention_loss(q, mask, action, torch.tensor([0., 1.], device=device), torch.ones(2, device=device), margin=.1)
            self.assertAlmostEqual(float(loss), .65, places=6)  # (.3 + (.5 + .5)) / 2
            weights = family_weights(torch.tensor([0, 1, 1, 1], device=device))
            self.assertTrue(torch.allclose(weights, torch.tensor([2., 2/3, 2/3, 2/3], device=device)))

    def test_real_policy_inference_retention_attachment_and_checkpoint_without_optimization(self):
        import torch
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from test_user_session import user_session, start
        from test_learning_driver import Collector, DriverTests
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.enhancements import EnhancementConfig
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.learning.user_features import FEATURE_SCHEMA
        from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
        u = user_session(); start(u); c = Collector(); d = DriverTests().driver(u, c)
        b = d.advance(); DriverTests().run_task(d, c); d.finish_sequence()
        bank = FixedObservedBank('alice', FEATURE_SCHEMA, tuple(c.transitions))
        policy = DDQNPermissionPolicy(seed=3, user_id='alice', training=False, enhancements=EnhancementConfig(), device='cpu')
        selected = policy.select(b)
        self.assertIn(selected, [c.candidate_id for c in b.view.candidates if c.valid])
        self.assertEqual(policy.learner.optimizer_steps, 0)
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / 'policy.pt'; save_checkpoint(policy, p)
            loaded = restore_checkpoint(p, user_id='alice', device='cpu')
            self.assertEqual(loaded.select(b), selected)
            with self.assertRaises(ValueError): restore_checkpoint(p, user_id='bob', device='cpu')
        enhanced = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu', enhancements=EnhancementConfig(True, .1, 'family', 3), bank=bank)
        self.assertIsNotNone(enhanced.learner.fixed_batch)
        self.assertEqual(enhanced.learner.optimizer_steps, 0)


if __name__ == '__main__': unittest.main()
