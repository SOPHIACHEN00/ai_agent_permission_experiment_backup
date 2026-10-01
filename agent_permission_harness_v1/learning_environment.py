"""Exact-once transitions around the live single-Agent permission boundary.

No simulator shortcut: all planner turns, permissions, receipts and local effects
go through AgentSession. Waiting for a human is suspension, not a transition.
"""
from __future__ import annotations

from uuid import uuid4
from pa_rl.contracts import ControllerAction as A, canonical_hash
from pa_rl.execution import StepStatus
from .candidates import grants_from_ledger
from .contracts import ControlView
from .exposure import ExposureAccount
from .learning_contracts import (ClosedTransition, DecisionBoundary, EpisodeConfig,
                                 HumanWait, PublicEpisodeContext)
from .learning_outcome import close_episode


class AgentLearningEnvironment:
    def __init__(self, session, config: EpisodeConfig | None = None, *, episode_id: str | None = None):
        if session.task.oracle is None:
            raise ValueError('learning requires an authored business oracle')
        if session._logical_step or session._turns or session._terminal is not None:
            raise ValueError('learning environment requires a fresh session')
        self.session = session
        self.config = EpisodeConfig() if config is None else config
        if not isinstance(self.config, EpisodeConfig):
            raise ValueError('config must be EpisodeConfig')
        self.exposure = ExposureAccount()
        if episode_id is not None and (not isinstance(episode_id, str) or not episode_id.strip()):
            raise ValueError('explicit episode_id must be non-empty text')
        self._episode_id = uuid4().hex if episode_id is None else episode_id
        self._ready = self._pending = self._end = None
        self._transitions = []

    @property
    def transitions(self):
        return tuple(self._transitions)

    def _boundary(self, view):
        session = self.session
        snapshot = session.adapter.task_engine.snapshot()
        context = PublicEpisodeContext(
            session.max_control_steps, session.max_planner_turns, session._turns,
            len(snapshot.steps), sum(status is StepStatus.COMMITTED for _, status in snapshot.steps),
            snapshot.primary_complete, snapshot.has_unknown_effect, session._escalations,
            self.exposure.used, self.config.interruption_budget, self.config.exposure_budget)
        token = canonical_hash({'episode': self._episode_id, 'view': view, 'context': context})
        return DecisionBoundary(view, context, token)

    def start(self):
        return self.resume()

    def step(self, candidate_id: str, *, decision_token: str):
        if self._ready is None or self._pending is not None or self._end is not None:
            raise ValueError('no actionable decision; resume outstanding reply or start an episode')
        try:
            if decision_token != self._ready.token:
                raise ValueError('stale or foreign controller decision')
            selected = self.session.validate_control(candidate_id)
        except ValueError:
            self.session.reject_control('invalid_controller_selection')
            self._ready = None
            self._end = close_episode(self.session, self.session.advance(), self.config, self.exposure)
            raise
        boundary, self._ready = self._ready, None
        self.exposure.charge(boundary.token, boundary.view.grants, boundary.view.logical_step)
        extra_prompt = int(selected.action in {A.REQUEST_AUTHORIZATION, A.REQUEST_REFRESH, A.ESCALATE})
        interruptions = boundary.view.prompts_used + boundary.context.escalations_used
        over_budget = (interruptions + extra_prompt > self.config.interruption_budget
                       or self.exposure.used > self.config.exposure_budget)
        self._pending = (boundary, candidate_id)
        self.session.dispatch_control(candidate_id, budget_stop=over_budget)
        return self.resume()

    def resume(self):
        if self._end is not None:
            return self._end
        if self._ready is not None:
            return self._ready
        advanced = self.session.advance()
        if not isinstance(advanced, ControlView) and advanced.status == 'awaiting_human':
            return HumanWait(advanced)
        if self._pending is not None:
            self.exposure.settle(self._pending[0].token, grants_from_ledger(self.session.ledger))
        if isinstance(advanced, ControlView):
            self._ready = self._boundary(advanced)
        else:
            self._end = close_episode(self.session, advanced, self.config, self.exposure)
        if self._pending is None:
            return self._end or self._ready
        boundary, selected = self._pending
        self._pending = None
        transition = ClosedTransition(
            boundary.token, boundary, selected, 0 if self._end is None else self._end.reward,
            self._ready, False if self._end is None else self._end.terminated,
            False if self._end is None else self._end.truncated, self._end)
        self._transitions.append(transition)
        return transition
