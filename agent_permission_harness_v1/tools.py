"""Stateful synthetic tools whose results and effects follow an exact scope.

This module is trusted local harness code. Planners receive committed public
results, never the store, preparation object, or full synthetic records.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Any, Mapping

from pa_rl.contracts import freeze_value
from agent_mock_harness_v0.catalog import TOOL_OPERATIONS as _DATASET_TOOL_OPERATIONS

from .contracts import CompiledCall


TOOL_OPERATIONS = {**_DATASET_TOOL_OPERATIONS, "mira": frozenset({"read"})}
OPERATIONS = frozenset({"search", "read", "create", "update", "send", "book", "control"})
# Explicit virtual collections. An arbitrary missing record is NOT a collection.
SEARCH_COLLECTIONS = {tool: frozenset({'collection'}) for tool in TOOL_OPERATIONS}
SEARCH_COLLECTIONS['Cloud Drive'] = frozenset({'collection', 'drive.files'})


def _copy(value: Any) -> Any:
    """Copy frozen contract mappings without deepcopy's mappingproxy problem."""
    if isinstance(value, Mapping):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_copy(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return set(_copy(item) for item in value)
    return deepcopy(value)


def validate_call(call: CompiledCall) -> None:
    """Check shape and resource/recipient binding before effects or reservation."""
    if not isinstance(call, CompiledCall):
        raise ValueError("call must be a CompiledCall")
    scope, args = call.scope, call.arguments
    if scope.tool not in TOOL_OPERATIONS or scope.operation not in TOOL_OPERATIONS[scope.tool]:
        raise ValueError("unsupported dataset tool operation")
    if not isinstance(args, Mapping):
        raise ValueError("arguments must be a mapping")
    op = scope.operation
    permitted = {"search": {"query"}, "read": {"record_id"},
                 "create": {"new_id", "data"}, "book": {"new_id", "data"},
                 "update": {"record_id", "data"}, "control": {"record_id", "data"},
                 "send": {"data"}}[op]
    if set(args) - permitted:
        raise ValueError("unexpected operation argument")
    if op == "search":
        if not isinstance(args.get("query"), str) or not args["query"].strip():
            raise ValueError("search requires a non-empty query")
    elif op in {"read", "update", "control"}:
        if not isinstance(args.get("record_id"), str) or args["record_id"] != scope.resource:
            raise ValueError("record_id must match the operation resource")
    elif op in {"create", "book"}:
        if "new_id" in args and args["new_id"] != scope.resource:
            raise ValueError("new_id must match the operation resource")
    if op in {"create", "book", "update", "control", "send"}:
        data = args.get("data")
        if not isinstance(data, Mapping) or not data or any(not isinstance(key, str) for key in data):
            raise ValueError("write operation requires non-empty data")
        if set(data) - set(scope.data_attributes):
            raise ValueError("write fields exceed the actual operation scope")
        if op == "send" and ("recipient" not in scope.data_attributes or data.get("recipient") != scope.recipient):
            raise ValueError("send recipient must equal the operation scope recipient")


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


class LocalToolStore:
    """Single-threaded local records, explicit field reads, and synthetic outbox."""

    def __init__(self, records: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> None:
        if not isinstance(records, Mapping) or set(records) - set(TOOL_OPERATIONS):
            raise ValueError("records must use known local tool labels")
        if any(not isinstance(rows, Mapping) or any(not isinstance(record, Mapping) for record in rows.values()) for rows in records.values()):
            raise ValueError("records must map tool names to record ID/data mappings")
        self._records = {tool: _copy(records.get(tool, {})) for tool in TOOL_OPERATIONS}
        self._outbox: list[dict[str, Any]] = []
        self._reads: set[tuple[str, str, str]] = set()
        self._read_values: dict[tuple[str, str, str], Any] = {}
        self._events: list[dict[str, Any]] = []
        self._version = 0
        self._owner = object()
        self._issued_preparations: dict[int, PreparedEffect] = {}

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(TOOL_OPERATIONS))

    def snapshot(self) -> dict[str, Any]:
        return {"version": self._version, "records": _copy(self._records),
                "outbox": _copy(self._outbox), "reads": sorted(self._reads), "events": _copy(self._events)}

    @staticmethod
    def _selected(record: Mapping[str, Any], fields: set[str]) -> dict[str, Any]:
        if fields - set(record):
            raise ValueError("requested field is absent from the synthetic record")
        return {field: _copy(record[field]) for field in sorted(fields)}

    def prepare(self, call: CompiledCall) -> PreparedEffect:
        """Compute projected results and effects without mutating business state."""
        validate_call(call)
        scope, args = call.scope, _copy(call.arguments)
        fields = set(scope.data_attributes)
        records, outbox = _copy(self._records), _copy(self._outbox)
        reads, read_values = set(self._reads), {key: _copy(value) for key, value in self._read_values.items()}
        tool_records = records[scope.tool]
        op = scope.operation

        def expose(record_id: str, visible: Mapping[str, Any]) -> None:
            for field, value in visible.items():
                reads.add((scope.tool, record_id, field))
                read_values[(scope.tool, record_id, field)] = _copy(value)

        if op == "search":
            term = args["query"].casefold()
            matches = []
            concrete = scope.resource in tool_records
            if not concrete and scope.resource not in SEARCH_COLLECTIONS[scope.tool]:
                raise ValueError('search resource is neither an existing record nor a declared collection')
            for record_id, record in sorted(tool_records.items()):
                # A declared collection resource searches its tool-local records;
                # a concrete existing record resource searches only that record.
                if concrete and scope.resource != record_id:
                    continue
                visible = self._selected(record, fields)
                if term in json.dumps(visible, ensure_ascii=False, sort_keys=True).casefold():
                    matches.append({**visible, "id": record_id})
                    expose(record_id, visible)
            result: dict[str, Any] = {"matches": matches}
        elif op == "read":
            record_id = args["record_id"]
            if record_id not in tool_records:
                raise ValueError("record not found")
            visible = self._selected(tool_records[record_id], fields)
            result = {**visible, "id": record_id}
            expose(record_id, visible)
        elif op in {"create", "book"}:
            record_id = args.get("new_id", scope.resource)
            if not isinstance(record_id, str) or not record_id or record_id in tool_records:
                raise ValueError("new record ID must be unique and non-empty")
            tool_records[record_id] = args["data"]
            result = {"id": record_id, "status": "created", "operation": op}
        elif op in {"update", "control"}:
            record_id = args["record_id"]
            if record_id not in tool_records:
                raise ValueError("record not found")
            tool_records[record_id].update(args["data"])
            result = {"id": record_id, "status": "updated", "operation": op}
        else:  # send: local message effect only
            data = args["data"]
            attachment_id = data.get("attachment_id")
            if attachment_id is not None:
                source = ("Cloud Drive", attachment_id, "content")
                if not isinstance(attachment_id, str) or source not in reads:
                    raise ValueError("attachment content must first be observed from Cloud Drive")
                source_record = records["Cloud Drive"].get(attachment_id, {})
                if "content" not in source_record or read_values[source] != source_record["content"]:
                    raise ValueError("attachment changed after its content was observed")
                content = source_record["content"]
                if data.get("attachment_content") not in (None, content):
                    raise ValueError("attachment content differs from the observed file")
                if "attachment_content" not in fields:
                    raise ValueError("attachment content requires its own scope field")
                data["attachment_content"] = _copy(content)
            outbox.append({"tool": scope.tool, "purpose": scope.purpose, **data})
            result = {"outbox_index": len(outbox) - 1, "status": "sent_locally"}

        # Nested state is immutable so a caller cannot expand an approved effect.
        prepared = PreparedEffect(self._version, call, freeze_value(result), freeze_value(records),
                                  tuple(freeze_value(row) for row in outbox), frozenset(reads),
                                  MappingProxyType({key: freeze_value(value) for key, value in read_values.items()}), self._owner)
        self._issued_preparations[id(prepared)] = prepared
        return prepared

    def commit(self, prepared: PreparedEffect) -> Mapping[str, Any]:
        if (not isinstance(prepared, PreparedEffect) or prepared._owner is not self._owner
                or prepared.version != self._version or self._issued_preparations.get(id(prepared)) is not prepared):
            raise ValueError("stale, foreign, or invalid prepared effect")
        self._records = _copy(prepared.records_after)
        self._outbox = _copy(prepared.outbox_after)
        self._reads = set(prepared.reads_after)
        self._read_values = {key: _copy(value) for key, value in prepared.read_values_after.items()}
        self._events.append({"step_id": prepared.call.step_id, "tool": prepared.call.scope.tool,
                             "operation": prepared.call.scope.operation, "resource": prepared.call.scope.resource,
                             "fields": list(prepared.call.scope.data_attributes), "purpose": prepared.call.scope.purpose,
                             "recipient": prepared.call.scope.recipient, "result": _copy(prepared.result)})
        self._version += 1
        self._issued_preparations.clear()
        return _copy(prepared.result)
