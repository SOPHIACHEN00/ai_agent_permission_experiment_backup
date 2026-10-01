"""Immutable public and operational contracts for Family-3 v2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .contracts import Scope


FAMILY3_V2_SCHEMA_VERSION = "family3_v2_graph_row_v0"
FAMILY3_V2_SUITE_VERSION = "increment8_family3_v2_forecast_scope_reservation_v0"
FAMILY3_V2_RESPONSE_PROFILE = "deterministic_allow_reuse"
FAMILY3_V2_GRANT_LIFETIME_PROFILE = "reusable_through_horizon_plus_one_v0"
FAMILY3_V2_TOOL_OUTCOME_PROFILE = "deterministic_exactly_once_commit_v0"


class CandidateRoleV2(str, Enum):
    REQUEST_NARROW = "request_narrow"
    REQUEST_BROADER = "request_broader"
    EXECUTE_COVERING = "execute_covering"
    REFRESH_CLOSED = "refresh_closed"
    DISABLE_ACTIVE = "disable_active"
    DENY = "deny"
    ESCALATE = "escalate"


FAMILY3_V2_CANDIDATE_ORDER = (
    CandidateRoleV2.REQUEST_NARROW,
    CandidateRoleV2.REQUEST_BROADER,
    CandidateRoleV2.EXECUTE_COVERING,
    CandidateRoleV2.REFRESH_CLOSED,
    CandidateRoleV2.DISABLE_ACTIVE,
    CandidateRoleV2.DENY,
    CandidateRoleV2.ESCALATE,
)


class OfferWindowV2(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class ContinuationModeV2(str, Enum):
    UNREALIZED = "unrealized"
    EXACT = "exact"
    BROADER = "broader"


class ForecastModeV2(str, Enum):
    EXACT_HEAVY = "exact_heavy"
    BROADER_HEAVY = "broader_heavy"


def _exact_int(name: str, value: object, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an exact int >= {minimum}")
    return value


def forecast_mode_from_probabilities(
    forecast_exact_probability: Fraction,
    forecast_broader_probability: Fraction,
) -> ForecastModeV2:
    """Return the sole forecast label allowed by the fixed denominator-five contract."""
    if type(forecast_exact_probability) is not Fraction or type(forecast_broader_probability) is not Fraction:
        raise ValueError("forecast probabilities must be exact Fraction values")
    if (forecast_exact_probability, forecast_broader_probability) == (Fraction(4, 5), Fraction(1, 5)):
        return ForecastModeV2.EXACT_HEAVY
    if (forecast_exact_probability, forecast_broader_probability) == (Fraction(1, 5), Fraction(4, 5)):
        return ForecastModeV2.BROADER_HEAVY
    raise ValueError("forecast probabilities must be the frozen 4/5 and 1/5 pair")


@dataclass(frozen=True, slots=True)
class ForecastScopeOfferV2:
    """Authority-side scope offer; both operational scopes remain immutable."""

    narrow_scope: Scope
    broader_scope: Scope
    narrow_exposure_cost: int
    broader_exposure_cost: int
    forecast_exact_probability: Fraction
    forecast_broader_probability: Fraction
    response_profile: str = FAMILY3_V2_RESPONSE_PROFILE
    offer_window: OfferWindowV2 = OfferWindowV2.OPEN

    def __post_init__(self) -> None:
        if not isinstance(self.narrow_scope, Scope) or not isinstance(self.broader_scope, Scope):
            raise ValueError("offered scopes must be typed Scope values")
        _exact_int("narrow exposure cost", self.narrow_exposure_cost, minimum=1)
        _exact_int("broader exposure cost", self.broader_exposure_cost, minimum=1)
        if self.broader_exposure_cost <= self.narrow_exposure_cost:
            raise ValueError("broader exposure cost must exceed narrow exposure cost")
        if self.response_profile != FAMILY3_V2_RESPONSE_PROFILE:
            raise ValueError("response profile is not the frozen deterministic profile")
        if not isinstance(self.offer_window, OfferWindowV2):
            raise ValueError("offer window must be typed")
        forecast_mode_from_probabilities(self.forecast_exact_probability, self.forecast_broader_probability)

    @property
    def forecast_mode(self) -> ForecastModeV2:
        return forecast_mode_from_probabilities(
            self.forecast_exact_probability,
            self.forecast_broader_probability,
        )


__all__ = [
    "CandidateRoleV2",
    "ContinuationModeV2",
    "FAMILY3_V2_CANDIDATE_ORDER",
    "FAMILY3_V2_GRANT_LIFETIME_PROFILE",
    "FAMILY3_V2_RESPONSE_PROFILE",
    "FAMILY3_V2_SCHEMA_VERSION",
    "FAMILY3_V2_SUITE_VERSION",
    "FAMILY3_V2_TOOL_OUTCOME_PROFILE",
    "ForecastModeV2",
    "ForecastScopeOfferV2",
    "OfferWindowV2",
    "forecast_mode_from_probabilities",
]
