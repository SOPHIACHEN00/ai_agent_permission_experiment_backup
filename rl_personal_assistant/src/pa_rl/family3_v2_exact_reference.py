"""Independent terminal-free bottom-up reference for Family-3 v2 graphs."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping


_SUPPORTED_GRAPH_IDS = frozenset({"i8_f3v2_v0", "i8_f3v2_v1"})


def _exact_binary_reward(value: object) -> Fraction:
    if type(value) is not int or value not in {0, 1}:
        raise ValueError("terminal reward must be an exact binary integer")
    return Fraction(value)


def _json_value(value: object) -> object:
    """Encode a nonterminal semantic state without repr or object identity."""
    if isinstance(value, Fraction):
        return {"fraction_numerator": value.numerator, "fraction_denominator": value.denominator}
    if isinstance(value, Enum):
        return {"enum_type": type(value).__qualname__, "value": value.value}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "dataclass_type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {field.name: _json_value(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, Mapping):
        items = ((str(key), _json_value(item)) for key, item in value.items())
        return {"mapping": dict(sorted(items))}
    if isinstance(value, tuple):
        return {"tuple": [_json_value(item) for item in value]}
    if isinstance(value, list):
        return {"list": [_json_value(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        encoded = [_json_value(item) for item in value]
        return {"set": sorted(encoded, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))}
    if value is None or type(value) in {str, int, bool}:
        return value
    raise ValueError(f"unsupported nonterminal semantic value: {type(value)!r}")


def _state_key(state: object) -> str:
    payload = json.dumps(_json_value(state), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _state_graph_id(state: object) -> str:
    try:
        graph_id = state.kernel.source_graph_id  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("state must expose kernel.source_graph_id") from exc
    if type(graph_id) is not str:
        raise ValueError("source graph ID must be text")
    return graph_id


def _decision_index(state: object) -> int:
    try:
        value = state.decision_index  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("nonterminal state must expose decision_index") from exc
    if type(value) is not int or value < 0:
        raise ValueError("decision index must be a nonnegative exact integer")
    return value


def _is_terminal(state: object) -> bool:
    try:
        value = state.terminated  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("state must expose terminated") from exc
    if type(value) is not bool:
        raise ValueError("terminated must be an exact boolean")
    return value


@dataclass(frozen=True, slots=True)
class TerminalFreeReferenceResult:
    graph_id: str
    root_value: Fraction
    root_q_values: tuple[tuple[str, Fraction], ...]
    nonterminal_state_count: int
    terminal_leaf_count: int
    action_count: int
    transition_count: int
    max_decision_depth: int

    def __post_init__(self) -> None:
        if self.graph_id not in _SUPPORTED_GRAPH_IDS or type(self.root_value) is not Fraction:
            raise ValueError("reference result graph or root value is invalid")
        if not isinstance(self.root_q_values, tuple):
            raise ValueError("reference root Q rows must be a caller-ordered tuple")
        action_ids: list[str] = []
        for row in self.root_q_values:
            if (
                not isinstance(row, tuple)
                or len(row) != 2
                or type(row[0]) is not str
                or not row[0]
                or type(row[1]) is not Fraction
            ):
                raise ValueError("reference Q rows require a non-empty string ID and exact Fraction")
            action_ids.append(row[0])
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("reference Q action IDs must be unique")
        for value in (
            self.nonterminal_state_count, self.terminal_leaf_count, self.action_count,
            self.transition_count, self.max_decision_depth,
        ):
            if type(value) is not int or value < 0:
                raise ValueError("reference counts must be nonnegative exact integers")

    def as_mapping(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "root_value": {"numerator": self.root_value.numerator, "denominator": self.root_value.denominator},
            "root_q_values": tuple(
                (action, {"numerator": value.numerator, "denominator": value.denominator})
                for action, value in self.root_q_values
            ),
            "nonterminal_state_count": self.nonterminal_state_count,
            "terminal_leaf_count": self.terminal_leaf_count,
            "action_count": self.action_count,
            "transition_count": self.transition_count,
            "max_decision_depth": self.max_decision_depth,
        }


@dataclass(frozen=True, slots=True)
class _Leaf:
    probability: Fraction
    terminal_value: Fraction | None = None
    child_key: str | None = None

    def __post_init__(self) -> None:
        if type(self.probability) is not Fraction or self.probability <= 0:
            raise ValueError("reference transition probability must be positive and exact")
        if (self.terminal_value is None) == (self.child_key is None):
            raise ValueError("reference successor must be exactly a terminal leaf or a nonterminal key")


def _requested_actions(initial_action_ids: object) -> tuple[str, ...]:
    if not isinstance(initial_action_ids, tuple) or not initial_action_ids:
        raise ValueError("requested root action IDs must be a nonempty tuple")
    if any(type(value) is not str or not value for value in initial_action_ids):
        raise ValueError("requested root action IDs must be nonempty text")
    if len(set(initial_action_ids)) != len(initial_action_ids):
        raise ValueError("requested root action IDs must be unique")
    return initial_action_ids


def _valid_actions(model: object, state: object) -> tuple[str, ...]:
    try:
        candidates = model.candidates(state)  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("model must expose candidates(state)") from exc
    actions: list[str] = []
    for candidate in candidates:
        try:
            action_id = candidate.semantic_candidate_id
            mask_valid = candidate.mask_valid
        except AttributeError as exc:
            raise ValueError("candidate must expose semantic_candidate_id and mask_valid") from exc
        if type(action_id) is not str or type(mask_valid) is not bool:
            raise ValueError("candidate fields are invalid")
        if mask_valid:
            actions.append(action_id)
    if len(set(actions)) != len(actions):
        raise ValueError("mask-valid semantic candidate IDs must be unique")
    if not actions:
        raise ValueError("reachable nonterminal state has no valid action")
    return tuple(actions)


def _distribution(model: object, state: object, action_id: str) -> tuple[object, ...]:
    try:
        values = model.transition_distribution(state, action_id)  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise ValueError("model must expose transition_distribution") from exc
    if not isinstance(values, tuple) or not values:
        raise ValueError("transition distribution must be a nonempty tuple")
    probability_sum = Fraction(0)
    for transition in values:
        try:
            probability = transition.probability
        except AttributeError as exc:
            raise ValueError("transition must expose probability") from exc
        if type(probability) is not Fraction or probability <= 0:
            raise ValueError("transition probability must be a positive exact Fraction")
        probability_sum += probability
    if probability_sum != Fraction(1):
        raise ValueError("transition probabilities must sum exactly to one")
    return values


def enumerate_terminal_free_reference(
    model: object,
    initial_state: object,
    initial_action_ids: tuple[str, ...],
) -> TerminalFreeReferenceResult:
    """BFS nonterminals and evaluate them in reverse decision-index order."""
    requested = _requested_actions(initial_action_ids)
    if _is_terminal(initial_state):
        raise ValueError("reference initial state must be nonterminal")
    graph_id = _state_graph_id(initial_state)
    if graph_id not in _SUPPORTED_GRAPH_IDS:
        raise ValueError("reference is limited to i8_f3v2_v0 and i8_f3v2_v1")

    root_key = _state_key(initial_state)
    states: dict[str, object] = {root_key: initial_state}
    depths: dict[str, int] = {root_key: _decision_index(initial_state)}
    successor_rows: dict[str, dict[str, tuple[_Leaf, ...]]] = {}
    queue: deque[str] = deque((root_key,))
    terminal_leaf_count = action_count = transition_count = 0

    while queue:
        state_key = queue.popleft()
        state = states[state_key]
        parent_index = depths[state_key]
        actions = _valid_actions(model, state)
        action_count += len(actions)
        rows: dict[str, tuple[_Leaf, ...]] = {}
        for action_id in actions:
            leaves: list[_Leaf] = []
            for transition in _distribution(model, state, action_id):
                probability = transition.probability
                try:
                    successor = transition.next_state
                except AttributeError as exc:
                    raise ValueError("transition must expose next_state") from exc
                transition_count += 1
                # The terminal path intentionally reads only these two attributes.
                if _is_terminal(successor):
                    leaves.append(_Leaf(probability, terminal_value=_exact_binary_reward(successor.reward)))
                    terminal_leaf_count += 1
                    continue
                if _state_graph_id(successor) != graph_id:
                    raise ValueError(
                        "every reachable nonterminal child must use the same supported source graph"
                    )
                child_index = _decision_index(successor)
                if child_index != parent_index + 1:
                    raise ValueError("nonterminal successor must advance decision_index by one")
                child_key = _state_key(successor)
                if child_key not in states:
                    states[child_key] = successor
                    depths[child_key] = child_index
                    queue.append(child_key)
                leaves.append(_Leaf(probability, child_key=child_key))
            rows[action_id] = tuple(leaves)
        successor_rows[state_key] = rows

    values: dict[str, Fraction] = {}
    q_rows: dict[str, dict[str, Fraction]] = {}
    for state_key in sorted(states, key=lambda key: depths[key], reverse=True):
        action_values: dict[str, Fraction] = {}
        for action_id, leaves in successor_rows[state_key].items():
            total = Fraction(0)
            for leaf in leaves:
                child_value = leaf.terminal_value if leaf.terminal_value is not None else values[leaf.child_key or ""]
                total += leaf.probability * child_value
            action_values[action_id] = total
        q_rows[state_key] = action_values
        values[state_key] = max(action_values.values())

    root_actions = _valid_actions(model, initial_state)
    if any(action not in root_actions for action in requested):
        raise ValueError("requested root action must be present and mask-valid")
    return TerminalFreeReferenceResult(
        graph_id=graph_id,
        root_value=values[root_key],
        root_q_values=tuple((action, q_rows[root_key][action]) for action in requested),
        nonterminal_state_count=len(states),
        terminal_leaf_count=terminal_leaf_count,
        action_count=action_count,
        transition_count=transition_count,
        max_decision_depth=max(depths.values()),
    )


__all__ = ["TerminalFreeReferenceResult", "enumerate_terminal_free_reference"]
