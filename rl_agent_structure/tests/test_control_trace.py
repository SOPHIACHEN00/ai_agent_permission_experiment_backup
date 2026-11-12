"""Read-only control trace acceptance, with no local torch dependency or training."""
import importlib.util
import random
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from helpers import ROOT
sys.path.insert(0, str(ROOT))
from rl_testing.control_trace import TracedPolicy
from personal_assistant.contracts.permission import ControllerAction as A, canonical_hash
from personal_assistant.learning.user_features import STATE_FEATURE_NAMES


class Vector:
    def __init__(self, values): self.values = values
    def detach(self): return self
    def cpu(self): return self
    def tolist(self): return list(self.values)


def fixture():
    candidates = tuple(NS(candidate_id=f'candidate-{i}', action=action, valid=valid,
        request_scope=NS(data_attributes=('field',)) if action == A.REQUEST else None,
        operation_scope=NS(data_attributes=('field',)) if action == A.EXECUTE else None,
        release_keys=('key',) if action == A.RELEASE else ())
        for i, (action, valid) in enumerate(((A.REQUEST, True), (A.EXECUTE, False),
                                           (A.RELEASE, True), (A.END, True))))
    boundary = NS(token='boundary-1', view=NS(candidates=candidates,
        position=NS(user_id='alice', task_id='task-1'), logical_step=7, phase='task'),
        context=NS(controller_horizon=21, planner_horizon=8, planner_turns=2,
                   interruption_budget=24, exposure_budget=80))
    encoded = NS(candidate_ids=tuple(c.candidate_id for c in candidates),
        mask=Vector([c.valid for c in candidates]), state=Vector(range(len(STATE_FEATURE_NAMES))),
        validate=lambda: None)
    return boundary, encoded


class FakeLearner:
    def __init__(self, seed): self._rng = random.Random(seed); self.calls = 0
    def select_candidate(self, encoded, *, policy_mask, epsilon, rng):
        self.calls += 1
        valid = [i for i, yes in enumerate(policy_mask.tolist()) if yes]
        if rng.random() < epsilon:
            selected = rng.choice(valid)
        else:
            scores = [1., 100., 1., -1.]
            best = max(scores[i] for i in valid)
            selected = rng.choice([i for i in valid if scores[i] == best])
        return encoded.candidate_ids[selected]


class FakePolicy:
    def __init__(self, encoded, *, training=True, seed=3):
        self.training, self.seed, self.user_id = training, seed, 'alice'
        self.evaluation_context = 'fixed-evaluation'
        self.enhancements = NS(exploration='candidate')
        self.encoder = NS(encode=lambda boundary: encoded)
        self.learner = FakeLearner(seed)
        self.calls = 0; self.observed = []
    def select(self, boundary, *, epsilon=0.):
        self.calls += 1
        if self.training:
            rng = self.learner._rng
        else:
            seed = int(canonical_hash({'seed': self.seed, 'context': self.evaluation_context,
                'interruption_budget': boundary.context.interruption_budget,
                'exposure_budget': boundary.context.exposure_budget,
                'decision_index': boundary.view.logical_step})[:16], 16)
            rng = random.Random(seed)
        return self.learner.select_candidate(self.encoder.encode(boundary),
            policy_mask=self.encoder.encode(boundary).mask, epsilon=epsilon, rng=rng)
    def observe(self, transition): self.observed.append(transition); return True


class Log:
    def __init__(self): self.events = []
    def event(self, kind, row): self.events.append((kind, row))


