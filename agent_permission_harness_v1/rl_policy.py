"""Schema-specific public features and masked RL inference adapters.

The encoder never consumes record values, compiler arguments, oracle labels,
or public-event payloads. A scorer may produce one score per current candidate;
the authoritative candidate mask limits selection. Tabular inference reuses
the real pa_rl learner but does not train or load legacy checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
import random
from typing import Callable, Mapping, Sequence

from pa_rl.baselines import TabularQLearner
from pa_rl.contracts import (
    AuthorizationStatus, ControllerAction, PublicEvent, Scope,
    canonical_hash, contract_json_round_trip, freeze_value,
)

from .contracts import CompiledCall, ControlCandidate, ControlView, GrantView


PUBLIC_FEATURE_SCHEMA = "agent_permission_harness_v1.public_structure.v1"


def _scope(scope: Scope | None) -> Mapping | None:
    if scope is None:
        return None
    if not isinstance(scope, Scope):
        raise ValueError("feature scope must be a Scope or None")
    return {
        "domain": scope.domain, "tool": scope.tool, "resource": scope.resource,
        "data_attributes": scope.data_attributes, "operation": scope.operation,
        "purpose": scope.purpose, "recipient": scope.recipient,
        "retention": scope.retention,
    }


def _identifier(value: object, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _counter(value: object, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _schema(schema_version: str) -> None:
    if schema_version != PUBLIC_FEATURE_SCHEMA:
        raise ValueError("RL feature schema mismatch; legacy fixed-seven checkpoints need explicit adaptation")


@dataclass(frozen=True)
class EncodedControlView:
    schema_version: str
    state_id: str
    candidate_ids: tuple[str, ...]
    valid_mask: tuple[bool, ...]
    state_features: Mapping
    candidate_features: tuple[Mapping, ...]

    def snapshot(self) -> dict:
        return contract_json_round_trip(self)


class PublicFeatureEncoder:
    """Encode permission structure only, with variable candidate cardinality."""

    schema_version = PUBLIC_FEATURE_SCHEMA

    def encode(self, view: ControlView) -> EncodedControlView:
        if not isinstance(view, ControlView) or not isinstance(view.pending, CompiledCall):
            raise ValueError("encoder requires a ControlView with a compiled pending call")
        _identifier(view.pending.step_id, "step_id")
        _counter(view.logical_step, "logical_step")
        _counter(view.prompts_used, "prompts_used")
        grants = []
        grant_ids = set()
        for grant in view.grants:
            if not isinstance(grant, GrantView) or not isinstance(grant.status, AuthorizationStatus):
                raise ValueError("grant features require typed GrantView status")
            _identifier(grant.authorization_id, "authorization_id")
            if grant.authorization_id in grant_ids:
                raise ValueError("grant identities must be unique")
            grant_ids.add(grant.authorization_id)
            _counter(grant.remaining_uses, "remaining_uses", optional=True)
            _counter(grant.expires_at_step, "expires_at_step")
            grants.append({
                "authorization_id": grant.authorization_id, "scope": _scope(grant.scope),
                "status": grant.status.value, "remaining_uses": grant.remaining_uses,
                "expires_at_step": grant.expires_at_step,
            })
        event_types = []
        for event in view.public_history:
            if not isinstance(event, PublicEvent):
                raise ValueError("public_history must contain typed PublicEvents")
            event_types.append(event.event_type)
        state = freeze_value({
            "pending_step_id": view.pending.step_id, "pending_scope": _scope(view.pending.scope),
            "grants": sorted(grants, key=lambda grant: grant["authorization_id"]),
            "logical_step": view.logical_step, "prompts_used": view.prompts_used,
            "public_event_types": tuple(event_types),
        })
        candidate_ids = []
        mask = []
        features = []
        for candidate in view.candidates:
            if not isinstance(candidate, ControlCandidate) or not isinstance(candidate.action, ControllerAction):
                raise ValueError("candidate features require typed ControlCandidate actions")
            _identifier(candidate.candidate_id, "candidate_id")
            if candidate.candidate_id in candidate_ids:
                raise ValueError("candidate IDs must be unique")
            if type(candidate.valid) is not bool:
                raise ValueError("candidate valid mask must be boolean")
            for name in ("authorization_id", "prior_authorization_id", "reason_code", "escalation_target"):
                _identifier(getattr(candidate, name), name, optional=True)
            candidate_ids.append(candidate.candidate_id)
            mask.append(candidate.valid)
            features.append(freeze_value({
                "action": candidate.action.value,
                "request_scope": _scope(candidate.request_scope),
                "operation_scope": _scope(candidate.operation_scope),
                "authorization_id": candidate.authorization_id,
                "prior_authorization_id": candidate.prior_authorization_id,
                "reason_code": candidate.reason_code,
                "escalation_target": candidate.escalation_target,
                "valid": candidate.valid,
            }))
        return EncodedControlView(
            PUBLIC_FEATURE_SCHEMA,
            canonical_hash({"schema": PUBLIC_FEATURE_SCHEMA, "state": state}),
            tuple(candidate_ids), tuple(mask), state, tuple(features),
        )


CandidateScorer = Callable[[EncodedControlView], Sequence[Real]]


def _legal_ids(encoded: EncodedControlView) -> tuple[str, ...]:
    legal = tuple(identifier for identifier, valid in zip(encoded.candidate_ids, encoded.valid_mask) if valid)
    if not legal:
        raise ValueError("no valid permission candidate")
    return legal


def _finite_score(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError("candidate scores must be finite non-boolean real numbers")
    return float(value)


class CandidateScorerPolicy:
    """Bridge a candidate scorer to the runner's semantic-candidate interface."""

    def __init__(self, scorer: CandidateScorer, *, schema_version: str,
                 encoder: PublicFeatureEncoder | None = None) -> None:
        _schema(schema_version)
        if not callable(scorer):
            raise ValueError("scorer must be callable")
        self.scorer = scorer
        self.encoder = encoder or PublicFeatureEncoder()
        _schema(self.encoder.schema_version)

    def choose(self, view: ControlView) -> str:
        encoded = self.encoder.encode(view)
        _schema(encoded.schema_version)
        _legal_ids(encoded)
        scores = self.scorer(encoded)
        if isinstance(scores, (str, bytes, Mapping)):
            raise ValueError("scorer must return one-dimensional candidate scores")
        try:
            scores = tuple(scores)
        except TypeError as exc:
            raise ValueError("scorer must return one-dimensional candidate scores") from exc
        if len(scores) != len(encoded.candidate_ids):
            raise ValueError("candidate score shape does not match current candidate catalog")
        values = tuple(_finite_score(score) for score in scores)
        valid_indices = tuple(index for index, valid in enumerate(encoded.valid_mask) if valid)
        chosen = max(valid_indices, key=lambda index: values[index])
        return encoded.candidate_ids[chosen]


