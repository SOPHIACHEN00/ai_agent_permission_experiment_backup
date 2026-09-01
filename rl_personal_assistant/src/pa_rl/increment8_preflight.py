"""Exact reachability, Markov, encoder, and DP checks for Increment 8."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Hashable, Mapping

from .increment8_environment import (
    LifecycleObservation,
    project_lifecycle_observation,
)
from .increment8_model import LifecycleModel, LifecycleState, LifecycleTransition
from .increment8_policy import BudgetedLifecycleFeatureEncoder
from .increment8_suite import Increment8Suite


@dataclass(frozen=True, slots=True)
class DPGraphCertificate:
    graph_id: str
    reachable_state_count: int
    initial_success_probability: Fraction
    initial_optimal_actions: tuple[str, ...]

    def as_mapping(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "reachable_state_count": self.reachable_state_count,
            "initial_success_probability": {
                "numerator": self.initial_success_probability.numerator,
                "denominator": self.initial_success_probability.denominator,
            },
            "initial_optimal_actions": self.initial_optimal_actions,
        }


@dataclass(frozen=True, slots=True)
class Increment8Certification:
    graph_ids: tuple[str, ...]
    reachable_state_count: int
    public_group_count: int
    encoder_group_count: int
    public_kernel_mismatches: tuple[str, ...]
    encoder_kernel_mismatches: tuple[str, ...]
    disjoint_optimal_action_groups: tuple[str, ...]
    dp_graphs: tuple[DPGraphCertificate, ...]

    def as_mapping(self) -> dict[str, object]:
        return {
            "graph_ids": self.graph_ids,
            "reachable_state_count": self.reachable_state_count,
            "public_group_count": self.public_group_count,
            "encoder_group_count": self.encoder_group_count,
            "public_kernel_mismatches": self.public_kernel_mismatches,
            "encoder_kernel_mismatches": self.encoder_kernel_mismatches,
            "disjoint_optimal_action_groups": self.disjoint_optimal_action_groups,
            "dp_graphs": tuple(item.as_mapping() for item in self.dp_graphs),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Increment8Certification":
        if not isinstance(value, Mapping) or set(value) != {
            "graph_ids",
            "reachable_state_count",
            "public_group_count",
            "encoder_group_count",
            "public_kernel_mismatches",
            "encoder_kernel_mismatches",
            "disjoint_optimal_action_groups",
            "dp_graphs",
        }:
            raise ValueError("certification mapping has an unexpected schema")
        graph_rows = value["dp_graphs"]
        if not isinstance(graph_rows, tuple):
            raise ValueError("dp_graphs must be a tuple")
        dp_graphs: list[DPGraphCertificate] = []
        for row in graph_rows:
            if not isinstance(row, Mapping) or set(row) != {
                "graph_id",
                "reachable_state_count",
                "initial_success_probability",
                "initial_optimal_actions",
            }:
                raise ValueError("DP graph mapping has an unexpected schema")
            probability = row["initial_success_probability"]
            if not isinstance(probability, Mapping) or set(probability) != {
                "numerator",
                "denominator",
            }:
                raise ValueError("DP probability must be an exact fraction mapping")
            dp_graphs.append(
                DPGraphCertificate(
                    graph_id=str(row["graph_id"]),
                    reachable_state_count=int(row["reachable_state_count"]),
                    initial_success_probability=Fraction(
                        int(probability["numerator"]),
                        int(probability["denominator"]),
                    ),
                    initial_optimal_actions=tuple(row["initial_optimal_actions"]),
                )
            )
        return cls(
            graph_ids=tuple(value["graph_ids"]),
            reachable_state_count=int(value["reachable_state_count"]),
            public_group_count=int(value["public_group_count"]),
            encoder_group_count=int(value["encoder_group_count"]),
            public_kernel_mismatches=tuple(value["public_kernel_mismatches"]),
            encoder_kernel_mismatches=tuple(value["encoder_kernel_mismatches"]),
            disjoint_optimal_action_groups=tuple(
                value["disjoint_optimal_action_groups"]
            ),
            dp_graphs=tuple(dp_graphs),
        )


class _ExactGraphAnalysis:
    def __init__(self, model: LifecycleModel, initial_state: LifecycleState) -> None:
        self.model = model
        self.initial_state = initial_state
        self.transition_cache: dict[
            tuple[LifecycleState, str], tuple[LifecycleTransition, ...]
        ] = {}
        self.states = self._enumerate()
        self._optimal_actions: dict[LifecycleState, frozenset[str]] = {}

    def transitions(
        self, state: LifecycleState, semantic_candidate_id: str
    ) -> tuple[LifecycleTransition, ...]:
        key = (state, semantic_candidate_id)
        if key not in self.transition_cache:
            self.transition_cache[key] = self.model.transition_distribution(
                state, semantic_candidate_id
            )
        return self.transition_cache[key]

    def _enumerate(self) -> tuple[LifecycleState, ...]:
        seen = {self.initial_state}
        queue = deque((self.initial_state,))
        while queue:
            state = queue.popleft()
            if state.terminated:
                continue
            valid = tuple(
                item for item in self.model.candidates(state) if item.mask_valid
            )
            if not valid:
                raise ValueError("reachable nonterminal state has no valid candidate")
            for candidate in valid:
                for transition in self.transitions(
                    state, candidate.semantic_candidate_id
                ):
                    if transition.probability <= 0:
                        raise ValueError("reachable transition has non-positive probability")
                    if transition.next_state not in seen:
                        seen.add(transition.next_state)
                        queue.append(transition.next_state)
            if len(seen) > 1_000_000:
                raise ValueError(
                    "exact reachable state count exceeded the Phase A safety ceiling"
                )
        return tuple(
            sorted(
                seen,
                key=lambda item: (
                    item.logical_step,
                    item.terminated,
                    repr(item),
                ),
            )
        )

    def solve(self) -> Fraction:
        @lru_cache(maxsize=None)
        def value(state: LifecycleState) -> Fraction:
            if state.terminated:
                self._optimal_actions[state] = frozenset()
                return Fraction(state.reward)
            action_values: dict[str, Fraction] = {}
            for candidate in self.model.candidates(state):
                if not candidate.mask_valid:
                    continue
                action_values[candidate.semantic_candidate_id] = sum(
                    transition.probability * value(transition.next_state)
                    for transition in self.transitions(
                        state, candidate.semantic_candidate_id
                    )
                )
            if not action_values:
                raise ValueError("DP reached a nonterminal state with no valid action")
            best = max(action_values.values())
            self._optimal_actions[state] = frozenset(
                action for action, action_value in action_values.items()
                if action_value == best
            )
            return best

        return value(self.initial_state)

    def optimal_actions(self, state: LifecycleState) -> frozenset[str]:
        if state not in self._optimal_actions:
            self.solve()
        return self._optimal_actions[state]


def _aggregate_distribution(
    transitions: tuple[LifecycleTransition, ...],
    successor_key,
) -> frozenset[tuple[Hashable, Fraction]]:
    weights: dict[Hashable, Fraction] = defaultdict(Fraction)
    for transition in transitions:
        key = (
            successor_key(transition.next_state),
            transition.reward,
            transition.terminated,
            transition.truncated,
        )
        weights[key] += transition.probability
    if sum(weights.values(), Fraction()) != 1:
        raise ValueError("exact successor distribution does not sum to one")
    return frozenset(weights.items())


def certify_increment8_inputs(
    suite: Increment8Suite,
    *,
    graph_ids: tuple[str, ...] | None = None,
) -> Increment8Certification:
    if not isinstance(suite, Increment8Suite):
        raise ValueError("suite must be Increment8Suite")
    available = {member.graph.graph_id: member.graph for member in suite.members}
    selected_ids = (
        tuple(item.graph.graph_id for item in suite.members)
        if graph_ids is None
        else graph_ids
    )
    if (
        not isinstance(selected_ids, tuple)
        or not selected_ids
        or len(set(selected_ids)) != len(selected_ids)
        or any(item not in available for item in selected_ids)
    ):
        raise ValueError("graph_ids must be a unique non-empty tuple from the suite")

    # These fields are public, encoded without collision in v2, and invariant
    # under the global kernel (purpose is retained by every scope branch).
    # A unique key therefore proves that no public or encoded state can alias
    # across graphs, allowing exact per-graph certification without retaining
    # the full 48-graph state space in memory at once.
    partition_keys = tuple(
        (
            available[graph_id].horizon,
            available[graph_id].utility_target,
            available[graph_id].prompt_budget,
            available[graph_id].exposure_budget,
            available[graph_id].authorization_objective,
            available[graph_id].purpose,
        )
        for graph_id in selected_ids
    )
    if len(selected_ids) > 1 and len(set(partition_keys)) == len(partition_keys):
        parts = tuple(
            certify_increment8_inputs(suite, graph_ids=(graph_id,))
            for graph_id in selected_ids
        )
        return Increment8Certification(
            graph_ids=selected_ids,
            reachable_state_count=sum(item.reachable_state_count for item in parts),
            public_group_count=sum(item.public_group_count for item in parts),
            encoder_group_count=sum(item.encoder_group_count for item in parts),
            public_kernel_mismatches=tuple(
                f"{part.graph_ids[0]}:{mismatch}"
                for part in parts
                for mismatch in part.public_kernel_mismatches
            ),
            encoder_kernel_mismatches=tuple(
                f"{part.graph_ids[0]}:{mismatch}"
                for part in parts
                for mismatch in part.encoder_kernel_mismatches
            ),
            disjoint_optimal_action_groups=tuple(
                f"{part.graph_ids[0]}:{mismatch}"
                for part in parts
                for mismatch in part.disjoint_optimal_action_groups
            ),
            dp_graphs=tuple(
                graph for part in parts for graph in part.dp_graphs
            ),
        )

    model = LifecycleModel()
    encoder = BudgetedLifecycleFeatureEncoder()
    analyses: dict[str, _ExactGraphAnalysis] = {}
    dp_graphs: list[DPGraphCertificate] = []
    all_states: list[tuple[_ExactGraphAnalysis, LifecycleState]] = []
    for graph_id in selected_ids:
        analysis = _ExactGraphAnalysis(
            model, model.initial_state(available[graph_id])
        )
        analyses[graph_id] = analysis
        initial_value = analysis.solve()
        dp_graphs.append(
            DPGraphCertificate(
                graph_id,
                len(analysis.states),
                initial_value,
                tuple(sorted(analysis.optimal_actions(analysis.initial_state))),
            )
        )
        all_states.extend((analysis, state) for state in analysis.states)

    observation_cache: dict[LifecycleState, LifecycleObservation] = {}
    representation_cache: dict[LifecycleState, Hashable | None] = {}

    def observation(state: LifecycleState) -> LifecycleObservation:
        if state not in observation_cache:
            observation_cache[state] = project_lifecycle_observation(state, model)
        return observation_cache[state]

    def representation(state: LifecycleState) -> Hashable | None:
        if state.terminated:
            return None
        if state not in representation_cache:
            representation_cache[state] = encoder.encode(
                observation(state)
            ).representation_key()
        return representation_cache[state]

    public_groups: dict[LifecycleObservation, list[tuple[_ExactGraphAnalysis, LifecycleState]]] = defaultdict(list)
    encoder_groups: dict[Hashable, list[tuple[_ExactGraphAnalysis, LifecycleState]]] = defaultdict(list)
    for analysis, state in all_states:
        public_groups[observation(state)].append((analysis, state))
        if not state.terminated:
            encoded = representation(state)
            assert encoded is not None
            encoder_groups[encoded].append((analysis, state))

    public_mismatches: list[str] = []
    for group_index, group in enumerate(public_groups.values()):
        if len(group) < 2 or group[0][1].terminated:
            continue
        candidate_sets = tuple(
            frozenset(
                item.semantic_candidate_id
                for item in model.candidates(state)
                if item.mask_valid
            )
            for _, state in group
        )
        common = set.intersection(*(set(item) for item in candidate_sets))
        if any(item != candidate_sets[0] for item in candidate_sets[1:]):
            public_mismatches.append(
                f"public_group_{group_index}:valid_action_set"
            )
            continue
        for action in sorted(common):
            expected = None
            for analysis, state in group:
                distribution = _aggregate_distribution(
                    analysis.transitions(state, action), observation
                )
                if expected is None:
                    expected = distribution
                elif distribution != expected:
                    public_mismatches.append(
                        f"public_group_{group_index}:action:{action}"
                    )
                    break

    encoder_mismatches: list[str] = []
    disjoint_groups: list[str] = []
    for group_index, group in enumerate(encoder_groups.values()):
        if len(group) < 2:
            continue
        candidate_sets = tuple(
            frozenset(
                item.semantic_candidate_id
                for item in model.candidates(state)
                if item.mask_valid
            )
            for _, state in group
        )
        common = set.intersection(*(set(item) for item in candidate_sets))
        if any(item != candidate_sets[0] for item in candidate_sets[1:]):
            encoder_mismatches.append(
                f"encoder_group_{group_index}:valid_action_set"
            )
            continue
        for action in sorted(common):
            expected = None
            for analysis, state in group:
                distribution = _aggregate_distribution(
                    analysis.transitions(state, action), representation
                )
                if expected is None:
                    expected = distribution
                elif distribution != expected:
                    encoder_mismatches.append(
                        f"encoder_group_{group_index}:action:{action}"
                    )
                    break
        optimal_sets = tuple(
            analysis.optimal_actions(state) for analysis, state in group
        )
        if optimal_sets and not set.intersection(*(set(item) for item in optimal_sets)):
            disjoint_groups.append(f"encoder_group_{group_index}")

    return Increment8Certification(
        graph_ids=selected_ids,
        reachable_state_count=len(all_states),
        public_group_count=len(public_groups),
        encoder_group_count=len(encoder_groups),
        public_kernel_mismatches=tuple(public_mismatches),
        encoder_kernel_mismatches=tuple(encoder_mismatches),
        disjoint_optimal_action_groups=tuple(disjoint_groups),
        dp_graphs=tuple(dp_graphs),
    )


__all__ = [
    "DPGraphCertificate",
    "Increment8Certification",
    "certify_increment8_inputs",
]
