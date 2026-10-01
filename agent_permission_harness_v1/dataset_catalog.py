"""Read-only provenance inventory for original Wu permission contexts.

This catalog inventories source tasks and data items. It deliberately does not
invent executable business oracles or turn static preference labels into grants.
Only context metadata is retained from the processed participant-response CSV.
"""

from __future__ import annotations

from copy import deepcopy
import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


SOURCE_PATHS = {
    "queries": "external/ai-agent-permissions/queries.json",
    "processed_contexts": "data/processed/four_label_dataset.csv",
    "questionnaire": "qstn_simulator/outputs/questionnaire_items.csv",
}
DATA_FIELDS = ("datatype", "data_tool1", "data_tool2", "data_MIRA", "data_incorrect",
               "data_tool1_incorrect", "data_tool2_incorrect", "data_MIRA_incorrect")
CONTEXT_COLUMNS = ("query_id", "domain", "tool", "raw_data_type", "generic_data_type", "necessity_status")
Q22_TEXT = 'Share the "Q1_Revenue_Report.pdf" from my Cloud Drive in an email to Lisa with the subject "Q1 Financial Update".'


def normalize_text(value: str) -> str:
    """Match source aliases without changing stored source text."""
    return " ".join(value.split()).casefold()


def _text(value: Any, name: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{name} must be a {'possibly empty' if empty else 'non-empty'} string")
    return value


def _query_id(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("query ID must be a non-negative integer")
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ValueError("query ID must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class PermissionContext:
    query_id: int
    tool: str
    raw_data_type: str
    generic_data_type: str
    necessity_status: str
    tool_aliases: tuple[str, ...]
    raw_data_type_aliases: tuple[str, ...]
    questionnaire_item_id: str
    # Inventing mappings from survey phrases into mock fields would imply
    # executable coverage we have not authored. Keep the missing mapping clear.
    synthetic_field: str | None = None
    field_mapping_status: str = "unmapped_to_executable_mock_field"

    def to_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "tool": self.tool, "raw_data_type": self.raw_data_type,
                "generic_data_type": self.generic_data_type, "necessity_status": self.necessity_status,
                "tool_aliases": list(self.tool_aliases), "raw_data_type_aliases": list(self.raw_data_type_aliases),
                "questionnaire_item_id": self.questionnaire_item_id, "synthetic_field": self.synthetic_field,
                "field_mapping_status": self.field_mapping_status}


@dataclass(frozen=True, slots=True)
class QueryInventory:
    query_id: int
    query: str
    domain: str
    external_tool_labels: tuple[str, ...]
    internal_channels: tuple[str, ...]
    original_fields: Mapping[str, Any]
    original_data_item_maps: Mapping[str, Any]
    query_aliases: tuple[str, ...]
    permission_contexts: tuple[PermissionContext, ...]
    coverage_status: str
    authored_task_oracle: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"query_id": self.query_id, "query": self.query, "domain": self.domain,
                "external_tool_labels": list(self.external_tool_labels), "internal_channels": list(self.internal_channels),
                "original_fields": deepcopy(dict(self.original_fields)),
                "original_data_item_maps": deepcopy(dict(self.original_data_item_maps)),
                "query_aliases": list(self.query_aliases),
                "permission_contexts": [context.to_dict() for context in self.permission_contexts],
                "coverage_status": self.coverage_status, "authored_task_oracle": self.authored_task_oracle}


@dataclass(frozen=True, slots=True)
class DatasetCatalog:
    queries: tuple[QueryInventory, ...]
    external_tool_labels: tuple[str, ...]
    internal_channels: tuple[str, ...]
    domains: tuple[str, ...]
    tools_without_questionnaire_contexts: tuple[str, ...]
    sources: Mapping[str, str]

    @property
    def query_ids(self) -> tuple[int, ...]:
        return tuple(query.query_id for query in self.queries)

    @property
    def counts(self) -> dict[str, int]:
        authored = sum(query.coverage_status == "authored_task_oracle" for query in self.queries)
        return {"query_count": len(self.queries), "external_tool_label_count": len(self.external_tool_labels),
                "internal_channel_count": len(self.internal_channels), "domain_count": len(self.domains),
                "permission_context_count": sum(len(query.permission_contexts) for query in self.queries),
                "authored_task_oracle_count": authored,
                "catalogued_without_task_oracle_count": len(self.queries) - authored}

    def to_dict(self) -> dict[str, Any]:
        return {"catalog_version": "wu_source_inventory_v1", "counts": self.counts,
                "sources": dict(self.sources), "external_tool_labels": list(self.external_tool_labels),
                "internal_channels": list(self.internal_channels), "domains": list(self.domains),
                "tools_without_questionnaire_contexts": list(self.tools_without_questionnaire_contexts),
                "queries": [query.to_dict() for query in self.queries],
                "coverage_note": "Catalogued source tasks are not evidence of executable-task or LLM success. Authored q22 oracle belongs to v0."}


def _csv_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(required).issubset(reader.fieldnames):
            raise ValueError(f"missing required CSV columns in {path.name}")
        return list(reader)


def _context_key(row: Mapping[str, Any]) -> tuple[int, str, str]:
    return (_query_id(row["query_id"]), normalize_text(_text(row["tool"], "tool")),
            normalize_text(_text(row["raw_data_type"], "raw_data_type")))


def _metadata(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(normalize_text(_text(row[field], field))
                 for field in ("domain", "generic_data_type", "necessity_status"))


def load_dataset_catalog(project_root: Path | str | None = None) -> DatasetCatalog:
    """Validate and inventory original tasks and their static permission items.

    Repeated participant rows are expected and collapse to unique contexts.
    Duplicate source IDs/items and contradictory or invented contexts fail.
    All three local sources must exist; missing data is never synthesized.
    """
    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[1]
    paths = {name: root / relative for name, relative in SOURCE_PATHS.items()}
    source_queries = json.loads(paths["queries"].read_text(encoding="utf-8-sig"))
    if not isinstance(source_queries, list) or not source_queries:
        raise ValueError("queries source must be a non-empty list")
    by_id: dict[int, Mapping[str, Any]] = {}
    raw_labels: set[str] = set()
    for row in source_queries:
        if not isinstance(row, dict):
            raise ValueError("query source row must be an object")
        query_id = _query_id(row.get("id"))
        if query_id in by_id:
            raise ValueError(f"duplicate query ID: {query_id}")
        _text(row.get("query"), "query")
        _text(row.get("domain"), "domain")
        for field in ("tool1", "tool2"):
            label = _text(row.get(field, ""), field, empty=True)
            if label.strip():
                raw_labels.add(label)
        by_id[query_id] = row

    # Normalized identities aid matching but never merge distinct raw labels.
    label_lookup: dict[str, str] = {}
    for label in sorted(raw_labels):
        normalized = normalize_text(label)
        if normalized in label_lookup and label_lookup[normalized] != label:
            raise ValueError("ambiguous normalized external tool labels")
        label_lookup[normalized] = label
    label_lookup["mira"] = "mira"
    aliases = {query_id: {row["query"]} for query_id, row in by_id.items()}
    contexts: dict[tuple[int, str, str], dict[str, Any]] = {}
    for row in _csv_rows(paths["processed_contexts"], CONTEXT_COLUMNS + ("query",)):
        key = _context_key(row)
        query_id, tool_key, _ = key
        if query_id not in by_id:
            raise ValueError(f"unknown query ID: {query_id}")
        query = by_id[query_id]
        if normalize_text(_text(row["query"], "query")) != normalize_text(query["query"]):
            raise ValueError(f"query text mismatch: {query_id}")
        aliases[query_id].add(row["query"])
        declared = {normalize_text(query.get(field, "")) for field in ("tool1", "tool2")} | {"mira"}
        if tool_key not in declared or tool_key not in label_lookup:
            raise ValueError(f"undeclared tool for query {query_id}: {row['tool']}")
        if normalize_text(row["domain"]) != normalize_text(query["domain"]):
            raise ValueError(f"query domain mismatch: {query_id}")
        if row["necessity_status"] not in {"necessary", "incorrect_explicit", "unknown"}:
            raise ValueError("invalid necessity_status")
        meta = _metadata(row)
        if key in contexts and contexts[key]["metadata"] != meta:
            raise ValueError(f"conflicting context metadata: {key}")
        if key not in contexts:
            contexts[key] = {"metadata": meta, "tool": label_lookup[tool_key],
                             "raw_data_type": row["raw_data_type"], "generic_data_type": row["generic_data_type"],
                             "necessity_status": row["necessity_status"], "tool_aliases": set(), "item_aliases": set()}
        contexts[key]["tool_aliases"].add(row["tool"])
        contexts[key]["item_aliases"].add(row["raw_data_type"])

    questionnaire_keys: set[tuple[int, str, str]] = set()
    questionnaire_ids: set[str] = set()
    for row in _csv_rows(paths["questionnaire"], CONTEXT_COLUMNS + ("questionnaire_item_id", "question_content")):
        key = _context_key(row)
        item_id = _text(row["questionnaire_item_id"], "questionnaire_item_id")
        if key in questionnaire_keys:
            raise ValueError(f"duplicate questionnaire context: {key}")
        if item_id in questionnaire_ids:
            raise ValueError(f"duplicate questionnaire item ID: {item_id}")
        questionnaire_keys.add(key)
        questionnaire_ids.add(item_id)
        if key not in contexts or contexts[key]["metadata"] != _metadata(row):
            raise ValueError(f"questionnaire context mismatch: {key}")
        expected_content = (f"User request: {by_id[key[0]]['query']}\nTool: {row['tool']}\n"
                            f"Data item requested: {row['raw_data_type']}")
        if normalize_text(row["question_content"]) != normalize_text(expected_content):
            raise ValueError(f"questionnaire query text mismatch: {key}")
        contexts[key]["questionnaire_item_id"] = item_id
        contexts[key]["tool_aliases"].add(row["tool"])
        contexts[key]["item_aliases"].add(row["raw_data_type"])
    if questionnaire_keys != set(contexts):
        raise ValueError("questionnaire context mismatch: missing source contexts")

    query_inventories = []
    for query_id in sorted(by_id):
        query = by_id[query_id]
        query_contexts = []
        for key in sorted(contexts):
            if key[0] != query_id:
                continue
            values = contexts[key]
            query_contexts.append(PermissionContext(query_id, values["tool"], values["raw_data_type"],
                values["generic_data_type"], values["necessity_status"], tuple(sorted(values["tool_aliases"])),
                tuple(sorted(values["item_aliases"])), values["questionnaire_item_id"]))
        has_mira = any(context.tool == "mira" for context in query_contexts) or any(
            query.get(field) for field in ("data_MIRA", "data_MIRA_incorrect"))
        oracle_path = root / "agent_mock_harness_v0/agent_runner.py"
        authored = query_id == 22 and query["query"] == Q22_TEXT and oracle_path.is_file()
        query_inventories.append(QueryInventory(query_id, query["query"], query["domain"],
            tuple(dict.fromkeys(query[field] for field in ("tool1", "tool2") if query.get(field))),
            ("mira",) if has_mira else (), deepcopy(query),
            {field: deepcopy(query.get(field, "")) for field in DATA_FIELDS}, tuple(sorted(aliases[query_id])),
            tuple(query_contexts), "authored_task_oracle" if authored else "catalogued",
            "agent_mock_harness_v0/agent_runner.py::run_report_episode" if authored else None))
    context_tools = {values["tool"] for values in contexts.values()}
    return DatasetCatalog(tuple(query_inventories), tuple(sorted(raw_labels)),
                          ("mira",) if any(query.internal_channels for query in query_inventories) else (),
                          tuple(sorted({query.domain for query in query_inventories})),
                          tuple(sorted(raw_labels - context_tools)),
                          {name: str(path.resolve()) for name, path in paths.items()})
