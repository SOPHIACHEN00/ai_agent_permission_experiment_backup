"""Read-only action scoring diagnostics; importing this module does not need torch.

Training delegates selection to the original policy. Frozen exploratory probes
use a separate RNG and the same masked learner selector, without enabling training.
Only public numeric features, candidate identities and field counts are logged.
"""
from __future__ import annotations

import math
import random


def _epsilon(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('epsilon must be finite in [0,1]')
    return float(value)


def _values(tensor):
    return tensor.detach().cpu().tolist()


def _score_candidates(policy, encoded):
    # This is the first torch import in the module. No train/eval toggles, optimizer
    # calls or model copies are needed for the current Linear/ReLU network.
    import torch
    network = policy.learner.online_network
    modes = tuple(module.training for module in network.modules())
    tensors = tuple(network.parameters()) + tuple(network.buffers())
    versions = tuple(tensor._version for tensor in tensors)
    rng_state = policy.learner._rng.getstate()
    device = policy.learner.device
    devices = ([device.index if device.index is not None else torch.cuda.current_device()]
               if device.type == 'cuda' else [])
    with torch.random.fork_rng(devices=devices), torch.no_grad():
        scores = network(encoded.state.unsqueeze(0),
                         encoded.candidate_features.unsqueeze(0)).squeeze(0)
        values = _values(scores)
    if (tuple(module.training for module in network.modules()) != modes
            or tuple(tensor._version for tensor in tensors) != versions
            or policy.learner._rng.getstate() != rng_state):
        raise RuntimeError('diagnostic Q forward mutated policy state')
    if len(values) != len(encoded.candidate_ids) or any(not math.isfinite(q) for q in values):
        raise ValueError('diagnostic Q values must be finite and match candidates')
    return values


class TracedPolicy:
    """Transparent training proxy plus explicitly labelled frozen-epsilon probes."""

    def __init__(self, base_policy, log, evaluation_epsilon=0., exploration_seed=3):
        self.base_policy, self.log = base_policy, log
        self.evaluation_epsilon = _epsilon(evaluation_epsilon)
        if type(exploration_seed) is not int:
            raise ValueError('exploration seed must be an exact integer')
        if getattr(base_policy.enhancements, 'exploration', None) != 'candidate':
            raise ValueError('action trace currently supports candidate exploration only')
        if type(base_policy.training) is not bool or not callable(getattr(log, 'event', None)):
            raise ValueError('typed policy training flag and event log required')
        if base_policy.training and self.evaluation_epsilon:
            raise ValueError('evaluation epsilon is only for a frozen policy')
        self._evaluation_rng = random.Random(exploration_seed)
        self.rows = []

    def __getattr__(self, name):
        return getattr(self.base_policy, name)

    def observe(self, transition):
        return self.base_policy.observe(transition)

    def select(self, boundary, *, epsilon=0.):
        from personal_assistant.contracts.permission import canonical_hash
        from personal_assistant.learning.user_features import state_feature_names

        epsilon = _epsilon(epsilon)
        base = self.base_policy
        if getattr(base.enhancements, 'exploration', None) != 'candidate':
            raise ValueError('action trace currently supports candidate exploration only')
        if boundary.view.position.user_id != base.user_id:
            raise ValueError('foreign user policy input')
        if not base.training and epsilon:
            raise ValueError('frozen diagnostic epsilon must be configured on TracedPolicy')
        encoded = base.encoder.encode(boundary)
        encoded.validate()
        candidates = boundary.view.candidates
        if tuple(c.candidate_id for c in candidates) != encoded.candidate_ids:
            raise ValueError('candidate row order disagrees with encoded identities')
        mask = tuple(_values(encoded.mask))
        if mask != tuple(c.valid for c in candidates):
            raise ValueError('candidate mask disagrees with public boundary')
        scores = _score_candidates(base, encoded)
        effective_epsilon = epsilon if base.training else self.evaluation_epsilon

        if base.training:
            actual_rng = base.learner._rng
            selection_mode = 'training_original'
        elif effective_epsilon:
            actual_rng = self._evaluation_rng
            selection_mode = 'frozen_epsilon_probe'
        else:
            # Exact same derivation as DDQNPermissionPolicy.select, not a fresh
            # seed chosen by diagnostics. This local RNG never reaches the policy.
            evaluation_seed = int(canonical_hash({'seed': base.seed,
                'context': base.evaluation_context,
                'interruption_budget': boundary.context.interruption_budget,
                'exposure_budget': boundary.context.exposure_budget,
                'decision_index': boundary.view.logical_step})[:16], 16)
            actual_rng = random.Random(evaluation_seed)
            selection_mode = 'frozen_original'
        shadow = random.Random()
        shadow.setstate(actual_rng.getstate())
        explored = shadow.random() < effective_epsilon
        # Do not draw from the real RNG here or predict a tie-breaking choice.
        base_rng_before = base.learner._rng.getstate()
        if selection_mode == 'frozen_epsilon_probe':
            selected = base.learner.select_candidate(encoded, policy_mask=encoded.mask,
                epsilon=effective_epsilon, rng=self._evaluation_rng)
        else:
            selected = base.select(boundary, epsilon=epsilon)
        if not base.training and base.learner._rng.getstate() != base_rng_before:
            raise RuntimeError('frozen diagnostic mutated the learner RNG')
        selected_index = encoded.candidate_ids.index(selected)
        if not mask[selected_index]:
            raise ValueError('selector returned an invalid candidate')
        best = max(q for q, valid in zip(scores, mask) if valid)
        greedy = [cid for cid, q, valid in zip(encoded.candidate_ids, scores, mask) if valid and q == best]
        state_values = _values(encoded.state)
        feature_names = state_feature_names(getattr(base, 'budget_representation', 'none'))
        if len(state_values) != len(feature_names):
            raise ValueError('state features disagree with diagnostic schema')
        rows = []
        for index, (candidate, q) in enumerate(zip(candidates, scores)):
            request = candidate.request_scope
            operation = candidate.operation_scope
            rows.append({'index': index, 'candidate_id': candidate.candidate_id,
                'action': candidate.action.value, 'valid': candidate.valid, 'q': float(q),
                'request_field_count': 0 if request is None else len(request.data_attributes),
                'operation_field_count': 0 if operation is None else len(operation.data_attributes),
                'release_key_count': len(candidate.release_keys)})
        chosen = rows[selected_index]
        global_decision = boundary.view.logical_step
        row = {'schema': 'rl_testing.action_scores.v1', 'token': boundary.token,
            'task_id': boundary.view.position.task_id,
            'global_decision': global_decision, 'phase': boundary.view.phase,
            # The driver defines horizon = global_decision + remaining + 1.
            'control_remaining': max(0, boundary.context.controller_horizon - global_decision - 1),
            'controller_horizon': boundary.context.controller_horizon,
            'planner_remaining': max(0, boundary.context.planner_horizon - boundary.context.planner_turns),
            'state_features': dict(zip(feature_names, state_values)),
            'runtime_budgets': {name: getattr(boundary.context, name, None) for name in
                ('control_steps_used', 'control_step_limit', 'release_steps_used', 'release_step_limit')},
            'epsilon': effective_epsilon, 'requested_epsilon': epsilon,
            'explored': explored, 'selection_mode': selection_mode,
            'candidates': rows, 'selected_candidate_id': selected,
            'selected_index': selected_index, 'selected_action': chosen['action'],
            'selected_q': chosen['q'], 'greedy_candidate_ids': greedy,
            'selected_is_greedy': selected in greedy,
            'execute_legal': any(c['action'] == 'EXECUTE' and c['valid'] for c in rows)}
        self.rows.append(row)
        self.log.event('action_scores', row)
        return selected
