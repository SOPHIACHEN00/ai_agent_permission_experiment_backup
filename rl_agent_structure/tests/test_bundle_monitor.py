import unittest
from dataclasses import replace
from helpers import binding
from personal_assistant.config import PermissionConfig, PERMISSION_SCHEMA
from personal_assistant.contracts.permission import PermissionChoice as C, AuthorizationStatus as S
from personal_assistant.contracts.tool_call import CompiledCall
from personal_assistant.permissions.ledger import UserAuthorizationLedger
from personal_assistant.execution.store import LocalToolStore
from personal_assistant.execution.adapter import ExecutionAdapter
from personal_assistant.permissions.effects import ExecutionDisposition as D
from personal_assistant.permissions.gates import CapabilityGates
from mock_tools.runtime import ReadWriteRuntime as MinimalToolBackend


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.b = binding(40); self.l = UserAuthorizationLedger('alice', PermissionConfig(3))
        self.p = self.l.begin_task('q40', 40)
        s = self.b.task.steps[0]; scope = s.operation_scopes[0]
        self.call = CompiledCall(s.step_id, scope, s.io_contract.public_contract(scope)['argument_bindings'], s.io_contract)
        self.keys = self.b.keys_for_scope(scope, 'alice', 'q40')
        self.gate = CapabilityGates('q40', 32)

    def allow(self, key, choice=C.ALLOW_REUSE):
        name = 'ask'+str(len(self.l.events()))
        req = self.l.request((key,), self.p, name, need_id=self.call.step_id)
        return self.l.apply_answer(req, key, choice, name+'reply', self.p)

    def adapter(self, backend=None):
        task = self.b.task
        store = LocalToolStore(task.records, backend=backend or MinimalToolBackend(), private_inputs=task.private_inputs, tool_models=task.tool_models)
        return ExecutionAdapter(task, store, self.l, gate=self.gate), store

    def activate(self, keys=None):
        self.gate.activate(self.keys if keys is None else keys, self.l, self.p, self.call.step_id)

    def test_partial_bundle_has_no_tool_effect(self):
        self.allow(self.keys[0]); adapter, store = self.adapter()
        self.activate((self.keys[0],))
        bundle = self.l.authorize_call(self.call, self.p)
        self.assertIsNone(bundle)
        outcome, _ = adapter.execute(self.call, None, 1, bundle=bundle, position=self.p)
        self.assertEqual(outcome.disposition, D.BLOCKED)
        self.assertEqual(store.snapshot()['outbox'], [])
        self.assertEqual(adapter.invocation_count, 0)
        self.allow(self.keys[1], C.ALLOW_ONCE)
        self.activate()
        bundle = self.l.authorize_call(self.call, self.p)
        outcome, _ = adapter.execute(self.call, None, 1, bundle=bundle, position=self.p)
        self.assertEqual(outcome.disposition, D.COMMITTED)
        self.assertEqual(adapter.invocation_count, 1)
        self.assertEqual(adapter.monitor.audit_events()[-1].payload['authorization_policy_version'], PERMISSION_SCHEMA)
        self.assertEqual(len(store.snapshot()['outbox']), 1)
        self.assertEqual([r.status for r in self.l.records()], [S.ACTIVE, S.CONSUMED])
        self.assertEqual(UserAuthorizationLedger.replay(self.l.events()).records(), self.l.records())

    def test_complete_consent_without_gates_has_no_effect(self):
        for key in self.keys: self.allow(key)
        adapter, store = self.adapter()
        outcome, _ = adapter.execute(self.call, None, 1,
                                    bundle=self.l.authorize_call(self.call, self.p), position=self.p)
        self.assertEqual(outcome.disposition, D.BLOCKED)
        self.assertEqual(adapter.invocation_count, 0)
        self.assertEqual(store.snapshot()['data_flows'], [])

    def test_gate_release_does_not_revoke_c_and_once_cannot_reactivate_after_use(self):
        for key in self.keys: self.allow(key, C.ALLOW_ONCE)
        self.activate(); records = self.l.records()
        self.gate.release((self.keys[0],), self.l, self.p)
        self.assertEqual(self.l.records(), records)
        self.activate()
        adapter, _ = self.adapter()
        outcome, _ = adapter.execute(self.call, None, 1,
                                    bundle=self.l.authorize_call(self.call, self.p), position=self.p)
        self.assertEqual(outcome.disposition, D.COMMITTED)
        self.assertEqual(self.gate.active_keys(self.l, self.p), frozenset())
        with self.assertRaises(ValueError): self.activate()

    def test_external_revoke_invalidates_gate_and_old_bundle(self):
        ids = [self.allow(key) for key in self.keys]
        self.activate()
        bundle = self.l.authorize_call(self.call, self.p)
        self.l.disable(ids[0], self.p)
        self.assertNotIn(self.keys[0], self.gate.active_keys(self.l, self.p))
        adapter, store = self.adapter()
        outcome, _ = adapter.execute(self.call, None, 1, bundle=bundle, position=self.p)
        self.assertEqual(outcome.disposition, D.BLOCKED)
        self.assertEqual(store.snapshot()['data_flows'], [])

    def test_one_use_permit_cannot_be_replayed(self):
        for key in self.keys: self.allow(key)
        self.activate(); adapter, store = self.adapter()
        captured = []
        actual_execute = adapter._tool._execute
        def capture(permit):
            captured.append(permit)
            return actual_execute(permit)
        adapter._tool._execute = capture
        outcome, _ = adapter.execute(self.call, None, 1,
                                    bundle=self.l.authorize_call(self.call, self.p), position=self.p)
        self.assertEqual(outcome.disposition, D.COMMITTED)
        before = store.snapshot()
        with self.assertRaises(ValueError): adapter._tool._invoke(captured[0])
        self.assertEqual(store.snapshot(), before)

    def test_stale_revision_revocation_and_second_reservation_reject(self):
        ids = [self.allow(k) for k in self.keys]
        bundle = self.l.authorize_call(self.call, self.p)
        self.l.disable(ids[0], self.p)
        with self.assertRaises(ValueError): self.l.reserve_bundle(bundle, self.call, self.p)
        self.allow(self.keys[0])
        bundle = self.l.authorize_call(self.call, self.p)
        token = self.l.reserve_bundle(bundle, self.call, self.p)
        with self.assertRaises(ValueError): self.l.reserve_bundle(bundle, self.call, self.p)
        self.l.abort_bundle(token, self.p)
        with self.assertRaises(ValueError): self.l.commit_bundle(token, self.p)

    def test_unknown_effect_is_absorbing_and_does_not_release_authority(self):
        class Faulty(MinimalToolBackend):
            def prepare_io_effect(self, *args, **kwargs): raise RuntimeError('unknown transport outcome')
        for k in self.keys: self.allow(k, C.ALLOW_ONCE)
        self.activate()
        adapter, store = self.adapter(Faulty())
        out, _ = adapter.execute(self.call, None, 1, bundle=self.l.authorize_call(self.call, self.p), position=self.p)
        self.assertEqual(out.disposition, D.UNKNOWN)
        self.assertTrue(out.task_snapshot.has_unknown_effect)
        self.assertTrue(all(r.status == S.RECONCILIATION_REQUIRED for r in self.l.records()))
        self.assertIsNone(self.l.authorize_call(self.call, self.p))

    def test_absent_effect_releases_all_reservations(self):
        class Absent(MinimalToolBackend):
            def prepare_io_effect(self, *args, **kwargs): raise ValueError('failed before effect')
        for k in self.keys: self.allow(k, C.ALLOW_ONCE)
        self.activate()
        adapter, store = self.adapter(Absent())
        out, _ = adapter.execute(self.call, None, 1, bundle=self.l.authorize_call(self.call, self.p), position=self.p)
        self.assertEqual(out.disposition, D.ABSENT)
        self.assertTrue(all(r.status == S.ACTIVE and r.remaining_uses == 1 for r in self.l.records()))

    def test_bundle_binds_arguments_task_and_recipient(self):
        for k in self.keys: self.allow(k)
        bundle = self.l.authorize_call(self.call, self.p)
        for call in (replace(self.call, arguments={}), replace(self.call, scope=replace(self.call.scope, recipient='Local Search'))):
            with self.assertRaises(ValueError): self.l.reserve_bundle(bundle, call, self.p)
        with self.assertRaises(ValueError): self.l.reserve_bundle(bundle, self.call, replace(self.p, task_id='other'))


if __name__ == '__main__': unittest.main()
