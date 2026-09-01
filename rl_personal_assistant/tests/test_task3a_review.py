"""Regression tests for the Task 3A independent-review findings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from pa_rl.contracts import ActionCandidate, AuthorizationStatus, ControllerAction, PermissionChoice, Scope, canonical_hash
from pa_rl.policy_interface import CandidateCatalog, EnvironmentObservation, PublicMaskState, build_action_mask, build_environment_observation, make_resolved_candidate
from pa_rl.public_events import PublicEventChain, PublicEventChainError, PublicEventRecord, verify_public_event_chain
from pa_rl.scenarios import load_scenario, project_public_observation
from pa_rl.scripted_user import ScriptedUserAdapter, ScriptedUserInputError


ROOT = Path(__file__).resolve().parents[1]
AUTH = "authorization_" + "a" * 20
PRIOR = "authorization_" + "b" * 20


def scope() -> Scope:
    return Scope("productivity", "calendar_api", "calendar.events", ("title",), "read", "agenda", "local_user", "session")


def resolved(action: ControllerAction, **values: object):
    base = ActionCandidate("candidate_" + canonical_hash({"action": action.value, "scope": scope()})[:16], action, scope())
    bindings: dict[str, object] = {"base_candidate": base, "task_step_id": None, "authorization_id": None, "prior_authorization_id": None, "public_reason_code": None, "escalation_target_code": None}
    if action is ControllerAction.REQUEST_AUTHORIZATION:
        bindings["task_step_id"] = "step"
    if action is ControllerAction.REQUEST_REFRESH:
        bindings.update(task_step_id="step", prior_authorization_id=PRIOR)
    if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
        bindings.update(task_step_id="step", authorization_id=AUTH)
    if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
        bindings["authorization_id"] = AUTH
    if action is ControllerAction.DENY_WITH_REASON:
        bindings["public_reason_code"] = "not_needed"
    if action is ControllerAction.ESCALATE:
        bindings["escalation_target_code"] = "human_owner"
    bindings.update(values)
    return make_resolved_candidate(**bindings)  # type: ignore[arg-type]


def task_view(*, finished: bool = False) -> dict[str, object]:
    return {"phase": "finished" if finished else "open", "next_required_step_id": None if finished else "step", "next_required_scope_identity": None if finished else "scope_" + "0" * 16, "remaining_step_count": 0 if finished else 1, "primary_complete": finished, "has_unknown_effect": False, "last_public_execution_result_code": None}


def auth_view(status: str, relation: str, uses: int | None, expiry: int = 4) -> dict[str, object]:
    return {"status": status, "grant_type": "reusable" if uses is None else "one_time", "remaining_uses": uses, "expiry_bucket": "future", "expiry_step": expiry, "scope_relation": relation, "last_public_authority_event_id": None, "reask_relation": None}


def canonical_record(sequence: int, previous_event_hash: str | None) -> PublicEventRecord:
    logical_step = 1
    event_type = "verified_error"
    payload = {"error_code": "e"}
    payload_hash = canonical_hash(payload)
    event_id = "public_event_" + canonical_hash({"sequence": sequence, "logical_step": logical_step, "event_type": event_type, "payload_hash": payload_hash, "previous_event_hash": previous_event_hash})[:16]
    event_hash = canonical_hash({"sequence": sequence, "event_id": event_id, "logical_step": logical_step, "event_type": event_type, "payload_hash": payload_hash, "previous_event_hash": previous_event_hash})
    return PublicEventRecord(sequence, event_id, logical_step, event_type, payload, payload_hash, previous_event_hash, event_hash)


class AdapterProjectionRegressionTests(unittest.TestCase):
    def test_adapter_resets_from_real_nonempty_visibility_projection(self) -> None:
        manifest = load_scenario(ROOT / "fixtures" / "scenarios" / "01_one_time_grant_success.json")
        adapter = ScriptedUserAdapter(manifest.scripted_permission_responses)
        adapter.reset(project_public_observation(manifest), 9)

    def test_permission_request_has_exact_request_or_refresh_schema_before_consumption(self) -> None:
        manifest = load_scenario(ROOT / "fixtures" / "scenarios" / "01_one_time_grant_success.json")
        adapter = ScriptedUserAdapter((PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE))
        adapter.reset(project_public_observation(manifest), 9)
        base = {"request_id": "permission_request_" + "a" * 16, "scope_identity": "scope_" + "b" * 16, "logical_step": 1, "request_kind": "request"}
        attacks = (
            {**base, "request_id": 7}, {**base, "scope_identity": ("scope",)}, {**base, "logical_step": True},
            {**base, "logical_step": 0}, {**base, "request_kind": "oracle"}, {**base, "authorization_id": AUTH},
            {**base, "request_kind": "refresh"}, {**base, "request_kind": "refresh", "authorization_id": "bad"},
        )
        for attack in attacks:
            with self.subTest(attack=attack):
                with self.assertRaises(ScriptedUserInputError):
                    adapter.answer_permission(attack, ())
        self.assertEqual(adapter.answer_permission(base, ()), PermissionChoice.ALLOW_ONCE)
        refresh = {**base, "request_kind": "refresh", "authorization_id": AUTH}
        self.assertEqual(adapter.answer_permission(refresh, ()), PermissionChoice.ALLOW_ONCE)


class MaskSemanticRegressionTests(unittest.TestCase):
    def test_execute_honors_exact_and_narrower_and_reusable_none_but_not_broader_or_disjoint(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.EXECUTE_WITH_AUTHORIZATION), resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        for relation, expected in (("exact", True), ("narrower", True), ("broader", False), ("disjoint", False)):
            with self.subTest(relation=relation):
                state = PublicMaskState(1, task_view=task_view(), authorization_views={AUTH: auth_view("active", relation, None)}, preference_relation=None)
                execute_index = next(slot.slot_index for slot in catalog.slots if slot.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION)
                self.assertEqual(build_action_mask(catalog, state)[execute_index], expected)

    def test_refresh_disable_and_candidate_scope_preference_require_real_eligible_public_bindings(self) -> None:
        slots = CandidateCatalog.build((resolved(ControllerAction.REQUEST_AUTHORIZATION), resolved(ControllerAction.REQUEST_REFRESH), resolved(ControllerAction.DISABLE_LOCAL_AUTHORIZATION), resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        request = next(slot for slot in slots.slots if slot.action is ControllerAction.REQUEST_AUTHORIZATION)
        state = PublicMaskState(1, task_view=task_view(), authorization_views={AUTH: auth_view("active", "exact", 1), PRIOR: auth_view("consumed", "broader", 0)}, preference_relation={request.public_scope_identity: "do_not_reask_until_scope_change"})
        def selected(mask: tuple[bool, ...]) -> tuple[bool, bool, bool]:
            return tuple(mask[next(slot.slot_index for slot in slots.slots if slot.action is action)] for action in (ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH, ControllerAction.DISABLE_LOCAL_AUTHORIZATION))
        self.assertEqual(selected(build_action_mask(slots, state)), (False, False, True))
        stale = replace(state, authorization_views={AUTH: auth_view("revoked", "exact", 0), PRIOR: auth_view("consumed", "disjoint", 0)})
        self.assertEqual(selected(build_action_mask(slots, stale)), (False, False, False))

    def test_refresh_requires_positive_relation_and_respects_same_scope_persistent_denial(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.REQUEST_REFRESH), resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        refresh = next(slot for slot in catalog.slots if slot.action is ControllerAction.REQUEST_REFRESH)
        index = refresh.slot_index
        eligible = {"active", "consumed", "expired", "revoked", "superseded"}
        for status in (item.value for item in AuthorizationStatus):
            for relation in (None, "exact", "narrower", "broader", "disjoint"):
                view = auth_view(status, "exact", 1)
                view["scope_relation"] = relation
                if status == "consumed": view["remaining_uses"] = 0
                if status == "expired": view.update(expiry_bucket="expired", expiry_step=1)
                if status == "rejected": view.update(grant_type=None, remaining_uses=None)
                if status == "pending": view.update(grant_type=None, remaining_uses=None)
                state = PublicMaskState(1, task_view(), {PRIOR: view}, None)
                self.assertEqual(build_action_mask(catalog, state)[index], status in eligible and relation in {"exact", "narrower", "broader"})
        denied = PublicMaskState(1, task_view(), {PRIOR: {**auth_view("rejected", "exact", 0), "grant_type": None, "remaining_uses": None, "reask_relation": "do_not_reask_until_scope_change"}}, {refresh.public_scope_identity: "do_not_reask_until_scope_change"})
        self.assertFalse(build_action_mask(catalog, denied)[index])
        changed = replace(denied, preference_relation={"scope_" + "f" * 16: "do_not_reask_until_scope_change"})
        self.assertFalse(build_action_mask(catalog, changed)[index])  # rejected remains ineligible independently

    def test_expiry_bucket_is_bound_to_logical_step_before_refresh_masking(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.REQUEST_REFRESH), resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        refresh_index = next(slot.slot_index for slot in catalog.slots if slot.action is ControllerAction.REQUEST_REFRESH)
        impossible_active = auth_view("active", "exact", 1, expiry=2)
        with self.assertRaises(ValueError):
            build_action_mask(catalog, PublicMaskState(3, task_view(), {PRIOR: impossible_active}, None))
        impossible_expired = {**auth_view("expired", "exact", 0, expiry=4), "expiry_bucket": "expired"}
        with self.assertRaises(ValueError):
            PublicMaskState(3, task_view(), {PRIOR: impossible_expired}, None)
        valid_active = PublicMaskState(3, task_view(), {PRIOR: auth_view("active", "exact", 1, expiry=4)}, None)
        valid_expired = PublicMaskState(3, task_view(), {PRIOR: {**auth_view("expired", "exact", 0, expiry=3), "expiry_bucket": "expired"}}, None)
        self.assertTrue(build_action_mask(catalog, valid_active)[refresh_index])
        self.assertTrue(build_action_mask(catalog, valid_expired)[refresh_index])

    def test_changed_scope_preference_keeps_an_otherwise_eligible_refresh_enabled(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.REQUEST_REFRESH), resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        refresh = next(slot for slot in catalog.slots if slot.action is ControllerAction.REQUEST_REFRESH)
        eligible = {PRIOR: auth_view("consumed", "exact", 0)}
        same_scope = PublicMaskState(1, task_view(), eligible, {refresh.public_scope_identity: "do_not_reask_until_scope_change"})
        changed_scope = PublicMaskState(1, task_view(), eligible, {"scope_" + "f" * 16: "do_not_reask_until_scope_change"})
        self.assertFalse(build_action_mask(catalog, same_scope)[refresh.slot_index])
        self.assertTrue(build_action_mask(catalog, changed_scope)[refresh.slot_index])


class PublicBoundaryRegressionTests(unittest.TestCase):
    def test_allowed_field_private_object_and_unverified_chain_are_rejected(self) -> None:
        class PrivateValue:
            secret = "oracle"

        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        with self.assertRaises(ValueError):
            PublicMaskState(1, {**task_view(), "primary_complete": PrivateValue()}, {}, None)
        with self.assertRaises(ValueError):
            build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": PrivateValue(), "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True, True))
        invalid = object.__new__(PublicEventRecord)
        object.__setattr__(invalid, "sequence", 1); object.__setattr__(invalid, "event_id", "public_event_" + "0" * 16)
        object.__setattr__(invalid, "logical_step", 1); object.__setattr__(invalid, "event_type", "permission_requested")
        object.__setattr__(invalid, "payload", {"request_id": "r"}); object.__setattr__(invalid, "payload_hash", "0" * 64)
        object.__setattr__(invalid, "previous_event_hash", None); object.__setattr__(invalid, "event_hash", "0" * 64)
        with self.assertRaises(ValueError):
            build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(invalid,), catalog=catalog, action_mask=(True, True))

    def test_event_specific_schema_and_fully_rehashed_invalid_types_fail(self) -> None:
        chain = PublicEventChain()
        with self.assertRaises(PublicEventChainError):
            chain.append("permission_requested", {"authorization_id": AUTH}, 1)
        record = object.__new__(PublicEventRecord)
        for name, value in (("sequence", True), ("event_id", "public_event_" + "0" * 16), ("logical_step", 0), ("event_type", "permission_requested"), ("payload", {"request_id": "r"}), ("payload_hash", "0" * 64), ("previous_event_hash", None), ("event_hash", "0" * 64)):
            object.__setattr__(record, name, value)
        with self.assertRaises(PublicEventChainError):
            verify_public_event_chain((record,))

    def test_direct_catalog_and_closed_horizon_observation_are_validated(self) -> None:
        first = resolved(ControllerAction.REQUEST_AUTHORIZATION)
        second = resolved(ControllerAction.REQUEST_AUTHORIZATION, task_step_id="other")
        with self.assertRaises(ValueError):
            CandidateCatalog((second.with_slot(0), first.with_slot(1)), canonical_hash(tuple(slot.public_view() for slot in (second.with_slot(0), first.with_slot(1)))))
        empty = CandidateCatalog.build(())
        closed = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=4, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(finished=True), authorization_views={}, public_records=(), catalog=empty, action_mask=())
        self.assertEqual((closed.horizon_remaining, closed.candidate_catalog, closed.action_mask), (0, (), ()))
        with self.assertRaises(ValueError):
            build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=4, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(finished=True), authorization_views={}, public_records=(), catalog=CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON),)), action_mask=(True,))

    def test_resolved_binding_matrix_rejects_irrelevant_fields_and_bad_codes(self) -> None:
        with self.assertRaises(ValueError):
            resolved(ControllerAction.REQUEST_AUTHORIZATION, authorization_id=AUTH)
        with self.assertRaises(ValueError):
            resolved(ControllerAction.DENY_WITH_REASON, public_reason_code="oracle_secret")

    def test_authorization_summary_domains_and_cross_fields_fail_closed(self) -> None:
        valid = auth_view("active", "exact", 1)
        attacks = (
            {**valid, "expiry_bucket": "private-canary"}, {**valid, "last_public_authority_event_id": "oracle"},
            {**valid, "reask_relation": "future-answer"}, {**valid, "grant_type": None},
            {**valid, "grant_type": "one_time", "remaining_uses": None},
            {**valid, "grant_type": "reusable", "remaining_uses": 1},
            {**valid, "status": None, "grant_type": "one_time"},
        )
        for attack in attacks:
            with self.subTest(attack=attack):
                with self.assertRaises(ValueError):
                    PublicMaskState(1, task_view(), {AUTH: attack}, None)

    def test_all_fixture_request_contexts_pass_exact_schema_and_recursive_extensions_fail(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        for path in sorted((ROOT / "fixtures" / "scenarios").glob("*.json")):
            manifest = load_scenario(path)
            build_environment_observation(scenario_id=manifest.scenario_id, environment_version="pa_env_v0.10", logical_step=1, horizon=manifest.horizon, request_context=manifest.public_request_context, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True, True))
        for key in ("private", "Oracle", "future_answer", "HIDDEN", "audit", "Evaluator", "permit", "reservation_token", "effect_id"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": {key: "canary"}}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True, True))

    def test_direct_observation_rejects_mutable_or_forged_catalog_and_history(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        built = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True, True))
        with self.assertRaises(TypeError): built.candidate_catalog[0]["action"] = "oracle"  # type: ignore[index]
        forged = ({"private_detail": "oracle"},)
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, built.interaction_history, forged, canonical_hash(forged), (True,))
        bad_history = {"records": ({"oracle": "x"},) * 4, "counts": {}, "response_counts": {}, "response_rates": {}}
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, bad_history, built.candidate_catalog, built.catalog_hash, built.action_mask)
        chain = PublicEventChain()
        chain.append("permission_requested", {"request_id": "r"}, 1)
        chain.append("verified_error", {"error_code": "e"}, 1)
        with_history = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=chain.records, catalog=catalog, action_mask=(True, True))
        rows = with_history.interaction_history["records"]
        reordered = {**with_history.interaction_history, "records": rows[:2] + tuple(reversed(rows[2:]))}
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, reordered, with_history.candidate_catalog, with_history.catalog_hash, with_history.action_mask)

    def test_complete_direct_history_recomputes_counts_and_global_identities(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON),))
        built = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True,))
        base_counts = dict(built.interaction_history["counts"])
        attacks = (
            {**built.interaction_history, "counts": {**base_counts, "permission_choice": 1}},
            {**built.interaction_history, "counts": {**base_counts, "permission_choice": 1, "denial": 1, "grant": 1}, "response_counts": {"allow": 0, "deny": 1, "total": 1}, "response_rates": {"allow": 1.0 / 3.0, "deny": 2.0 / 3.0}},
            {**built.interaction_history, "counts": {**base_counts, "prompt": 1}},
        )
        for history in attacks:
            with self.subTest(history=history):
                with self.assertRaises(ValueError):
                    EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, history, built.candidate_catalog, built.catalog_hash, built.action_mask)

    def test_direct_history_suffix_counts_cover_every_visible_record(self) -> None:
        chain = PublicEventChain()
        for number in range(5):
            chain.append("permission_requested", {"request_id": f"r{number}"}, 1)
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON),))
        built = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=chain.records, catalog=catalog, action_mask=(True,))
        forged_counts = {**built.interaction_history["counts"], "prompt": 3}
        forged_history = {**built.interaction_history, "counts": forged_counts}
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, forged_history, built.candidate_catalog, built.catalog_hash, built.action_mask)

    def test_direct_history_suffix_requires_a_predecessor_commitment(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON),))
        empty = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True,))
        counts = {**empty.interaction_history["counts"], "verified_error": 1}
        history = {**empty.interaction_history, "records": empty.interaction_history["records"][:3] + (canonical_record(2, None).public_view(),), "counts": counts}
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, history, empty.candidate_catalog, empty.catalog_hash, empty.action_mask)
        anchored = {**history, "records": empty.interaction_history["records"][:3] + (canonical_record(2, "f" * 64).public_view(),)}
        EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, anchored, empty.candidate_catalog, empty.catalog_hash, empty.action_mask)

    def test_direct_candidate_rehash_cannot_separate_scope_identity_from_hash(self) -> None:
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON),))
        built = build_environment_observation(scenario_id="s", environment_version="pa_env_v0.10", logical_step=1, horizon=3, request_context={"request": "x", "task": "y"}, task_view=task_view(), authorization_views={}, public_records=(), catalog=catalog, action_mask=(True,))
        row = dict(built.candidate_catalog[0])
        row["public_scope_identity"] = "scope_" + "f" * 16
        semantic = {key: value for key, value in row.items() if key not in {"slot_index", "identifier"}}
        row["identifier"] = "resolved_" + canonical_hash({"slot_index": 0, **semantic})[:16]
        forged = (row,)
        with self.assertRaises(ValueError):
            EnvironmentObservation("s", "pa_env_v0.10", 1, 3, 3, {"request": "x", "task": "y"}, task_view(), {}, built.interaction_history, forged, canonical_hash(forged), (True,))

    def test_genuinely_recomputed_boolean_sequence_record_is_rejected(self) -> None:
        payload = {"request_id": "r"}; payload_hash = canonical_hash(payload); sequence = True; logical_step = 1
        event_id = "public_event_" + canonical_hash({"sequence": sequence, "logical_step": logical_step, "event_type": "permission_requested", "payload_hash": payload_hash, "previous_event_hash": None})[:16]
        event_hash = canonical_hash({"sequence": sequence, "event_id": event_id, "logical_step": logical_step, "event_type": "permission_requested", "payload_hash": payload_hash, "previous_event_hash": None})
        record = object.__new__(PublicEventRecord)
        for name, value in (("sequence", sequence), ("event_id", event_id), ("logical_step", logical_step), ("event_type", "permission_requested"), ("payload", payload), ("payload_hash", payload_hash), ("previous_event_hash", None), ("event_hash", event_hash)): object.__setattr__(record, name, value)
        with self.assertRaises(PublicEventChainError): verify_public_event_chain((record,))


if __name__ == "__main__":
    unittest.main()
