"""Public-state finite MDP, rational DP and fixed rules for Stage A only."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, replace
from fractions import Fraction as F

ACTIONS = ("deny", "disable", "escalate", "execute_covering", "request_broader",
           "request_narrow", "request_refresh")


@dataclass(frozen=True, slots=True)
class State:
    n1: int
    n2: int
    forecast: F
    future_high: F
    exposure: int
    prompts: int
    stage: int = 1
    progress: int = 0
    grant: int = 0
    request_open: bool = True
    branch: int = 0
    remaining: int = 12
    status: str = "running"

    def __post_init__(self) -> None:
        for name in ("n1", "n2", "exposure", "prompts", "stage", "progress", "grant", "branch", "remaining"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an exact integer")
        if min(self.n1, self.n2) < 1 or min(self.exposure, self.prompts, self.remaining) < 0:
            raise ValueError("invalid costs or remaining resources")
        if self.stage not in (1, 2) or self.progress not in (0, 1, 2):
            raise ValueError("invalid task position")
        if self.grant not in (0, 1, 2) or self.branch not in (0, 1, 2):
            raise ValueError("invalid scope/branch")
        if type(self.request_open) is not bool or self.remaining > 12:
            raise ValueError("invalid request window or horizon")
        for probability in (self.forecast, self.future_high):
            if type(probability) is not F or not 0 < probability < 1:
                raise ValueError("probabilities must be rational and strictly between zero and one")
        if self.status not in ("running", "success", "deny", "escalate", "truncated"):
            raise ValueError("invalid termination")

    @property
    def cost(self) -> int:
        return self.n1 if self.stage == 1 else self.n2


def legal_actions(state: State) -> tuple[str, ...]:
    if state.status != "running" or state.remaining == 0:
        return ()
    valid = {"deny", "escalate"}
    if state.grant:
        valid.add("disable")
    required = state.branch if state.progress == 1 else 1
    if state.grant >= required and state.grant and state.exposure >= state.grant * state.cost:
        valid.add("execute_covering")
    if state.prompts > 0:
        if state.request_open and state.exposure >= state.cost:
            valid.add("request_narrow")
        recourse = state.progress == 1 and state.branch == 2 and state.grant == 1
        if (state.request_open or recourse) and state.exposure >= 2 * state.cost:
            valid.add("request_broader")
    return tuple(sorted(valid))


def _bounded(state: State) -> State:
    if state.status == "running" and state.remaining == 0:
        return replace(state, status="truncated", grant=0)
    return state


def transitions(state: State, action: str) -> tuple[tuple[F, State], ...]:
    """No histories, graph IDs, sampled futures or oracle labels in state."""
    if action not in legal_actions(state):
        raise ValueError("invalid action; no transition or effect")
    next_state = replace(state, remaining=state.remaining - 1)
    if action in ("deny", "escalate"):
        return ((F(1), replace(next_state, status=action, grant=0)),)
    if action == "disable":
        return ((F(1), _bounded(replace(next_state, grant=0))),)
    if action.startswith("request_"):
        width = 1 if action == "request_narrow" else 2
        return ((F(1), _bounded(replace(next_state, grant=width, request_open=False,
                     exposure=state.exposure - width * state.cost, prompts=state.prompts - 1))),)
    next_state = replace(next_state, exposure=state.exposure - state.grant * state.cost)
    if state.progress == 0:
        return tuple((p, _bounded(replace(next_state, progress=1, branch=branch)))
                     for p, branch in ((state.forecast, 1), (1 - state.forecast, 2)))
    if state.stage == 2:
        return ((F(1), replace(next_state, progress=2, status="success", grant=0)),)
    return tuple((p, _bounded(replace(next_state, stage=2, progress=0, branch=0,
                                     grant=0, request_open=True, forecast=forecast)))
                 for p, forecast in ((1 - state.future_high, F(1, 5)), (state.future_high, F(4, 5))))


def peak_rss_bytes() -> int:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = wintypes.HANDLE
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not get_info(current(), ctypes.byref(counters), counters.cb):
            raise OSError("cannot measure process memory")
        return int(counters.PeakWorkingSetSize)
    import resource
    import sys
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss * 1024)


class ResourceLimit(RuntimeError):
    pass


class Budget:
    def __init__(self, max_states: int = 100000, seconds: float = 60, rss_mib: int = 512) -> None:
        if max_states < 1 or seconds <= 0 or rss_mib <= 0:
            raise ValueError("resource caps must be positive")
        self.max_states, self.seconds, self.rss_bytes = max_states, seconds, rss_mib * 1024**2
        self.started = time.monotonic()
        self.states: set[State] = set()
        self.peak_rss = 0

    def check(self, state: State | None = None) -> None:
        if state is not None and state.status == "running":
            self.states.add(state)
        self.peak_rss = max(self.peak_rss, peak_rss_bytes())
        if len(self.states) > self.max_states or time.monotonic() - self.started > self.seconds or self.peak_rss > self.rss_bytes:
            raise ResourceLimit("fixed state/time/RSS cap reached; do not raise caps or retry")


class Solver:
    def __init__(self, budget: Budget | None = None) -> None:
        self.budget = budget or Budget()
        self.values: dict[State, F] = {}
        self.policy_values: dict[tuple[str, State], F] = {}
        self.local_scores: dict[State, tuple[F, F, F]] = {}
        self.local_actions: dict[State, str] = {}

    def q_values(self, state: State) -> dict[str, F]:
        self.budget.check(state)
        return {action: sum((p * self.value(child) for p, child in transitions(state, action)), F(0))
                for action in legal_actions(state)}

    def value(self, state: State) -> F:
        self.budget.check(state)
        if state.status != "running":
            return F(state.status == "success")
        if state not in self.values:
            self.values[state] = max(self.q_values(state).values(), default=F(0))
        return self.values[state]

    def optimal_actions(self, state: State) -> tuple[str, ...]:
        q = self.q_values(state)
        best = max(q.values(), default=F(0))
        return tuple(action for action, value in q.items() if value == best)

    def _local_score(self, state: State) -> tuple[F, F, F]:
        """Current-task completion, added exposure, prompts; never reads full V*."""
        self.budget.check(state)
        if state.status != "running":
            return F(state.status == "success"), F(0), F(0)
        if state in self.local_scores:
            return self.local_scores[state]
        scored = []
        for action in legal_actions(state):
            totals = [F(0), F(0), F(0)]
            for probability, child in transitions(state, action):
                completed = child.stage > state.stage or child.status == "success"
                tail = (F(1), F(0), F(0)) if completed else self._local_score(child)
                totals[0] += probability * tail[0]
                totals[1] += probability * (state.exposure - child.exposure + tail[1])
                totals[2] += probability * (state.prompts - child.prompts + tail[2])
            scored.append((tuple(totals), action))
        if not scored:
            return F(0), F(0), F(0)
        score, action = min(scored, key=lambda pair: (-pair[0][0], pair[0][1], pair[0][2], pair[1]))
        self.local_scores[state], self.local_actions[state] = score, action
        return score

    def choose(self, method: str, state: State) -> str:
        valid = legal_actions(state)
        if not valid:
            raise ValueError("terminal state has no action")
        if method == "forecast_transfer_rule":
            if "execute_covering" in valid:
                return "execute_covering"
            if not state.request_open:
                return "request_broader" if "request_broader" in valid else "deny"
            preferred = "request_narrow" if state.forecast > F(1, 2) else "request_broader"
            other = "request_broader" if preferred == "request_narrow" else "request_narrow"
            return next((action for action in (preferred, other, "deny") if action in valid))
        if method not in ("current_task_rule", "reservation_rule"):
            raise ValueError("unknown deterministic rule")
        local = state
        if method == "reservation_rule" and state.stage == 1:
            if state.exposure < 3 * state.n2 or state.prompts < 1:
                return "deny"
            local = replace(state, exposure=state.exposure - 3 * state.n2, prompts=state.prompts - 1)
        if self._local_score(local)[0] == 0:
            return "deny"
        return self.local_actions[local]

    def policy_value(self, method: str, state: State) -> F:
        self.budget.check(state)
        if state.status != "running":
            return F(state.status == "success")
        key = method, state
        if key not in self.policy_values:
            actions = legal_actions(state) if method == "random_valid" else (self.choose(method, state),)
            self.policy_values[key] = sum((p * self.policy_value(method, child) / len(actions)
                for action in actions for p, child in transitions(state, action)), F(0)) if actions else F(0)
        return self.policy_values[key]


def state_from_row(row: dict[str, object], *, toggle: bool = False) -> State:
    prompts = int(row["prompt_budget"])
    return State(n1=int(row["n1"]), n2=int(row["n2"]), forecast=F(row["p1"]),
                 future_high=F(row["r"]), exposure=int(row["exposure_budget"]),
                 prompts=5 - prompts if toggle else prompts)
