"""Compile S-QSTN v2.0 prompts and bounded-memory diagnostics offline.

The compiler combines the inherited v1.1 current-turn context with one explicit
label-free memory fixture. It never reads or joins human answer labels. The
fixture is an engineering diagnostic and must not be reported as a human
calibration result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from scripts.v1.compile_s_qstn_v1 import (
    QUESTION_PLACEHOLDER,
    RULEPACK_CONTEXT_PLACEHOLDER,
    add_rulepack_placeholder,
    validate_inputs,
)
from scripts.v1_1.compile_s_qstn_v1_1 import validate_context
from scripts.v1_1.rulepack_v1_1 import normalize_context_v1_1
from scripts.v2.build_memory_fixtures_v2 import build_fixtures
from scripts.v2.rulepack_v2 import (
    SUPPORTED_SKILL_MODES,
    V2_BEHAVIOR_MODES,
    build_memory_view,
    load_v2_context_schema,
    load_v2_contract,
    load_v2_event_schema,
    load_v2_reason_codes,
    load_v2_retention_policy,
    load_v2_rulepack,
    load_v2_skill,
    load_v2_state_schema,
    render_v2_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PERSONAS = PROJECT_ROOT / "outputs" / "empirical_personas_v2" / "personas_with_empirical_profiles.csv"
DEFAULT_QUESTIONNAIRE = PROJECT_ROOT / "outputs" / "questionnaire_items.csv"
DEFAULT_CONTEXT = PROJECT_ROOT / "outputs" / "questionnaire_context_v1.1.csv"
DEFAULT_RULEPACK = PROJECT_ROOT / "config" / "v2.0" / "security_behavior_rules.json"
DEFAULT_CONTRACT = PROJECT_ROOT / "config" / "v2.0" / "respondent_contract.en.md"
DEFAULT_SKILL = PROJECT_ROOT / "config" / "v2.0" / "privacy_security_rule_skill.md"
DEFAULT_SCHEMA = PROJECT_ROOT / "config" / "v2.0" / "context_schema.json"
DEFAULT_EVENT_SCHEMA = PROJECT_ROOT / "config" / "v2.0" / "event_schema.json"
DEFAULT_STATE_SCHEMA = PROJECT_ROOT / "config" / "v2.0" / "state_schema.json"
DEFAULT_RETENTION_POLICY = PROJECT_ROOT / "config" / "v2.0" / "retention_policy.json"
DEFAULT_REASON_CODES = PROJECT_ROOT / "config" / "v2.0" / "reason_codes.json"
DEFAULT_FIXTURES = PROJECT_ROOT / "outputs" / "s_qstn_v2" / "memory_fixtures_v2.json"
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "s_qstn_v2"
TARGET_COLUMNS = {"label_id", "label_text", "task3"}
AUDIT_COLUMNS = [
    "profile_id",
    "questionnaire_item_id",
    "rule_pack_version",
    "behavior_mode",
    "memory_fixture_id",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
    "uncertainty_bucket",
    "prompt_burden_bucket",
    "unknown_context_fields",
    "unknown_context_categories",
    "reason_codes",
    "active_rule_ids",
    "unknown_rule_ids",
    "inactive_rule_ids",
    "audit_evaluations_json",
    "transition_audit_json",
    "memory_view_json",
    "state_snapshot_json",
    "rendered_rule_context",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS)
    parser.add_argument("--questionnaire", type=Path, default=DEFAULT_QUESTIONNAIRE)
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--rulepack", type=Path, default=DEFAULT_RULEPACK)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--event-schema", type=Path, default=DEFAULT_EVENT_SCHEMA)
    parser.add_argument("--state-schema", type=Path, default=DEFAULT_STATE_SCHEMA)
    parser.add_argument("--retention-policy", type=Path, default=DEFAULT_RETENTION_POLICY)
    parser.add_argument("--reason-codes", type=Path, default=DEFAULT_REASON_CODES)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument(
        "--fixture-id",
        default="verified_scope_violation_visible",
        help="Label-free memory fixture used for the compiled diagnostic context.",
    )
    parser.add_argument(
        "--behavior-mode",
        choices=sorted(V2_BEHAVIOR_MODES),
        default="stateful_audit_compatible",
    )
    parser.add_argument(
        "--skill-mode",
        choices=sorted(SUPPORTED_SKILL_MODES),
        default="active_excerpt",
    )
    parser.add_argument("--contract-version", default="respondent_contract_v2.0.en")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_fixture_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Memory fixture file is missing: {path}. Run build_memory_fixtures_v2.py first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != "2.0.0":
        raise ValueError("Memory fixture file must be a v2.0.0 object.")
    if TARGET_COLUMNS.intersection(payload):
        raise ValueError("Memory fixture file contains forbidden target columns.")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("Memory fixture file must contain at least one fixture.")
    return payload


def select_fixture(payload: Mapping[str, Any], fixture_id: str) -> dict[str, Any]:
    fixtures = [item for item in payload["fixtures"] if str(item.get("fixture_id")) == fixture_id]
    if len(fixtures) != 1:
        available = sorted(str(item.get("fixture_id")) for item in payload["fixtures"])
        raise ValueError(f"Expected one fixture {fixture_id!r}; available fixtures: {available}")
    return dict(fixtures[0])


def context_lookup(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        str(row["questionnaire_item_id"]): {
            key: value for key, value in row.items() if key != "questionnaire_item_id"
        }
        for row in frame.to_dict(orient="records")
    }


def context_for_question(
    question: Mapping[str, Any],
    profile_id: str,
    sidecar: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    item_id = str(question["questionnaire_item_id"])
    context = dict(sidecar.get(item_id, {}))
    for field in (
        "questionnaire_item_id",
        "query_id",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
    ):
        context.setdefault(field, question.get(field, "unknown"))
    context["questionnaire_item_id"] = item_id
    context["profile_id"] = profile_id
    return normalize_context_v1_1(context)


def make_memory_diagnostic(
    fixture: Mapping[str, Any],
    event_schema: Mapping[str, Any],
    state_schema: Mapping[str, Any],
    retention_policy: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, memory_view, transition_audit = build_memory_view(
        event_schema=event_schema,
        state_schema=state_schema,
        retention_policy=retention_policy,
        events=list(fixture.get("events", [])),
        subject_id=str(fixture["subject_id"]),
        current_turn=int(fixture["current_turn"]),
        memory_horizon_turns=(
            int(fixture["memory_horizon_turns"])
            if fixture.get("memory_horizon_turns") is not None
            else None
        ),
        memory_horizon_source=str(fixture.get("memory_horizon_source", "unknown")),
    )
    return memory_view, transition_audit


def make_audit_rows(
    personas: pd.DataFrame,
    questionnaire: pd.DataFrame,
    context_frame: pd.DataFrame,
    rulepack: Mapping[str, Any],
    memory_view: Mapping[str, Any],
    transition_audit: list[Mapping[str, Any]],
    fixture_id: str,
    behavior_mode: str,
) -> pd.DataFrame:
    sidecar = context_lookup(context_frame)
    profile_ids = sorted(personas["profile_id"].astype(str).unique())
    rows: list[dict[str, Any]] = []
    for question in questionnaire.to_dict(orient="records"):
        for profile_id in profile_ids:
            context = context_for_question(question, profile_id, sidecar)
            rendered, evaluations, audit_evaluations = render_v2_rule_context(
                rulepack,
                context,
                memory_view,
                behavior_mode=behavior_mode,
            )
            active = [item for item in evaluations if item.status == "active"]
            unknown = [item for item in evaluations if item.status == "unknown"]
            inactive = [item for item in evaluations if item.status == "inactive"]
            rows.append(
                {
                    "profile_id": profile_id,
                    "questionnaire_item_id": str(question["questionnaire_item_id"]),
                    "rule_pack_version": str(rulepack["version"]),
                    "behavior_mode": behavior_mode,
                    "memory_fixture_id": fixture_id,
                    "query_id": question.get("query_id", ""),
                    "domain": question.get("domain", ""),
                    "tool": question.get("tool", ""),
                    "raw_data_type": question.get("raw_data_type", ""),
                    "generic_data_type": question.get("generic_data_type", ""),
                    "necessity_status": question.get("necessity_status", "unknown"),
                    "uncertainty_bucket": context.get("uncertainty_bucket", "unknown"),
                    "prompt_burden_bucket": context.get("prompt_burden_bucket", "unknown"),
                    "unknown_context_fields": ";".join(
                        map(str, context.get("unknown_context_fields", []))
                    ),
                    "unknown_context_categories": ";".join(
                        map(str, context.get("unknown_context_categories", []))
                    ),
                    "reason_codes": ";".join(map(str, context.get("reason_codes", []))),
                    "active_rule_ids": ";".join(item.rule_id for item in active),
                    "unknown_rule_ids": ";".join(item.rule_id for item in unknown),
                    "inactive_rule_ids": ";".join(item.rule_id for item in inactive),
                    "audit_evaluations_json": json.dumps(
                        audit_evaluations, ensure_ascii=False, sort_keys=True
                    ),
                    "transition_audit_json": json.dumps(
                        transition_audit, ensure_ascii=False, sort_keys=True
                    ),
                    "memory_view_json": json.dumps(
                        memory_view, ensure_ascii=False, sort_keys=True
                    ),
                    "state_snapshot_json": json.dumps(
                        memory_view.get("state_snapshot", {}), ensure_ascii=False, sort_keys=True
                    ),
                    "rendered_rule_context": rendered,
                }
            )
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def make_persona_templates(
    personas: pd.DataFrame,
    rulepack: Mapping[str, Any],
    contract_version: str,
    skill_mode: str,
) -> pd.DataFrame:
    output = personas.copy()
    output["rule_pack_version"] = str(rulepack["version"])
    output["respondent_contract_version"] = contract_version
    output["skill_catalog_version"] = str(rulepack.get("skill_catalog_version", "2.0.0"))
    output["skill_mode"] = skill_mode
    output["prompt_compilation_mode"] = "per_question_bounded_memory_context"
    output["rulepack_context_placeholder"] = RULEPACK_CONTEXT_PLACEHOLDER
    output["questionnaire_instruction_template"] = output[
        "questionnaire_instruction"
    ].map(add_rulepack_placeholder)
    return output


def main() -> None:
    args = parse_args()
    personas = pd.read_csv(args.personas)
    questionnaire = pd.read_csv(args.questionnaire)
    context_frame = pd.read_csv(args.context)
    validate_inputs(personas, questionnaire)
    validate_context(context_frame)
    rulepack = load_v2_rulepack(args.rulepack)
    load_v2_context_schema(args.schema)
    event_schema = load_v2_event_schema(args.event_schema)
    state_schema = load_v2_state_schema(args.state_schema)
    retention_policy = load_v2_retention_policy(args.retention_policy)
    reason_codes = load_v2_reason_codes(args.reason_codes)
    contract = load_v2_contract(args.contract)
    skill = load_v2_skill(args.skill)
    if not contract or not skill or not reason_codes.get("codes"):
        raise ValueError("v2 contract, skill, and reason-code assets must be non-empty.")
    fixture_payload = load_fixture_payload(args.fixtures)
    fixture = select_fixture(fixture_payload, args.fixture_id)
    memory_view, transition_audit = make_memory_diagnostic(
        fixture, event_schema, state_schema, retention_policy
    )
    audit = make_audit_rows(
        personas,
        questionnaire,
        context_frame,
        rulepack,
        memory_view,
        transition_audit,
        str(fixture["fixture_id"]),
        args.behavior_mode,
    )
    templates = make_persona_templates(
        personas, rulepack, args.contract_version, args.skill_mode
    )
    args.out.mkdir(parents=True, exist_ok=True)
    templates.to_csv(args.out / "s_qstn_personas.csv", index=False, encoding="utf-8")
    audit.to_csv(args.out / "rule_context_audit.csv", index=False, encoding="utf-8")
    diagnostic = {
        "fixture_id": fixture["fixture_id"],
        "subject_id": fixture["subject_id"],
        "current_turn": fixture["current_turn"],
        "memory_view": memory_view,
        "transition_audit": transition_audit,
        "human_calibration": "not_claimed",
    }
    (args.out / "memory_diagnostic.json").write_text(
        json.dumps(diagnostic, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest = {
        "status": "compiled",
        "api_called": False,
        "purpose": "offline v2 bounded-memory prompt and transition diagnostic",
        "rule_pack_id": rulepack["rule_pack_id"],
        "rule_pack_version": rulepack["version"],
        "parent_rule_pack_version": rulepack["parent_rule_pack_version"],
        "respondent_contract_version": args.contract_version,
        "skill_catalog_version": rulepack.get("skill_catalog_version", "2.0.0"),
        "skill_mode": args.skill_mode,
        "behavior_mode": args.behavior_mode,
        "state_schema_version": rulepack["state_schema_version"],
        "calibration_status": rulepack["calibration_status"],
        "memory_fixture_id": fixture["fixture_id"],
        "human_calibration": "not_claimed",
        "source_principle_count": int(rulepack.get("source_principle_count", 12)),
        "source_concrete_rule_count": int(rulepack.get("source_concrete_rule_count", 56)),
        "personas": int(len(templates)),
        "profiles": sorted(templates["profile_id"].astype(str).unique()),
        "questionnaire_items": int(len(questionnaire)),
        "rule_context_rows": int(len(audit)),
        "target_answer_columns_absent": True,
        "numeric_behavior_parameters": False,
        "input_hashes": {
            "personas": sha256_file(args.personas),
            "questionnaire": sha256_file(args.questionnaire),
            "context": sha256_file(args.context),
            "rulepack": sha256_file(args.rulepack),
            "contract": sha256_file(args.contract),
            "skill_catalog": sha256_file(args.skill),
            "event_schema": sha256_file(args.event_schema),
            "state_schema": sha256_file(args.state_schema),
            "retention_policy": sha256_file(args.retention_policy),
            "reason_codes": sha256_file(args.reason_codes),
            "fixtures": sha256_file(args.fixtures),
        },
    }
    (args.out / "s_qstn_v2_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
