"""Cache correctness and fail-closed equivalence; no learning/API execution."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent), str(ROOT / 'tests')]

from dataclasses import replace
import unittest
from unittest.mock import patch
from helpers import key_for
from personal_assistant.config import PermissionConfig
from personal_assistant.contracts.permission import PermissionChoice as C, AuthorizationStatus as S
from personal_assistant.permissions.persistent_ledger import UserAuthorizationLedger
from personal_assistant.permissions.replay_verification import ReplayVerificationCache


class ReplayVerificationTests(unittest.TestCase):
    def ledger(self):
        ledger = UserAuthorizationLedger('alice', PermissionConfig(3))
        position = ledger.begin_task('task-a', 40)
        request = ledger.request((key_for(),), position, 'question')
        rid = ledger.apply_answer(request, key_for(), C.ALLOW_REUSE, 'response', position)
        return ledger, rid

    def test_identical_complete_events_reuse_replay_and_stats_are_readonly(self):
        ledger, _ = self.ledger()
        for _ in range(3): self.assertTrue(ledger.verify_replay())
        self.assertEqual(dict(ledger.replay_verification_stats),
                         dict(cache_hits=2, full_calls=1, verification_failures=0))
        with self.assertRaises(TypeError): ledger.replay_verification_stats['full_calls'] = 99

    def test_appended_event_requires_new_full_replay(self):
        ledger, _ = self.ledger()
        self.assertTrue(ledger.verify_replay())
        ledger.advance_decision(ledger.position)
        self.assertTrue(ledger.verify_replay())
        self.assertEqual(ledger.replay_verification_stats['full_calls'], 2)
        self.assertTrue(ledger.verify_replay())
        self.assertEqual(ledger.replay_verification_stats['cache_hits'], 1)

    def test_changed_current_records_are_compared_even_on_hit(self):
        ledger, rid = self.ledger()
        self.assertTrue(ledger.verify_replay())
        ledger._records[rid] = replace(ledger.record(rid), status=S.REVOKED)
        self.assertFalse(ledger.verify_replay())
        self.assertFalse(ledger.verify_replay(cache=False))
        self.assertEqual(ledger.replay_verification_stats['cache_hits'], 1)

    def test_mutating_original_record_cannot_mutate_cached_expected_record(self):
        ledger, rid = self.ledger()
        self.assertTrue(ledger.verify_replay())
        object.__setattr__(ledger.record(rid), 'expires_at_round', 999)
        self.assertFalse(ledger.verify_replay())
        self.assertFalse(ledger.verify_replay(cache=False))

    def test_prefix_tamper_with_same_length_and_tail_hash_rejected(self):
        ledger, _ = self.ledger()
        self.assertTrue(ledger.verify_replay())
        old_tail, old_length = ledger.events()[-1].event_hash, len(ledger.events())
        first = ledger._events[0]
        ledger._events[0] = replace(first, payload={**first.payload, 'persist_rounds': 999})
        self.assertEqual(len(ledger.events()), old_length)
        self.assertEqual(ledger.events()[-1].event_hash, old_tail)
        self.assertFalse(ledger.verify_replay())
        self.assertFalse(ledger.verify_replay(cache=False))

    def test_in_place_event_replacement_cannot_alias_cached_value_snapshot(self):
        ledger, _ = self.ledger()
        self.assertTrue(ledger.verify_replay())
        object.__setattr__(ledger._events[0], 'payload', {'user_id': 'mallory', 'persist_rounds': 3})
        self.assertFalse(ledger.verify_replay())

    def test_json_equivalent_malformed_payload_does_not_bypass_full_replay(self):
        from personal_assistant.contracts.permission import canonical_json, contract_json_round_trip
        ledger, _ = self.ledger()
        self.assertTrue(ledger.verify_replay())
        original = ledger._events[2]
        payload = contract_json_round_trip(original.payload)
        # Tuple -> list has the same canonical JSON, but is not equal to the
        # immutable command reconstructed by the unchanged full replay.
        changed = replace(original, payload=payload)
        self.assertEqual(canonical_json(original), canonical_json(changed))
        ledger._events[2] = changed
        self.assertFalse(ledger.verify_replay())
        self.assertFalse(ledger.verify_replay(cache=False))

    def test_reordering_and_truncation_rejected_like_full_baseline(self):
        for change in ('reorder', 'truncate'):
            ledger, _ = self.ledger()
            self.assertTrue(ledger.verify_replay())
            if change == 'reorder': ledger._events[1], ledger._events[2] = ledger._events[2], ledger._events[1]
            else: ledger._events.pop()
            self.assertFalse(ledger.verify_replay())
            self.assertFalse(ledger.verify_replay(cache=False))

    def test_disabled_cache_replays_each_time_and_switch_is_typed(self):
        ledger, _ = self.ledger()
        ledger.set_replay_cache_enabled(False)
        for _ in range(3): self.assertTrue(ledger.verify_replay())
        self.assertEqual(ledger.replay_verification_stats['full_calls'], 3)
        self.assertEqual(ledger.replay_verification_stats['cache_hits'], 0)
        with self.assertRaises(ValueError): ledger.set_replay_cache_enabled(1)
        self.assertFalse(ledger.verify_replay(cache='yes'))

    def test_failure_does_not_create_success_cache_entry(self):
        ledger, _ = self.ledger()
        calls = []
        def broken(events):
            calls.append(1)
            raise RuntimeError('replay failed')
        verifier = ReplayVerificationCache(broken)
        self.assertFalse(verifier.verify(ledger.events(), ledger.records()))
        self.assertFalse(verifier.verify(ledger.events(), ledger.records()))
        self.assertEqual(len(calls), 2)
        self.assertEqual(verifier.stats['cache_hits'], 0)

    def test_run_deadline_propagates_instead_of_reporting_corruption(self):
        ledger, _ = self.ledger()
        def timed_out(events):
            raise TimeoutError('diagnostic wall deadline')
        verifier = ReplayVerificationCache(timed_out)
        with self.assertRaises(TimeoutError):
            verifier.verify(ledger.events(), ledger.records())
        self.assertEqual(verifier.stats['verification_failures'], 0)

    def test_records_cannot_be_replaced_by_json_equivalent_dict(self):
        from personal_assistant.contracts.permission import contract_json_round_trip
        ledger, rid = self.ledger()
        self.assertTrue(ledger.verify_replay())
        ledger._records[rid] = contract_json_round_trip(ledger.record(rid))
        self.assertFalse(ledger.verify_replay())

    def test_cache_enabled_and_disabled_preserve_rule_execution_evidence(self):
        sys.path.insert(0, str(ROOT))
        from rl_testing.config import RunConfig
        from rl_testing.records import RunLog
        from rl_testing.runner import run_sequence, RuleSelection
        config = RunConfig(queries=(40, 41), max_seconds=30)
        original = UserAuthorizationLedger.__init__
        def uncached(self, *args, **kwargs):
            original(self, *args, **kwargs)
            self.set_replay_cache_enabled(False)
        cached = run_sequence(config, RuleSelection(), RunLog(config), queries=(40, 41), training=False)
        with patch.object(UserAuthorizationLedger, '__init__', uncached):
            full = run_sequence(config, RuleSelection(), RunLog(config), queries=(40, 41), training=False)
        self.assertEqual(cached.tasks, full.tasks)
        self.assertEqual(cached.user.ledger.records(), full.user.ledger.records())
        self.assertEqual(cached.user.ledger.events(), full.user.ledger.events())
        self.assertGreater(cached.user.ledger.replay_verification_stats['cache_hits'], 0)
        self.assertEqual(full.user.ledger.replay_verification_stats['cache_hits'], 0)


if __name__ == '__main__': unittest.main()