class TabularQPolicy:
    """Epsilon-zero pa_rl TabularQLearner inference under the v1 schema."""

    def __init__(self, learner: TabularQLearner, *, schema_version: str,
                 seed: int = 0, encoder: PublicFeatureEncoder | None = None) -> None:
        _schema(schema_version)
        if not isinstance(learner, TabularQLearner):
            raise ValueError("learner must be the pa_rl TabularQLearner")
        if type(seed) is not int:
            raise ValueError("seed must be an integer")
        self.learner = learner
        self.encoder = encoder or PublicFeatureEncoder()
        _schema(self.encoder.schema_version)
        self.rng = random.Random(seed)

    def choose(self, view: ControlView) -> str:
        encoded = self.encoder.encode(view)
        _schema(encoded.schema_version)
        candidate_ids = _legal_ids(encoded)
        for identifier in candidate_ids:
            _finite_score(self.learner.value(encoded.state_id, identifier))
        selected = self.learner.choose(encoded.state_id, candidate_ids, epsilon=0.0, rng=self.rng)
        if selected not in candidate_ids:
            raise ValueError("learner returned a masked or unknown candidate")
        return selected


__all__ = ["PUBLIC_FEATURE_SCHEMA", "EncodedControlView", "PublicFeatureEncoder",
           "CandidateScorerPolicy", "TabularQPolicy"]
