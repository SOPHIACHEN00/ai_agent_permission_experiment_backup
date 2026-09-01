"""Observable public policy-interface contracts for Task 3A."""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
import unittest

from pa_rl.contracts import ActionCandidate, ControllerAction, Scope, canonical_hash
from pa_rl.policy_interface import (
    CandidateCatalog,
    EnvironmentObservation,
    PublicMaskState,
    build_action_mask,
    build_environment_observation,
    make_resolved_candidate,
)
from pa_rl.public_events import PublicEventChain, PublicEventChainError, verify_public_event_chain

AUTH = "authorization_" + "a" * 20
PRIOR = "authorization_" + "b" * 20

def full_task_view(phase: str = "open", complete: bool = False) -> dict[str, object]:
    return {"phase": phase, "next_required_step_id": None if complete else "step_1", "next_required_scope_identity": None if complete else "scope_" + "0" * 16, "remaining_step_count": 0 if complete else 1, "primary_complete": complete, "has_unknown_effect": False, "last_public_execution_result_code": None}

def full_auth(status: str, relation: str, uses: int | None, expiry: int = 4) -> dict[str, object]:
    return {"status": status, "grant_type": "reusable" if uses is None else "one_time", "remaining_uses": uses, "expiry_bucket": "future", "expiry_step": expiry, "scope_relation": relation, "last_public_authority_event_id": None, "reask_relation": None}


def scope() -> Scope:
    return Scope("productivity", "calendar_api", "calendar.events", ("title",), "read", "agenda", "local_user", "session")


def candidate(action: ControllerAction = ControllerAction.REQUEST_AUTHORIZATION) -> ActionCandidate:
    value = scope()
    return ActionCandidate("candidate_" + canonical_hash({"action": action.value, "scope": value})[:16], action, value)


def resolved(action: ControllerAction, **overrides: object):
    base = candidate(action)
    values: dict[str, object] = {
        "base_candidate": base,
        "task_step_id": "step_1" if action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH, ControllerAction.EXECUTE_WITH_AUTHORIZATION} else None,
        "authorization_id": AUTH if action in {ControllerAction.EXECUTE_WITH_AUTHORIZATION, ControllerAction.DISABLE_LOCAL_AUTHORIZATION} else None,
        "prior_authorization_id": PRIOR if action is ControllerAction.REQUEST_REFRESH else None,
        "public_reason_code": "not_needed" if action is ControllerAction.DENY_WITH_REASON else None,
        "escalation_target_code": "human_owner" if action is ControllerAction.ESCALATE else None,
    }
    values.update(overrides)
    return make_resolved_candidate(**values)  # type: ignore[arg-type]


class PublicEventChainTests(unittest.TestCase):
    def test_chain_is_canonical_deeply_immutable_and_independently_detects_tampering(self) -> None:
        chain = PublicEventChain()
        first = chain.append("permission_requested", {"request_id": "r1"}, 1)
        second = chain.append("permission_granted", {"authorization_id": AUTH}, 1)
        records = chain.records
        self.assertEqual(verify_public_event_chain(records, expected_head=chain.head_hash, expected_length=2), chain.head_hash)
        with self.assertRaises(TypeError):
            first.payload["request_id"] = "changed"  # type: ignore[index]
        for altered in (
            (second,),
            (second,),
            (second, first),
            (first, first),
        ):
            with self.subTest(altered=altered):
                with self.assertRaises(PublicEventChainError):
                    verify_public_event_chain(altered, expected_head=chain.head_hash, expected_length=2)

    def test_rehashed_unknown_or_invalid_sequence_is_rejected_not_authenticated(self) -> None:
        chain = PublicEventChain()
        first = chain.append("permission_requested", {"request_id": "r1"}, 1)
        with self.assertRaises(PublicEventChainError):
            replace(first, sequence=2)
        with self.assertRaises(PublicEventChainError):
            PublicEventChain().append("oracle_success", {"oracle": "never public"}, 1)

    def test_preview_then_commit_preserves_the_exact_prebound_event_and_rejects_stale_commits(self) -> None:
        chain = PublicEventChain()
        prepared = chain.preview("permission_requested", {"request_id": "r1"}, 1)
        self.assertEqual(prepared.sequence, 1)
        self.assertEqual(chain.records, ())
        self.assertEqual(chain.commit(prepared), prepared)
        stale = chain.preview("permission_granted", {"authorization_id": AUTH}, 1)
        chain.append("permission_denied", {"authorization_id": AUTH}, 1)
        with self.assertRaises(PublicEventChainError):
            chain.commit(stale)

    def test_valid_chain_can_be_verified_without_a_caller_supplied_head_and_nested_private_payload_is_rejected(self) -> None:
        chain = PublicEventChain()
        chain.append("permission_requested", {"request_id": "r1"}, 1)
        self.assertEqual(verify_public_event_chain(chain.records), chain.head_hash)
        with self.assertRaises(PublicEventChainError):
            PublicEventChain().append("permission_requested", {"request": {"private_detail": "no"}}, 1)
        with self.assertRaises(PublicEventChainError):
            PublicEventChain().append("permission_requested", {"oracle": "not an allowlisted payload key"}, 1)


