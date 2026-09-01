"""Observable contracts for the Task 3A scripted public user."""

from __future__ import annotations

import unittest
from pathlib import Path

from pa_rl.contracts import PermissionChoice, PublicEvent
from pa_rl.scripted_user import ScriptedUserAdapter, ScriptedUserInputError
from pa_rl.scenarios import load_scenario, project_public_observation


def public_scenario() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    return project_public_observation(load_scenario(root / "fixtures" / "scenarios" / "01_one_time_grant_success.json"))  # type: ignore[return-value]


def public_request() -> dict[str, object]:
    return {
        "request_id": "permission_request_" + "a" * 16,
        "scope_identity": "scope_" + "b" * 16,
        "logical_step": 1,
        "request_kind": "request",
    }


class ScriptedUserAdapterTests(unittest.TestCase):
    def test_reset_restarts_fifo_choices_and_clears_received_events(self) -> None:
        adapter = ScriptedUserAdapter((
            PermissionChoice.ALLOW_ONCE, PermissionChoice.DENY_REASK,
            PermissionChoice.ALLOW_REUSE, PermissionChoice.DENY_PERSIST,
        ))
        adapter.reset(public_scenario(), 11)
        event = PublicEvent("permission_requested", {"request_id": "request_1"})
        adapter.observe_event(event)
        self.assertEqual(adapter.received_events, (event,))
        self.assertEqual(adapter.answer_permission(public_request(), (event,)), PermissionChoice.ALLOW_ONCE)
        self.assertEqual(adapter.answer_permission(public_request(), (event,)), PermissionChoice.DENY_REASK)

        adapter.reset(public_scenario(), 11)
        self.assertEqual(adapter.received_events, ())
        self.assertEqual(adapter.answer_permission(public_request(), ()), PermissionChoice.ALLOW_ONCE)

    def test_observing_public_events_never_consumes_a_permission_answer(self) -> None:
        adapter = ScriptedUserAdapter((PermissionChoice.ALLOW_ONCE,))
        adapter.reset(public_scenario(), 7)
        adapter.observe_event(PublicEvent("permission_requested", {"request_id": "request_1"}))
        adapter.observe_event(PublicEvent("permission_granted", {"authorization_id": "authorization_" + "a" * 20}))
        self.assertEqual(adapter.answer_permission(public_request(), ()), PermissionChoice.ALLOW_ONCE)

    def test_exhaustion_and_non_public_inputs_fail_closed_without_remaining_script_access(self) -> None:
        adapter = ScriptedUserAdapter((PermissionChoice.ALLOW_ONCE,))
        adapter.reset(public_scenario(), 3)
        self.assertEqual(adapter.answer_permission(public_request(), ()), PermissionChoice.ALLOW_ONCE)
        with self.assertRaises(ScriptedUserInputError):
            adapter.answer_permission(public_request(), ())
        self.assertFalse(hasattr(adapter, "remaining_responses"))
        with self.assertRaises(ScriptedUserInputError):
            adapter.answer_permission({"request_id": "r", "oracle": "secret"}, ())
        with self.assertRaises(ScriptedUserInputError):
            adapter.answer_permission(public_request(), (PublicEvent("permission_requested", {"private_detail": "no"}),))

    def test_reset_rejects_boolean_or_non_integer_seed_and_private_scenario_shape(self) -> None:
        adapter = ScriptedUserAdapter((PermissionChoice.ALLOW_ONCE,))
        for seed in (True, "7"):
            with self.subTest(seed=seed):
                with self.assertRaises(ScriptedUserInputError):
                    adapter.reset(public_scenario(), seed)  # type: ignore[arg-type]
        with self.assertRaises(ScriptedUserInputError):
            adapter.reset({"scenario_id": "x", "scripted_permission_responses": ["allow_once"]}, 7)


if __name__ == "__main__":
    unittest.main()
