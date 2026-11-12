"""Observed query-local n-step return, gamma=1; every terminal query flushes."""
from collections import deque
from dataclasses import dataclass
from .transitions import ClosedTransition


@dataclass(frozen=True)
class NStepSample:
    pre_decision: object
    action_candidate_id: str
    reward: float
    next_decision: object
    done: bool
    steps: int


class ObservedNStep:
    def __init__(self, n_steps=1):
        if type(n_steps) is not int or not 1 <= n_steps <= 8: raise ValueError('n_steps must be 1..8')
        self.n_steps, self._pending = n_steps, deque()
        self._last = None

    @property
    def pending_count(self): return len(self._pending)

    def append(self, transition):
        if not isinstance(transition, ClosedTransition): raise ValueError('closed observed transition required')
        if self._last is not None and not self._last.done and self._last.next_decision.token != transition.pre_decision.token:
            raise ValueError('noncontiguous or foreign transition')
        if self._last is not None and self._last.pre_decision.view.position.user_id != transition.pre_decision.view.position.user_id:
            raise ValueError('user-local n-step buffer')
        if (self._last is not None and not self._last.done
                and self._last.pre_decision.view.position.task_id != transition.pre_decision.view.position.task_id):
            raise ValueError('n-step returns cannot cross a query boundary')
        self._pending.append(transition); self._last = transition
        out = []
        while self._pending and (transition.done or len(self._pending) >= self.n_steps):
            window = tuple(self._pending)[:self.n_steps]; first, last = window[0], window[-1]
            out.append(NStepSample(first.pre_decision, first.action_candidate_id, sum(t.reward for t in window),
                                  last.next_decision, last.done, len(window)))
            self._pending.popleft()
        return tuple(out)
