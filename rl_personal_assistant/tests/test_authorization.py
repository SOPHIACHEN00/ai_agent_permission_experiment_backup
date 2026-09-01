"""Observable contracts for the Increment 1 authority kernel."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import AuthorizationStatus, GrantType, PermissionChoice, Scope, canonical_hash
from pa_rl.scope_matching import ScopeRelation, covers, relation


BASE = dict(
    domain="calendar",
    tool="calendar_api",
    resource="calendar.events/primary/*",
    data_attributes=("time", "title"),
    operation="read",
    purpose="schedule_assistance",
    recipient="user_self",
    retention="episode",
)


def scope(**changes: object) -> Scope:
    values = dict(BASE)
    values.update(changes)
    return Scope(**values)


def mutable(value: object) -> object:
    if hasattr(value, "items"):
        return {key: mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(mutable(item) for item in value)
    return value


def recompute_event(event: object, payload: object) -> object:
    payload_hash = canonical_hash(payload)
    basis = {
        "episode_id": "episode-1", "sequence": event.sequence, "logical_step": event.logical_step,
        "actor": event.actor, "authorization_id": event.authorization_id,
        "previous_revision": event.previous_revision, "new_revision": event.new_revision,
        "event_type": event.event_type, "payload_hash": payload_hash,
        "policy_version": event.policy_version, "environment_version": event.environment_version,
    }
    event_id = "authorization_event_" + canonical_hash(basis)[:20]
    event_hash = canonical_hash({
        "previous_event_hash": event.previous_event_hash,
        "event_id": event_id,
        "payload_hash": payload_hash,
    })
    return replace(event, payload=payload, payload_hash=payload_hash, event_id=event_id, event_hash=event_hash)


def rechain(events: tuple[object, ...], changes: dict[int, dict[str, object]]) -> tuple[object, ...]:
    rebuilt = []
    previous_hash = None
    for index, original in enumerate(events):
        change = changes.get(index, {})
        event = replace(
            original,
            logical_step=change.get("logical_step", original.logical_step),
            actor=change.get("actor", original.actor),
            event_type=change.get("event_type", original.event_type),
            previous_event_hash=previous_hash,
        )
        payload = change.get("payload", mutable(original.payload))
        event = recompute_event(event, payload)
        rebuilt.append(event)
        previous_hash = event.event_hash
    return tuple(rebuilt)


class ScopeMatchingTests(unittest.TestCase):
    def test_exact_data_subset_wildcard_and_retention_relations(self) -> None:
        grant = scope(resource="calendar.events/primary/evt-7")
        exact = scope(resource="calendar.events/primary/evt-7")
        subset = scope(resource="calendar.events/primary/evt-7", data_attributes=("time",))
        wildcard_grant = scope()
        child_resource = scope(resource="calendar.events/primary/evt-7")
        shorter_retention = scope(resource="calendar.events/primary/evt-7", retention="transient")

        self.assertTrue(covers(grant, exact))
        self.assertEqual(relation(grant, exact), ScopeRelation.EXACT)
        self.assertEqual(relation(grant, subset), ScopeRelation.NARROWER)
        self.assertEqual(relation(wildcard_grant, child_resource), ScopeRelation.NARROWER)
        self.assertEqual(relation(grant, shorter_retention), ScopeRelation.NARROWER)

    def test_broader_and_scalar_mismatches_are_disjoint(self) -> None:
        grant = scope(data_attributes=("time",), resource="calendar.events/primary/evt-7", retention="transient")
        operation = scope(data_attributes=("time", "title"), resource="calendar.events/primary/evt-7", retention="episode")

        self.assertEqual(relation(grant, operation), ScopeRelation.BROADER)
        for field, value in (("purpose", "analytics"), ("recipient", "team"), ("tool", "mail_api")):
            with self.subTest(field=field):
                self.assertFalse(covers(scope(), scope(**{field: value})))
                self.assertEqual(relation(scope(), scope(**{field: value})), ScopeRelation.DISJOINT)

    def test_operation_wildcard_never_gains_authority(self) -> None:
        grant = scope(resource="calendar.events/primary/evt-7")
        wildcard_operation = scope(resource="calendar.events/primary/*")

        self.assertFalse(covers(grant, wildcard_operation))
        self.assertEqual(relation(grant, wildcard_operation), ScopeRelation.DISJOINT)

    def test_external_retention_is_categorical_self_only(self) -> None:
        external = scope(resource="calendar.events/primary/evt-7", retention="external")

        self.assertTrue(covers(external, external))
        self.assertEqual(relation(external, external), ScopeRelation.EXACT)
        for ranked_retention in ("none", "transient", "episode", "session"):
            ranked = scope(resource="calendar.events/primary/evt-7", retention=ranked_retention)
            with self.subTest(ranked_retention=ranked_retention):
                self.assertFalse(covers(external, ranked))
                self.assertFalse(covers(ranked, external))
                self.assertEqual(relation(external, ranked), ScopeRelation.DISJOINT)
                self.assertEqual(relation(ranked, external), ScopeRelation.DISJOINT)

    def test_unknown_retention_values_fail_instead_of_matching_themselves(self) -> None:
        unknown = scope(resource="calendar.events/primary/evt-7", retention="future_unknown")

        with self.assertRaises(ValueError):
            covers(unknown, unknown)
        with self.assertRaises(ValueError):
            relation(unknown, unknown)


class AuthorizationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AuthorizationService("episode-1")
        self.declared_scope = scope()
        self.operation = scope(resource="calendar.events/primary/evt-7", data_attributes=("time",))

    def _active(self, choice: PermissionChoice = PermissionChoice.ALLOW_ONCE):
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1")
        return self.service.apply_permission_choice(pending.authorization_id, choice, step=2)

    def test_request_is_pending_and_only_permission_choice_mints_active(self) -> None:
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1")
        self.assertEqual(pending.status, AuthorizationStatus.PENDING)
        self.assertIsNone(pending.grant_type)
        self.assertEqual(pending.grantor, "pending_grantor")
        self.assertFalse(hasattr(self.service, "activate"))
        self.assertIsNone(self.service.reserve(self.operation, step=1))

    def test_every_permission_choice_has_its_declared_effect(self) -> None:
        expected = {
            PermissionChoice.ALLOW_ONCE: (AuthorizationStatus.ACTIVE, GrantType.ONE_TIME, 1, None),
            PermissionChoice.ALLOW_REUSE: (AuthorizationStatus.ACTIVE, GrantType.REUSABLE, None, None),
            PermissionChoice.DENY_PERSIST: (AuthorizationStatus.REJECTED, None, None, "do_not_reask_until_scope_change"),
            PermissionChoice.DENY_REASK: (AuthorizationStatus.REJECTED, None, None, "reask_on_new_need"),
        }
        for choice, (status, grant_type, uses, preference) in expected.items():
            with self.subTest(choice=choice):
                service = AuthorizationService("episode-choices")
                pending = service.start_request(self.declared_scope, step=1, source_public_event_id="public-1")
                record = service.apply_permission_choice(pending.authorization_id, choice, step=2)
                self.assertEqual((record.status, record.grant_type, record.remaining_uses), (status, grant_type, uses))
                self.assertEqual(record.grantor, "user_public_event")
                summary = service.public_summary(self.operation)
                self.assertEqual(summary.reask_relation, preference)

    def test_one_time_commit_consumes_and_second_reserve_fails(self) -> None:
        record = self._active()
        token = self.service.reserve(self.operation, step=3, expected_revision=record.revision)
        self.assertIsNotNone(token)
        consumed = self.service.commit(token, step=3)
        self.assertEqual(consumed.status, AuthorizationStatus.CONSUMED)
        self.assertEqual(consumed.remaining_uses, 0)
        self.assertIsNone(self.service.reserve(self.operation, step=5))

    def test_reusable_commit_returns_active_and_can_be_reserved_again(self) -> None:
        record = self._active(PermissionChoice.ALLOW_REUSE)
        first = self.service.reserve(self.operation, step=3, expected_revision=record.revision)
        restored = self.service.commit(first, step=3)
        self.assertEqual(restored.status, AuthorizationStatus.ACTIVE)
        self.assertIsNotNone(self.service.reserve(self.operation, step=5, expected_revision=restored.revision))

    def test_abort_restores_active_and_unknown_effect_locks_authorization(self) -> None:
        record = self._active(PermissionChoice.ALLOW_REUSE)
        token = self.service.reserve(self.operation, step=3, expected_revision=record.revision)
        active = self.service.abort(token, step=3)
        self.assertEqual(active.status, AuthorizationStatus.ACTIVE)
        token = self.service.reserve(self.operation, step=5, expected_revision=active.revision)
        locked = self.service.mark_reconciliation_required(token, step=5)
        self.assertEqual(locked.status, AuthorizationStatus.RECONCILIATION_REQUIRED)
        self.assertIsNone(self.service.reserve(self.operation, step=7))

    def test_disable_and_expiry_prevent_reserve_without_reactivation(self) -> None:
        active = self._active(PermissionChoice.ALLOW_REUSE)
        revoked = self.service.disable(active.authorization_id, step=3)
        self.assertEqual(revoked.status, AuthorizationStatus.REVOKED)
        self.assertIsNone(self.service.reserve(self.operation, step=4))

        service = AuthorizationService("episode-expiry")
        pending = service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=3)
        active = service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        expired = service.expire_eligible(step=3)
        self.assertEqual(expired[0].status, AuthorizationStatus.EXPIRED)
        self.assertIsNone(service.reserve(self.operation, step=3))
        self.assertEqual(service.records()[0].authorization_id, active.authorization_id)

    def test_same_revision_allows_only_one_reserve(self) -> None:
        active = self._active(PermissionChoice.ALLOW_REUSE)
        first = self.service.reserve(self.operation, step=3, expected_revision=active.revision)
        second = self.service.reserve(self.operation, step=3, expected_revision=active.revision)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_refresh_creates_new_record_and_supersedes_only_after_new_grant(self) -> None:
        old = self._active(PermissionChoice.ALLOW_REUSE)
        broader = scope(data_attributes=("time", "title", "location"))
        refresh = self.service.start_refresh(old.authorization_id, broader, step=3, source_public_event_id="public-2")
        self.assertNotEqual(refresh.authorization_id, old.authorization_id)
        self.assertEqual(refresh.supersedes_authorization_id, old.authorization_id)
        self.assertEqual(self.service.record(old.authorization_id), old)
        new = self.service.apply_permission_choice(refresh.authorization_id, PermissionChoice.ALLOW_REUSE, step=4)
        self.assertEqual(new.status, AuthorizationStatus.ACTIVE)
        self.assertEqual(self.service.record(old.authorization_id).status, AuthorizationStatus.SUPERSEDED)
        self.assertEqual(self.service.record(old.authorization_id).scope, old.scope)

    def test_event_replay_reconstructs_records_preferences_revisions_and_hashes(self) -> None:
        record = self._active()
        token = self.service.reserve(self.operation, step=3, expected_revision=record.revision)
        self.service.abort(token, step=3)
        denied = self.service.start_request(scope(resource="calendar.events/other/*"), step=5, source_public_event_id="public-2")
        self.service.apply_permission_choice(denied.authorization_id, PermissionChoice.DENY_PERSIST, step=6)

        replayed = AuthorizationService.replay("episode-1", self.service.events())
        self.assertEqual(replayed.records(), self.service.records())
        self.assertEqual(replayed.preferences(), self.service.preferences())
        self.assertEqual(replayed.events(), self.service.events())

    def test_replay_rejects_tampered_out_of_order_and_bad_revision_events(self) -> None:
        self._active()
        events = self.service.events()
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", tuple(reversed(events)))
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", (replace(events[0], payload_hash="0" * 64),) + events[1:])
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", events[:1] + (replace(events[1], previous_revision=99),) + events[2:])

    def test_replay_rejects_self_consistent_rewrite_that_mints_active_request(self) -> None:
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1")
        event = self.service.events()[0]
        payload = mutable(event.payload)
        payload["record"]["status"] = AuthorizationStatus.ACTIVE.value
        payload["record"]["grantor"] = "user_public_event"
        payload["record"]["grant_type"] = GrantType.ONE_TIME.value
        payload["record"]["remaining_uses"] = 1
        forged = recompute_event(event, payload)
        self.assertEqual(forged.authorization_id, pending.authorization_id)
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", (forged,))

    def test_reservation_event_carries_typed_selected_operation_context(self) -> None:
        active = self._active(PermissionChoice.ALLOW_REUSE)
        self.service.reserve(self.operation, step=3, authorization_id=active.authorization_id)
        event = self.service.events()[-1]
        self.assertEqual(event.event_type, "reserved")
        self.assertEqual(event.payload["reservation_logical_step"], 3)
        self.assertEqual(event.payload["selected_authorization_id"], active.authorization_id)
        self.assertEqual(event.payload["operation_scope_hash"], canonical_hash(self.operation))
        self.assertEqual(event.payload["operation_scope"]["resource"], self.operation.resource)

    def test_replay_rejects_rehashed_late_settlement_and_reserve_at_expiry(self) -> None:
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=4)
        active = self.service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        token = self.service.reserve(self.operation, step=3, authorization_id=active.authorization_id)
        self.service.commit(token, step=3)
        self.service.start_request(scope(resource="calendar.events/other/*"), step=4, source_public_event_id="public-2")
        late = rechain(self.service.events(), {3: {"logical_step": 4}})
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", late)

        at_expiry = rechain(self.service.events(), {2: {"logical_step": 4}, 3: {"logical_step": 4}})
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", at_expiry)

    def test_replay_rejects_rehashed_early_expiry(self) -> None:
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=3)
        self.service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        self.service.expire_eligible(step=3)
        early = rechain(self.service.events(), {2: {"logical_step": 2}})
        with self.assertRaises(ValueError):
            AuthorizationService.replay("episode-1", early)

    def test_allow_at_pending_expiry_fails_closed_and_summary_never_reports_expired_active(self) -> None:
        pending = self.service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=2)
        with self.assertRaises(ValueError):
            self.service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        self.assertEqual(self.service.record(pending.authorization_id).status, AuthorizationStatus.PENDING)

        service = AuthorizationService("episode-summary")
        request = service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=3)
        service.apply_permission_choice(request.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        self.assertEqual(service.public_summary(self.operation, step=3).status, AuthorizationStatus.EXPIRED)

    def test_reserve_requires_unambiguous_match_or_named_active_grant(self) -> None:
        first = self._active(PermissionChoice.ALLOW_REUSE)
        pending = self.service.start_request(self.declared_scope, step=2, source_public_event_id="public-2")
        second = self.service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        self.assertIsNone(self.service.reserve(self.operation, step=3))
        self.assertIsNone(self.service.reserve(self.operation, step=3, authorization_id="missing"))
        token = self.service.reserve(
            self.operation, step=3, authorization_id=second.authorization_id, expected_revision=second.revision,
        )
        self.assertIsNotNone(token)
        self.assertEqual(token.authorization_id, second.authorization_id)
        self.assertEqual(self.service.record(first.authorization_id).status, AuthorizationStatus.ACTIVE)

    def test_all_live_mutations_are_monotonic_and_settlement_is_token_step_bound(self) -> None:
        active = self._active(PermissionChoice.ALLOW_REUSE)
        with self.assertRaises(ValueError):
            self.service.disable(active.authorization_id, step=1)
        token = self.service.reserve(self.operation, step=3, expected_revision=active.revision)
        with self.assertRaises(ValueError):
            self.service.abort(token, step=4)
        self.assertEqual(self.service.record(active.authorization_id).status, AuthorizationStatus.RESERVED)

        short = AuthorizationService("short", episode_end_step=3)
        request = short.start_request(self.declared_scope, step=1, source_public_event_id="public-1")
        granted = short.apply_permission_choice(request.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        self.assertIsNone(short.reserve(self.operation, step=3, authorization_id=granted.authorization_id))
        with self.assertRaises(ValueError):
            short.start_request(self.declared_scope, step=4, source_public_event_id="public-2")

    def test_denial_preference_lasts_to_episode_end_and_summary_ignores_it_afterward(self) -> None:
        service = AuthorizationService("episode-preference", episode_end_step=5)
        pending = service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=2)
        service.apply_permission_choice(pending.authorization_id, PermissionChoice.DENY_PERSIST, step=2)
        self.assertEqual(service.preferences()[0].expires_at_step, 5)
        self.assertEqual(service.public_summary(self.operation, step=5).reask_relation, "do_not_reask_until_scope_change")
        self.assertIsNone(service.public_summary(self.operation, step=6).reask_relation)

    def test_refresh_summary_prefers_new_active_record_and_terminal_prior_is_unchanged(self) -> None:
        old = self._active(PermissionChoice.ALLOW_REUSE)
        refresh = self.service.start_refresh(old.authorization_id, self.declared_scope, step=3, source_public_event_id="public-2")
        new = self.service.apply_permission_choice(refresh.authorization_id, PermissionChoice.ALLOW_REUSE, step=4)
        self.assertEqual(self.service.public_summary(self.operation, step=4).last_public_authority_event_id, new.source_public_event_id)
        self.assertEqual(self.service.public_summary(self.operation, step=4).status, AuthorizationStatus.ACTIVE)

        for terminal in (AuthorizationStatus.CONSUMED, AuthorizationStatus.EXPIRED, AuthorizationStatus.REVOKED):
            with self.subTest(terminal=terminal):
                service = AuthorizationService("terminal-" + terminal.value)
                initial = service.start_request(self.declared_scope, step=1, source_public_event_id="public-1", expires_at_step=3)
                old_record = service.apply_permission_choice(initial.authorization_id, PermissionChoice.ALLOW_ONCE, step=2)
                if terminal is AuthorizationStatus.CONSUMED:
                    consumed = service.reserve(self.operation, step=2, authorization_id=old_record.authorization_id)
                    service.commit(consumed, step=2)
                elif terminal is AuthorizationStatus.EXPIRED:
                    service.expire_eligible(step=3)
                else:
                    service.disable(old_record.authorization_id, step=2)
                refresh = service.start_refresh(old_record.authorization_id, self.declared_scope, step=3, source_public_event_id="public-2")
                service.apply_permission_choice(refresh.authorization_id, PermissionChoice.ALLOW_REUSE, step=3)
                self.assertEqual(service.record(old_record.authorization_id).status, terminal)

    def test_returned_events_and_records_are_deeply_immutable(self) -> None:
        record = self._active()
        event = self.service.events()[0]
        with self.assertRaises(TypeError):
            event.payload["record"] = "changed"
        with self.assertRaises(TypeError):
            event.payload["record"]["scope"]["tool"] = "mail_api"
        with self.assertRaises(FrozenInstanceError):
            record.status = AuthorizationStatus.REVOKED

    def test_public_summary_excludes_private_audit_and_oracle_values(self) -> None:
        self._active()
        summary = self.service.public_summary(self.operation)
        self.assertEqual(summary.status, AuthorizationStatus.ACTIVE)
        self.assertEqual(summary.scope_relation, ScopeRelation.NARROWER)
        rendered = repr(summary).lower()
        for forbidden in ("payload", "oracle", "private", "grantor", "requester", "source_public_event_id"):
            self.assertNotIn(forbidden, rendered)

    def test_new_episode_service_is_empty(self) -> None:
        self._active(PermissionChoice.DENY_REASK)
        new_episode = AuthorizationService("episode-2")
        self.assertEqual(new_episode.records(), ())
        self.assertEqual(new_episode.preferences(), ())
        self.assertIsNone(new_episode.public_summary(self.operation).status)


if __name__ == "__main__":
    unittest.main()
