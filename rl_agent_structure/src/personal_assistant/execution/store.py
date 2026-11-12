"""Transactional projected effects; no vendor logic or legacy package imports."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from ..contracts.permission import freeze_value
from ..contracts.tool_call import CompiledCall


class ToolBackend(Protocol):
    """Trusted local backend, separate from the untrusted planner's proposals."""

    @property
    def tool_names(self) -> tuple[str, ...]: ...

    def validate_call(self, call: CompiledCall) -> None: ...

    def prepare_io_effect(self, call, records, outbox, reads, read_values,
                          private_inputs, models) -> tuple[dict, list]: ...


def _copy(value: Any) -> Any:
    """Copy frozen contract mappings without deepcopy's mappingproxy problem."""
    if isinstance(value, Mapping):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_copy(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return set(_copy(item) for item in value)
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class PreparedEffect:
    version: int
    call: CompiledCall
    result: Mapping[str, Any]
    records_after: Mapping[str, Mapping[str, Mapping[str, Any]]]
    outbox_after: tuple[Mapping[str, Any], ...]
    reads_after: frozenset[tuple[str, str, str]]
    read_values_after: Mapping[tuple[str, str, str], Any]
    _owner: object
    data_flows_after: tuple[Mapping[str, Any], ...] = ()


class LocalToolStore:
    """Private records and immutable preparations, committed exactly once."""

    def __init__(self, records: Mapping, *, backend: ToolBackend,
                 private_inputs: Mapping | None = None, tool_models: Mapping | None = None) -> None:
        self._backend = backend
        self._tool_names = tuple(backend.tool_names)
        if not self._tool_names or len(set(self._tool_names)) != len(self._tool_names):
            raise ValueError("backend must declare unique tool labels")
        if not isinstance(records, Mapping) or set(records) - set(self._tool_names):
            raise ValueError("records must use known local tool labels")
        if any(not isinstance(rows, Mapping) or any(not isinstance(record, Mapping) for record in rows.values())
               for rows in records.values()):
            raise ValueError("records must map tool names to record ID/data mappings")
        self._records = {tool: _copy(records.get(tool, {})) for tool in self._tool_names}
        self._outbox: list[dict[str, Any]] = []
        self._reads: set[tuple[str, str, str]] = set()
        self._read_values: dict[tuple[str, str, str], Any] = {}
        self._events: list[dict[str, Any]] = []
        self._version = 0
        self._owner = object()
        self._issued_preparations: dict[int, PreparedEffect] = {}
        self._private_inputs = freeze_value(private_inputs or {})
        self._tool_models = freeze_value(tool_models or {})
        self._data_flows: list[dict[str, Any]] = []

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tool_names))

    def validate_call(self, call: CompiledCall) -> None:
        self._backend.validate_call(call)

    def snapshot(self) -> dict[str, Any]:
        return {"version": self._version, "records": _copy(self._records),
                "outbox": _copy(self._outbox), "reads": sorted(self._reads), "events": _copy(self._events),
                "data_flows": _copy(self._data_flows)}

    def prepare(self, call: CompiledCall) -> PreparedEffect:
        """Compute effects on detached copies; live state is unchanged until commit."""
        self.validate_call(call)
        records, outbox = _copy(self._records), _copy(self._outbox)
        reads = set(self._reads)
        read_values = {key: _copy(value) for key, value in self._read_values.items()}
        result, new_flows = self._backend.prepare_io_effect(
            call, records, outbox, reads, read_values, self._private_inputs, self._tool_models)
        flows = _copy(self._data_flows) + new_flows
        prepared = PreparedEffect(self._version, call, freeze_value(result), freeze_value(records),
                                  tuple(freeze_value(row) for row in outbox), frozenset(reads),
                                  MappingProxyType({key: freeze_value(value) for key, value in read_values.items()}),
                                  self._owner, tuple(freeze_value(flow) for flow in flows))
        self._issued_preparations[id(prepared)] = prepared
        return prepared

    def commit(self, prepared: PreparedEffect, *, effect_id=None) -> Mapping[str, Any]:
        if (not isinstance(prepared, PreparedEffect) or prepared._owner is not self._owner
                or prepared.version != self._version or self._issued_preparations.get(id(prepared)) is not prepared):
            raise ValueError("stale, foreign, or invalid prepared effect")
        self._records = _copy(prepared.records_after)
        self._outbox = _copy(prepared.outbox_after)
        self._reads = set(prepared.reads_after)
        self._read_values = {key: _copy(value) for key, value in prepared.read_values_after.items()}
        previous_flow_count = len(self._data_flows)
        self._data_flows = _copy(prepared.data_flows_after)
        for flow in self._data_flows[previous_flow_count:]:
            flow['effect_id'] = effect_id
        self._events.append({"effect_id": effect_id, "step_id": prepared.call.step_id, "tool": prepared.call.scope.tool,
                             "operation": prepared.call.scope.operation, "resource": prepared.call.scope.resource,
                             "fields": list(prepared.call.scope.data_attributes), "purpose": prepared.call.scope.purpose,
                             "recipient": prepared.call.scope.recipient, "result": _copy(prepared.result)})
        self._version += 1
        self._issued_preparations.clear()
        return _copy(prepared.result)
