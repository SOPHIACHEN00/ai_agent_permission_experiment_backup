"""Trusted, pilot-only canonical-protocol outcome tracking.

This module intentionally consumes the manifest's evaluator-only trace.  It
must remain outside public policy projections, replay entries, and learners.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import ControllerAction, PermissionChoice, action_requires_permission_answer
from .policy_interface import ResolvedCandidate
from .scenarios import ExpectedTermination, ScenarioManifest


_REASON_IN_PROGRESS = "in_progress"
_REASON_SUCCESS = "protocol_success"
_REASON_TRACE = "trace_diverged"
_REASON_PERMISSION = "permission_choice_diverged"
_REASON_AUDIT = "audit_invalid"
_REASON_TERMINATION = "termination_mismatch"
_REASON_BASE_REWARD = "base_reward_mismatch"


@dataclass(frozen=True)
class ProtocolOutcome:
    """One immutable protocol-reward observation for a selected action."""

    reward: int
    base_reward: int
    conforming_prefix: bool
    complete: bool
    expected_termination_matched: bool
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.reward) is not int or self.reward not in {0, 1}:
            raise ValueError("protocol reward must be binary")
        if type(self.base_reward) is not int or self.base_reward not in {0, 1}:
            raise ValueError("base reward must be binary")
        if not isinstance(self.conforming_prefix, bool):
            raise ValueError("conforming_prefix must be boolean")
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be boolean")
        if not isinstance(self.expected_termination_matched, bool):
            raise ValueError("expected_termination_matched must be boolean")
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise ValueError("reason_code must be non-empty text")


class CanonicalProtocolTracker:
    """Compare trusted episode evidence with one manifest's canonical trace."""

    def __init__(self, manifest: ScenarioManifest) -> None:
        if not isinstance(manifest, ScenarioManifest):
            raise ValueError("manifest must be a ScenarioManifest")
        self._expected_signatures = tuple(
            (step.action, step.scope_step_id) for step in manifest.legal_action_trace
        )
        self._expected_permissions = tuple(
            step.permission_response
            for step in manifest.legal_action_trace
            if step.permission_response is not None
        )
        self._expected_termination = manifest.expected_termination
        self._observed_signatures: list[tuple[ControllerAction, str | None]] = []

    @staticmethod
    def _selected_signature(
        selected_row: Mapping[str, Any] | ResolvedCandidate,
    ) -> tuple[ControllerAction, str | None]:
        if isinstance(selected_row, ResolvedCandidate):
            return selected_row.action, selected_row.task_step_id
        if not isinstance(selected_row, Mapping):
            raise ValueError("selected_row must be a public candidate row")
        try:
            action = ControllerAction(selected_row["action"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("selected_row has an invalid action") from error
        step_id = selected_row.get("task_step_id")
        if step_id is not None and (not isinstance(step_id, str) or not step_id):
            raise ValueError("selected_row has an invalid task binding")
        return action, step_id

    @staticmethod
    def _permission_choices(audit: Mapping[str, Any]) -> tuple[PermissionChoice, ...]:
        events = audit.get("authorization_events")
        if not isinstance(events, tuple):
            raise ValueError("audit lacks authorization events")
        choices: list[PermissionChoice] = []
        for event in events:
            event_type = getattr(event, "event_type", None)
            payload = getattr(event, "payload", None)
            if isinstance(event, Mapping):
                event_type = event.get("event_type")
                payload = event.get("payload")
            if event_type != "permission_applied":
                continue
            if not isinstance(payload, Mapping):
                raise ValueError("permission audit payload is invalid")
            try:
                choices.append(PermissionChoice(payload["permission_choice"]))
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("permission audit choice is invalid") from error
        return tuple(choices)

    def observe(
        self,
        selected_row: Mapping[str, Any] | ResolvedCandidate,
        *,
        base_reward: int,
        terminated: bool,
        truncated: bool,
        audit: Mapping[str, Any],
    ) -> ProtocolOutcome:
        """Record one environment step and return a binary benchmark reward."""
        if type(base_reward) is not int or base_reward not in {0, 1}:
            raise ValueError("base_reward must be binary")
        if not isinstance(terminated, bool) or not isinstance(truncated, bool):
            raise ValueError("terminated and truncated must be boolean")
        if terminated and truncated:
            raise ValueError("a transition cannot terminate and truncate")
        if not isinstance(audit, Mapping):
            raise ValueError("audit must be a mapping")

        signature = self._selected_signature(selected_row)
        self._observed_signatures.append(signature)
        try:
            observed_permissions = self._permission_choices(audit)
        except ValueError:
            return self._outcome(
                base_reward=base_reward,
                conforming_prefix=False,
                complete=False,
                expected_termination_matched=False,
                reason_code=_REASON_AUDIT,
            )

        expected_permission_count = sum(
            action_requires_permission_answer(action)
            for action, _step_id in self._observed_signatures
        )
        actions_match = tuple(self._observed_signatures) == self._expected_signatures[: len(self._observed_signatures)]
        permissions_match = (
            len(observed_permissions) == expected_permission_count
            and observed_permissions == self._expected_permissions[: len(observed_permissions)]
        )
        conforming_prefix = actions_match and permissions_match
        complete = (
            tuple(self._observed_signatures) == self._expected_signatures
            and observed_permissions == self._expected_permissions
        )
        expected_termination_matched = (
            (self._expected_termination is ExpectedTermination.TERMINAL and terminated and not truncated)
            or (self._expected_termination is ExpectedTermination.TRUNCATED and truncated and not terminated)
        )

        closed = terminated or truncated
        if not conforming_prefix:
            reason = _REASON_TRACE if not actions_match else _REASON_PERMISSION
        elif not closed:
            reason = _REASON_IN_PROGRESS
        elif not complete:
            reason = _REASON_TRACE
        elif not expected_termination_matched:
            reason = _REASON_TERMINATION
        elif base_reward != (0 if self._expected_termination is ExpectedTermination.TRUNCATED else 1):
            reason = _REASON_BASE_REWARD
        else:
            reason = _REASON_SUCCESS

        return self._outcome(
            base_reward=base_reward,
            conforming_prefix=conforming_prefix,
            complete=complete,
            expected_termination_matched=expected_termination_matched,
            reason_code=reason,
        )

    @staticmethod
    def _outcome(
        *,
        base_reward: int,
        conforming_prefix: bool,
        complete: bool,
        expected_termination_matched: bool,
        reason_code: str,
    ) -> ProtocolOutcome:
        return ProtocolOutcome(
            reward=int(reason_code == _REASON_SUCCESS),
            base_reward=base_reward,
            conforming_prefix=conforming_prefix,
            complete=complete,
            expected_termination_matched=expected_termination_matched,
            reason_code=reason_code,
        )


__all__ = ["CanonicalProtocolTracker", "ProtocolOutcome"]
