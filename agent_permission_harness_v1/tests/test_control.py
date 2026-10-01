import importlib
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import AuthorizationStatus, ControllerAction, PermissionChoice, Scope


def scope(fields=('title',), resource='file', operation='read'):
    return Scope('Work', 'Cloud Drive', resource, fields, operation, 'task', 'self', 'session')


class ControlTests(unittest.TestCase):
    def modules(self):
        try:
            return (importlib.import_module('agent_permission_harness_v1.contracts'),
                    importlib.import_module('agent_permission_harness_v1.candidates'))
        except ModuleNotFoundError:
            self.fail('six-action candidate and scope contracts are not implemented')

    def test_all_six_types_with_masks_and_bound_scope(self):
        c, m = self.modules()
        narrow, broad = scope(), scope(('title', 'private_notes'))
        step = c.TaskStepSpec('read', (narrow, broad), (narrow, broad), {'record_id': 'file'})
        ledger = AuthorizationService('candidate-test', 30)
        call = c.CompiledCall('read', broad, {'record_id': 'file'})
        candidates = m.build_candidates(call, step, ledger, 0)
        self.assertEqual(set(x.action for x in candidates), set(ControllerAction))
        self.assertFalse(any(x.valid for x in candidates if x.action == ControllerAction.EXECUTE_WITH_AUTHORIZATION))
        record = ledger.start_request(broad, 0, 'human-1')
        ledger.apply_permission_choice(record.authorization_id, PermissionChoice.ALLOW_REUSE, 0)
        candidates = m.build_candidates(call, step, ledger, 1)
        execute = [x for x in candidates if x.valid and x.action == ControllerAction.EXECUTE_WITH_AUTHORIZATION]
        self.assertEqual({x.operation_scope for x in execute}, {narrow, broad})
        self.assertTrue(all(x.authorization_id == record.authorization_id for x in execute))
        ledger.disable(record.authorization_id, 1)
        self.assertFalse(any(x.valid for x in m.build_candidates(call, step, ledger, 2)
                             if x.action == ControllerAction.EXECUTE_WITH_AUTHORIZATION))

    def test_scope_expansion_needs_new_consent(self):
        c, m = self.modules()
        narrow, broad = scope(), scope(('title', 'private_notes'))
        step = c.TaskStepSpec('read', (broad,), (narrow, broad), {'record_id': 'file'})
        ledger = AuthorizationService('expand-test', 30)
        record = ledger.start_request(narrow, 0, 'human-1')
        ledger.apply_permission_choice(record.authorization_id, PermissionChoice.ALLOW_REUSE, 0)
        call = c.CompiledCall('read', broad, {'record_id': 'file'})
        candidates = m.build_candidates(call, step, ledger, 1)
        self.assertFalse(any(x.valid for x in candidates if x.action == ControllerAction.EXECUTE_WITH_AUTHORIZATION))
        self.assertTrue(any(x.valid and x.request_scope == broad for x in candidates
                            if x.action == ControllerAction.REQUEST_REFRESH))
        self.assertEqual(ledger.record(record.authorization_id).status, AuthorizationStatus.ACTIVE)

    def test_manifest_is_immutable_and_does_not_alias_input(self):
        c, _ = self.modules()
        args = {'data': {'title': 'x'}}
        step = c.TaskStepSpec('read', (scope(),), (scope(),), args)
        args['data']['title'] = 'changed'
        self.assertEqual(step.arguments['data']['title'], 'x')
        with self.assertRaises(TypeError):
            step.arguments['data']['title'] = 'evil'


if __name__ == '__main__':
    unittest.main()
