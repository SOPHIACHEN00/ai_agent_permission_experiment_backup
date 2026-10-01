"""Fixed safe controller and genuine WP-FTS public-feature transfer."""
from __future__ import annotations

import numpy as np

from .adapter import AdapterFault, CHOICES, PublicAnswer
from .common import digest
from .environment import PolicyFrame
from .features import bandit_vector, encode
from bandit_experiment.run_stated_policy_bandit import FactoredJointPolicy
from online_bandit_experiment.wp_fts import tempered_factored_copy


def _valid(frame: PolicyFrame) -> dict[str, int]:
    result = {}
    for row, valid in zip(frame.observation.candidate_catalog, frame.observation.action_mask):
        if valid:
            result.setdefault(row['action'], row['slot_index'])
    return result


def _fallback(valid: dict[str, int]) -> int:
    for action in ('DENY_WITH_REASON', 'ESCALATE'):
        if action in valid:
            return valid[action]
    raise AdapterFault('No safe public fallback')


def _declined(frame: PolicyFrame) -> bool:
    scope = frame.observation.task_view['next_required_scope_identity']
    return any(answer.scope_id == scope and answer.choice.startswith('deny') for answer in frame.answers)


def rule_action(frame: PolicyFrame) -> int:
    valid = _valid(frame)
    if 'EXECUTE_WITH_AUTHORIZATION' in valid:
        return valid['EXECUTE_WITH_AUTHORIZATION']
    if _declined(frame):
        return _fallback(valid)
    for action in ('REQUEST_REFRESH', 'REQUEST_AUTHORIZATION'):
        if action in valid:
            return valid[action]
    return _fallback(valid)


class MABPolicy:
    method_id = 'wp_fts_public_transfer_v0'

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.global_policy = FactoredJointPolicy(303, 'thompson', 2.0)
        self.active = self.global_policy
        self._pending = None
        self.feedback_count = 0
        self.correct_predictions = 0
        self.steps = 0

    @property
    def pending_prediction(self):
        return None if self._pending is None else self._pending['prediction']

    def choose(self, frame: PolicyFrame, *, training: bool) -> int:
        if self._pending is not None:
            raise AdapterFault('Previous MAB feedback not consumed')
        valid = _valid(frame)
        if 'EXECUTE_WITH_AUTHORIZATION' in valid:
            return valid['EXECUTE_WITH_AUTHORIZATION']
        if _declined(frame):
            return _fallback(valid)
        vector = np.asarray(bandit_vector(encode(frame)), dtype=np.float64)
        indices = np.flatnonzero(vector)
        values = vector[indices]
        prediction = self.active.choose_for_training(indices, values, self.rng) if training else self.active.choose_greedy(indices, values)
        prediction = tuple(int(value) for value in prediction)
        if prediction[2] == 0:
            return _fallback(valid)
        index = next((valid[action] for action in ('REQUEST_REFRESH', 'REQUEST_AUTHORIZATION') if action in valid), None)
        if index is None:
            return _fallback(valid)
        if training:
            self._pending = {'prediction': prediction, 'indices': indices.tolist(), 'values': values.tolist(),
                             'scope_id': frame.observation.candidate_catalog[index]['public_scope_identity'],
                             'logical_step': frame.observation.logical_step}
        return index

    def feedback(self, answer: PublicAnswer | None) -> None:
        pending, self._pending = self._pending, None
        if answer is None:
            return
        if pending is None or not isinstance(answer, PublicAnswer) or answer.scope_id != pending['scope_id'] or answer.logical_step != pending['logical_step']:
            raise AdapterFault('Unselected or mismatched MAB feedback')
        access, persistence, action = pending['prediction']
        reward = int(CHOICES[action] == answer.choice)
        self.active.update(access, persistence, np.asarray(pending['indices'], dtype=int),
                           np.asarray(pending['values'], dtype=float), reward)
        self.feedback_count += 1
        self.correct_predictions += reward

    def advance(self, steps: int) -> None:
        if type(steps) is not int or steps < self.steps:
            raise ValueError('MAB step count must be monotone')
        self.steps = steps
        if steps >= 600 and self.active is self.global_policy:
            self.active = tempered_factored_copy(self.global_policy, .01, exploration=.5)

    @staticmethod
    def _arrays(policy) -> dict:
        return {name: {'precision': getattr(policy, name).precision.tolist(),
                       'reward_sum': getattr(policy, name).reward_sum.tolist()}
                for name in ('access_bandit', 'persistence_bandit')}

    def state_dict(self) -> dict:
        return {'method': self.method_id, 'seed': self.seed, 'steps': self.steps,
                'feedback_count': self.feedback_count, 'correct_predictions': self.correct_predictions,
                'global': self._arrays(self.global_policy),
                'personal': None if self.active is self.global_policy else self._arrays(self.active),
                'rng': self.rng.bit_generator.state, 'pending': self._pending}

    @classmethod
    def from_state_dict(cls, state: dict) -> 'MABPolicy':
        if state['method'] != cls.method_id or state['pending'] is not None:
            raise ValueError('Invalid MAB checkpoint')
        policy = cls(state['seed'])
        for name in ('access_bandit', 'persistence_bandit'):
            for field in ('precision', 'reward_sum'):
                setattr(getattr(policy.global_policy, name), field, np.asarray(state['global'][name][field], dtype=float))
        if state['personal'] is not None:
            policy.active = tempered_factored_copy(policy.global_policy, .01, exploration=.5)
            for name in ('access_bandit', 'persistence_bandit'):
                for field in ('precision', 'reward_sum'):
                    setattr(getattr(policy.active, name), field, np.asarray(state['personal'][name][field], dtype=float))
        policy.steps = state['steps']
        policy.feedback_count = state['feedback_count']
        policy.correct_predictions = state['correct_predictions']
        policy.rng.bit_generator.state = state['rng']
        return policy

    def fingerprint(self) -> str:
        return digest(self.state_dict())