class CandidateCatalogAndMaskTests(unittest.TestCase):
    def test_catalog_resolves_canonical_slots_without_changing_task_zero_base_ids(self) -> None:
        inputs = (
            resolved(ControllerAction.ESCALATE), resolved(ControllerAction.EXECUTE_WITH_AUTHORIZATION),
            resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.REQUEST_AUTHORIZATION),
        )
        first = CandidateCatalog.build(inputs)
        second = CandidateCatalog.build(tuple(reversed(inputs)))
        self.assertEqual(first, second)
        self.assertEqual([slot.slot_index for slot in first.slots], list(range(4)))
        self.assertEqual(first.slots[1].base_candidate_id, first.slots[1].base_candidate.identifier)
        self.assertEqual({slot.action for slot in first.slots}, {
            ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.EXECUTE_WITH_AUTHORIZATION,
            ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE,
        })

    def test_catalog_rejects_duplicate_semantics_and_overflow(self) -> None:
        one = resolved(ControllerAction.REQUEST_AUTHORIZATION)
        with self.assertRaises(ValueError):
            CandidateCatalog.build((one, one))
        slots = tuple(resolved(ControllerAction.REQUEST_AUTHORIZATION, task_step_id=f"step_{index}") for index in range(17))
        with self.assertRaises(ValueError):
            CandidateCatalog.build(slots)

    def test_mask_uses_only_explicit_public_state_and_keeps_safe_terminal_slots(self) -> None:
        slots = CandidateCatalog.build((
            resolved(ControllerAction.REQUEST_AUTHORIZATION),
            resolved(ControllerAction.EXECUTE_WITH_AUTHORIZATION),
            resolved(ControllerAction.REQUEST_REFRESH),
            resolved(ControllerAction.DISABLE_LOCAL_AUTHORIZATION),
            resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE),
        ))
        state = PublicMaskState(
            logical_step=2, task_view=full_task_view(),
            authorization_views={
                AUTH: full_auth("active", "exact", 1), PRIOR: full_auth("consumed", "exact", 0),
            },
            preference_relation=None,
        )
        mask = build_action_mask(slots, state)
        self.assertEqual(mask, (True, True, True, True, True, True))
        self.assertEqual(build_action_mask(slots, state), mask)
        with self.assertRaises(TypeError):
            PublicMaskState(logical_step=2, task_view={}, authorization_views={}, preference_relation=None, future_permission_choice="allow_reuse")  # type: ignore[call-arg]
        blocked = replace(state, task_view=full_task_view("finished", True))
        blocked_mask = build_action_mask(slots, blocked)
        execute_index = next(slot.slot_index for slot in slots.slots if slot.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION)
        self.assertFalse(blocked_mask[execute_index])
        self.assertTrue(any(blocked_mask))

    def test_unbound_execute_slot_is_masked_but_remains_resolved_for_monitor_mediation(self) -> None:
        slot = resolved(ControllerAction.EXECUTE_WITH_AUTHORIZATION, authorization_id=None)
        catalog = CandidateCatalog.build((slot, resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        mask = build_action_mask(catalog, PublicMaskState(1, full_task_view(), {}, None))
        execute_index = next(item.slot_index for item in catalog.slots if item.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION)
        self.assertFalse(mask[execute_index])


class EnvironmentObservationTests(unittest.TestCase):
    def test_observation_is_exactly_allowlisted_history_bounded_and_deeply_immutable(self) -> None:
        chain = PublicEventChain()
        for number, (event_type, payload) in enumerate((("permission_requested", {"request_id": "r"}), ("permission_granted", {"authorization_id": AUTH}), ("execution_result", {"task_step_id": "step_1", "outcome": "committed", "reason_code": "ok"}), ("authorization_revoked", {"authorization_id": AUTH}), ("verified_error", {"error_code": "e"})), 1):
            chain.append(event_type, payload, number)
        catalog = CandidateCatalog.build((resolved(ControllerAction.DENY_WITH_REASON), resolved(ControllerAction.ESCALATE)))
        observation = build_environment_observation(
            scenario_id="s1", environment_version="pa_env_v0.10", logical_step=3, horizon=5,
            request_context={"request": "public", "task": "public task"},
            task_view=full_task_view(), authorization_views={AUTH: full_auth("active", "exact", 1)},
            public_records=chain.records, catalog=catalog, action_mask=(True, True),
        )
        self.assertIsInstance(observation, EnvironmentObservation)
        view = observation.as_mapping()
        self.assertEqual(set(view), {
            "scenario_id", "environment_version", "logical_step", "horizon", "horizon_remaining", "request_context",
            "task_view", "authorization_views", "interaction_history", "candidate_catalog", "catalog_hash", "action_mask",
        })
        self.assertEqual(len(view["interaction_history"]["records"]), 4)
        self.assertEqual(view["interaction_history"]["counts"]["grant"], 1)
        self.assertEqual(view["interaction_history"]["counts"]["verified_error"], 1)
        self.assertNotIn("reservation_token", str(view))
        with self.assertRaises(TypeError):
            view["task_view"]["phase"] = "changed"  # type: ignore[index]
        self.assertEqual(view, MappingProxyType(dict(view)))
        with self.assertRaises(ValueError):
            build_environment_observation(
                scenario_id="s1", environment_version="pa_env_v0.10", logical_step=3, horizon=5,
                request_context={"scripted_permission_responses": "must fail closed"}, task_view=full_task_view(),
                authorization_views={}, public_records=(), catalog=catalog, action_mask=(True, True),
            )


if __name__ == "__main__":
    unittest.main()
