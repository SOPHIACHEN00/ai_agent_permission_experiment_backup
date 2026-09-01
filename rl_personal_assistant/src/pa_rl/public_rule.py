"""Frozen public-only Rule policy for the Increment-7 held-out suite."""

from __future__ import annotations

from collections.abc import Callable

from .contracts import ControllerAction
from .multiscenario_policy import (
    PUBLIC_CANDIDATE_INDEX_V1,
    PUBLIC_STATE_INDEX_V1,
    PolicyDecisionV1,
)


def choose_public_rule(decision: PolicyDecisionV1) -> str:
    """Select a valid semantic candidate using only public v1 decision fields."""
    if not isinstance(decision, PolicyDecisionV1):
        raise ValueError("decision must be PolicyDecisionV1")
    valid = tuple(
        index
        for index, enabled in enumerate(decision.mask.tolist())
        if enabled
    )
    if not valid:
        raise ValueError("public Rule requires at least one valid candidate")

    def first(
        action: ControllerAction, predicate: Callable[[int], bool] | None = None
    ) -> str | None:
        for index in valid:
            if decision.actions[index] != action.value:
                continue
            if predicate is None or predicate(index):
                return decision.semantic_candidate_ids[index]
        return None

    candidate = PUBLIC_CANDIDATE_INDEX_V1
    usable_execution = first(
        ControllerAction.EXECUTE_WITH_AUTHORIZATION,
        lambda index: bool(decision.candidate_features[index, candidate["authorization_status_active"]].item())
        and bool(decision.candidate_features[index, candidate["expiry_future"]].item())
        and (
            bool(decision.candidate_features[index, candidate["scope_relation_exact"]].item())
            or bool(decision.candidate_features[index, candidate["scope_relation_narrower"]].item())
        )
        and not bool(decision.candidate_features[index, candidate["remaining_uses_zero"]].item()),
    )
    if usable_execution is not None:
        return usable_execution
    refreshed = first(ControllerAction.REQUEST_REFRESH)
    if refreshed is not None:
        return refreshed

    state = PUBLIC_STATE_INDEX_V1
    if float(decision.state[state["public_denial_count"]].item()) > 0.0:
        terminal = first(
            ControllerAction.ESCALATE
            if float(decision.state[state["purpose_unavailable_resolution"]].item()) > 0.5
            else ControllerAction.DENY_WITH_REASON
        )
        if terminal is not None:
            return terminal
    requested = first(ControllerAction.REQUEST_AUTHORIZATION)
    if requested is not None:
        return requested
    return decision.semantic_candidate_ids[valid[0]]


__all__ = ["choose_public_rule"]
