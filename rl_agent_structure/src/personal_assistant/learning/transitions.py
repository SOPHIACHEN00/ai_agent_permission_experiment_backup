"""Public facts and controller-decision boundaries for the Agent DDQN bridge."""
from __future__ import annotations

from dataclasses import dataclass, fields
import math
from ..contracts.task import AgentResult, ControlView


def nonnegative(value: object, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a non-negative integer')


@dataclass(frozen=True)
class EpisodeConfig:
    interruption_budget: int = 3
    exposure_budget: int = 20

    def __post_init__(self) -> None:
        for field in fields(self):
            nonnegative(getattr(self, field.name), field.name)


@dataclass(frozen=True)
class PublicEpisodeContext:
    controller_horizon: int
    planner_horizon: int
    planner_turns: int
    total_required_steps: int
    committed_steps: int
    primary_complete: bool
    has_unknown_effect: bool
    escalations_used: int
    exposure_used: int
    interruption_budget: int
    exposure_budget: int
    control_steps_used: int | None = None
    control_step_limit: int | None = None
    release_steps_used: int | None = None
    release_step_limit: int | None = None

    def __post_init__(self) -> None:
        budget_fields = {'control_steps_used', 'control_step_limit',
                         'release_steps_used', 'release_step_limit'}
        for field in fields(self):
            if field.name in budget_fields:
                continue
            value = getattr(self, field.name)
            if field.name in {'primary_complete', 'has_unknown_effect'}:
                if type(value) is not bool:
                    raise ValueError(f'{field.name} must be bool')
            else:
                nonnegative(value, field.name)
        if min(self.controller_horizon, self.planner_horizon, self.total_required_steps) < 1:
            raise ValueError('horizons and task size must be positive')
        if self.committed_steps > self.total_required_steps or self.planner_turns > self.planner_horizon:
            raise ValueError('public progress exceeds its declared horizon')
        present = [getattr(self, name) is not None for name in budget_fields]
        if any(present) and not all(present):
            raise ValueError('public runtime budget counters must be all present or all absent')
        if all(present):
            for name in budget_fields:
                nonnegative(getattr(self, name), name)
            if min(self.control_step_limit, self.release_step_limit) < 1:
                raise ValueError('public runtime budget limits must be positive')
            # Cleanup decisions also advance the original runtime control clock.
            # Used may exceed the main limit; encoders clamp remaining to zero.


@dataclass(frozen=True)
class DecisionBoundary:
    view: ControlView
    context: PublicEpisodeContext
    token: str

    def __post_init__(self) -> None:
        if not isinstance(self.view, ControlView) or not isinstance(self.context, PublicEpisodeContext):
            raise ValueError('decision requires a public control view and episode context')
        if not isinstance(self.token, str) or not self.token:
            raise ValueError('decision token is required')


@dataclass(frozen=True)
class HumanWait:
    result: AgentResult


@dataclass(frozen=True)
class EpisodeEnd:
    result: AgentResult
    reward: float
    terminated: bool
    truncated: bool
    exposure_used: int
    residual_footprint: int
    integrity_failures: tuple[str, ...]


@dataclass(frozen=True)
class ClosedTransition:
    transition_id: str
    pre_decision: DecisionBoundary
    action_candidate_id: str
    reward: float
    next_decision: DecisionBoundary | None
    terminated: bool
    truncated: bool
    end: EpisodeEnd | None = None
    task_ended: bool = False
    task_outcome: object = None

    def __post_init__(self) -> None:
        if type(self.reward) not in (int, float) or not math.isfinite(self.reward):
            raise ValueError('reward must be a finite non-boolean number')
        if type(self.terminated) is not bool or type(self.truncated) is not bool or (self.terminated and self.truncated):
            raise ValueError('invalid termination flags')
        if self.done != (self.next_decision is None) or self.done != (self.end is not None):
            raise ValueError('closed episode has no successor and must have outcome evidence')
        if self.next_decision is not None and self.pre_decision.view.position is not None:
            left, right = self.pre_decision.view.position, self.next_decision.view.position
            if right is None or left.user_id != right.user_id or right.decision_index != left.decision_index + 1:
                raise ValueError('transition must connect adjacent decisions for the same user')
        if not self.transition_id or not any(c.candidate_id == self.action_candidate_id and c.valid
                                             for c in self.pre_decision.view.candidates):
            raise ValueError('transition action must bind to a legal pre-decision candidate')

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated
