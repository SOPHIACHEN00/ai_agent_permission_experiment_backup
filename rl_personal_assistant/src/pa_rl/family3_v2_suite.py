"""Literal Family-3 v2 graph registry and kernel input construction."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from .contracts import Scope, canonical_hash
from .family3_v2_contracts import (
    FAMILY3_V2_GRANT_LIFETIME_PROFILE,
    FAMILY3_V2_RESPONSE_PROFILE,
    FAMILY3_V2_SCHEMA_VERSION,
    FAMILY3_V2_SUITE_VERSION,
    FAMILY3_V2_TOOL_OUTCOME_PROFILE,
    ForecastModeV2,
    ForecastScopeOfferV2,
    forecast_mode_from_probabilities,
)
from .scope_matching import ScopeRelation, covers, relation


@dataclass(frozen=True, slots=True)
class _CarrierLiteral:
    code: str
    domain: str
    tool: str
    resource: str
    base_attributes: tuple[str, ...]
    broader_attribute: str
    operation: str
    recipient: str
    retention: str
    sensitivity: int

    def scope(self, purpose: str, *, broader: bool = False) -> Scope:
        return Scope(
            domain=self.domain,
            tool=self.tool,
            resource=self.resource,
            data_attributes=self.base_attributes + ((self.broader_attribute,) if broader else ()),
            operation=self.operation,
            purpose=purpose,
            recipient=self.recipient,
            retention=self.retention,
        )


_CARRIER_LITERALS = (
    _CarrierLiteral("c0_calendar", "productivity", "calendar_api", "calendar.events", ("start_time", "title"), "end_time", "read", "local_user", "session", 1),
    _CarrierLiteral("c1_mail_archive", "productivity", "mail_api", "mail.messages", ("message_id",), "body", "archive", "local_user", "session", 2),
    _CarrierLiteral("c2_mail_send", "productivity", "mail_api", "mail.messages", ("body",), "recipient", "send", "team", "session", 2),
    _CarrierLiteral("c3_report", "productivity", "report_api", "reports.weekly", ("end_time", "time"), "title", "read", "stakeholder", "session", 1),
    _CarrierLiteral("c4_records", "records", "records_api", "records.private", ("record",), "recipient", "send", "third_party", "external", 3),
)
_CARRIERS_BY_CODE = {carrier.code: carrier for carrier in _CARRIER_LITERALS}

_ROWS = (
    ("i8_f3v2_v0", "train", "c0_calendar", "agenda_summary", 4, 2, 1, 3, 9, 8),
    ("i8_f3v2_v1", "train", "c1_mail_archive", "status_notice", 1, 3, 1, 4, 12, 8),
    ("i8_f3v2_v2", "train", "c2_mail_send", "inbox_cleanup", 4, 3, 2, 4, 16, 8),
    ("i8_f3v2_v3", "train", "c3_report", "weekly_report", 1, 4, 2, 5, 12, 8),
    ("i8_f3v2_v4", "train", "c4_records", "approved_update", 4, 4, 3, 5, 30, 8),
    ("i8_f3v2_v5", "validation", "c0_calendar", "inbox_cleanup", 1, 5, 3, 6, 15, 9),
    ("i8_f3v2_v6", "validation", "c1_mail_archive", "weekly_report", 4, 5, 4, 6, 24, 9),
    ("i8_f3v2_v7", "test", "c2_mail_send", "approved_update", 1, 6, 4, 7, 24, 10),
    ("i8_f3v2_v8", "test", "c3_report", "agenda_summary", 4, 6, 5, 7, 21, 10),
    ("i8_f3v2_v9", "test", "c4_records", "status_notice", 1, 5, 3, 6, 30, 9),
)


def _exact_int(name: str, value: object, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an exact int >= {minimum}")
    return value


def _scope_exposure(scope: Scope, sensitivity: int) -> int:
    return sensitivity * len(scope.data_attributes)


def _scope_mapping(scope: Scope) -> dict[str, object]:
    return {
        "domain": scope.domain,
        "tool": scope.tool,
        "resource": scope.resource,
        "data_attributes": scope.data_attributes,
        "operation": scope.operation,
        "purpose": scope.purpose,
        "recipient": scope.recipient,
        "retention": scope.retention,
    }


@dataclass(frozen=True, slots=True)
class Family3V2GraphSpec:
    graph_id: str
    split: str
    carrier_code: str
    purpose: str
    narrow_scope: Scope
    broader_scope: Scope
    n: int
    b: int
    forecast_exact_probability: Fraction
    forecast_broader_probability: Fraction
    e: int
    d: int
    target: int
    prompt_budget: int
    exposure_budget: int
    horizon: int
    response_profile: str = FAMILY3_V2_RESPONSE_PROFILE
    grant_lifetime_profile: str = FAMILY3_V2_GRANT_LIFETIME_PROFILE
    tool_outcome_profile: str = FAMILY3_V2_TOOL_OUTCOME_PROFILE

    def __post_init__(self) -> None:
        carrier = _CARRIERS_BY_CODE.get(self.carrier_code)
        if carrier is None:
            raise ValueError("unknown frozen carrier code")
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        if not isinstance(self.narrow_scope, Scope) or not isinstance(self.broader_scope, Scope):
            raise ValueError("graph scopes must be typed Scope values")
        if self.narrow_scope != carrier.scope(self.purpose):
            raise ValueError("narrow scope is not canonical for the frozen carrier and purpose")
        if self.broader_scope != carrier.scope(self.purpose, broader=True):
            raise ValueError("broader scope is not canonical for the frozen carrier and purpose")
        if (
            not covers(self.narrow_scope, self.narrow_scope)
            or not covers(self.broader_scope, self.narrow_scope)
            or covers(self.narrow_scope, self.broader_scope)
            or relation(self.narrow_scope, self.narrow_scope) is not ScopeRelation.EXACT
            or relation(self.broader_scope, self.narrow_scope) is not ScopeRelation.NARROWER
            or relation(self.narrow_scope, self.broader_scope) is not ScopeRelation.BROADER
        ):
            raise ValueError("scopes do not satisfy the canonical coverage relation")
        for field_name in ("n", "b", "e", "d", "target", "prompt_budget", "exposure_budget", "horizon"):
            _exact_int(field_name, getattr(self, field_name), minimum=1)
        expected_n = _scope_exposure(self.narrow_scope, carrier.sensitivity)
        expected_b = _scope_exposure(self.broader_scope, carrier.sensitivity)
        if self.n != expected_n or self.b != expected_b or not self.n < self.b:
            raise ValueError("scope exposure costs do not match the frozen scope relation")
        _exact_int("e", self.e, minimum=1)
        _exact_int("d", self.d, minimum=1)
        if not self.e > self.d or self.e - self.d > 2:
            raise ValueError("continuation template must satisfy e > d >= 1 and e - d <= 2")
        if self.target != self.e + 1:
            raise ValueError("target must equal e + 1")
        if self.prompt_budget != 1:
            raise ValueError("prompt budget must be exactly one")
        if self.exposure_budget != max((self.e + 2) * self.n, (self.d + 2) * self.b):
            raise ValueError("exposure budget does not match the construction theorem")
        if self.horizon != max(8, self.e + 4):
            raise ValueError("horizon does not match the construction theorem")
        if self.response_profile != FAMILY3_V2_RESPONSE_PROFILE:
            raise ValueError("response profile is not frozen")
        if self.grant_lifetime_profile != FAMILY3_V2_GRANT_LIFETIME_PROFILE:
            raise ValueError("grant lifetime profile is not frozen")
        if self.tool_outcome_profile != FAMILY3_V2_TOOL_OUTCOME_PROFILE:
            raise ValueError("tool outcome profile is not frozen")
        forecast_mode_from_probabilities(self.forecast_exact_probability, self.forecast_broader_probability)
        if self.literal_row not in _ROWS:
            raise ValueError("graph must match one of the ten frozen literal rows")
        if tuple(self.row_mapping()) != (
            "schema_version", "suite_version", "graph_id", "split", "carrier_code", "purpose",
            "narrow_scope", "broader_scope", "n", "b", "forecast_exact_numerator",
            "forecast_exact_denominator", "e", "d", "target", "prompt_budget", "exposure_budget",
            "horizon", "response_profile", "grant_lifetime_profile", "tool_outcome_profile",
        ):
            raise ValueError("graph row mapping must retain the exact 21-field allowlist")

    @property
    def literal_row(self) -> tuple[object, ...]:
        return (
            self.graph_id, self.split, self.carrier_code, self.purpose,
            self.forecast_exact_probability.numerator, self.e, self.d, self.target,
            self.exposure_budget, self.horizon,
        )

    @property
    def forecast_mode(self) -> ForecastModeV2:
        return forecast_mode_from_probabilities(
            self.forecast_exact_probability,
            self.forecast_broader_probability,
        )

    @property
    def branch_coupling_uid(self) -> str:
        return canonical_hash({
            "suite_version": FAMILY3_V2_SUITE_VERSION,
            "source_graph_id": self.graph_id,
            "narrow_scope": _scope_mapping(self.narrow_scope),
            "broader_scope": _scope_mapping(self.broader_scope),
            "e": self.e,
            "d": self.d,
            "target": self.target,
            "prompt_budget": self.prompt_budget,
            "exposure_budget": self.exposure_budget,
            "horizon": self.horizon,
            "response_profile": self.response_profile,
            "grant_lifetime_profile": self.grant_lifetime_profile,
            "tool_outcome_profile": self.tool_outcome_profile,
        })

    def row_mapping(self) -> dict[str, object]:
        return {
            "schema_version": FAMILY3_V2_SCHEMA_VERSION,
            "suite_version": FAMILY3_V2_SUITE_VERSION,
            "graph_id": self.graph_id,
            "split": self.split,
            "carrier_code": self.carrier_code,
            "purpose": self.purpose,
            "narrow_scope": _scope_mapping(self.narrow_scope),
            "broader_scope": _scope_mapping(self.broader_scope),
            "n": self.n,
            "b": self.b,
            "forecast_exact_numerator": self.forecast_exact_probability.numerator,
            "forecast_exact_denominator": self.forecast_exact_probability.denominator,
            "e": self.e,
            "d": self.d,
            "target": self.target,
            "prompt_budget": self.prompt_budget,
            "exposure_budget": self.exposure_budget,
            "horizon": self.horizon,
            "response_profile": self.response_profile,
            "grant_lifetime_profile": self.grant_lifetime_profile,
            "tool_outcome_profile": self.tool_outcome_profile,
        }

    @property
    def row_hash(self) -> str:
        return canonical_hash(self.row_mapping())


@dataclass(frozen=True, slots=True)
class Family3V2Suite:
    graphs: tuple[Family3V2GraphSpec, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.graphs, tuple) or any(not isinstance(graph, Family3V2GraphSpec) for graph in self.graphs):
            raise ValueError("suite graphs must be a typed tuple")
        expected_ids = tuple(row[0] for row in _ROWS)
        actual_ids = tuple(graph.graph_id for graph in self.graphs)
        if actual_ids != expected_ids or len(set(actual_ids)) != len(_ROWS):
            raise ValueError("suite must contain the ten literal rows in canonical order")

    @property
    def suite_hash(self) -> str:
        return canonical_hash([graph.row_mapping() for graph in self.graphs])


@dataclass(frozen=True, slots=True)
class Family3V2KernelInput:
    source_graph_id: str
    offer: ForecastScopeOfferV2
    e: int
    d: int
    target: int
    prompt_budget: int
    exposure_budget: int
    horizon: int
    grant_lifetime_profile: str
    tool_outcome_profile: str
    branch_coupling_uid: str

    @classmethod
    def from_graph(cls, graph: Family3V2GraphSpec) -> Family3V2KernelInput:
        if not isinstance(graph, Family3V2GraphSpec):
            raise ValueError("kernel input must be constructed from a typed graph")
        return cls(
            source_graph_id=graph.graph_id,
            offer=ForecastScopeOfferV2(
                narrow_scope=graph.narrow_scope,
                broader_scope=graph.broader_scope,
                narrow_exposure_cost=graph.n,
                broader_exposure_cost=graph.b,
                forecast_exact_probability=graph.forecast_exact_probability,
                forecast_broader_probability=graph.forecast_broader_probability,
                response_profile=graph.response_profile,
            ),
            e=graph.e,
            d=graph.d,
            target=graph.target,
            prompt_budget=graph.prompt_budget,
            exposure_budget=graph.exposure_budget,
            horizon=graph.horizon,
            grant_lifetime_profile=graph.grant_lifetime_profile,
            tool_outcome_profile=graph.tool_outcome_profile,
            branch_coupling_uid=graph.branch_coupling_uid,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.offer, ForecastScopeOfferV2):
            raise ValueError("kernel offer must be typed")
        if type(self.source_graph_id) is not str or not self.source_graph_id:
            raise ValueError("source graph ID must be a non-empty string")
        for field_name in ("e", "d", "target", "prompt_budget", "exposure_budget", "horizon"):
            _exact_int(field_name, getattr(self, field_name), minimum=1)
        if not self.e > self.d or self.e - self.d > 2:
            raise ValueError("kernel continuation template is invalid")
        if self.target != self.e + 1:
            raise ValueError("kernel target must equal e + 1")
        if self.prompt_budget != 1:
            raise ValueError("kernel prompt budget must be exactly one")
        if self.exposure_budget != max((self.e + 2) * self.n, (self.d + 2) * self.b):
            raise ValueError("kernel exposure budget does not match the construction theorem")
        if self.horizon != max(8, self.e + 4):
            raise ValueError("kernel horizon does not match the construction theorem")
        if self.grant_lifetime_profile != FAMILY3_V2_GRANT_LIFETIME_PROFILE:
            raise ValueError("kernel grant lifetime profile is not frozen")
        if self.tool_outcome_profile != FAMILY3_V2_TOOL_OUTCOME_PROFILE:
            raise ValueError("kernel tool outcome profile is not frozen")
        if type(self.branch_coupling_uid) is not str or len(self.branch_coupling_uid) != 64:
            raise ValueError("kernel coupling UID must be a SHA-256 hex string")
        if any(character not in "0123456789abcdef" for character in self.branch_coupling_uid):
            raise ValueError("kernel coupling UID must be lowercase hexadecimal")

    @property
    def narrow_scope(self) -> Scope:
        return self.offer.narrow_scope

    @property
    def broader_scope(self) -> Scope:
        return self.offer.broader_scope

    @property
    def n(self) -> int:
        return self.offer.narrow_exposure_cost

    @property
    def b(self) -> int:
        return self.offer.broader_exposure_cost

    @property
    def forecast_exact_probability(self) -> Fraction:
        return self.offer.forecast_exact_probability

    @property
    def forecast_broader_probability(self) -> Fraction:
        return self.offer.forecast_broader_probability

    @property
    def forecast_mode(self) -> ForecastModeV2:
        return self.offer.forecast_mode

    def forecast_counterfactual(self) -> Family3V2KernelInput:
        return replace(
            self,
            offer=replace(
                self.offer,
                forecast_exact_probability=self.forecast_broader_probability,
                forecast_broader_probability=self.forecast_exact_probability,
            ),
        )


def _graph_from_row(row: tuple[object, ...]) -> Family3V2GraphSpec:
    graph_id, split, carrier_code, purpose, exact_numerator, e, d, target, exposure_budget, horizon = row
    carrier = _CARRIERS_BY_CODE[carrier_code]
    return Family3V2GraphSpec(
        graph_id=graph_id,
        split=split,
        carrier_code=carrier_code,
        purpose=purpose,
        narrow_scope=carrier.scope(purpose),
        broader_scope=carrier.scope(purpose, broader=True),
        n=carrier.sensitivity * len(carrier.base_attributes),
        b=carrier.sensitivity * (len(carrier.base_attributes) + 1),
        forecast_exact_probability=Fraction(exact_numerator, 5),
        forecast_broader_probability=Fraction(5 - exact_numerator, 5),
        e=e,
        d=d,
        target=target,
        prompt_budget=1,
        exposure_budget=exposure_budget,
        horizon=horizon,
    )


def build_family3_v2_suite() -> Family3V2Suite:
    return Family3V2Suite(tuple(_graph_from_row(row) for row in _ROWS))


__all__ = [
    "FAMILY3_V2_SUITE_VERSION",
    "Family3V2GraphSpec",
    "Family3V2KernelInput",
    "Family3V2Suite",
    "build_family3_v2_suite",
]
