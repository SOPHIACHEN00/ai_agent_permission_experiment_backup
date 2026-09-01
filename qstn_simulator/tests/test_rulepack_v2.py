from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.v1.rulepack_v1 import QUESTION_PLACEHOLDER, load_rulepack
from scripts.v1_1.rulepack_v1_1 import load_v1_1_rulepack
from scripts.v2.build_memory_fixtures_v2 import build_fixtures
from scripts.v2.rulepack_v2 import (
    build_memory_view,
    directional_parent_view,
    inject_v2_context,
    load_v2_contract,
    load_v2_event_schema,
    load_v2_reason_codes,
    load_v2_retention_policy,
    load_v2_rulepack,
    load_v2_skill,
    load_v2_state_schema,
    render_v2_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
V1_0_DIR = PROJECT_ROOT / "config" / "v1.0"
V1_1_DIR = PROJECT_ROOT / "config" / "v1.1"
V2_DIR = PROJECT_ROOT / "config" / "v2.0"


class RulePackV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent_v1 = load_rulepack(V1_0_DIR / "security_behavior_rules.json")
        cls.parent_v1_1 = load_v1_1_rulepack(V1_1_DIR / "security_behavior_rules.json")
        cls.rulepack = load_v2_rulepack(V2_DIR / "security_behavior_rules.json")
        cls.event_schema = load_v2_event_schema(V2_DIR / "event_schema.json")
        cls.state_schema = load_v2_state_schema(V2_DIR / "state_schema.json")
        cls.retention_policy = load_v2_retention_policy(V2_DIR / "retention_policy.json")

    def test_assets_are_v2_and_english_only(self) -> None:
        self.assertEqual(self.rulepack["version"], "2.0.0")
        self.assertEqual(self.rulepack["state_schema_version"], "2.0.0")
        self.assertEqual(len(self.rulepack["state_rules"]), 5)
        for path in V2_DIR.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"[\u3400-\u9fff]", path.name)
        for path in (V2_DIR / "privacy_security_rule_skill.md", V2_DIR / "respondent_contract.en.md"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"[\u3400-\u9fff]")

    def test_v2_preserves_inherited_grouped_rules(self) -> None:
        self.assertEqual(self.parent_v1["rules"], self.parent_v1_1["rules"])
        self.assertEqual(self.parent_v1_1["rules"], self.rulepack["rules"])
        self.assertEqual(directional_parent_view(self.rulepack)["version"], "1.1.0")

    def test_v2_has_no_numeric_behavior_parameters(self) -> None:
        serialized = json.dumps(self.rulepack)
        for key in (
            "weight",
            "logit_delta",
            "probability",
            "coefficient",
            "confidence_threshold",
            "confidence_score",
        ):
            self.assertNotIn(f'"{key}"', serialized)

    def test_verified_scope_violation_updates_bounded_state(self) -> None:
        fixture = next(
            item for item in build_fixtures()["fixtures"] if item["fixture_id"] == "verified_scope_violation_visible"
        )
        store, memory_view, audits = build_memory_view(
            event_schema=self.event_schema,
            state_schema=self.state_schema,
            retention_policy=self.retention_policy,
            events=fixture["events"],
            subject_id=fixture["subject_id"],
            current_turn=fixture["current_turn"],
            memory_horizon_turns=fixture["memory_horizon_turns"],
            memory_horizon_source=fixture["memory_horizon_source"],
        )
        self.assertEqual(store.state_snapshot(fixture["subject_id"])["trust_integrity"], "caution")
        self.assertEqual(
            store.state_snapshot(fixture["subject_id"])["consent_status"], "refresh_required"
        )
        self.assertIn("verified_scope_violation", memory_view["visible_verified_event_types"])
        self.assertTrue(audits[0]["accepted_for_state"])

    def test_repair_is_recovery_not_full_reset(self) -> None:
        fixture = next(
            item for item in build_fixtures()["fixtures"] if item["fixture_id"] == "verified_repair_recovery"
        )
        store, memory_view, _ = build_memory_view(
            event_schema=self.event_schema,
            state_schema=self.state_schema,
            retention_policy=self.retention_policy,
            events=fixture["events"],
            subject_id=fixture["subject_id"],
            current_turn=fixture["current_turn"],
            memory_horizon_turns=fixture["memory_horizon_turns"],
            memory_horizon_source=fixture["memory_horizon_source"],
        )
        state = store.state_snapshot(fixture["subject_id"])
        self.assertEqual(state["trust_integrity"], "recovery")
        self.assertEqual(state["memory_caution"], "residual")
        self.assertIn("verified_agent_error", memory_view["visible_verified_event_types"])

    def test_unverified_event_and_ordinary_denial_do_not_create_trust_state(self) -> None:
        fixtures = build_fixtures()["fixtures"]
        for fixture_id in ("ordinary_denial_is_not_violation", "unverified_event_remains_unknown"):
            fixture = next(item for item in fixtures if item["fixture_id"] == fixture_id)
            store, _, audits = build_memory_view(
                event_schema=self.event_schema,
                state_schema=self.state_schema,
                retention_policy=self.retention_policy,
                events=fixture["events"],
                subject_id=fixture["subject_id"],
                current_turn=fixture["current_turn"],
                memory_horizon_turns=fixture["memory_horizon_turns"],
                memory_horizon_source=fixture["memory_horizon_source"],
            )
            state = store.state_snapshot(fixture["subject_id"])
            self.assertEqual(state["trust_integrity"], "unknown")
            joined = ";".join(audits[0]["reason_codes"])
            if fixture_id == "ordinary_denial_is_not_violation":
                self.assertIn("ORDINARY_DENIAL_NOT_VIOLATION", joined)
            else:
                self.assertIn("EVENT_UNVERIFIED_NO_STATE_UPDATE", joined)

    def test_recent_event_can_expire_without_implying_forgiveness(self) -> None:
        fixture = next(
            item for item in build_fixtures()["fixtures"] if item["fixture_id"] == "recent_event_expired_from_view"
        )
        store, memory_view, _ = build_memory_view(
            event_schema=self.event_schema,
            state_schema=self.state_schema,
            retention_policy=self.retention_policy,
            events=fixture["events"],
            subject_id=fixture["subject_id"],
            current_turn=fixture["current_turn"],
            memory_horizon_turns=fixture["memory_horizon_turns"],
            memory_horizon_source=fixture["memory_horizon_source"],
        )
        self.assertEqual(memory_view["visible_event_count_bucket"], "none")
        self.assertIn("permission_request_presented", memory_view["expired_event_types"])
        self.assertEqual(store.state_snapshot(fixture["subject_id"])["memory_caution"], "unknown")

    def test_v2_prompt_injection_keeps_question_placeholder(self) -> None:
        fixture = next(
            item for item in build_fixtures()["fixtures"] if item["fixture_id"] == "verified_scope_violation_visible"
        )
        _, memory_view, _ = build_memory_view(
            event_schema=self.event_schema,
            state_schema=self.state_schema,
            retention_policy=self.retention_policy,
            events=fixture["events"],
            subject_id=fixture["subject_id"],
            current_turn=fixture["current_turn"],
            memory_horizon_turns=fixture["memory_horizon_turns"],
            memory_horizon_source=fixture["memory_horizon_source"],
        )
        rendered, _, _ = render_v2_rule_context(
            self.rulepack,
            {"profile_id": "broad_restrictors", "necessity_status": "unknown"},
            memory_view,
        )
        injected = inject_v2_context(
            "Profile text.\n\nPermission scenario:\n" + QUESTION_PLACEHOLDER,
            load_v2_contract(V2_DIR / "respondent_contract.en.md"),
            rendered,
            skill_text=load_v2_skill(V2_DIR / "privacy_security_rule_skill.md"),
            skill_mode="full_catalog_with_active_excerpt",
        )
        self.assertEqual(injected.count(QUESTION_PLACEHOLDER), 1)
        self.assertIn("Respondent contract v2.0", injected)
        self.assertIn("RulePack 2.0 bounded memory", injected)
        self.assertIn("Cao-R1", injected)
        self.assertNotIn("event_scope_violation_1", injected)

    def test_synthetic_mode_is_explicitly_separate(self) -> None:
        rendered, _, _ = render_v2_rule_context(
            self.rulepack,
            {"profile_id": "broad_restrictors", "necessity_status": "unknown"},
            {"state_snapshot": {}, "visible_verified_event_types": []},
            behavior_mode="synthetic_exploratory",
        )
        self.assertIn("v2.0 behavior_mode=synthetic_exploratory", rendered)
        self.assertIn("Exploratory guardrail", rendered)


if __name__ == "__main__":
    unittest.main()
