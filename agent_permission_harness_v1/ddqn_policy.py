"""Native six-action candidate-scoring DDQN for the Agent decision interface."""
from __future__ import annotations

import random
from pa_rl.contracts import canonical_hash
from pa_rl.ddqn import DDQNHyperparameters
from .ddqn_features import DDQNFeatureEncoder, FEATURE_SCHEMA, MODEL_SPEC
from .device_ddqn import DeviceMaskedDoubleDQN
from .learning_contracts import ClosedTransition

PILOT_HYPERPARAMETERS = DDQNHyperparameters(gamma=1, learning_rate=.001, batch_size=64,
    replay_capacity=2048, warmup_transitions=256, optimize_every=4, target_update_every=250, gradient_clip=5.)


class DDQNPermissionPolicy:
    schema_version = FEATURE_SCHEMA

    def __init__(self, *, seed: int, device='auto', hyperparameters=None, training=True):
        if type(training) is not bool:
            raise ValueError('training must be boolean')
        self.seed, self.training = seed, training
        self.encoder = DDQNFeatureEncoder()
        self.learner = DeviceMaskedDoubleDQN(seed=seed, device=device, model_spec=MODEL_SPEC,
            hyperparameters=PILOT_HYPERPARAMETERS if hyperparameters is None else hyperparameters)
        self.evaluation_context = 'standalone'
        self._delivered = {}
        if not training:
            self.learner.online_network.eval()

    def select(self, boundary, *, epsilon=0.):
        if not self.training and epsilon != 0:
            raise ValueError('frozen evaluation requires epsilon=0')
        encoded = self.encoder.encode(boundary)
        encoded.validate()
        evaluation_seed = int(canonical_hash({'seed': self.seed, 'context': self.evaluation_context,
            'interruption_budget': boundary.context.interruption_budget,
            'exposure_budget': boundary.context.exposure_budget,
            'decision_index': boundary.view.logical_step})[:16], 16)
        return self.learner.select_candidate(encoded, policy_mask=encoded.mask, epsilon=epsilon,
            rng=None if self.training else random.Random(evaluation_seed))

    def observe(self, transition: ClosedTransition) -> bool:
        """Deliver a closed learning transition once; identical repeats are no-ops."""
        if not self.training:
            raise ValueError('frozen evaluation cannot update replay or network')
        if not isinstance(transition, ClosedTransition):
            raise ValueError('only closed controller transitions can enter replay')
        pre = self.encoder.encode(transition.pre_decision)
        successor = None if transition.done else self.encoder.encode(transition.next_decision)
        if not transition.done:
            if (transition.next_decision.view.logical_step != transition.pre_decision.view.logical_step + 1
                    or transition.next_decision.context.interruption_budget != transition.pre_decision.context.interruption_budget
                    or transition.next_decision.context.exposure_budget != transition.pre_decision.context.exposure_budget):
                raise ValueError('transition does not connect adjacent decisions in one episode')
        elif transition.end.reward != transition.reward:
            raise ValueError('terminal reward disagrees with episode evidence')
        identity = canonical_hash({'pre': pre.checksum, 'action': transition.action_candidate_id,
            'reward': transition.reward, 'next': None if successor is None else successor.checksum,
            'terminated': transition.terminated, 'truncated': transition.truncated})
        if transition.transition_id != transition.pre_decision.token:
            raise ValueError('transition ID does not bind to pre-decision token')
        if transition.transition_id in self._delivered:
            if self._delivered[transition.transition_id] != identity:
                raise ValueError('duplicate transition carries conflicting data')
            return False
        self.learner.observe(pre, policy_mask=pre.mask, action_candidate_id=transition.action_candidate_id,
            reward=transition.reward, next_decision=successor,
            next_policy_mask=None if successor is None else successor.mask, done=transition.done)
        self._delivered[transition.transition_id] = identity
        return True
