"""Server-only real CUDA update/reload test; expected missing-module RED is local."""
from __future__ import annotations
import importlib
from pathlib import Path
import tempfile
import unittest


class CudaChecks(unittest.TestCase):
    def test_real_update_save_reload_and_frozen_evaluation(self):
        try:
            runtime = importlib.import_module('rl_sqstn_integration_v0.learner')
        except ModuleNotFoundError as error:
            if error.name == 'rl_sqstn_integration_v0.learner':
                self.fail('Expected missing feature: CUDA integration learner')
            raise
        from rl_sqstn_integration_v0.environment import Episode
        from rl_sqstn_integration_v0.features import encode
        from rl_sqstn_integration_v0.fixtures import build_cases
        from rl_sqstn_integration_v0.policies import rule_action
        episode = Episode(build_cases('train')[0])
        frame = episode.reset(1301)
        while True:
            decision = runtime.tensors(encode(frame))
            index = rule_action(frame)
            selected = decision.candidate_ids[index]
            result = episode.step(index)
            if result.done:
                break
            frame = result.frame
        self.assertEqual(result.reward, 1)
        learner = runtime.CudaLearner(1301)
        before = learner.weight_fingerprint()
        # Repeat one real terminal transition for plumbing only; not learning evidence.
        for _ in range(256):
            learner.observe(decision, policy_mask=decision.mask, action_candidate_id=selected,
                            reward=1, next_decision=None, next_policy_mask=None, done=True)
        self.assertEqual(learner.optimizer_steps, 1)
        self.assertNotEqual(before, learner.weight_fingerprint())
        with tempfile.TemporaryDirectory(prefix='sqstn_cuda_') as directory:
            path = Path(directory) / 'model.pt'
            learner.save(path)
            loaded = runtime.CudaLearner.load(path)
            self.assertEqual(learner.fingerprint(), loaded.fingerprint())
            before_eval = loaded.fingerprint()
            selected = loaded.select(decision, epsilon=0, evaluation=True)
            self.assertIn(selected, decision.candidate_ids)
            self.assertEqual(before_eval, loaded.fingerprint())
            self.assertEqual(loaded.device.type, 'cuda')


if __name__ == '__main__':
    unittest.main()
