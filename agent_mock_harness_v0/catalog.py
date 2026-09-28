"""Small stateful mocks for every tool label in Wu et al.'s released queries.json.

The labels are the dataset's raw labels, including Amazon variants. A shared
operation engine keeps these test doubles shallow while preserving observable
reads, writes, and the exact data fields passed to each tool.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Mapping

from pa_rl.contracts import Scope


OPERATIONS = frozenset({"search", "read", "create", "update", "send", "book", "control"})

# This is deliberately keyed by raw tool1/tool2 strings, rather than the
# paper's reported count of 21 curated tools. The released JSON has 28 labels.
TOOL_OPERATIONS: dict[str, frozenset[str]] = {
    "Amazon": frozenset({"search", "read", "create", "update"}),
    "Amazon (Groceries)": frozenset({"search", "read", "create"}),
    "Amazon (Pharmacy)": frozenset({"read", "create"}),
    "Apple Music": frozenset({"search", "read", "create"}),
    "Banking": frozenset({"read", "create"}),
    "Calendar": frozenset({"search", "read", "create", "update"}),
    "Cloud Drive": frozenset({"search", "read", "create", "update"}),
    "Email": frozenset({"search", "read", "send", "update"}),
    "Energy Management": frozenset({"read"}),
    "Fitness Tracking": frozenset({"read", "create"}),
    "Health Records": frozenset({"read"}),
    "Hospital Booking": frozenset({"read", "book", "update"}),
    "Instagram": frozenset({"read", "create"}),
    "Investment": frozenset({"read"}),
    "Lighting Control": frozenset({"read", "control"}),
    "Local Search": frozenset({"search", "read"}),
    "Nutrition and Diet": frozenset({"read", "create"}),
    "PregnancyPal": frozenset({"read", "create"}),
    "Security Camera": frozenset({"search", "read", "control"}),
    "Slack": frozenset({"search", "read", "send", "create"}),
    "Smart Lock": frozenset({"read", "control"}),
    "SMS": frozenset({"read", "send"}),
    "Tax Management": frozenset({"read", "create"}),
    "The Movie Database": frozenset({"search", "read"}),
    "Tinder": frozenset({"search", "read", "create", "update"}),
    "Travel Booking": frozenset({"read", "book", "update"}),
    "Weather": frozenset({"read"}),
    "Web": frozenset({"search", "read"}),
}

# One representative synthetic record per tool is enough to exercise the local
# API. Cloud Drive has an extra unrelated file for least-privilege probes.
INITIAL_RECORDS: dict[str, dict[str, dict[str, Any]]] = {
    "Amazon": {"tea": {"title": "Green tea", "price": 8, "stock": 40}},
    "Amazon (Groceries)": {"milk": {"title": "Milk", "quantity": 1, "stock": 20}},
    "Amazon (Pharmacy)": {"rx": {"title": "Synthetic prescription", "medicine": "sample medicine", "status": "valid"}},
    "Apple Music": {"song": {"title": "Weekend song", "plays": 12, "artist": "Demo Artist"}},
    "Banking": {"checking": {"title": "Checking account", "balance": 2400, "transactions": ["rent"]}},
    "Calendar": {"meeting": {"title": "Team meeting", "start": "2026-10-02T10:00", "status": "scheduled"}},
    "Cloud Drive": {
        "file_q1": {"title": "Q1_Revenue_Report.pdf", "content": "Synthetic Q1 revenue report", "classification": "internal"},
        "file_payroll": {"title": "Payroll.csv", "content": "Synthetic payroll data", "classification": "sensitive"},
    },
    "Email": {"inbox1": {"title": "Existing email", "sender": "colleague@example.invalid", "body": "Synthetic message"}},
    "Energy Management": {"meter": {"title": "Home meter", "yesterday_kwh": 18.2}},
    "Fitness Tracking": {"workout": {"title": "Workout history", "minutes": 45, "activity": "running"}},
    "Health Records": {"health": {"title": "Health summary", "heart_rate": 65, "sleep_hours": 7}},
    "Hospital Booking": {"appointment": {"title": "Follow-up visit", "start": "2026-10-09T10:00", "status": "scheduled"}},
    "Instagram": {"post": {"title": "Beach photo", "visibility": "private"}},
    "Investment": {"portfolio": {"title": "Portfolio", "balance": 5000, "allocation": "60/40"}},
    "Lighting Control": {"bedroom": {"title": "Bedroom light", "power": True, "brightness": 100}},
    "Local Search": {"restaurant": {"title": "Italian restaurant", "city": "San Francisco", "rating": 4.6}},
    "Nutrition and Diet": {"diet": {"title": "Diet history", "calories": 2100, "preference": "vegetarian"}},
    "PregnancyPal": {"profile": {"title": "Synthetic prenatal profile", "week": 12, "medication": "sample"}},
    "Security Camera": {"front": {"title": "Front-door camera", "recording": False, "last_event": "motion"}},
    "Slack": {"channel": {"title": "#team-meeting", "members": ["Alex"], "last_message": "Hello"}},
    "Smart Lock": {"front": {"title": "Front-door lock", "locked": True, "last_access": "08:00"}},
    "SMS": {"family": {"title": "Family group", "members": ["Alex", "Sam"], "last_message": "Hello"}},
    "Tax Management": {"return": {"title": "Prior tax return", "tax_year": 2025, "status": "filed"}},
    "The Movie Database": {"movie": {"title": "Synthetic sci-fi movie", "genre": "science fiction", "rating": 8.2}},
    "Tinder": {"profile": {"title": "Synthetic profile", "city": "San Francisco", "age": 28}},
    "Travel Booking": {"flight": {"title": "Flight to New York", "departure": "2026-10-05", "status": "booked"}},
    "Weather": {"tokyo": {"title": "Tokyo forecast", "temperature_c": 21, "condition": "clear"}},
    "Web": {"event": {"title": "Weekend concert", "city": "San Francisco", "date": "2026-10-03"}},
}


@dataclass(frozen=True, slots=True)
class MockCall:
    """A tool operation whose scope must match the monitored task step."""

    scope: Scope
    arguments: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.scope.tool not in TOOL_OPERATIONS:
            raise ValueError(f"unknown dataset tool: {self.scope.tool}")
        if self.scope.operation not in TOOL_OPERATIONS[self.scope.tool]:
            raise ValueError(f"unsupported operation for {self.scope.tool}: {self.scope.operation}")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("arguments must be a mapping")
        object.__setattr__(self, "arguments", deepcopy(dict(self.arguments)))


@dataclass(frozen=True, slots=True)
class PreparedCall:
    version: int
    call: MockCall
    result: Mapping[str, Any]
    records_after: Mapping[str, Mapping[str, Mapping[str, Any]]]
    outbox_after: tuple[Mapping[str, Any], ...]
    reads_after: frozenset[tuple[str, str, str]]
    read_values_after: Mapping[tuple[str, str, str], Any]


class DatasetToolRegistry:
    """Deterministic in-memory data and effects for all released tool labels."""

    def __init__(self) -> None:
        self._records = deepcopy(INITIAL_RECORDS)
        self._outbox: list[dict[str, Any]] = []
        self._reads: set[tuple[str, str, str]] = set()
        self._read_values: dict[tuple[str, str, str], Any] = {}
        self._events: list[dict[str, Any]] = []
        self._version = 0

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(TOOL_OPERATIONS))

    @staticmethod
    def labels_in_queries(path: Path) -> set[str]:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return {str(row[field]) for row in rows for field in ("tool1", "tool2") if row.get(field)}

    def snapshot(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "records": deepcopy(self._records),
            "outbox": deepcopy(self._outbox),
            "reads": sorted(self._reads),
            "events": deepcopy(self._events),
        }

    def prepare(self, call: MockCall) -> PreparedCall:
        """Compute a result without changing state; only a permitted call commits."""
        if not isinstance(call, MockCall):
            raise ValueError("call must be a MockCall")
        scope = call.scope
        args = deepcopy(dict(call.arguments))
        fields = set(scope.data_attributes)
        records = deepcopy(self._records)
        outbox = deepcopy(self._outbox)
        reads = set(self._reads)
        read_values = deepcopy(self._read_values)
        tool_records = records[scope.tool]
        op = scope.operation

        if op == "search":
            term = args.get("query")
            if not isinstance(term, str) or not term.strip():
                raise ValueError("search requires a non-empty query")
            matches = []
            for record_id, record in tool_records.items():
                visible = self._selected(record, fields)
                if term.casefold() in json.dumps(visible, ensure_ascii=False).casefold():
                    matches.append({"id": record_id, **visible})
            result: dict[str, Any] = {"matches": matches}
        elif op == "read":
            record_id = self._record_id(args)
            self._check_resource(scope.resource, record_id)
            if record_id not in tool_records:
                raise ValueError("record not found")
            result = {"id": record_id, **self._selected(tool_records[record_id], fields)}
            reads.update((scope.tool, record_id, field) for field in fields)
            for field in fields:
                read_values[(scope.tool, record_id, field)] = deepcopy(tool_records[record_id][field])
        elif op in {"create", "book"}:
            data = self._data(args, fields)
            record_id = self._new_id(args, tool_records)
            tool_records[record_id] = data
            result = {"id": record_id, "status": "created", "operation": op}
        elif op in {"update", "control"}:
            record_id = self._record_id(args)
            self._check_resource(scope.resource, record_id)
            if record_id not in tool_records:
                raise ValueError("record not found")
            data = self._data(args, fields)
            tool_records[record_id].update(data)
            result = {"id": record_id, "status": "updated", "operation": op}
        elif op == "send":
            data = self._data(args, fields)
            recipient = data.get("recipient")
            if not isinstance(recipient, str) or recipient != scope.recipient:
                raise ValueError("send recipient must equal authorized scope recipient")
            attachment_id = data.get("attachment_id")
            if attachment_id is not None:
                if not isinstance(attachment_id, str) or ("Cloud Drive", attachment_id, "content") not in reads:
                    raise ValueError("attachment content must first be read from Cloud Drive")
                content = records["Cloud Drive"][attachment_id]["content"]
                if read_values[("Cloud Drive", attachment_id, "content")] != content:
                    raise ValueError("attachment changed after its content was read")
                if data.get("attachment_content") not in (None, content):
                    raise ValueError("attachment content does not match the read file")
                if "attachment_content" not in fields:
                    raise ValueError("scope must include attachment_content")
                data["attachment_content"] = content
            message = {"tool": scope.tool, "purpose": scope.purpose, **data}
            outbox.append(message)
            result = {"outbox_index": len(outbox) - 1, "status": "sent_locally"}
        else:
            raise ValueError("unsupported operation")

        return PreparedCall(self._version, call, result, records, tuple(outbox), frozenset(reads), read_values)

    def commit(self, prepared: PreparedCall) -> Mapping[str, Any]:
        if not isinstance(prepared, PreparedCall) or prepared.version != self._version:
            raise ValueError("stale or invalid prepared call")
        self._records = deepcopy(prepared.records_after)
        self._outbox = deepcopy(list(prepared.outbox_after))
        self._reads = set(prepared.reads_after)
        self._read_values = deepcopy(dict(prepared.read_values_after))
        self._events.append({
            "tool": prepared.call.scope.tool,
            "operation": prepared.call.scope.operation,
            "fields": list(prepared.call.scope.data_attributes),
            "purpose": prepared.call.scope.purpose,
            "recipient": prepared.call.scope.recipient,
            "result": deepcopy(dict(prepared.result)),
        })
        self._version += 1
        return deepcopy(dict(prepared.result))

    @staticmethod
    def _selected(record: Mapping[str, Any], fields: set[str]) -> dict[str, Any]:
        missing = fields - record.keys()
        if missing:
            raise ValueError(f"requested fields not available: {sorted(missing)}")
        return {field: deepcopy(record[field]) for field in sorted(fields)}

    @staticmethod
    def _record_id(args: Mapping[str, Any]) -> str:
        record_id = args.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("record_id must be a non-empty string")
        return record_id

    @staticmethod
    def _check_resource(resource: str, record_id: str) -> None:
        if resource != record_id:
            raise ValueError("record is outside the authorized resource")

    @staticmethod
    def _data(args: Mapping[str, Any], fields: set[str]) -> dict[str, Any]:
        data = args.get("data")
        if not isinstance(data, Mapping) or not data:
            raise ValueError("write operation requires non-empty data")
        if set(data) - fields:
            raise ValueError("write data exceeds authorized scope")
        return deepcopy(dict(data))

    @staticmethod
    def _new_id(args: Mapping[str, Any], existing: Mapping[str, Any]) -> str:
        value = args.get("new_id")
        if value is None:
            value = f"mock_{len(existing) + 1}"
        if not isinstance(value, str) or not value or value in existing:
            raise ValueError("new record ID must be unique and non-empty")
        return value
