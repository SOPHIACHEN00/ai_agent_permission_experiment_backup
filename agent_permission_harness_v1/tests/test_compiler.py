import importlib
import unittest

from agent_mock_harness_v0.agent_protocol import parse_agent_decision
from agent_permission_harness_v1.contracts import TaskStepSpec
from test_control import scope


def decision(tool='Cloud Drive', operation='read', resource='file', fields=('title',), arguments=None):
    return parse_agent_decision({'kind': 'tool', 'tool': tool, 'operation': operation,
        'resource': resource, 'requested_fields': list(fields),
        'arguments': arguments if arguments is not None else {'record_id': resource},
        'answer': None, 'answer_status': None})


class CompilerTests(unittest.TestCase):
    def compiler(self):
        try:
            return importlib.import_module('agent_permission_harness_v1.compiler')
        except ModuleNotFoundError:
            self.fail('generic intent compiler is not implemented')

    def test_only_declared_projection_and_observed_record(self):
        module = self.compiler()
        step = TaskStepSpec('read', (scope(),), (scope(),), {'record_id': 'file'}, True)
        with self.assertRaises(ValueError):
            module.compile_intent(decision(), step, frozenset())
        call = module.compile_intent(decision(), step, frozenset({'file'}))
        self.assertEqual(call.scope, scope())
        with self.assertRaises(ValueError):
            module.compile_intent(decision(fields=('title', 'private_notes')), step, frozenset({'file'}))
        with self.assertRaises(ValueError):
            module.compile_intent(decision(arguments={'record_id': 'other'}), step, frozenset({'file'}))

    def test_request_does_not_mint_scope_or_authority(self):
        module = self.compiler()
        step = TaskStepSpec('read', (scope(),), (scope(),), {'record_id': 'file'})
        with self.assertRaises(ValueError):
            module.compile_intent(decision(tool='Bank'), step, frozenset())
        with self.assertRaises(ValueError):
            module.compile_intent(decision(arguments={'record_id': 'file', 'permission': 'allow'}), step, frozenset())


if __name__ == '__main__':
    unittest.main()