class TraceTests(unittest.TestCase):
    def test_import_does_not_import_torch(self):
        code = ("import sys; sys.path.insert(0, " + repr(str(ROOT)) + "); "
                "import rl_testing.control_trace; assert 'torch' not in sys.modules")
        subprocess.run([sys.executable, '-I', '-B', '-c', code], check=True, capture_output=True)

    @patch('rl_testing.control_trace._score_candidates', return_value=[1., 100., 1., -1.])
    def test_training_selection_rng_and_observe_are_unchanged(self, scores):
        boundary, encoded = fixture()
        plain, base = FakePolicy(encoded), FakePolicy(encoded)
        log = Log(); traced = TracedPolicy(base, log)
        for epsilon in (0., .3, 1., .7, 0.) * 8:
            shadow = random.Random(); shadow.setstate(base.learner._rng.getstate())
            explored = shadow.random() < epsilon
            self.assertEqual(traced.select(boundary, epsilon=epsilon), plain.select(boundary, epsilon=epsilon))
            self.assertEqual(base.learner._rng.getstate(), plain.learner._rng.getstate())
            self.assertEqual(traced.rows[-1]['explored'], explored)
        row = traced.rows[0]
        self.assertEqual(row['greedy_candidate_ids'], ['candidate-0', 'candidate-2'])
        self.assertFalse(row['execute_legal'])
        self.assertEqual(row['control_remaining'], 13)
        self.assertEqual(row['candidates'][1]['q'], 100.)
        self.assertEqual(row['state_features']['decision'], 1)
        self.assertIs(traced.learner, base.learner)
        self.assertTrue(traced.observe('transition'))
        self.assertEqual(base.observed, ['transition'])
        self.assertTrue(all(kind == 'action_scores' for kind, row in log.events))

    @patch('rl_testing.control_trace._score_candidates', return_value=[1., 100., 1., -1.])
    def test_frozen_greedy_and_exploration_do_not_touch_base_rng(self, scores):
        boundary, encoded = fixture()
        base = FakePolicy(encoded, training=False)
        initial = base.learner._rng.getstate()
        greedy = TracedPolicy(base, Log())
        self.assertEqual(greedy.select(boundary), base.select(boundary))
        self.assertFalse(greedy.rows[-1]['explored'])
        self.assertEqual(greedy.rows[-1]['selection_mode'], 'frozen_original')
        calls = base.calls
        probe = TracedPolicy(base, Log(), evaluation_epsilon=1., exploration_seed=9)
        control = random.Random(9)
        for _ in range(12):
            expected = base.learner.select_candidate(encoded, policy_mask=encoded.mask, epsilon=1., rng=control)
            self.assertEqual(probe.select(boundary), expected)
            self.assertTrue(probe.rows[-1]['explored'])
        self.assertEqual(base.calls, calls)
        self.assertFalse(base.training)
        self.assertEqual(base.learner._rng.getstate(), initial)
        self.assertEqual(base.observed, [])

    def test_rejects_unsupported_exploration_and_invalid_configuration(self):
        boundary, encoded = fixture(); base = FakePolicy(encoded)
        with self.assertRaises(ValueError): TracedPolicy(base, Log(), evaluation_epsilon=.1)
        with self.assertRaises(ValueError): TracedPolicy(base, Log(), exploration_seed=True)
        base.enhancements.exploration = 'family'
        with self.assertRaisesRegex(ValueError, 'candidate exploration'): TracedPolicy(base, Log())


@unittest.skipUnless(importlib.util.find_spec('torch'), 'torch unavailable: real trace parity requires server')
class RealTorchTraceTests(unittest.TestCase):
    def test_q_trace_preserves_real_selection_rng_parameters_and_modes(self):
        import torch
        from test_user_session import user_session, start
        from test_learning_driver import Collector
        from personal_assistant.learning.driver import LearningDriver
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        user = user_session(); start(user)
        boundary = LearningDriver(user, Collector(), lambda delta: 0.).advance()
        plain = DDQNPermissionPolicy(seed=7, user_id='alice', device='cpu')
        base = DDQNPermissionPolicy(seed=7, user_id='alice', device='cpu')
        params = {name: value.clone() for name, value in base.learner.online_network.state_dict().items()}
        modes = tuple(module.training for module in base.learner.online_network.modules())
        cpu_rng = torch.random.get_rng_state().clone()
        traced = TracedPolicy(base, Log())
        for epsilon in (0., .3, 1., 0.):
            self.assertEqual(traced.select(boundary, epsilon=epsilon), plain.select(boundary, epsilon=epsilon))
            self.assertEqual(base.learner._rng.getstate(), plain.learner._rng.getstate())
        self.assertTrue(torch.equal(cpu_rng, torch.random.get_rng_state()))
        self.assertEqual(modes, tuple(module.training for module in base.learner.online_network.modules()))
        self.assertTrue(all(torch.equal(value, params[name]) for name, value in base.learner.online_network.state_dict().items()))
        self.assertEqual(base.learner.optimizer_steps, 0)
        self.assertEqual(base.learner.replay_size, 0)


if __name__ == '__main__': unittest.main()
