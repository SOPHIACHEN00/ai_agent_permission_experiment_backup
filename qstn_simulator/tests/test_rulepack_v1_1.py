from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.v1_1.build_context_v1_1 import build_sidecar
from scripts.v1_1.compile_s_qstn_v1_1 import validate_context
from scripts.v1.rulepack_v1 import QUESTION_PLACEHOLDER, load_rulepack
from scripts.v1_1.rulepack_v1_1 import (
    BURDEN_BUCKETS,
    assert_grouped_rules_unchanged,
    build_context_record,
    derive_burden_bucket,
    derive_reason_codes,
    derive_uncertainty_bucket,
    evaluate_audit_rules,
    inject_v1_1_context,
    load_context_schema,
    load_reason_codes,
    load_skill,
    load_v1_1_contract,
    load_v1_1_rulepack,
    render_v1_1_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
V1_0_DIR = PROJECT_ROOT / "config" / "v1.0"
V1_1_DIR = PROJECT_ROOT / "config" / "v1.1"
V1_0_RULEPACK = V1_0_DIR / "security_behavior_rules.json"
V1_1_RULEPACK = V1_1_DIR / "security_behavior_rules.json"
V1_1_SCHEMA = V1_1_DIR / "context_schema.json"
V1_1_REASON_CODES = V1_1_DIR / "reason_codes.json"
V1_1_CONTRACT = V1_1_DIR / "respondent_contract.en.md"
V1_1_SKILL = V1_1_DIR / "privacy_security_rule_skill.md"


class RulePackV1_1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = load_rulepack(V1_0_RULEPACK)
        cls.rulepack = load_v1_1_rulepack(V1_1_RULEPACK)
        cls.schema = load_context_schema(V1_1_SCHEMA)
        cls.reason_codes = load_reason_codes(V1_1_REASON_CODES)

    def test_assets_are_versioned_and_english_only(self) -> None:
        self.assertEqual(self.rulepack["version"], "1.1.0")
        self.assertEqual(self.schema["version"], "1.1.0")
        self.assertEqual(self.reason_codes["version"], "1.1.0")
        for path in (V1_1_RULEPACK, V1_1_SCHEMA, V1_1_REASON_CODES, V1_1_CONTRACT, V1_1_SKILL):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"[\u3400-\u9fff]")

    def test_grouped_rules_are_unchanged_from_v1_0(self) -> None:
        assert_grouped_rules_unchanged(self.parent, self.rulepack)
        self.assertEqual(len(self.rulepack["rules"]), 6)
        self.assertEqual(len(self.rulepack["audit_rules"]), 2)

    def test_no_numeric_behavior_keys_are_present(self) -> None:
        serialized = json.dumps(self.rulepack)
        for key in ("weight", "logit_delta", "probability", "coefficient", "confidence_threshold"):
            self.assertNotIn(f'"{key}"', serialized)
        self.assertFalse(self.reason_codes["numeric_behavior_parameters"])

    def test_uncertainty_buckets_use_field_completeness(self) -> None:
        source = {
            "questionnaire_item_id": "q1",
            "query_id": "query_1",
            "domain": "health",
            "tool": "calendar",
            "raw_data_type": "appointment",
            "generic_data_type": "health",
            "necessity_status": "necessary",
        }
        medium = build_context_record(source)
        self.assertEqual(medium["uncertainty_bucket"], "medium")
        self.assertEqual(derive_burden_bucket(medium), "not_applicable_single_item")

        high = build_context_record({**source, "raw_data_type": None, "necessity_status": "unknown"})
        self.assertEqual(high["uncertainty_bucket"], "high")

        explicit = {
            "requester_id": "app",
            "requester_visibility": "visible",
            "foreground_task": "schedule an appointment",
            "purpose_status": "explicit",
            "expectedness": "expected",
            "expectation_match": True,
            "scope": "foreground_only",
            "duration": "one_time",
            "scope_explicit": True,
            "duration_explicit": True,
            "revocable": True,
            "review_available": True,
            "required_vs_optional": "optional",
            "consequence_of_decline": "none",
            "explanation_present": True,
            "explanation_timing": "just_in_time",
            "provenance_present": True,
            "explanation_source": "app",
            "explanation_readability": "readable",
            "prompt_burden_signal": "medium",
            "prompt_burden_bucket": "medium_explicit",
            "burden_basis": "explicit_annotation",
        }
        low = build_context_record(source, explicit_values=explicit)
        self.assertEqual(low["uncertainty_bucket"], "low")
        self.assertEqual(low["prompt_burden_bucket"], "medium_explicit")

    def test_question_text_does_not_infer_context_or_burden(self) -> None:
        source = {
            "questionnaire_item_id": "q2",
            "query_id": "query_2",
            "domain": "health",
            "tool": "calendar",
            "raw_data_type": "appointment",
            "generic_data_type": "health",
            "necessity_status": "necessary",
            "question_content": "This is a repeated persistent background request and feels exhausting.",
        }
        record = build_context_record(source)
        self.assertEqual(record["prompt_burden_bucket"], "not_applicable_single_item")
        self.assertEqual(record["uncertainty_bucket"], "medium")
        self.assertEqual(record["expectedness"], "unknown")
        self.assertEqual(record["scope"], "unknown")

    def test_reason_codes_are_deterministic_and_non_private(self) -> None:
        source = {
            "questionnaire_item_id": "q3",
            "query_id": "query_3",
            "domain": "finance",
            "tool": "budget",
            "raw_data_type": "transaction",
            "generic_data_type": "financial",
            "necessity_status": "incorrect_explicit",
            "profile_id": "broad_restrictors",
        }
        context = build_context_record(source)
        codes = derive_reason_codes(context)
        self.assertEqual(codes, derive_reason_codes(context))
        self.assertIn("NECESSITY_INCORRECT_EXPLICIT", codes)
        self.assertIn("PROFILE_PRIOR_APPLIED", codes)
        self.assertNotIn("agent_violation", ";".join(codes))

    def test_audit_rules_have_no_effects(self) -> None:
        context = build_context_record(
            {
                "questionnaire_item_id": "q4",
                "query_id": "query_4",
                "domain": "general",
                "tool": "notes",
                "raw_data_type": "note",
                "generic_data_type": "text",
                "necessity_status": "necessary",
            }
        )
        audits = evaluate_audit_rules(self.rulepack, context)
        self.assertEqual({item["rule_id"] for item in audits}, {
            "AUDIT.context_completeness",
            "AUDIT.current_turn_prompt_burden",
        })
        self.assertTrue(all(item["effects"] == [] for item in audits))

    def test_exploratory_mode_is_separate_from_audit_compatible(self) -> None:
        context = build_context_record(
            {
                "questionnaire_item_id": "q5",
                "query_id": None,
                "domain": "general",
                "tool": None,
                "raw_data_type": None,
                "generic_data_type": None,
                "necessity_status": "unknown",
            }
        )
        audit_text, _, _ = render_v1_1_rule_context(
            self.rulepack, context, behavior_mode="audit_compatible"
        )
        exploratory_text, _, _ = render_v1_1_rule_context(
            self.rulepack, context, behavior_mode="qualitative_exploratory"
        )
        self.assertNotIn("Exploratory guardrail", audit_text)
        self.assertIn("Exploratory guardrail", exploratory_text)

    def test_prompt_injection_preserves_placeholder(self) -> None:
        contract = load_v1_1_contract(V1_1_CONTRACT)
        skill = load_skill(V1_1_SKILL)
        rendered, _, _ = render_v1_1_rule_context(
            self.rulepack,
            {
                "profile_id": "broad_restrictors",
                "necessity_status": "unknown",
                "raw_data_type": "location",
                "tool": "maps",
            },
        )
        base = "Profile text.\n\nPermission scenario:\n" + QUESTION_PLACEHOLDER
        prompt = inject_v1_1_context(
            base,
            contract,
            rendered,
            skill_text=skill,
            skill_mode="full_catalog_with_active_excerpt",
        )
        self.assertEqual(prompt.count(QUESTION_PLACEHOLDER), 1)
        self.assertIn("Respondent contract v1.1", prompt)
        self.assertIn("Full privacy and security rule skill catalog v1.1", prompt)
        self.assertIn("Cao-R1", prompt)

    def test_sidecar_is_one_to_one_and_excludes_targets(self) -> None:
        import pandas as pd

        questionnaire = pd.DataFrame(
            [
                {
                    "questionnaire_item_id": "q1",
                    "query_id": "query_1",
                    "domain": "general",
                    "tool": "notes",
                    "raw_data_type": "note",
                    "generic_data_type": "text",
                    "necessity_status": "necessary",
                },
                {
                    "questionnaire_item_id": "q2",
                    "query_id": "query_2",
                    "domain": "general",
                    "tool": "notes",
                    "raw_data_type": "note",
                    "generic_data_type": "text",
                    "necessity_status": "unknown",
                },
            ]
        )
        sidecar = build_sidecar(questionnaire)
        validate_context(sidecar)
        self.assertEqual(len(sidecar), len(questionnaire))
        self.assertEqual(set(sidecar["questionnaire_item_id"]), {"q1", "q2"})
        self.assertNotIn("label_id", sidecar.columns)
        self.assertTrue(
            (sidecar["prompt_burden_bucket"] == "not_applicable_single_item").all()
        )


if __name__ == "__main__":
    unittest.main()
