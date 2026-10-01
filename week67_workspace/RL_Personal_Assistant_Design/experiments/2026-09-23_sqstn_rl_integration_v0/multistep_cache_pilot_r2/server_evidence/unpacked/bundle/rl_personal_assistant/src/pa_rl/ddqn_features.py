"""Public-only features for the Increment-5 rough masked-DDQN prototype.

The layout is frozen as ``public_ddqn_features_v0``.  It is intentionally
small and tailored to the single canonical smoke scenario.

State (23 values)
-----------------
0 logical step / horizon; 1 horizon remaining / horizon; 2 remaining task
steps / horizon; 3 primary complete; 4 unknown effect; 5..7 phase one-hot
(open, finished, unknown); 8 authorization count / horizon; 9..12 active,
consumed, rejected, and other authorization counts / horizon; 13..18 public
history counts (prompt, permission choice, denial, revocation, grant, verified
error) / horizon, clipped to one; 19..20 public allow/deny response rates;
21 candidate count / 16; 22 whether a public active authorization covers the
current task scope.

Candidate (16 values)
---------------------
0..5 action one-hot in ``ControllerAction`` declaration order; 6 has task-step
binding; 7 task-step binding matches the current task; 8 has a non-null current
authorization binding; 9 has a prior-authorization binding; 10 candidate scope
matches the current task scope; 11..13 denial reason one-hot (not needed, user
declined, safe impossibility); 14 bound authorization is active; 15 bound
authorization publicly covers the current scope (exact or narrower).

Raw identifier/hash digits are never encoded.  IDs are retained only for the
semantic action-to-slot boundary at ``PermissionEnvironment.step``.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from .contracts import ControllerAction
from .policy_interface import EnvironmentObservation


FEATURE_VERSION = "public_ddqn_features_v0"
STATE_DIM = 23
CANDIDATE_DIM = 16
MAX_CANDIDATES = 16

_ACTIONS = tuple(ControllerAction)
_PHASES = ("open", "finished", "unknown")
_REASONS = ("not_needed", "user_declined", "safe_impossibility")
_COVERING_RELATIONS = frozenset({"exact", "narrower"})


@dataclass(frozen=True, slots=True)
class EncodedDecision:
    """Frozen record containing only tensors derived from public observation."""

    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    candidate_ids: tuple[str, ...]
    slot_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        state = self.state.detach().to(device="cpu", dtype=torch.float32).clone()
        candidates = (
            self.candidate_features.detach()
            .to(device="cpu", dtype=torch.float32)
            .clone()
        )
        mask = self.mask.detach().to(device="cpu", dtype=torch.bool).clone()
        if tuple(state.shape) != (STATE_DIM,):
            raise ValueError("encoded state must have shape (23,)")
        if (
            candidates.ndim != 2
            or candidates.shape[1] != CANDIDATE_DIM
            or candidates.shape[0] < 1
            or candidates.shape[0] > MAX_CANDIDATES
        ):
            raise ValueError("candidate features must have shape (N,16), 1 <= N <= 16")
        if tuple(mask.shape) != (candidates.shape[0],):
            raise ValueError("encoded mask length must match candidate count")
        if len(self.candidate_ids) != candidates.shape[0] or len(self.slot_indices) != candidates.shape[0]:
            raise ValueError("candidate identities must match candidate count")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate IDs must be unique")
        if self.slot_indices != tuple(range(candidates.shape[0])):
            raise ValueError("candidate slots must be contiguous catalog positions")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "candidate_features", candidates)
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "candidate_ids", tuple(self.candidate_ids))
        object.__setattr__(self, "slot_indices", tuple(self.slot_indices))


def _ratio(value: int, denominator: int) -> float:
    return min(1.0, max(0.0, float(value) / float(max(1, denominator))))


class PublicFeatureEncoder:
    """Encode one live ``EnvironmentObservation`` without audit/oracle access."""

    version = FEATURE_VERSION

    def encode(self, observation: EnvironmentObservation) -> EncodedDecision:
        if not isinstance(observation, EnvironmentObservation):
            raise ValueError("observation must be EnvironmentObservation")
        if observation.logical_step > observation.horizon:
            raise ValueError("closed observations cannot be encoded for action selection")
        if not observation.candidate_catalog:
            raise ValueError("live observation requires a non-empty candidate catalog")

        horizon = observation.horizon
        task = observation.task_view
        authorizations = tuple(observation.authorization_views.values())
        statuses = tuple(row["status"] for row in authorizations)
        history = observation.interaction_history
        counts = history["counts"]
        rates = history["response_rates"]
        current_scope = task["next_required_scope_identity"]

        status_known = {"active", "consumed", "rejected"}
        active_covering = any(
            row["status"] == "active"
            and row["scope_relation"] in _COVERING_RELATIONS
            and row["expiry_bucket"] == "future"
            and (row["remaining_uses"] is None or row["remaining_uses"] > 0)
            for row in authorizations
        )
        state = (
            float(observation.logical_step) / float(horizon),
            float(observation.horizon_remaining) / float(horizon),
            _ratio(task["remaining_step_count"], horizon),
            float(task["primary_complete"]),
            float(task["has_unknown_effect"]),
            *(float(task["phase"] == phase) for phase in _PHASES),
            _ratio(len(authorizations), horizon),
            _ratio(statuses.count("active"), horizon),
            _ratio(statuses.count("consumed"), horizon),
            _ratio(statuses.count("rejected"), horizon),
            _ratio(sum(status not in status_known for status in statuses), horizon),
            *(
                _ratio(counts[key], horizon)
                for key in (
                    "prompt",
                    "permission_choice",
                    "denial",
                    "revocation",
                    "grant",
                    "verified_error",
                )
            ),
            float(rates["allow"]),
            float(rates["deny"]),
            float(len(observation.candidate_catalog)) / float(MAX_CANDIDATES),
            float(active_covering),
        )
        if len(state) != STATE_DIM:
            raise RuntimeError("public state layout drifted from 23 values")

        candidate_rows: list[tuple[float, ...]] = []
        candidate_ids: list[str] = []
        slot_indices: list[int] = []
        for row in observation.candidate_catalog:
            action = ControllerAction(row["action"])
            task_step_id = row.get("task_step_id")
            authorization_id = row.get("authorization_id")
            prior_authorization_id = row.get("prior_authorization_id")
            bound_id = authorization_id or prior_authorization_id
            bound = (
                None
                if bound_id is None
                else observation.authorization_views.get(bound_id)
            )
            features = (
                *(float(action is item) for item in _ACTIONS),
                float(task_step_id is not None),
                float(
                    task_step_id is not None
                    and task_step_id == task["next_required_step_id"]
                ),
                float(authorization_id is not None),
                float(prior_authorization_id is not None),
                float(row["public_scope_identity"] == current_scope),
                *(float(row.get("public_reason_code") == reason) for reason in _REASONS),
                float(bound is not None and bound["status"] == "active"),
                float(
                    bound is not None
                    and bound["scope_relation"] in _COVERING_RELATIONS
                ),
            )
            if len(features) != CANDIDATE_DIM:
                raise RuntimeError("candidate layout drifted from 16 values")
            candidate_rows.append(features)
            candidate_ids.append(row["identifier"])
            slot_indices.append(row["slot_index"])

        return EncodedDecision(
            state=torch.tensor(state, dtype=torch.float32, device="cpu"),
            candidate_features=torch.tensor(
                candidate_rows, dtype=torch.float32, device="cpu"
            ),
            mask=torch.tensor(
                observation.action_mask, dtype=torch.bool, device="cpu"
            ),
            candidate_ids=tuple(candidate_ids),
            slot_indices=tuple(slot_indices),
        )


__all__ = [
    "CANDIDATE_DIM",
    "EncodedDecision",
    "FEATURE_VERSION",
    "MAX_CANDIDATES",
    "PublicFeatureEncoder",
    "STATE_DIM",
]
