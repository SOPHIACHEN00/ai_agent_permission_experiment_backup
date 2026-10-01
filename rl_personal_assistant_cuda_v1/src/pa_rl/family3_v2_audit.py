"""Exact preflight audits for the frozen Family-3 v2 experiment."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from fractions import Fraction
from itertools import permutations
from typing import Callable, Iterable

from .authorization import AuthorizationService
from .contracts import AuthorizationStatus, ControllerAction, GrantType, PermissionChoice, Scope
from .family3_v2_authority import (
    DeterministicAllowReuseUserV2,
    Family3V2AuthorizationBindingGateway,
    Family3V2PermissionRequest,
)
from .family3_v2_contracts import (
    CandidateRoleV2,
    ContinuationModeV2,
    FAMILY3_V2_CANDIDATE_ORDER,
    FAMILY3_V2_GRANT_LIFETIME_PROFILE,
    FAMILY3_V2_RESPONSE_PROFILE,
    FAMILY3_V2_SCHEMA_VERSION,
    FAMILY3_V2_SUITE_VERSION,
    FAMILY3_V2_TOOL_OUTCOME_PROFILE,
    ForecastScopeOfferV2,
    OfferWindowV2,
)
from .family3_v2_environment import Family3V2Environment
from .family3_v2_model import Family3V2Model, Family3V2State
from .family3_v2_outcome import Family3V2TerminationKind
from .family3_v2_policy import Family3V2FeatureEncoder, project_family3_v2_observation
from .family3_v2_rng import draw_family3_v2_branch_residue
from .family3_v2_suite import Family3V2KernelInput, Family3V2Suite
from .scope_matching import ScopeRelation, covers, relation


@dataclass(frozen=True, slots=True)
class Family3V2AuditMismatch:
    audit: str
    provenance: tuple[object, ...]
    field: str
    expected: object
    actual: object


@dataclass(frozen=True, slots=True)
class Family3V2MarkovAuditReport:
    passed: bool
    mismatches: tuple[Family3V2AuditMismatch, ...]
    analysis_count: int
    occurrence_count: int
    public_group_count: int
    encoded_group_count: int
    row_count: int
    valid_action_count: int
    transition_count: int


@dataclass(frozen=True, slots=True)
class Family3V2KernelEnvironmentConformanceReport:
    passed: bool
    mismatches: tuple[Family3V2AuditMismatch, ...]
    analysis_count: int
    state_count: int
    action_count: int
    transition_count: int
    role_coverage: tuple[tuple[str, int], ...]
    residue_coverage: tuple[int, ...]
    first_effect_residue_replay_count: int


@dataclass(frozen=True, slots=True)
class Family3V2FirewallReport:
    passed: bool
    mismatches: tuple[Family3V2AuditMismatch, ...]
    manifest_count: int
    row_check_count: int
    schema_check_count: int
    algebra_check_count: int
    leakage_check_count: int


@dataclass(frozen=True, slots=True)
class Family3V2WitnessCell:
    graph_id: str
    request_role: str
    branch: str
    expected_probability: Fraction
    classification: str
    success: bool
    failure_reason: str | None
    final_exposure: int
    invalid_actions: int
    unauthorized_committed_effects: int
    monitor_blocked_attempts: int


@dataclass(frozen=True, slots=True)
class Family3V2WitnessReport:
    passed: bool
    mismatches: tuple[Family3V2AuditMismatch, ...]
    cell_count: int
    success_count: int
    resource_failure_count: int
    no_coverage_count: int
    cells: tuple[Family3V2WitnessCell, ...]


@dataclass(frozen=True, slots=True)
class Family3V2BindingRecord:
    graph_id: str
    request_role: str
    four_scopes_equal: bool
    reusable: bool
    remaining_uses: int | None
    expires_at_step: int
    expected_expires_at_step: int
    raw_id_public_ordinal_colocated: bool


@dataclass(frozen=True, slots=True)
class Family3V2NonemittedGuardRecord:
    graph_id: str
    trigger_role: str
    failure_reason: str | None
    catalog_row_count: int
    all_nonemitted: bool
    catalog_signature: tuple[tuple[object, ...], ...]
    expected_catalog_signature: tuple[tuple[object, ...], ...]
    task_installed: bool
    next_required_step_id: str | None
    next_required_step_pending: bool
    verified: bool


@dataclass(frozen=True, slots=True)
class Family3V2BindingNoRepairReport:
    passed: bool
    mismatches: tuple[Family3V2AuditMismatch, ...]
    binding_count: int
    catalog_row_count: int
    action_type_count: int
    no_repair_state_count: int
    closed_offer_row_check_count: int
    disable_guard_count: int
    execute_guard_count: int
    nonemitted_guard_count: int
    nonemitted_catalog_row_count: int
    forced_invalid_count: int
    precommit_rejection_count: int
    postcommit_quarantine_count: int
    forced_invalid_zero_delta_count: int
    emitted_literal_check_count: int
    pure_guard_literal_check_count: int
    real_guard_literal_check_count: int
    forced_invalid_stable_key_check_count: int
    forced_invalid_closure_check_count: int
    binding_records: tuple[Family3V2BindingRecord, ...]
    nonemitted_guard_records: tuple[Family3V2NonemittedGuardRecord, ...]


@dataclass(frozen=True, slots=True)
class _Occurrence:
    analysis: int
    graph_id: str
    counterfactual: bool
    state: Family3V2State
    history: tuple[tuple[int, int], ...]

    @property
    def provenance(self) -> tuple[object, ...]:
        return (self.analysis, self.graph_id, self.counterfactual, self.history)


def _analyses(suite: Family3V2Suite) -> tuple[tuple[str, bool, Family3V2KernelInput], ...]:
    values: list[tuple[str, bool, Family3V2KernelInput]] = []
    for graph in suite.graphs:
        kernel = Family3V2KernelInput.from_graph(graph)
        values.append((graph.graph_id, False, kernel))
        values.append((graph.graph_id, True, kernel.forecast_counterfactual()))
    return tuple(values)


def _reachable_occurrences(
    suite: Family3V2Suite,
    model: Family3V2Model,
) -> tuple[_Occurrence, ...]:
    occurrences: list[_Occurrence] = []
    for analysis, (graph_id, counterfactual, kernel) in enumerate(_analyses(suite)):
        frontier = [(model.initial_state(kernel), ())]
        while frontier:
            state, history = frontier.pop()
            if state.terminated:
                continue
            occurrence = _Occurrence(analysis, graph_id, counterfactual, state, history)
            occurrences.append(occurrence)
            for slot, candidate in enumerate(model.candidates(state)):
                if not candidate.mask_valid:
                    continue
                distribution = model.transition_distribution(state, candidate.semantic_candidate_id)
                for transition in distribution:
                    if transition.next_state.terminated:
                        continue
                    residue = 0
                    if len(distribution) == 2:
                        residue = 0 if transition.next_state.continuation_mode is ContinuationModeV2.EXACT else 4
                    frontier.append((transition.next_state, history + ((slot, residue),)))
    return tuple(occurrences)


def _signature(model: Family3V2Model, state: Family3V2State) -> tuple[tuple[object, bool, str | None], ...]:
    return tuple((row.role, row.mask_valid, row.invalid_reason) for row in model.candidates(state))


def _aggregate_distribution(
    occurrence: _Occurrence,
    model: Family3V2Model,
    role: CandidateRoleV2,
    key_builder: Callable[[object], object],
    channel: str,
    mutator: Callable[[tuple[object, ...], CandidateRoleV2, str, tuple[object, ...]], tuple[object, ...]] | None,
    mismatches: list[Family3V2AuditMismatch],
) -> tuple[tuple[tuple[object, ...], Fraction], ...]:
    candidate = next(row for row in model.candidates(occurrence.state) if row.role is role)
    totals: dict[tuple[object, ...], Fraction] = defaultdict(Fraction)
    probability_sum = Fraction(0)
    for transition in model.transition_distribution(occurrence.state, candidate.semantic_candidate_id):
        if transition.terminated:
            next_projection: object = ("terminal",)
        else:
            next_projection = key_builder(project_family3_v2_observation(transition.next_state, model))
        canonical = (
            next_projection,
            transition.reward,
            transition.next_state.termination_kind,
            transition.next_mask,
        )
        key = canonical if mutator is None else mutator(occurrence.provenance, role, channel, canonical)
        totals[key] += transition.probability
        probability_sum += transition.probability
    if probability_sum != Fraction(1):
        mismatches.append(Family3V2AuditMismatch(
            "markov", occurrence.provenance + (role.value,), "probability_sum", Fraction(1), probability_sum
        ))
    return tuple(sorted(totals.items(), key=repr))


def audit_family3_v2_markov(
    suite: Family3V2Suite,
    model: Family3V2Model,
    encoder: object,
    *,
    _public_key: Callable[[object], object] | None = None,
    _occurrence_mutator: Callable[[tuple[_Occurrence, ...]], tuple[_Occurrence, ...]] | None = None,
    _signature_mutator: Callable[[tuple[object, ...], tuple[object, ...]], tuple[object, ...]] | None = None,
    _transition_key_mutator: Callable[[tuple[object, ...], CandidateRoleV2, str, tuple[object, ...]], tuple[object, ...]] | None = None,
) -> Family3V2MarkovAuditReport:
    projection_key = (lambda observation: observation) if _public_key is None else _public_key
    occurrences = _reachable_occurrences(suite, model)
    if _occurrence_mutator is not None:
        occurrences = _occurrence_mutator(occurrences)
    mismatches: list[Family3V2AuditMismatch] = []
    if _public_key is not None and occurrences:
        initial_observation = project_family3_v2_observation(occurrences[0].state, model)
        toggled_window = replace(
            initial_observation,
            offer_window=(OfferWindowV2.CLOSED if initial_observation.offer_window is OfferWindowV2.OPEN else OfferWindowV2.OPEN),
        )
        if projection_key(initial_observation) == projection_key(toggled_window):
            mismatches.append(Family3V2AuditMismatch(
                "markov", (), "offer_window_sensitivity", "distinct keys", "equal keys"
            ))
        realized = next(
            (project_family3_v2_observation(item.state, model) for item in occurrences
             if item.state.continuation_mode is not ContinuationModeV2.UNREALIZED),
            None,
        )
        if realized is not None and realized.realized_tail_remaining is not None:
            changed_tail = replace(realized, realized_tail_remaining=realized.realized_tail_remaining + 1)
            if projection_key(realized) == projection_key(changed_tail):
                mismatches.append(Family3V2AuditMismatch(
                    "markov", (), "realized_tail_progress_sensitivity", "distinct keys", "equal keys"
                ))
    public_groups: dict[object, list[tuple[object, ...]]] = defaultdict(list)
    encoded_groups: dict[object, list[tuple[object, ...]]] = defaultdict(list)
    row_count = valid_action_count = transition_count = 0
    encoded_keys: set[object] = set()
    for occurrence in occurrences:
        observation = project_family3_v2_observation(occurrence.state, model)
        public = projection_key(observation)
        encoded = encoder.encode(observation).representation_key()
        encoded_keys.add(encoded)
        canonical_signature = _signature(model, occurrence.state)
        signature = canonical_signature if _signature_mutator is None else _signature_mutator(
            occurrence.provenance, canonical_signature
        )
        public_distributions: dict[CandidateRoleV2, object] = {}
        encoded_distributions: dict[CandidateRoleV2, object] = {}
        rows = model.candidates(occurrence.state)
        row_count += len(rows)
        for row in rows:
            if row.mask_valid:
                valid_action_count += 1
                public_distributions[row.role] = _aggregate_distribution(
                    occurrence, model, row.role, projection_key, "public",
                    _transition_key_mutator, mismatches
                )
                encoded_distributions[row.role] = _aggregate_distribution(
                    occurrence, model, row.role,
                    lambda item: encoder.encode(item).representation_key(), "encoded",
                    _transition_key_mutator, mismatches
                )
                transition_count += len(model.transition_distribution(occurrence.state, row.semantic_candidate_id))
        public_groups[public].append((occurrence, signature, public_distributions))
        encoded_groups[encoded].append((occurrence, signature, encoded_distributions))

    def compare_groups(name: str, groups: dict[object, list[object]]) -> None:
        for members in groups.values():
            reference_occurrence, reference_signature, reference_distributions = members[0]
            for occurrence, signature, distributions in members[1:]:
                if signature != reference_signature:
                    mismatches.append(Family3V2AuditMismatch(
                        "markov", occurrence.provenance, name + "_signature",
                        reference_signature, signature,
                    ))
                common = set(reference_distributions) & set(distributions)
                for role in common:
                    if reference_distributions[role] != distributions[role]:
                        mismatches.append(Family3V2AuditMismatch(
                            "markov", occurrence.provenance + (role.value,), name + "_kernel",
                            reference_distributions[role], distributions[role],
                        ))

    compare_groups("public", public_groups)
    compare_groups("encoded", encoded_groups)
    if occurrences and len(encoded_keys) == 1:
        mismatches.append(Family3V2AuditMismatch(
            "markov", (), "constant_encoder", "more than one representation", next(iter(encoded_keys))
        ))
    counts_valid = (
        len(_analyses(suite)) == 20 and bool(occurrences) and bool(public_groups) and bool(encoded_groups)
        and row_count > 0 and valid_action_count > 0 and transition_count > 0
    )
    if not counts_valid:
        mismatches.append(Family3V2AuditMismatch("markov", (), "nonvacuity", True, False))
    return Family3V2MarkovAuditReport(
        not mismatches, tuple(mismatches), len(_analyses(suite)), len(occurrences),
        len(public_groups), len(encoded_groups), row_count, valid_action_count, transition_count,
    )


def _seed_map(kernel: Family3V2KernelInput) -> dict[int, int]:
    found: dict[int, int] = {}
    seed = 0
    while len(found) < 5:
        residue = draw_family3_v2_branch_residue(seed, kernel.branch_coupling_uid, 0).residue
        found.setdefault(residue, seed)
        seed += 1
    return found


def _delta_tuple(before, after) -> tuple[tuple[str, int], ...]:
    return tuple(sorted({
        "ledger_events": len(after.ledger_events) - len(before.ledger_events),
        "monitor_events": len(after.monitor_events) - len(before.monitor_events),
        "tool_invocations": after.tool_invocation_count - before.tool_invocation_count,
        "committed_effects": len(after.committed_effect_ids) - len(before.committed_effect_ids),
        "prompts": after.semantic_state.prompts_used - before.semantic_state.prompts_used,
        "exposure": after.semantic_state.exposure_used - before.semantic_state.exposure_used,
        "branch_evidence": len(after.branch_evidence) - len(before.branch_evidence),
    }.items()))


def _expected_delta(state: Family3V2State, candidate, stochastic: bool) -> tuple[tuple[str, int], ...]:
    values = {
        "ledger_events": 0,
        "monitor_events": 0,
        "tool_invocations": 0,
        "committed_effects": 0,
        "prompts": 0,
        "exposure": 0,
        "branch_evidence": 0,
    }
    if candidate.action is ControllerAction.REQUEST_AUTHORIZATION:
        values["ledger_events"] = 2
        values["prompts"] = 1
        values["exposure"] = state.kernel.n if candidate.role is CandidateRoleV2.REQUEST_NARROW else state.kernel.b
    elif candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
        values["ledger_events"] = 2
        values["monitor_events"] = 1
        values["tool_invocations"] = 1
        values["committed_effects"] = 1
        values["exposure"] = state.authorization.exposure_step_cost if state.authorization else 0
        values["branch_evidence"] = int(stochastic)
    elif candidate.action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
        values["ledger_events"] = 1
    elif candidate.action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}:
        values["exposure"] = state.authorization.exposure_step_cost if state.authorization else 0
    return tuple(sorted(values.items()))


def _replay_prefix(env, occurrence: _Occurrence, root_seed: int):
    observation, info = env.reset(
        occurrence.graph_id, root_seed, 0, forecast_counterfactual=occurrence.counterfactual
    )
    for slot, _ in occurrence.history:
        observation, _, terminated, _, info = env.step(slot)
        if terminated:
            break
    return observation, info


def audit_family3_v2_kernel_environment_conformance(
    suite: Family3V2Suite,
    *,
    _environment_factory: Callable[[], object] = Family3V2Environment,
    _delta_mutator: Callable[[tuple[object, ...], tuple[tuple[str, int], ...]], tuple[tuple[str, int], ...]] | None = None,
) -> Family3V2KernelEnvironmentConformanceReport:
    model = Family3V2Model()
    occurrences = _reachable_occurrences(suite, model)
    mismatches: list[Family3V2AuditMismatch] = []
    coverage = {role.value: 0 for role in FAMILY3_V2_CANDIDATE_ORDER}
    transition_count = action_count = 0
    first_effect_residue_replay_count = 0
    residue_coverage: set[int] = set()
    analyses = _analyses(suite)
    seeds = {kernel.branch_coupling_uid: _seed_map(kernel) for _, _, kernel in analyses}
    stop_early = _environment_factory is not Family3V2Environment or _delta_mutator is not None
    for occurrence in occurrences:
        kernel = occurrence.state.kernel
        for slot, candidate in enumerate(model.candidates(occurrence.state)):
            if not candidate.mask_valid:
                continue
            action_count += 1
            coverage[candidate.role.value] += 1
            distribution = model.transition_distribution(occurrence.state, candidate.semantic_candidate_id)
            stochastic = len(distribution) == 2
            residues: Iterable[int] = range(5) if stochastic else (0,)
            for residue in residues:
                transition_count += 1
                if stochastic:
                    first_effect_residue_replay_count += 1
                    residue_coverage.add(residue)
                branch_residue = next((value for _, value in occurrence.history if value != 0), None)
                if occurrence.state.effect_index > 0:
                    branch_residue = next(
                        (value for slot_value, value in occurrence.history if slot_value == 2), 0
                    )
                desired_residue = residue if stochastic else branch_residue
                root_seed = 0 if desired_residue is None else seeds[kernel.branch_coupling_uid][desired_residue]
                env = _environment_factory()
                observation, before = _replay_prefix(env, occurrence, root_seed)
                provenance = occurrence.provenance + (candidate.role.value, residue)
                if before.semantic_state != occurrence.state:
                    mismatches.append(Family3V2AuditMismatch(
                        "conformance", provenance, "replayed_prefix", occurrence.state, before.semantic_state
                    ))
                    if stop_early:
                        break
                expected = model.transition_from_residue(occurrence.state, candidate.semantic_candidate_id, residue)
                observation, reward, terminated, truncated, after = env.step(slot)
                expected_observation = (
                    project_family3_v2_observation(expected.next_state, model)
                    if not expected.terminated else project_family3_v2_observation(expected.next_state, model)
                )
                comparisons = (
                    ("successor", expected.next_state, after.semantic_state),
                    ("reward", expected.reward, reward),
                    ("terminated", expected.terminated, terminated),
                    ("truncated", expected.truncated, truncated),
                    ("observation", expected_observation, observation),
                    ("next_mask", expected.next_mask, () if terminated else observation.mask),
                    ("run_valid", True, after.run_valid),
                )
                for field, wanted, actual in comparisons:
                    if wanted != actual:
                        mismatches.append(Family3V2AuditMismatch(
                            "conformance", provenance, field, wanted, actual
                        ))
                actual_delta = _delta_tuple(before, after)
                if _delta_mutator is not None:
                    actual_delta = _delta_mutator(provenance, actual_delta)
                expected_delta = _expected_delta(occurrence.state, candidate, stochastic)
                if actual_delta != expected_delta:
                    mismatches.append(Family3V2AuditMismatch(
                        "conformance", provenance, "side_effect_delta", expected_delta, actual_delta
                    ))
                if mismatches and stop_early:
                    break
            if mismatches and stop_early:
                break
        if mismatches and stop_early:
            break
    if (
        len(analyses) != 20 or not occurrences or not action_count or not transition_count
        or residue_coverage != set(range(5)) or first_effect_residue_replay_count != 200
    ):
        mismatches.append(Family3V2AuditMismatch("conformance", (), "nonvacuity", True, False))
    return Family3V2KernelEnvironmentConformanceReport(
        not mismatches, tuple(mismatches), len(analyses), len(occurrences), action_count,
        transition_count, tuple((role.value, coverage[role.value]) for role in FAMILY3_V2_CANDIDATE_ORDER),
        tuple(sorted(residue_coverage)), first_effect_residue_replay_count,
    )


@dataclass(frozen=True, slots=True)
class _AuditRow:
    mapping: tuple[tuple[str, object], ...]
    kernel: Family3V2KernelInput
    carrier_code: str
    purpose: str


def _scope_from_prototype(prototype: Scope, purpose: str) -> Scope:
    return Scope(
        domain=prototype.domain, tool=prototype.tool, resource=prototype.resource,
        data_attributes=prototype.data_attributes, operation=prototype.operation,
        purpose=purpose, recipient=prototype.recipient, retention=prototype.retention,
    )


def _walk(value: object):
    yield value
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _walk(getattr(value, field.name))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(key)
            yield from _walk(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from _walk(item)


def _structural_key(kernel: Family3V2KernelInput) -> tuple[object, ...]:
    narrow_sensitivity = kernel.n // len(kernel.narrow_scope.data_attributes)
    broader_sensitivity = kernel.b // len(kernel.broader_scope.data_attributes)
    return (
        relation(kernel.narrow_scope, kernel.narrow_scope),
        relation(kernel.broader_scope, kernel.narrow_scope),
        len(kernel.narrow_scope.data_attributes), len(kernel.broader_scope.data_attributes),
        narrow_sensitivity, broader_sensitivity, kernel.n, kernel.b, kernel.forecast_exact_probability,
        kernel.forecast_broader_probability, kernel.e, kernel.d, kernel.target,
        kernel.prompt_budget, kernel.exposure_budget, kernel.horizon,
        kernel.offer.response_profile, kernel.grant_lifetime_profile, kernel.tool_outcome_profile,
        kernel.offer.offer_window, ContinuationModeV2.UNREALIZED,
    )


def _audit_row_schema(
    mapping: tuple[tuple[str, object], ...], expected_keys: tuple[str, ...]
) -> bool:
    if len(mapping) != 21 or tuple(key for key, _ in mapping) != expected_keys:
        return False
    values = dict(mapping)
    return (
        values["schema_version"] == FAMILY3_V2_SCHEMA_VERSION
        and values["suite_version"] == FAMILY3_V2_SUITE_VERSION
        and type(values["graph_id"]) is str and bool(values["graph_id"])
        and values["split"] in {"train", "validation", "test"}
        and type(values["carrier_code"]) is str and bool(values["carrier_code"])
        and type(values["purpose"]) is str and bool(values["purpose"])
        and isinstance(values["narrow_scope"], Scope)
        and isinstance(values["broader_scope"], Scope)
        and all(type(values[name]) is int for name in (
            "n", "b", "forecast_exact_numerator", "forecast_exact_denominator",
            "e", "d", "target", "prompt_budget", "exposure_budget", "horizon",
        ))
        and all(type(values[name]) is str and bool(values[name]) for name in (
            "response_profile", "grant_lifetime_profile", "tool_outcome_profile",
        ))
    )


def _audit_row_algebra(mapping: tuple[tuple[str, object], ...], kernel: Family3V2KernelInput) -> bool:
    values = dict(mapping)
    narrow = values["narrow_scope"]
    broader = values["broader_scope"]
    n, b = values["n"], values["b"]
    e, d = values["e"], values["d"]
    if not isinstance(narrow, Scope) or not isinstance(broader, Scope):
        return False
    if any(type(value) is not int for value in (
        n, b, e, d, values["target"], values["prompt_budget"],
        values["exposure_budget"], values["horizon"],
        values["forecast_exact_numerator"], values["forecast_exact_denominator"],
    )):
        return False
    narrow_count = len(narrow.data_attributes)
    broader_count = len(broader.data_attributes)
    if n % narrow_count or b % broader_count:
        return False
    sensitivity = n // narrow_count
    return (
        values["schema_version"] == FAMILY3_V2_SCHEMA_VERSION
        and values["suite_version"] == FAMILY3_V2_SUITE_VERSION
        and values["split"] in {"train", "validation", "test"}
        and b // broader_count == sensitivity and n < b
        and covers(narrow, narrow) and covers(broader, narrow) and not covers(narrow, broader)
        and e > d >= 1 and e - d <= 2 and values["target"] == e + 1
        and values["prompt_budget"] == 1
        and values["exposure_budget"] == max((e + 2) * n, (d + 2) * b)
        and values["exposure_budget"] < (e + 2) * b
        and values["horizon"] == max(8, e + 4)
        and values["response_profile"] == FAMILY3_V2_RESPONSE_PROFILE
        and values["grant_lifetime_profile"] == FAMILY3_V2_GRANT_LIFETIME_PROFILE
        and values["tool_outcome_profile"] == FAMILY3_V2_TOOL_OUTCOME_PROFILE
        and values["forecast_exact_denominator"] == 5
        and values["forecast_exact_numerator"] in {1, 4}
        and kernel.forecast_exact_probability == Fraction(values["forecast_exact_numerator"], 5)
        and kernel.forecast_broader_probability == Fraction(5 - values["forecast_exact_numerator"], 5)
    )


def _analytic_optimal_role(exact_probability: Fraction) -> CandidateRoleV2:
    if exact_probability == Fraction(4, 5):
        return CandidateRoleV2.REQUEST_NARROW
    if exact_probability == Fraction(1, 5):
        return CandidateRoleV2.REQUEST_BROADER
    raise ValueError("analytic theorem requires a frozen forecast probability")


def _carrier_transforms() -> tuple[dict[str, str], ...]:
    identity: dict[str, str] = {}
    swap03 = {"c0_calendar": "c3_report", "c3_report": "c0_calendar"}
    swap12 = {"c1_mail_archive": "c2_mail_send", "c2_mail_send": "c1_mail_archive"}
    both = {**swap03, **swap12}
    return identity, swap03, swap12, both


def audit_family3_v2_firewall(
    suite: Family3V2Suite,
    encoder: object,
    *,
    _channel_mutator: Callable[[str, object], object] | None = None,
    _manifest_limit: int | None = None,
    _row_limit: int | None = None,
    _suppress_required_scope_change: bool = False,
    _check_mutator: Callable[[str, object], object] | None = None,
    _audit_row_mutator: Callable[[tuple[tuple[str, object], ...]], tuple[tuple[str, object], ...]] | None = None,
    _audit_kernel_mutator: Callable[[Family3V2KernelInput], Family3V2KernelInput] | None = None,
) -> Family3V2FirewallReport:
    model = Family3V2Model()
    original_hashes = tuple(graph.row_hash for graph in suite.graphs)
    original_scopes = tuple((graph.narrow_scope, graph.broader_scope) for graph in suite.graphs)
    purposes = tuple(dict.fromkeys(graph.purpose for graph in suite.graphs))
    prototypes = {
        graph.carrier_code: (graph.narrow_scope, graph.broader_scope, graph.n, graph.b)
        for graph in suite.graphs
    }
    sentinels: set[str] = set(purposes)
    sentinels.update(prototypes)
    for graph in suite.graphs:
        for scope in (graph.narrow_scope, graph.broader_scope):
            sentinels.update((scope.domain, scope.tool, scope.resource, scope.operation,
                              scope.purpose, scope.recipient, scope.retention, *scope.data_attributes))
    manifests = list((permutation, transform) for permutation in permutations(purposes) for transform in _carrier_transforms())
    if _manifest_limit is not None:
        manifests = manifests[:_manifest_limit]
    mismatches: list[Family3V2AuditMismatch] = []
    row_checks = schema_checks = algebra_checks = leakage_checks = 0
    for manifest_index, (purpose_order, carrier_map) in enumerate(manifests):
        purpose_map = dict(zip(purposes, purpose_order))
        rows = suite.graphs if _row_limit is None else suite.graphs[:_row_limit]
        for row_index, graph in enumerate(rows):
            row_checks += 1
            target_carrier = carrier_map.get(graph.carrier_code, graph.carrier_code)
            target_purpose = purpose_map[graph.purpose]
            narrow_prototype, broader_prototype, n, b = prototypes[target_carrier]
            narrow = _scope_from_prototype(narrow_prototype, target_purpose)
            broader = _scope_from_prototype(broader_prototype, target_purpose)
            expected_change = target_carrier != graph.carrier_code or target_purpose != graph.purpose
            if _suppress_required_scope_change and expected_change and not mismatches:
                narrow, broader = graph.narrow_scope, graph.broader_scope
            actual_change = (narrow, broader) != (graph.narrow_scope, graph.broader_scope)
            provenance = (manifest_index, graph.graph_id)
            if actual_change != expected_change:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "scope_changed_iff_mapping", expected_change, actual_change
                ))
            offer = ForecastScopeOfferV2(
                narrow, broader, n, b, graph.forecast_exact_probability,
                graph.forecast_broader_probability, graph.response_profile,
            )
            kernel = Family3V2KernelInput(
                graph.graph_id, offer, graph.e, graph.d, graph.target, graph.prompt_budget,
                graph.exposure_budget, graph.horizon, graph.grant_lifetime_profile,
                graph.tool_outcome_profile, graph.branch_coupling_uid,
            )
            if _audit_kernel_mutator is not None:
                kernel = _audit_kernel_mutator(kernel)
            mapping = (
                ("schema_version", FAMILY3_V2_SCHEMA_VERSION),
                ("suite_version", FAMILY3_V2_SUITE_VERSION),
                ("graph_id", graph.graph_id), ("split", graph.split),
                ("carrier_code", target_carrier), ("purpose", target_purpose),
                ("narrow_scope", narrow), ("broader_scope", broader),
                ("n", n), ("b", b),
                ("forecast_exact_numerator", graph.forecast_exact_probability.numerator),
                ("forecast_exact_denominator", graph.forecast_exact_probability.denominator),
                ("e", graph.e), ("d", graph.d), ("target", graph.target),
                ("prompt_budget", graph.prompt_budget), ("exposure_budget", graph.exposure_budget),
                ("horizon", graph.horizon), ("response_profile", graph.response_profile),
                ("grant_lifetime_profile", graph.grant_lifetime_profile),
                ("tool_outcome_profile", graph.tool_outcome_profile),
            )
            if _audit_row_mutator is not None:
                mapping = _audit_row_mutator(mapping)
            copied = _AuditRow(mapping, kernel, target_carrier, target_purpose)
            schema_checks += 1
            schema_shape = tuple(key for key, _ in copied.mapping)
            if _check_mutator is not None:
                schema_shape = _check_mutator("schema", schema_shape)
            expected_keys = tuple(graph.row_mapping())
            schema_valid = _audit_row_schema(copied.mapping, expected_keys)
            if not schema_valid:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "schema_validation", True, False,
                ))
            if schema_shape != expected_keys:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "schema_shape", tuple(graph.row_mapping()),
                    schema_shape,
                ))
            algebra_checks += 1
            algebra = _audit_row_algebra(copied.mapping, kernel)
            if _check_mutator is not None:
                algebra = _check_mutator("algebra", algebra)
            if algebra is not True:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "construction_algebra", True, algebra
                ))
            expected_structural = _structural_key(Family3V2KernelInput.from_graph(graph))
            actual_structural = _structural_key(kernel)
            if _check_mutator is not None:
                actual_structural = _check_mutator("structural", actual_structural)
            if actual_structural != expected_structural:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "structural_key", expected_structural, actual_structural
                ))
            original_observation = project_family3_v2_observation(
                model.initial_state(Family3V2KernelInput.from_graph(graph)), model
            )
            transformed_observation = project_family3_v2_observation(model.initial_state(kernel), model)
            if transformed_observation != original_observation:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "initial_projection", original_observation, transformed_observation
                ))
            original_encoded = encoder.encode(original_observation).representation_key()
            transformed_encoded = encoder.encode(transformed_observation).representation_key()
            if transformed_encoded != original_encoded:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "initial_representation", original_encoded, transformed_encoded
                ))
            original_signature = tuple((row.role, row.mask_valid) for row in original_observation.candidates)
            transformed_signature = tuple((row.role, row.mask_valid) for row in transformed_observation.candidates)
            if transformed_signature != original_signature:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "roles_masks", original_signature, transformed_signature
                ))
            expected_role = _analytic_optimal_role(graph.forecast_exact_probability)
            analytic_role: object = _analytic_optimal_role(kernel.forecast_exact_probability)
            if _check_mutator is not None:
                analytic_role = _check_mutator("analytic", analytic_role)
            if analytic_role != expected_role:
                mismatches.append(Family3V2AuditMismatch(
                    "firewall", provenance, "analytic_optimal_role", expected_role, analytic_role
                ))
            channels = {
                "observation": transformed_observation,
                "semantic_id": tuple(row.semantic_candidate_id for row in transformed_observation.candidates),
                "representation": transformed_encoded,
            }
            for channel, value in channels.items():
                leakage_checks += 1
                inspected = value if _channel_mutator is None else _channel_mutator(channel, value)
                leaked = tuple(item for item in _walk(inspected) if isinstance(item, str) and item in sentinels)
                if leaked:
                    mismatches.append(Family3V2AuditMismatch(
                        "firewall", provenance, channel + "_sentinel_leakage", (), leaked
                    ))
            if _channel_mutator is not None and mismatches:
                break
        if (
            _channel_mutator is not None or _suppress_required_scope_change
            or _check_mutator is not None or _audit_row_mutator is not None
            or _audit_kernel_mutator is not None
        ) and mismatches:
            break
    if tuple(graph.row_hash for graph in suite.graphs) != original_hashes or tuple(
        (graph.narrow_scope, graph.broader_scope) for graph in suite.graphs
    ) != original_scopes:
        mismatches.append(Family3V2AuditMismatch("firewall", (), "original_mutation", original_hashes, None))
    if len(manifests) != 480 or row_checks != 4_800:
        mismatches.append(Family3V2AuditMismatch(
            "firewall", (), "cardinality", (480, 4_800), (len(manifests), row_checks)
        ))
    return Family3V2FirewallReport(
        not mismatches, tuple(mismatches), len(manifests), row_checks,
        schema_checks, algebra_checks, leakage_checks,
    )


def audit_family3_v2_witnesses(
    suite: Family3V2Suite,
    model: Family3V2Model,
) -> Family3V2WitnessReport:
    mismatches: list[Family3V2AuditMismatch] = []
    cells: list[Family3V2WitnessCell] = []
    for graph in suite.graphs:
        kernel = Family3V2KernelInput.from_graph(graph)
        for request_role in (CandidateRoleV2.REQUEST_NARROW, CandidateRoleV2.REQUEST_BROADER):
            for branch, residue in ((ContinuationModeV2.EXACT, 0), (ContinuationModeV2.BROADER, 4)):
                state = model.initial_state(kernel)
                state = model.transition_from_residue(state, request_role.value, 0).next_state
                first_distribution = model.transition_distribution(
                    state, CandidateRoleV2.EXECUTE_COVERING.value
                )
                branch_transition = next(
                    item for item in first_distribution
                    if item.next_state.continuation_mode is branch
                )
                expected_probability = branch_transition.probability
                while not state.terminated:
                    state = model.transition_from_residue(
                        state, CandidateRoleV2.EXECUTE_COVERING.value, residue
                    ).next_state
                theorem_probability = (
                    kernel.forecast_exact_probability if branch is ContinuationModeV2.EXACT
                    else kernel.forecast_broader_probability
                )
                if expected_probability != theorem_probability:
                    mismatches.append(Family3V2AuditMismatch(
                        "witness", (graph.graph_id, request_role.value, branch.value),
                        "branch_probability", theorem_probability, expected_probability,
                    ))
                if request_role is CandidateRoleV2.REQUEST_NARROW and branch is ContinuationModeV2.EXACT:
                    classification = "success"
                    expected = (True, None, (kernel.e + 2) * kernel.n)
                elif request_role is CandidateRoleV2.REQUEST_NARROW:
                    classification = "no_coverage_failure"
                    expected = (False, "irreversible_no_coverage", (kernel.d + 1) * kernel.n)
                elif branch is ContinuationModeV2.EXACT:
                    classification = "resource_failure"
                    expected = (
                        False, "exposure_budget_exceeded",
                        (kernel.exposure_budget // kernel.b + 1) * kernel.b,
                    )
                else:
                    classification = "success"
                    expected = (True, None, (kernel.d + 2) * kernel.b)
                cell = Family3V2WitnessCell(
                    graph.graph_id, request_role.value, branch.value, expected_probability, classification,
                    state.success, state.failure_reason, state.exposure_used, state.invalid_actions,
                    state.unauthorized_committed_effects, state.monitor_blocked_attempts,
                )
                cells.append(cell)
                actual = (cell.success, cell.failure_reason, cell.final_exposure)
                if actual != expected or any((cell.invalid_actions, cell.unauthorized_committed_effects, cell.monitor_blocked_attempts)):
                    mismatches.append(Family3V2AuditMismatch(
                        "witness", (graph.graph_id, request_role.value, branch.value), "cell", expected, actual
                    ))
    counts = (
        len(cells), sum(cell.classification == "success" for cell in cells),
        sum(cell.classification == "resource_failure" for cell in cells),
        sum(cell.classification == "no_coverage_failure" for cell in cells),
    )
    if counts != (40, 20, 10, 10):
        mismatches.append(Family3V2AuditMismatch(
            "witness", (), "classification_cardinality", (40, 20, 10, 10), counts
        ))
    return Family3V2WitnessReport(
        not mismatches, tuple(mismatches), *counts, tuple(cells),
    )


class _PostcommitMismatchService(AuthorizationService):
    def __init__(self, episode_id: str, episode_end_step: int, wrong_scope: Scope) -> None:
        super().__init__(episode_id, episode_end_step)
        self._wrong_scope = wrong_scope
        self._permission_applied = False

    def apply_permission_choice(self, authorization_id, choice, step):
        record = super().apply_permission_choice(authorization_id, choice, step)
        self._permission_applied = True
        return record

    def record(self, authorization_id):
        record = super().record(authorization_id)
        return replace(record, scope=self._wrong_scope) if self._permission_applied else record


def _slot(observation, role: CandidateRoleV2) -> int:
    return next(index for index, row in enumerate(observation.candidates) if row.role is role)


def _catalog_signature(catalog) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (row.role, row.action, row.mask_valid, row.invalid_reason, row.emitted)
        for row in catalog
    )


def _emitted_catalog_signature(catalog) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (row.role, row.action, row.mask_valid, row.invalid_reason)
        for row in catalog
    )


_EMITTED_POST_GRANT_LITERAL = (
    (CandidateRoleV2.REQUEST_NARROW, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed"),
    (CandidateRoleV2.REQUEST_BROADER, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed"),
    (CandidateRoleV2.EXECUTE_COVERING, ControllerAction.EXECUTE_WITH_AUTHORIZATION, True, None),
    (CandidateRoleV2.REFRESH_CLOSED, ControllerAction.REQUEST_REFRESH, False, "offer_window_closed"),
    (CandidateRoleV2.DISABLE_ACTIVE, ControllerAction.DISABLE_LOCAL_AUTHORIZATION, True, None),
    (CandidateRoleV2.DENY, ControllerAction.DENY_WITH_REASON, True, None),
    (CandidateRoleV2.ESCALATE, ControllerAction.ESCALATE, True, None),
)

_NO_COVERAGE_COMMON_LITERAL = (
    (CandidateRoleV2.REQUEST_NARROW, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed", False),
    (CandidateRoleV2.REQUEST_BROADER, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed", False),
    (CandidateRoleV2.EXECUTE_COVERING, ControllerAction.EXECUTE_WITH_AUTHORIZATION, False, "no_covering_authorization", False),
    (CandidateRoleV2.REFRESH_CLOSED, ControllerAction.REQUEST_REFRESH, False, "offer_window_closed", False),
)
_DISABLE_NO_COVERAGE_LITERAL = _NO_COVERAGE_COMMON_LITERAL + (
    (CandidateRoleV2.DISABLE_ACTIVE, ControllerAction.DISABLE_LOCAL_AUTHORIZATION, False, "no_active_authorization", False),
    (CandidateRoleV2.DENY, ControllerAction.DENY_WITH_REASON, True, None, False),
    (CandidateRoleV2.ESCALATE, ControllerAction.ESCALATE, True, None, False),
)
_EXECUTE_NO_COVERAGE_LITERAL = _NO_COVERAGE_COMMON_LITERAL + (
    (CandidateRoleV2.DISABLE_ACTIVE, ControllerAction.DISABLE_LOCAL_AUTHORIZATION, True, None, False),
    (CandidateRoleV2.DENY, ControllerAction.DENY_WITH_REASON, True, None, False),
    (CandidateRoleV2.ESCALATE, ControllerAction.ESCALATE, True, None, False),
)

_FORCED_INVALID_CLOSURE_FIELDS = frozenset({
    "decision_index", "invalid_actions", "termination_kind", "failure_reason", "reward",
})


def _forced_invalid_stable_key(state: Family3V2State) -> tuple[tuple[str, object], ...]:
    return tuple(
        (field.name, getattr(state, field.name))
        for field in fields(state)
        if field.name not in _FORCED_INVALID_CLOSURE_FIELDS
    )


def audit_family3_v2_binding_no_repair(
    suite: Family3V2Suite,
    *,
    _forced_invalid_mutator: Callable[[tuple[object, ...], str, object], object] | None = None,
    _catalog_input_mutator: Callable[
        [tuple[object, ...], str, tuple[tuple[object, ...], ...]],
        tuple[tuple[object, ...], ...],
    ] | None = None,
    _forced_invalid_state_mutator: Callable[
        [tuple[object, ...], Family3V2State], Family3V2State,
    ] | None = None,
) -> Family3V2BindingNoRepairReport:
    model = Family3V2Model()
    mismatches: list[Family3V2AuditMismatch] = []
    binding_count = 0
    binding_records: list[Family3V2BindingRecord] = []
    for graph in suite.graphs:
        for role in (CandidateRoleV2.REQUEST_NARROW, CandidateRoleV2.REQUEST_BROADER):
            env = Family3V2Environment()
            observation, _ = env.reset(graph.graph_id, 0, 0)
            observation, _, terminated, truncated, info = env.step(_slot(observation, role))
            evidence = info.binding_evidence[-1]
            record = info.ledger_records[-1]
            scopes_equal = (
                evidence.selected_candidate_scope == evidence.dispatched_scope
                == evidence.accepted_scope == evidence.recorded_ledger_scope
            )
            raw_public_colocation = any(
                isinstance(item, str) and item.startswith("authorization_") for item in _walk(evidence)
            )
            valid = (
                not terminated and not truncated and info.run_valid and evidence.run_valid and scopes_equal
                and record.status is AuthorizationStatus.ACTIVE and record.grant_type is GrantType.REUSABLE
                and record.remaining_uses is None and record.expires_at_step == graph.horizon + 1
                and evidence.public_issuance_ordinal == 1 and not raw_public_colocation
            )
            binding_records.append(Family3V2BindingRecord(
                graph.graph_id, role.value, scopes_equal,
                record.grant_type is GrantType.REUSABLE,
                record.remaining_uses, record.expires_at_step, graph.horizon + 1,
                raw_public_colocation,
            ))
            binding_count += 1
            if not valid:
                mismatches.append(Family3V2AuditMismatch(
                    "binding", (graph.graph_id, role.value), "four_way_reusable_binding", True, valid
                ))

    graph = suite.graphs[0]
    user = DeterministicAllowReuseUserV2()
    request = Family3V2PermissionRequest(
        CandidateRoleV2.REQUEST_NARROW, graph.narrow_scope, 0, "family3_v2_permission_0"
    )
    response = user.answer_permission(request)
    pre_service = AuthorizationService("family3_v2_audit_precommit", graph.horizon + 1)
    pre_gateway = Family3V2AuthorizationBindingGateway(pre_service)
    pre = pre_gateway.commit_request(graph.broader_scope, request, response, graph.horizon + 1)
    pre_ok = (
        not pre.run_valid and pre.failure_reason == "authorization_binding_precommit_mismatch"
        and not pre_service.events() and not pre_service.records()
    )
    if not pre_ok:
        mismatches.append(Family3V2AuditMismatch("binding", (), "precommit_zero_ledger", True, pre_ok))
    post_service = _PostcommitMismatchService(
        "family3_v2_audit_postcommit", graph.horizon + 1, graph.broader_scope
    )
    post_gateway = Family3V2AuthorizationBindingGateway(post_service)
    post = post_gateway.commit_request(graph.narrow_scope, request, response, graph.horizon + 1)
    post_ok = (
        not post.run_valid and post.failure_reason == "authorization_binding_integrity_failure"
        and post.usable_authorization_id is None and post.quarantined_authorization_id is not None
        and post.quarantined_authorization_id in post_gateway.quarantined_authorization_ids
        and len(post_service.records()) == 1 and len(post_service.events()) == 2
    )
    if not post_ok:
        mismatches.append(Family3V2AuditMismatch("binding", (), "postcommit_quarantine", True, post_ok))

    occurrences = _reachable_occurrences(suite, model)
    audited = tuple(
        occurrence for occurrence in occurrences
        if occurrence.state.authorization is not None or occurrence.state.effect_index > 0
    )
    catalog_row_count = sum(len(model.candidates(occurrence.state)) for occurrence in audited)
    action_types = {row.action for occurrence in audited for row in model.candidates(occurrence.state)}
    closed_offer_row_check_count = 0
    forced_invalid_count = 0
    forced_invalid_zero_delta_count = 0
    emitted_literal_check_count = 0
    forced_invalid_stable_key_check_count = 0
    forced_invalid_closure_check_count = 0
    for occurrence in audited:
        rows = model.candidates(occurrence.state)
        emitted_signature = _emitted_catalog_signature(rows)
        if _catalog_input_mutator is not None:
            emitted_signature = _catalog_input_mutator(
                occurrence.provenance, "emitted", emitted_signature,
            )
        emitted_literal_check_count += 1
        if emitted_signature != _EMITTED_POST_GRANT_LITERAL or not all(row.emitted for row in rows):
            mismatches.append(Family3V2AuditMismatch(
                "binding", occurrence.provenance, "emitted_post_grant_literal_catalog",
                _EMITTED_POST_GRANT_LITERAL, emitted_signature,
            ))
        for row in rows:
            if row.role in {
                CandidateRoleV2.REQUEST_NARROW, CandidateRoleV2.REQUEST_BROADER,
                CandidateRoleV2.REFRESH_CLOSED,
            }:
                closed_offer_row_check_count += 1
                if row.mask_valid or row.invalid_reason != "offer_window_closed":
                    mismatches.append(Family3V2AuditMismatch(
                        "binding", occurrence.provenance + (row.role.value,), "offer_window_closed",
                        (False, "offer_window_closed"), (row.mask_valid, row.invalid_reason),
                    ))
            if row.mask_valid:
                continue
            forced_invalid_count += 1
            branch_residue = next((value for slot_value, value in occurrence.history if slot_value == 2), 0)
            seed = _seed_map(occurrence.state.kernel)[branch_residue]
            env = Family3V2Environment()
            observation, before = _replay_prefix(env, occurrence, seed)
            observation, _, _, _, after = env.step(_slot(observation, row.role))
            provenance = occurrence.provenance + (row.role.value,)
            actual_after_state = after.semantic_state
            if _forced_invalid_state_mutator is not None:
                actual_after_state = _forced_invalid_state_mutator(provenance, actual_after_state)
            expected_invalid = model.transition_distribution(
                occurrence.state, row.semantic_candidate_id
            )[0].next_state
            if actual_after_state != expected_invalid:
                mismatches.append(Family3V2AuditMismatch(
                    "binding", provenance,
                    "forced_invalid_semantic_successor", expected_invalid, actual_after_state,
                ))
            before_stable_key = _forced_invalid_stable_key(before.semantic_state)
            after_stable_key = _forced_invalid_stable_key(actual_after_state)
            forced_invalid_stable_key_check_count += 1
            stable_key_matches = before_stable_key == after_stable_key
            if not stable_key_matches:
                mismatches.append(Family3V2AuditMismatch(
                    "binding", provenance, "forced_invalid_stable_state",
                    before_stable_key, after_stable_key,
                ))
            expected_closure = (
                before.semantic_state.decision_index + 1,
                before.semantic_state.invalid_actions + 1,
                0,
                Family3V2TerminationKind.IRREVERSIBLE_FAILURE,
                row.invalid_reason,
                True,
            )
            actual_closure = (
                actual_after_state.decision_index,
                actual_after_state.invalid_actions,
                actual_after_state.reward,
                actual_after_state.termination_kind,
                actual_after_state.failure_reason,
                after.run_valid,
            )
            forced_invalid_closure_check_count += 1
            closure_matches = actual_closure == expected_closure
            if not closure_matches:
                mismatches.append(Family3V2AuditMismatch(
                    "binding", provenance, "forced_invalid_closure",
                    expected_closure, actual_closure,
                ))
            before_channels = {
                "binding_evidence": before.binding_evidence,
                "user_dispatch_count": before.user_dispatch_count,
                "ledger_records": before.ledger_records,
                "ledger_events": before.ledger_events,
                "monitor_events": before.monitor_events,
                "tool_invocations": before.tool_invocation_count,
                "committed_effects": before.committed_effect_ids,
                "prompts": before.semantic_state.prompts_used,
                "exposure": before.semantic_state.exposure_used,
                "branch_evidence": before.branch_evidence,
                "task_snapshot": before.task_snapshot,
                "semantic_authorization": before.semantic_state.authorization,
                "semantic_tasks": (before.semantic_state.current_task, before.semantic_state.queued_tasks),
                "semantic_continuation": before.semantic_state.continuation_mode,
                "semantic_effect": before.semantic_state.effect_index,
            }
            after_channels = {
                "binding_evidence": after.binding_evidence,
                "user_dispatch_count": after.user_dispatch_count,
                "ledger_records": after.ledger_records,
                "ledger_events": after.ledger_events,
                "monitor_events": after.monitor_events,
                "tool_invocations": after.tool_invocation_count,
                "committed_effects": after.committed_effect_ids,
                "prompts": actual_after_state.prompts_used,
                "exposure": actual_after_state.exposure_used,
                "branch_evidence": after.branch_evidence,
                "task_snapshot": after.task_snapshot,
                "semantic_authorization": actual_after_state.authorization,
                "semantic_tasks": (actual_after_state.current_task, actual_after_state.queued_tasks),
                "semantic_continuation": actual_after_state.continuation_mode,
                "semantic_effect": actual_after_state.effect_index,
            }
            channel_mismatch = False
            for channel, expected_value in before_channels.items():
                actual_value = after_channels[channel]
                if _forced_invalid_mutator is not None:
                    actual_value = _forced_invalid_mutator(
                        provenance, channel, actual_value
                    )
                if actual_value != expected_value:
                    channel_mismatch = True
                    mismatches.append(Family3V2AuditMismatch(
                        "binding", provenance,
                        "forced_invalid_" + channel, expected_value, actual_value,
                    ))
            if (
                not channel_mismatch and stable_key_matches and closure_matches
                and actual_after_state == expected_invalid
            ):
                forced_invalid_zero_delta_count += 1
            if _forced_invalid_mutator is not None and mismatches:
                break
        if _forced_invalid_mutator is not None and mismatches:
            break
    guard_supports: list[tuple[_Occurrence, int, object, int]] = []
    guard_occurrences = () if (_forced_invalid_mutator is not None and mismatches) else occurrences
    for occurrence in guard_occurrences:
        for slot, candidate in enumerate(model.candidates(occurrence.state)):
            if not candidate.mask_valid:
                continue
            distribution = model.transition_distribution(
                occurrence.state, candidate.semantic_candidate_id
            )
            for transition in distribution:
                if transition.next_state.failure_reason == "irreversible_no_coverage":
                    residue = 4 if len(distribution) == 2 else 0
                    guard_supports.append((occurrence, slot, transition, residue))
    guard_records: list[Family3V2NonemittedGuardRecord] = []
    pure_guard_literal_check_count = 0
    real_guard_literal_check_count = 0
    seed_cache = {
        kernel.branch_coupling_uid: _seed_map(kernel) for _, _, kernel in _analyses(suite)
    }
    for occurrence, slot, transition, residue in guard_supports:
        candidate = model.candidates(occurrence.state)[slot]
        prefix_residue = next(
            (value for slot_value, value in occurrence.history if slot_value == 2), 0
        )
        replay_residue = residue if len(model.transition_distribution(
            occurrence.state, candidate.semantic_candidate_id
        )) == 2 else prefix_residue
        seed = seed_cache[occurrence.state.kernel.branch_coupling_uid][replay_residue]
        env = Family3V2Environment()
        observation, before = _replay_prefix(env, occurrence, seed)
        observation, reward, terminated, truncated, after = env.step(slot)
        state = transition.next_state
        catalog = state.nonemitted_guard_catalog
        actual_catalog = after.semantic_state.nonemitted_guard_catalog
        pure_signature = _catalog_signature(catalog)
        actual_signature = _catalog_signature(actual_catalog)
        literal_signature = (
            _EXECUTE_NO_COVERAGE_LITERAL
            if candidate.role is CandidateRoleV2.EXECUTE_COVERING
            else _DISABLE_NO_COVERAGE_LITERAL
        )
        provenance = occurrence.provenance + (candidate.role.value,)
        if _catalog_input_mutator is not None:
            pure_signature = _catalog_input_mutator(provenance, "pure_guard", pure_signature)
            actual_signature = _catalog_input_mutator(provenance, "real_guard", actual_signature)
        pure_guard_literal_check_count += 1
        real_guard_literal_check_count += 1
        pure_literal_matches = pure_signature == literal_signature
        real_literal_matches = actual_signature == literal_signature
        if not pure_literal_matches:
            mismatches.append(Family3V2AuditMismatch(
                "binding", provenance, "pure_no_coverage_literal_catalog",
                literal_signature, pure_signature,
            ))
        if not real_literal_matches:
            mismatches.append(Family3V2AuditMismatch(
                "binding", provenance, "real_no_coverage_literal_catalog",
                literal_signature, actual_signature,
            ))
        next_required = after.task_snapshot.next_required_step_id
        next_pending = next_required is not None and any(
            step_id == next_required and status.value == "pending"
            for step_id, status in after.task_snapshot.steps
        )
        task_installed = True
        if candidate.role is CandidateRoleV2.EXECUTE_COVERING:
            expected_task = after.semantic_state.current_task
            expected_step_id = None if expected_task is None else f"family3_v2_task_{expected_task.ordinal}"
            task_installed = expected_step_id == next_required and next_pending
        verified = (
            before.semantic_state == occurrence.state
            and after.semantic_state == state and reward == 0 and terminated and not truncated
            and state.offer.offer_window is OfferWindowV2.CLOSED
            and observation.candidates == () and observation.mask == ()
            and pure_literal_matches and real_literal_matches and len(actual_catalog) == 7
            and all(not row.emitted for row in actual_catalog)
            and (candidate.role is not CandidateRoleV2.EXECUTE_COVERING or task_installed)
        )
        guard_records.append(Family3V2NonemittedGuardRecord(
            state.kernel.source_graph_id, candidate.role.value, state.failure_reason,
            len(actual_catalog), all(not row.emitted for row in actual_catalog),
            actual_signature, literal_signature, task_installed, next_required,
            next_pending, verified,
        ))
        if not verified:
            mismatches.append(Family3V2AuditMismatch(
                "binding", occurrence.provenance + (candidate.role.value,),
                "real_no_coverage_guard", True, verified,
            ))
    disable_guard_count = sum(
        record.trigger_role == CandidateRoleV2.DISABLE_ACTIVE.value for record in guard_records
    )
    execute_guard_count = sum(
        record.trigger_role == CandidateRoleV2.EXECUTE_COVERING.value for record in guard_records
    )
    exact_counts = (
        len(audited) == 294 and closed_offer_row_check_count == 882
        and disable_guard_count == 294 and execute_guard_count == 20
        and len(guard_records) == 314
    )
    if binding_count != 20 or not catalog_row_count or len(action_types) != 6 or not exact_counts or not forced_invalid_count:
        mismatches.append(Family3V2AuditMismatch("binding", (), "nonvacuity", True, False))
    return Family3V2BindingNoRepairReport(
        not mismatches, tuple(mismatches), binding_count, catalog_row_count, len(action_types),
        len(audited), closed_offer_row_check_count, disable_guard_count, execute_guard_count,
        len(guard_records), len(guard_records) * 7, forced_invalid_count, int(pre_ok), int(post_ok),
        forced_invalid_zero_delta_count, emitted_literal_check_count,
        pure_guard_literal_check_count, real_guard_literal_check_count,
        forced_invalid_stable_key_check_count, forced_invalid_closure_check_count,
        tuple(binding_records), tuple(guard_records),
    )


__all__ = [
    "Family3V2AuditMismatch", "Family3V2BindingNoRepairReport", "Family3V2BindingRecord",
    "Family3V2NonemittedGuardRecord", "Family3V2FirewallReport",
    "Family3V2KernelEnvironmentConformanceReport", "Family3V2MarkovAuditReport",
    "Family3V2WitnessCell", "Family3V2WitnessReport", "audit_family3_v2_binding_no_repair",
    "audit_family3_v2_firewall", "audit_family3_v2_kernel_environment_conformance",
    "audit_family3_v2_markov", "audit_family3_v2_witnesses",
]
