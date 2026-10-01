"""Public facts and controller-decision boundaries for the Agent DDQN bridge."""
from __future__ import annotations

from dataclasses import dataclass, fields
from .contracts import AgentResult, ControlView


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

    def __post_init__(self) -> None:
        for field in fields(self):
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
    reward: int
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
    reward: int
    next_decision: DecisionBoundary | None
    terminated: bool
    truncated: bool
    end: EpisodeEnd | None = None

    def __post_init__(self) -> None:
        if type(self.reward) is not int or self.reward not in {0, 1}:
            raise ValueError('reward must be exact integer 0 or 1')
        if type(self.terminated) is not bool or type(self.truncated) is not bool or (self.terminated and self.truncated):
            raise ValueError('invalid termination flags')
        if self.done != (self.next_decision is None) or self.done != (self.end is not None):
            raise ValueError('closed episode has no successor and must have outcome evidence')
        if not self.done and self.reward != 0:
            raise ValueError('nonterminal reward must be zero')
        if not self.transition_id or not any(c.candidate_id == self.action_candidate_id and c.valid
                                             for c in self.pre_decision.view.candidates):
            raise ValueError('transition action must bind to a legal pre-decision candidate')

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated
