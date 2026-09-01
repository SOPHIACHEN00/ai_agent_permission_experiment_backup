from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from scripts.v1.rulepack_v1 import (
    QUESTION_PLACEHOLDER,
    add_rulepack_placeholder,
    evaluate_rule_pack,
    inject_rulepack_context,
    load_contract,
    load_rulepack,
    load_skill,
    render_rule_context,
    validate_rulepack,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULEPACK_PATH = PROJECT_ROOT / "config" / "v1.0" / "security_behavior_rules.json"
CONTRACT_PATH = PROJECT_ROOT / "config" / "v1.0" / "respondent_contract.md"
ENGLISH_CONTRACT_PATH = PROJECT_ROOT / "config" / "v1.0" / "respondent_contract.en.md"
SKILL_PATH = PROJECT_ROOT / "config" / "v1.0" / "privacy_security_rule_skill.md"


class RulePackV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rulepack = load_rulepack(RULEPACK_PATH)

    def test_v1_rulepack_is_directional_and_stateless(self) -> None:
        self.assertEqual(self.rulepack["version"], "1.0.0")
        self.assertEqual(self.rulepack["source_principle_count"], 12)
        self.assertEqual(self.rulepack["source_concrete_rule_count"], 56)
        self.assertEqual(self.rulepack["calibration_status"], "directional_only")
        self.assertEqual(self.rulepack["state_schema_version"], "none")
        self.assertTrue(all(rule["state_updates"] == [] for rule in self.rulepack["rules"]))

    def test_necessity_profile_and_context_rules_activate(self) -> None:
        evaluations = evaluate_rule_pack(
            self.rulepack,
            {
                "profile_id": "persistent_granters",
                "tool": "Travel Booking",
                "raw_data_type": "Trip location",
                "necessity_status": "necessary",
            },
        )
        active = {
            evaluation.rule_id: evaluation
            for evaluation in evaluations
            if evaluation.status == "active"
        }
        self.assertEqual(
            set(active),
            {
                "P9.necessity_and_privacy_calculus",
                "P10.stable_privacy_trait",
                "P11.context_dependency",
            },
        )
        self.assertEqual(
            active["P9.necessity_and_privacy_calculus"].effects,
            ({"target": "current_task_specific_sharing", "direction": "prefer"},),
        )

    def test_explicit_expectation_mismatch_activates_p4(self) -> None:
        rendered, evaluations = render_rule_context(
            self.rulepack,
            {
                "profile_id": "reconsent_seekers",
                "expectedness": "unexpected",
                "necessity_status": "unknown",
            },
        )
        active_ids = {
            evaluation.rule_id
            for evaluation in evaluations
            if evaluation.status == "active"
        }
        self.assertIn("P4.expectation_mismatch", active_ids)
        self.assertIn("ask_for_explanation=prefer", rendered)
        self.assertIn("persistent_grant=avoid", rendered)

    def test_explicit_control_and_transparency_activate_p5_and_p6(self) -> None:
        _, evaluations = render_rule_context(
            self.rulepack,
            {
                "profile_id": "reconsent_seekers",
                "necessity_status": "necessary",
                "scope_explicit": True,
                "revocable": True,
                "explanation_present": True,
            },
        )
        active_ids = {
            evaluation.rule_id
            for evaluation in evaluations
            if evaluation.status == "active"
        }
        self.assertIn("P5.perceived_control", active_ids)
        self.assertIn("P6.transparency_calibration", active_ids)

    def test_unknown_fields_are_not_inferred(self) -> None:
        evaluations = evaluate_rule_pack(
            self.rulepack,
            {"profile_id": "broad_restrictors", "necessity_status": "unknown"},
        )
        expectation = next(
            item for item in evaluations if item.rule_id == "P4.expectation_mismatch"
        )
        self.assertEqual(expectation.status, "unknown")
        self.assertIn("expectedness", expectation.unknown_fields)
        self.assertIn("expectation_match", expectation.unknown_fields)

    def test_v1_rejects_numeric_effects(self) -> None:
        invalid = deepcopy(self.rulepack)
        invalid["rules"][0]["effects"][0]["weight"] = 0.5
        with self.assertRaisesRegex(ValueError, "numeric keys"):
            validate_rulepack(invalid)

    def test_prompt_injection_preserves_qstn_placeholder(self) -> None:
        contract = load_contract(CONTRACT_PATH)
        base = "Profile text.\n\nPermission scenario:\n" + QUESTION_PLACEHOLDER
        rendered, _ = render_rule_context(
            self.rulepack,
            {"profile_id": "broad_restrictors", "necessity_status": "incorrect_explicit"},
        )
        injected = inject_rulepack_context(base, contract, rendered)
        self.assertEqual(injected.count(QUESTION_PLACEHOLDER), 1)
        self.assertIn("Respondent contract v1.0", injected)
        self.assertIn("P9.necessity_and_privacy_calculus", injected)

    def test_skill_catalog_is_english_and_complete(self) -> None:
        skill = load_skill(SKILL_PATH)
        self.assertIn("Cao-R1", skill)
        self.assertIn("Esterwood-R8", skill)
        self.assertNotRegex(skill, r"[\u3400-\u9fff]")

    def test_full_skill_mode_exposes_catalog_without_changing_placeholder(self) -> None:
        contract = load_contract(ENGLISH_CONTRACT_PATH)
        base = "Profile text.\n\nPermission scenario:\n" + QUESTION_PLACEHOLDER
        rendered, _ = render_rule_context(
            self.rulepack,
            {"profile_id": "broad_restrictors", "necessity_status": "unknown"},
        )
        injected = inject_rulepack_context(
            base,
            contract,
            rendered,
            skill_text=load_skill(SKILL_PATH),
            skill_mode="full_catalog_with_active_excerpt",
        )
        self.assertEqual(injected.count(QUESTION_PLACEHOLDER), 1)
        self.assertIn("Full privacy and security rule skill catalog", injected)
        self.assertIn("Cao-R1", injected)

    def test_offline_template_uses_private_placeholder(self) -> None:
        template = add_rulepack_placeholder(
            "Profile text.\n\nPermission scenario:\n" + QUESTION_PLACEHOLDER
        )
        self.assertIn("{{RULEPACK_CONTEXT_PLACEHOLDER}}", template)
        self.assertEqual(template.count(QUESTION_PLACEHOLDER), 1)


if __name__ == "__main__":
    unittest.main()
