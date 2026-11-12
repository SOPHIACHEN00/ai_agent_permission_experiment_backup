"""Native four-action candidate-scoring DDQN for the Agent decision interface."""
from __future__ import annotations

import random
import math
from ..contracts.permission import canonical_hash, ControllerAction
from .ddqn import DDQNHyperparameters
from .features import DDQNFeatureEncoder, FEATURE_SCHEMA, model_spec_for
from .user_features import MAX_CANDIDATES
from .retention_backend import RetainedDoubleDQN
from .enhancements import EnhancementConfig, select_exploration_candidate
from .credit import ObservedNStep
from .transitions import ClosedTransition
from .count_representation import RAW_V1, feature_schema_for
from .budget_representation import NONE, combined_schema_for

DEFAULT_HYPERPARAMETERS = DDQNHyperparameters(gamma=1, learning_rate=.001, batch_size=64,
    replay_capacity=2048, warmup_transitions=256, optimize_every=4, target_update_every=250, gradient_clip=5.)


class DDQNPermissionPolicy:
    schema_version = FEATURE_SCHEMA

    def __init__(self, *, seed: int, user_id: str, device='auto', hyperparameters=None, training=True, enhancements=None, bank=None, max_candidates=MAX_CANDIDATES, count_representation=RAW_V1, budget_representation=NONE):
        if type(training) is not bool:
            raise ValueError('training must be boolean')
        self.seed, self.training = seed, training
        if not isinstance(user_id, str) or not user_id: raise ValueError('policy must be user local')
        self.user_id = user_id
        self._count_representation = count_representation
        self._budget_representation = budget_representation
        self.schema_version = combined_schema_for(count_representation, budget_representation)
        self.enhancements = enhancements if enhancements is not None else EnhancementConfig()
        self.enhancements.validate_bank(bank)
        if bank is not None and (bank.user_id != user_id or bank.feature_schema != self.schema_version):
            raise ValueError('foreign bank or schema')
        self.bank, self.bank_hash = bank, None if bank is None else bank.digest
        hyperparameters = DEFAULT_HYPERPARAMETERS if hyperparameters is None else hyperparameters
        if hyperparameters.gamma != 1.:
            raise ValueError('four-action query-local reward protocol requires gamma=1')
        self.encoder = DDQNFeatureEncoder(public_effects=self.enhancements.public_effects, max_candidates=max_candidates,
                                         count_representation=count_representation, budget_representation=budget_representation)
        self.learner = RetainedDoubleDQN(seed=seed, device=device,
            model_spec=model_spec_for(budget_representation=budget_representation, max_candidates=max_candidates),
            retention_weight=self.enhancements.retention_weight,
            hyperparameters=hyperparameters)
        if bank is not None and self.enhancements.retention_weight: self.learner.set_bank(bank, self.encoder)
        self.credit = ObservedNStep(self.enhancements.n_steps)
        self.last_observed_done = True
        self.evaluation_context = 'standalone'
        self._delivered = {}
        if not training:
            self.learner.online_network.eval()

    @property
    def count_representation(self):
        return self._count_representation

    @property
    def budget_representation(self):
        return self._budget_representation

    def _validate_representation(self):
        if (self.schema_version != combined_schema_for(self.count_representation, self.budget_representation)
                or self.encoder.count_representation != self.count_representation
                or self.encoder.budget_representation != self.budget_representation
                or self.encoder.schema_version != self.schema_version):
            raise ValueError('policy/replay feature representation cannot change in place')

    def select(self, boundary, *, epsilon=0.):
        self._validate_representation()
        if boundary.view.position.user_id != self.user_id: raise ValueError('foreign user policy input')
        if type(epsilon) not in (int, float) or not math.isfinite(epsilon) or not 0 <= epsilon <= 1:
            raise ValueError('epsilon must be finite in [0,1]')
        if not self.training and epsilon != 0:
            raise ValueError('frozen evaluation requires epsilon=0')
        encoded = self.encoder.encode(boundary)
        encoded.validate()
        evaluation_seed = int(canonical_hash({'seed': self.seed, 'context': self.evaluation_context,
            'interruption_budget': boundary.context.interruption_budget,
            'exposure_budget': boundary.context.exposure_budget,
            'decision_index': boundary.view.logical_step})[:16], 16)
        rng = self.learner._rng if self.training else random.Random(evaluation_seed)
        if self.enhancements.exploration == 'family':
            if rng.random() < epsilon:
                families = tuple(list(ControllerAction).index(c.action) for c in boundary.view.candidates)
                return select_exploration_candidate(encoded.candidate_ids, families, tuple(encoded.mask.tolist()), rng)
            epsilon = 0.
        return self.learner.select_candidate(encoded, policy_mask=encoded.mask, epsilon=epsilon, rng=rng)

    def observe(self, transition: ClosedTransition) -> bool:
        """Deliver a closed learning transition once; identical repeats are no-ops."""
        self._validate_representation()
        if not self.training:
            raise ValueError('frozen evaluation cannot update replay or network')
        if not isinstance(transition, ClosedTransition):
            raise ValueError('only closed controller transitions can enter replay')
        if transition.pre_decision.view.position.user_id != self.user_id:
            raise ValueError('foreign user transition')
        if self.bank is not None and self.bank.digest != self.bank_hash: raise ValueError('fixed bank mutated')
        pre = self.encoder.encode(transition.pre_decision)
        successor = None if transition.done else self.encoder.encode(transition.next_decision)
        if not transition.done:
            if (transition.next_decision.view.position.task_id != transition.pre_decision.view.position.task_id
                    or transition.next_decision.view.logical_step != transition.pre_decision.view.logical_step + 1
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
        for sample in self.credit.append(transition):
            observed = self.encoder.encode(sample.pre_decision)
            successor = None if sample.done else self.encoder.encode(sample.next_decision)
            self.learner.observe(observed, policy_mask=observed.mask, action_candidate_id=sample.action_candidate_id,
                reward=sample.reward, next_decision=successor,
                next_policy_mask=None if successor is None else successor.mask, done=sample.done)
        self.last_observed_done = transition.done
        self._delivered[transition.transition_id] = identity
        return True
