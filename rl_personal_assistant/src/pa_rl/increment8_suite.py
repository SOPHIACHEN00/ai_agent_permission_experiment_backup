"""Frozen typed inputs for the Increment 8 budgeted-lifecycle study."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .contracts import Scope, canonical_hash


INCREMENT8_SUITE_VERSION = "increment8_budgeted_lifecycle_v0"
_SPLIT_FORMULA = (
    "strategic:v0..4=train,v5..6=validation,v7..9=test;"
    "mandatory:v0..3=train,v4..7=test"
)


class LikelihoodLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LifecycleGraphRole(str, Enum):
    STRATEGIC = "strategic"
    MANDATORY = "mandatory"


@dataclass(frozen=True, slots=True)
class _Carrier:
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
        attributes = self.base_attributes + ((self.broader_attribute,) if broader else ())
        return Scope(
            domain=self.domain,
            tool=self.tool,
            resource=self.resource,
            data_attributes=attributes,
            operation=self.operation,
            purpose=purpose,
            recipient=self.recipient,
            retention=self.retention,
        )


_CARRIERS = (
    _Carrier(
        "c0_calendar", "productivity", "calendar_api", "calendar.events",
        ("start_time", "title"), "end_time", "read", "local_user", "session", 1,
    ),
    _Carrier(
        "c1_mail_archive", "productivity", "mail_api", "mail.messages",
        ("message_id",), "body", "archive", "local_user", "session", 2,
    ),
    _Carrier(
        "c2_mail_send", "productivity", "mail_api", "mail.messages",
        ("body",), "recipient", "send", "team", "session", 2,
    ),
    _Carrier(
        "c3_report", "productivity", "report_api", "reports.weekly",
        ("end_time", "time"), "title", "read", "stakeholder", "session", 1,
    ),
    _Carrier(
        "c4_records", "records", "records_api", "records.private",
        ("record",), "recipient", "send", "third_party", "external", 3,
    ),
)

_PURPOSES = (
    "agenda_summary",
    "status_notice",
    "inbox_cleanup",
    "weekly_report",
    "approved_update",
    "team_sync",
    "records_review",
    "calendar_maintenance",
    "report_delivery",
    "mail_triage",
)

_BASE_ROWS = (
    (8, 4, 3, 18, LikelihoodLevel.HIGH, LikelihoodLevel.LOW),
    (9, 5, 3, 16, LikelihoodLevel.MEDIUM, LikelihoodLevel.LOW),
    (10, 5, 4, 20, LikelihoodLevel.HIGH, LikelihoodLevel.MEDIUM),
    (11, 6, 3, 18, LikelihoodLevel.MEDIUM, LikelihoodLevel.HIGH),
    (12, 6, 4, 22, LikelihoodLevel.HIGH, LikelihoodLevel.HIGH),
    (8, 4, 2, 12, LikelihoodLevel.LOW, LikelihoodLevel.LOW),
    (10, 5, 3, 14, LikelihoodLevel.LOW, LikelihoodLevel.MEDIUM),
    (9, 5, 2, 12, LikelihoodLevel.MEDIUM, LikelihoodLevel.HIGH),
    (11, 6, 3, 16, LikelihoodLevel.HIGH, LikelihoodLevel.MEDIUM),
    (12, 7, 3, 18, LikelihoodLevel.LOW, LikelihoodLevel.HIGH),
)


def _exact_int(name: str, value: object, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an exact int in [{minimum}, {maximum}]")
    return value


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
class LifecycleGraphSpec:
    graph_id: str
    role: LifecycleGraphRole
    family_index: int | None
    variant: int
    horizon: int
    utility_target: int
    prompt_budget: int
    exposure_budget: int
    initial_task_utility: int
    reuse_likelihood: LikelihoodLevel
    scope_change_likelihood: LikelihoodLevel
    carrier_code: str
    initial_scope: Scope
    broader_scope: Scope
    initial_sensitivity: int
    purpose: str
    authorization_objective: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, LifecycleGraphRole):
            raise ValueError("graph role must be a LifecycleGraphRole")
        if type(self.variant) is not int:
            raise ValueError("graph variant must be an exact int")
        if self.role is LifecycleGraphRole.STRATEGIC:
            if type(self.family_index) is not int or not 0 <= self.family_index <= 3:
                raise ValueError("strategic family index must be an exact int in [0, 3]")
            if not 0 <= self.variant <= 9 or self.graph_id != f"i8_s{self.family_index}_v{self.variant}":
                raise ValueError("strategic graph identity is not canonical")
            if self.authorization_objective != "scope_sensitive_offer":
                raise ValueError("strategic authorization objective is invalid")
        else:
            if self.family_index is not None:
                raise ValueError("mandatory family index must be None")
            if not 0 <= self.variant <= 7 or self.graph_id != f"i8_m_v{self.variant}":
                raise ValueError("mandatory graph identity is not canonical")
            if self.authorization_objective != "reusable_then_one_time_replacement":
                raise ValueError("mandatory authorization objective is invalid")
        _exact_int("horizon", self.horizon, minimum=8, maximum=12)
        _exact_int("utility_target", self.utility_target, minimum=1, maximum=12)
        _exact_int("prompt_budget", self.prompt_budget, minimum=1, maximum=4)
        _exact_int("exposure_budget", self.exposure_budget, minimum=1, maximum=30)
        _exact_int("initial_task_utility", self.initial_task_utility, minimum=1, maximum=3)
        _exact_int("initial_sensitivity", self.initial_sensitivity, minimum=1, maximum=3)
        if not isinstance(self.reuse_likelihood, LikelihoodLevel) or not isinstance(
            self.scope_change_likelihood, LikelihoodLevel
        ):
            raise ValueError("likelihoods must be typed")
        carrier = next((item for item in _CARRIERS if item.code == self.carrier_code), None)
        if carrier is None:
            raise ValueError("unknown carrier code")
        if not isinstance(self.initial_scope, Scope) or not isinstance(self.broader_scope, Scope):
            raise ValueError("graph scopes must be typed Scope values")
        if self.purpose not in _PURPOSES or self.initial_scope.purpose != self.purpose:
            raise ValueError("graph purpose is invalid")
        if self.initial_scope != carrier.scope(self.purpose):
            raise ValueError("initial scope does not match carrier and purpose")
        if self.broader_scope != carrier.scope(self.purpose, broader=True):
            raise ValueError("broader scope does not match carrier and purpose")
        if self.initial_sensitivity != carrier.sensitivity:
            raise ValueError("initial sensitivity does not match carrier")

    def public_initial_mapping(self) -> dict[str, object]:
        """Return only ex-ante public kernel parameters, with no graph labels."""
        return {
            "current_scope": _scope_mapping(self.initial_scope),
            "broader_scope": _scope_mapping(self.broader_scope),
            "current_task_utility": self.initial_task_utility,
            "current_sensitivity": self.initial_sensitivity,
            "accumulated_utility": 0,
            "utility_target": self.utility_target,
            "logical_step": 1,
            "horizon": self.horizon,
            "prompts_used": 0,
            "prompt_budget": self.prompt_budget,
            "exposure_used": 0,
            "exposure_budget": self.exposure_budget,
            "reuse_likelihood": self.reuse_likelihood.value,
            "scope_change_likelihood": self.scope_change_likelihood.value,
            "authorization_objective": self.authorization_objective,
            "directive": "none",
        }

    def as_mapping(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "role": self.role.value,
            "family_index": self.family_index,
            "variant": self.variant,
            "carrier_code": self.carrier_code,
            "public_initial": self.public_initial_mapping(),
        }


@dataclass(frozen=True, slots=True)
class Increment8SuiteMember:
    graph: LifecycleGraphSpec
    split: str

    def __post_init__(self) -> None:
        if not isinstance(self.graph, LifecycleGraphSpec):
            raise ValueError("suite member graph must be typed")
        expected = _split(self.graph.role, self.graph.variant)
        if self.split != expected:
            raise ValueError("suite member split does not match the frozen formula")


@dataclass(frozen=True, slots=True)
class Increment8Suite:
    members: tuple[Increment8SuiteMember, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.members, tuple) or any(
            not isinstance(item, Increment8SuiteMember) for item in self.members
        ):
            raise ValueError("suite members must be a typed tuple")
        ordered = tuple(sorted(self.members, key=lambda item: item.graph.graph_id))
        expected_ids = {
            *(f"i8_s{family}_v{variant}" for family in range(4) for variant in range(10)),
            *(f"i8_m_v{variant}" for variant in range(8)),
        }
        actual_ids = [item.graph.graph_id for item in ordered]
        if len(ordered) != 48 or len(set(actual_ids)) != 48 or set(actual_ids) != expected_ids:
            raise ValueError("suite must contain the exact 40 strategic and 8 mandatory graphs")
        counts = {split: sum(item.split == split for item in ordered) for split in ("train", "validation", "test")}
        if counts != {"train": 24, "validation": 8, "test": 16}:
            raise ValueError("suite split counts must be exactly 24/8/16")
        object.__setattr__(self, "members", ordered)

    def graphs(self, split: str) -> tuple[LifecycleGraphSpec, ...]:
        if split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        return tuple(item.graph for item in self.members if item.split == split)

    @property
    def suite_hash(self) -> str:
        return canonical_hash(
            {
                "suite_version": INCREMENT8_SUITE_VERSION,
                "graphs": tuple(item.graph.as_mapping() for item in self.members),
            }
        )

    @property
    def split_hash(self) -> str:
        return canonical_hash(
            {
                "formula": _SPLIT_FORMULA,
                "assignments": tuple((item.graph.graph_id, item.split) for item in self.members),
            }
        )

    def as_mapping(self) -> dict[str, object]:
        return {
            "suite_version": INCREMENT8_SUITE_VERSION,
            "suite_hash": self.suite_hash,
            "split_hash": self.split_hash,
            "members": tuple(
                {
                    "graph_id": item.graph.graph_id,
                    "role": item.graph.role.value,
                    "split": item.split,
                    "graph_hash": canonical_hash(item.graph.as_mapping()),
                }
                for item in self.members
            ),
        }


def _split(role: LifecycleGraphRole, variant: int) -> str:
    if role is LifecycleGraphRole.STRATEGIC:
        return "train" if variant <= 4 else "validation" if variant <= 6 else "test"
    return "train" if variant <= 3 else "test"


def _strategic_graph(family: int, variant: int) -> LifecycleGraphSpec:
    horizon, target, prompts, exposure_base, reuse, scope_change = _BASE_ROWS[variant]
    carrier = _CARRIERS[(2 * family + variant) % len(_CARRIERS)]
    purpose = _PURPOSES[(3 * family + variant) % len(_PURPOSES)]
    if family == 0:
        scope_change = LikelihoodLevel.LOW
    elif family == 1:
        reuse = LikelihoodLevel.MEDIUM
    elif family == 2:
        reuse = LikelihoodLevel.LOW
        scope_change = LikelihoodLevel.LOW
    exposure = exposure_base + (2, 0, 4, -2)[family]
    return LifecycleGraphSpec(
        graph_id=f"i8_s{family}_v{variant}",
        role=LifecycleGraphRole.STRATEGIC,
        family_index=family,
        variant=variant,
        horizon=horizon,
        utility_target=target,
        prompt_budget=prompts,
        exposure_budget=exposure,
        initial_task_utility=1 + ((family + variant) % 3),
        reuse_likelihood=reuse,
        scope_change_likelihood=scope_change,
        carrier_code=carrier.code,
        initial_scope=carrier.scope(purpose),
        broader_scope=carrier.scope(purpose, broader=True),
        initial_sensitivity=carrier.sensitivity,
        purpose=purpose,
        authorization_objective="scope_sensitive_offer",
    )


def _mandatory_graph(variant: int) -> LifecycleGraphSpec:
    carrier = _CARRIERS[variant % len(_CARRIERS)]
    # Continue the neutral cross-family purpose rotation without introducing a
    # mandatory-family label into the public state.
    purpose = _PURPOSES[(variant + 2) % len(_PURPOSES)]
    utility = 1 + (variant % 3)
    return LifecycleGraphSpec(
        graph_id=f"i8_m_v{variant}",
        role=LifecycleGraphRole.MANDATORY,
        family_index=None,
        variant=variant,
        horizon=8 + (variant % 5),
        utility_target=utility,
        prompt_budget=2,
        exposure_budget=12 + 2 * (variant % 3),
        initial_task_utility=utility,
        reuse_likelihood=LikelihoodLevel.HIGH,
        scope_change_likelihood=LikelihoodLevel.LOW,
        carrier_code=carrier.code,
        initial_scope=carrier.scope(purpose),
        broader_scope=carrier.scope(purpose, broader=True),
        initial_sensitivity=carrier.sensitivity,
        purpose=purpose,
        authorization_objective="reusable_then_one_time_replacement",
    )


def build_increment8_suite() -> Increment8Suite:
    members = tuple(
        Increment8SuiteMember(graph, _split(graph.role, graph.variant))
        for graph in (
            *(_strategic_graph(family, variant) for family in range(4) for variant in range(10)),
            *(_mandatory_graph(variant) for variant in range(8)),
        )
    )
    return Increment8Suite(members)


__all__ = [
    "INCREMENT8_SUITE_VERSION",
    "Increment8Suite",
    "Increment8SuiteMember",
    "LifecycleGraphRole",
    "LifecycleGraphSpec",
    "LikelihoodLevel",
    "build_increment8_suite",
]
