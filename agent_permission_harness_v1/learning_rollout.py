"""Train/evaluate the same controller boundary; human waits remain resumable."""
from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
import hashlib
import random
import torch
from pa_rl.contracts import ControllerAction as A
from .ddqn_policy import DDQNPermissionPolicy
from .learning_contracts import ClosedTransition, DecisionBoundary, EpisodeEnd, HumanWait


class RandomValidPolicy:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def choose(self, view):
        return self.rng.choice([c.candidate_id for c in view.candidates if c.valid])


def drive_episode(environment, policy, *, epsilon=0., learn=False):
    if learn and (not isinstance(policy, DDQNPermissionPolicy) or not policy.training):
        raise ValueError('learning requires a trainable native DDQN policy')
    outcome = environment.start()
    while True:
        if isinstance(outcome, (EpisodeEnd, HumanWait)):
            return outcome
        if isinstance(outcome, ClosedTransition):
            if learn:
                policy.observe(outcome)
            if outcome.done:
                return outcome.end
            outcome = outcome.next_decision
        if not isinstance(outcome, DecisionBoundary):
            raise ValueError('unknown learning environment boundary')
        selected = policy.select(outcome, epsilon=epsilon) if isinstance(policy, DDQNPermissionPolicy) else policy.choose(outcome.view)
        outcome = environment.step(selected, decision_token=outcome.token)


def episode_metrics(end):
    result = end.result
    actions = Counter(row['selected']['action'] for row in result.controller_trace if row['dispatched'])
    return {'status': result.status, 'reward': end.reward, 'business_success': result.oracle_result['success'],
        'permission_prompts': result.prompts_used, 'refresh_prompts': actions[A.REQUEST_REFRESH.value],
        'escalations': result.escalations_used, 'user_interruptions': result.prompts_used + result.escalations_used,
        'controller_steps': result.controller_steps, 'planner_turns': result.planner_turns,
        'exposure_used': end.exposure_used, 'terminal_residual_footprint': end.residual_footprint,
        'privacy_proxy': result.oracle_result.get('privacy_proxy'), 'action_counts': dict(actions),
        'integrity_failures': list(end.integrity_failures), 'terminated': end.terminated, 'truncated': end.truncated}


def training_state_digest(policy):
    """Hash online/target/optimizer/replay/counters/training RNG, not eval-only IDs."""
    digest = hashlib.sha256()
    def add(value):
        if isinstance(value, torch.Tensor):
            digest.update(str((value.dtype, tuple(value.shape))).encode())
            digest.update(value.detach().cpu().contiguous().numpy().tobytes())
        elif is_dataclass(value):
            add({f.name: getattr(value, f.name) for f in fields(value)})
        elif isinstance(value, dict):
            for key in sorted(value, key=str):
                add(key)
                add(value[key])
        elif isinstance(value, (tuple, list)):
            digest.update(str(len(value)).encode())
            for item in value:
                add(item)
        else:
            digest.update(repr(value).encode())
    learner = policy.learner
    add((learner.online_network.state_dict(), learner.target_network.state_dict(), learner._optimizer.state_dict(),
         learner._buffer._items, learner._buffer._cursor, learner._rng.getstate(), learner.environment_steps,
         learner.optimizer_steps, learner.last_loss, learner.online_network.training, learner.target_network.training))
    return digest.hexdigest()
