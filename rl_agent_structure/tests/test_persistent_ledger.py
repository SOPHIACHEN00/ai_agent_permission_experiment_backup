import unittest
from dataclasses import replace
from helpers import binding, key_for
from personal_assistant.config import PermissionConfig
from personal_assistant.contracts.permission import PermissionChoice as C


class PersistentLedgerTests(unittest.TestCase):
    def ledger(self, n=3, user='alice'):
        from personal_assistant.permissions.ledger import UserAuthorizationLedger
        return UserAuthorizationLedger(user, PermissionConfig(n))

    def answer(self, l, p, key, choice=C.ALLOW_REUSE, name='r'):
        request = l.request((key,), p, name)
        return l.apply_answer(request, key, choice, name+'-answer', p)

    def test_persistent_answer_expires_at_task_13(self):
        l = self.ledger()
        for i in range(1, 10):
            p = l.begin_task(str(i), 40); l.finish_task(p)
        p = l.begin_task('10', 40)
        k = key_for()
        rid = self.answer(l, p, k)
        self.assertEqual(l.record(rid).expires_at_round, 13)
        valid = []
        for i in range(10, 14):
            if i > 10: p = l.begin_task(str(i), 41)
            if l.decision(k, p) is not None: valid.append(i)
            l.finish_task(p)
        self.assertEqual(valid, [10, 11, 12])

    def test_n1_once_and_denial_expire_without_turning_into_allow(self):
        for choice in C:
            l = self.ledger(1); p = l.begin_task('a', 40); k = key_for()
            self.answer(l, p, k, choice)
            l.finish_task(p); p = l.begin_task('b', 41)
            self.assertIsNone(l.decision(k, p))

    def test_revocation_cannot_be_reactivated_from_history(self):
        l = self.ledger(); p = l.begin_task('a', 40); k = key_for()
        rid = self.answer(l, p, k); l.disable(rid, p)
        l.finish_task(p); p = l.begin_task('b', 41)
        self.assertIsNone(l.decision(k, p))
        self.assertEqual(len(l.records()), 1)

    def test_never_blocks_reask_refresh_and_disable_but_user_can_change(self):
        l = self.ledger(); p = l.begin_task('a', 40); k = key_for()
        rid = self.answer(l, p, k, C.DENY_PERSIST)
        with self.assertRaises(ValueError): l.request((k,), p, 'again')
        with self.assertRaises(ValueError): l.disable(rid, p)
        l.user_change(k, C.ALLOW_REUSE, 'explicit-change', p)
        self.assertEqual(l.decision(k, p).choice, C.ALLOW_REUSE)

    def test_answers_deduplicate_conflicts_and_late_answers_reject(self):
        l = self.ledger(); p = l.begin_task('a', 40); k = key_for()
        req = l.request((k,), p, 'one')
        rid = l.apply_answer(req, k, C.ALLOW_ONCE, 'answer', p)
        self.assertEqual(l.apply_answer(req, k, C.ALLOW_ONCE, 'answer', p), rid)
        with self.assertRaises(ValueError): l.apply_answer(req, k, C.DENY_REASK, 'answer', p)
        req2 = l.request((key_for(tool='Local Search'),), p, 'pending')
        l.finish_task(p); p2 = l.begin_task('b', 41)
        with self.assertRaises(ValueError): l.apply_answer(req2, key_for(tool='Local Search'), C.ALLOW_REUSE, 'late', p2)
        with self.assertRaises(ValueError): l.apply_answer(req2, key_for(tool='Local Search'), C.ALLOW_REUSE, 'late', p)

    def test_clock_resume_replay_and_user_isolation(self):
        from personal_assistant.permissions.ledger import UserAuthorizationLedger
        l = self.ledger(); p = l.begin_task('a', 40)
        self.assertEqual(l.begin_task('a', 40), p)
        with self.assertRaises(ValueError): l.begin_task('a', 41)
        with self.assertRaises(ValueError): l.request((key_for(user='bob'),), p, 'foreign')
        self.answer(l, p, key_for())
        replay = UserAuthorizationLedger.replay(l.events())
        self.assertEqual(replay.records(), l.records())
        self.assertEqual(replay.position, p)
        other = self.ledger(user='bob'); op = other.begin_task('a', 40)
        self.assertIsNone(other.decision(key_for(user='bob'), op))

    def test_reply_to_pre_revocation_request_cannot_restore_revoked_allow(self):
        l = self.ledger(); p = l.begin_task('a', 40); k = key_for()
        rid = self.answer(l, p, k)
        pending = l.request((k,), p, 'refresh-before-revoke')
        l.disable(rid, p)
        with self.assertRaises(ValueError): l.apply_answer(pending, k, C.ALLOW_REUSE, 'late-refresh', p)
        self.assertIsNone(l.decision(k, p))

    def test_new_explicit_denial_invalidates_earlier_pending_question(self):
        l = self.ledger(); p = l.begin_task('a', 40); k = key_for()
        pending = l.request((k,), p, 'before-explicit-change')
        l.user_change(k, C.DENY_PERSIST, 'new-explicit-never', p)
        with self.assertRaises(ValueError): l.apply_answer(pending, k, C.ALLOW_REUSE, 'stale-answer', p)
        self.assertEqual(l.decision(k, p).choice, C.DENY_PERSIST)


if __name__ == '__main__': unittest.main()
