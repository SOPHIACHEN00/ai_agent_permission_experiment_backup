"""Approved task adaptations; no API, no learning, no new benchmark queries."""
import unittest
from types import SimpleNamespace

from helpers import binding
from mock_tools.tasks import build_wu_task
from mock_tools.runtime import ReadWriteRuntime
from personal_assistant.contracts.permission import contract_json_round_trip
from personal_assistant.contracts.tool_call import CompiledCall
from personal_assistant.execution.store import LocalToolStore
from personal_assistant.integration.task_semantics import (
    required_field_sets, necessary_fields, extra_fields, need_id_for,
    is_necessary_field, needed_keys,
)


def run_dataflow(task, select_scope=lambda step: step.operation_scopes[0]):
    """Exercise the unchanged tool backend in isolation; not an auth bypass test."""
    store = LocalToolStore(task.records, backend=ReadWriteRuntime(),
                           private_inputs=task.private_inputs, tool_models=task.tool_models)
    for step in task.steps:
        scope = select_scope(step)
        call = CompiledCall(step.step_id, scope,
                            step.io_contract.public_contract(scope)['argument_bindings'], step.io_contract)
        store.commit(store.prepare(call))
    facts = SimpleNamespace(primary_complete=True, has_unknown_effect=False)
    return store.snapshot(), facts


class FourActionTaskContractTests(unittest.TestCase):
    def test_q55_has_two_minimal_ranges_and_original_broad_range(self):
        original = build_wu_task(55)
        task = binding(55).task
        step = task.steps[0]
        self.assertEqual([len(s.data_attributes) for s in step.operation_scopes], [11, 11, 12])
        self.assertEqual(len(original.steps[0].operation_scopes), 1)
        self.assertEqual(task.goal, original.goal)
        self.assertEqual(task.oracle.source, original.oracle.source)
        self.assertEqual(set(task.oracle.expectations[step.step_id]['required_fields']),
                         set(original.oracle.expectations[step.step_id]['required_fields']))
        self.assertEqual(len(required_field_sets(task, step.step_id)), 2)
        self.assertIn('H55-1', task.oracle.extensions[-1])

    def test_each_q55_alternative_executes_and_completes_without_extra_disclosure(self):
        task = binding(55).task
        for index, selected_contact in ((0, 'Email address'), (1, 'Phone number')):
            with self.subTest(contact=selected_contact):
                snapshot, facts = run_dataflow(task, lambda step: step.operation_scopes[index])
                self.assertTrue(task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])
                selected = snapshot['outbox'][0]['data']
                self.assertIn(selected_contact, selected)
                self.assertEqual(len(selected), 11)
                self.assertEqual(extra_fields(task, task.steps[0].step_id, selected), frozenset())
                # The original oracle and raw source labels remain unchanged.
                self.assertFalse(build_wu_task(55).oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])

    def test_q55_both_contacts_have_exactly_one_execution_extra(self):
        task = binding(55).task
        snapshot, facts = run_dataflow(task, lambda step: step.operation_scopes[-1])
        self.assertTrue(task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])
        fields = snapshot['outbox'][0]['data']
        self.assertEqual(len(fields), 12)
        self.assertEqual(len(extra_fields(task, task.steps[0].step_id, fields)), 1)
        self.assertEqual(sum(flow['source_negative'] for flow in snapshot['data_flows']), 0)

    def test_missing_common_data_or_unknown_effect_is_not_success(self):
        task = binding(55).task
        snapshot, facts = run_dataflow(task)
        field = next(f for f in snapshot['outbox'][0]['data'] if f not in ('Email address', 'Phone number'))
        del snapshot['outbox'][0]['data'][field]
        snapshot['events'][0]['fields'].remove(field)
        snapshot['data_flows'] = [flow for flow in snapshot['data_flows'] if flow['field'] != field]
        self.assertFalse(task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])
        snapshot, facts = run_dataflow(task)
        facts.has_unknown_effect = True
        self.assertFalse(task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])

    def test_valid_phone_receipt_remains_valid_before_final_answer(self):
        task = binding(55).task
        snapshot, facts = run_dataflow(task, lambda step: step.operation_scopes[1])
        result = task.oracle.evaluate(snapshot, facts, None, None)
        self.assertFalse(result['success'])
        self.assertTrue(result['step_checks'][task.steps[0].step_id])

    def test_contact_need_is_shared_but_authority_keys_remain_distinct(self):
        b = binding(55); task = b.task; step = task.steps[0]
        self.assertEqual(need_id_for(task, step.step_id, 'Email address'),
                         need_id_for(task, step.step_id, 'Phone number'))
        self.assertTrue(is_necessary_field(task, step.step_id, 'Phone number'))
        email_keys = needed_keys(b, step.step_id, step.operation_scopes[0], 'alice', 'task55')
        phone_keys = needed_keys(b, step.step_id, step.operation_scopes[1], 'alice', 'task55')
        self.assertEqual(len(email_keys), 11)
        self.assertEqual(len(phone_keys), 11)
        self.assertEqual(len(email_keys & phone_keys), 10)
        self.assertEqual(needed_keys(b, None, None, 'alice', 'task55'), frozenset())
        self.assertEqual(necessary_fields(task, step.step_id, step.operation_scopes[-1]),
                         frozenset(step.operation_scopes[0].data_attributes))

    def test_all_original_65_tasks_keep_compatible_minimal_tool_contracts(self):
        for query_id in range(65):
            with self.subTest(query_id=query_id):
                b = binding(query_id)
                snapshot, facts = run_dataflow(b.task)
                self.assertTrue(b.task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])
                for step in b.task.steps:
                    for scope in step.operation_scopes:
                        args = step.io_contract.public_contract(scope)['argument_bindings']
                        ReadWriteRuntime().validate_call(CompiledCall(step.step_id, scope, args, step.io_contract))
                        self.assertEqual(len(extra_fields(b.task, step.step_id, scope.data_attributes)),
                                         len(set(scope.data_attributes) - necessary_fields(b.task, step.step_id, scope)))
                if query_id != 55:
                    original = build_wu_task(query_id)
                    self.assertEqual(contract_json_round_trip(original.steps), contract_json_round_trip(b.task.steps))
                if query_id in (63, 64):
                    step = b.task.steps[0]
                    self.assertEqual(len(needed_keys(b, step.step_id, step.operation_scopes[0], 'alice', 'setup')), 1)

    def test_undeclared_fields_and_missing_steps_fail_closed(self):
        task = binding(55).task
        with self.assertRaises(ValueError): need_id_for(task, task.steps[0].step_id, 'invented')
        with self.assertRaises(ValueError): required_field_sets(task, 'not-a-step')
        snapshot, facts = run_dataflow(task)
        snapshot['data_flows'].append({'step_id': 'foreign', 'field': 'invented',
                                      'direction': 'write', 'source_negative': False})
        self.assertFalse(task.oracle.evaluate(snapshot, facts, 'done', 'completed')['success'])


if __name__ == '__main__': unittest.main()
