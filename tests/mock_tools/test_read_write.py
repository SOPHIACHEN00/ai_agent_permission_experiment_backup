"""Real Agent checks for the minimal Wu read/write environment (no torch/API)."""
from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'rl_agent_structure/src'), str(PROJECT)]

from personal_assistant.contracts.permission import AuthorizationStatus, ControllerAction as A, PermissionChoice as P, contract_json_round_trip
from personal_assistant.permissions.effects import ExecutionDisposition
from personal_assistant.planning.compiler import project_call
from personal_assistant.contracts.tool_call import CompiledCall
from personal_assistant.interaction.human_channel import HumanReply, LocalHumanChannel
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from personal_assistant.execution.runner import AgentSession
from mock_tools.runtime import ReadWriteRuntime


class MinimalWuTests(unittest.TestCase):
    def task(self, query_id):
        try:
            module = importlib.import_module('mock_tools.tasks')
        except ModuleNotFoundError:
            self.fail('minimal read/write tasks are not implemented in mock_tools')
        return module.build_wu_task(query_id)

    def session(self, query_id, reply=P.ALLOW_REUSE):
        task = self.task(query_id)
        channel = LocalHumanChannel(lambda m: HumanReply(m.message_id, 'permission', reply))
        return AgentSession(task, ScriptedPlanner(fixture_decisions(task)), channel=channel,
                            tools=ReadWriteRuntime(), max_planner_turns=24, max_control_steps=80)

    def call(self, step, broad=False):
        scope = step.operation_scopes[-1 if broad else 0]
        return CompiledCall(step.step_id, scope, step.io_contract.public_contract(scope)['argument_bindings'], step.io_contract)

    def grant(self, session, call, choice=P.ALLOW_REUSE):
        position = session.user_context.position
        keys = session.ledger.call_keys(call, position)
        message_id = f'fixture-answer-{len(session.ledger.events())}'
        request = session.ledger.request(keys, position, message_id, need_id=call.step_id)
        records = tuple(session.ledger.apply_answer(request, key, choice, f'{message_id}-{i}', position)
                        for i, key in enumerate(keys))
        session.gate.activate(keys, session.ledger, position, call.step_id)
        return records

    def execute(self, session, call):
        position = session.user_context.position
        bundle = session.ledger.authorize_call(call, position)
        return session.adapter.execute(call, None, max(1, position.decision_index),
                                       bundle=bundle, position=position)

    def test_all_original_queries_run_without_business_simulation(self):
        source = Path(__file__).resolve().parents[2] / 'external/ai-agent-permissions/queries.json'
        rows = json.loads(source.read_text(encoding='utf-8-sig'))
        seen, domains = set(), set()
        for row in rows:
            with self.subTest(query_id=row['id']):
                session = self.session(row['id'])
                result = session.run()
                self.assertEqual(session.task.goal, row['query'])
                self.assertEqual(contract_json_round_trip(session.task.oracle.source), row)
                self.assertTrue(result.oracle_result['dataflow_complete'], (result.status, result.error))
                self.assertTrue(result.monitor_audit_verified)
                self.assertTrue(result.ledger_replay_verified)
                self.assertFalse(result.oracle_result['business_answer_quality_evaluated'])
                self.assertEqual(result.oracle_result['privacy_proxy']['source_negative_field_instances'], 0)
                for step in session.task.steps:
                    scope = step.operation_scopes[0]
                    self.assertIn(scope.operation, {'read', 'update', 'control'})
                    seen.add(scope.tool)
                    domains.add(scope.domain)
        self.assertEqual(len(rows), 65)
        self.assertEqual(len(seen - {'mira'}), 28)
        self.assertEqual(len(domains), 8)

    def test_q22_read_then_write_uses_same_report_and_no_email_business_sim(self):
        result = self.session(22).run()
        flows = result.tool_snapshot['data_flows']
        self.assertEqual([(f['direction'], f['tool'], f['field']) for f in flows], [
            ('read', 'Cloud Drive', 'Revenue report'),
            ('write', 'Email', 'Revenue report'),
            ('write', 'Email', "Colleague's email"),
            ('write', 'Email', 'Email content')])
        email = result.tool_snapshot['outbox'][0]
        self.assertEqual(email['data']['Revenue report'], flows[0]['value'])
        self.assertEqual(set(email['data']), {'Revenue report', "Colleague's email", 'Email content'})
        self.assertEqual(email['simulation'], 'wu_minimal_read_write_v1')
        self.assertNotIn('subject', email)  # no invented email workflow

    def test_weather_records_location_disclosure_but_does_not_fabricate_forecast(self):
        session = self.session(38)
        result = session.run()
        event = result.tool_snapshot['events'][0]
        self.assertEqual(event['operation'], 'update')  # write alias, not a vendor API
        self.assertEqual(event['result']['status'], 'recorded_locally')
        self.assertNotIn('condition', event['result'])
        self.assertNotIn('temperature_c', event['result'])
        self.assertEqual(result.tool_snapshot['outbox'][0]['tool'], 'Weather')
        self.assertEqual(set(result.tool_snapshot['outbox'][0]['data']), {'User location'})
        private_value = result.tool_snapshot['outbox'][0]['data']['User location']
        self.assertNotIn(private_value, str(session._available_calls(session.task.steps[0])))
        self.assertNotIn(private_value, str(event['result']))

    def test_waiting_and_both_denials_produce_no_dataflow(self):
        task = self.task(38)
        waiting = AgentSession(task, ScriptedPlanner(fixture_decisions(task)), tools=ReadWriteRuntime()).run()
        self.assertEqual(waiting.status, 'awaiting_human')
        self.assertEqual(waiting.tool_snapshot['events'], [])
        for choice in (P.DENY_REASK, P.DENY_PERSIST):
            with self.subTest(choice=choice):
                result = self.session(38, choice).run()
                self.assertEqual(result.tool_snapshot['data_flows'], [])
                self.assertEqual(result.tool_snapshot['outbox'], [])
                self.assertFalse(result.oracle_result['dataflow_complete'])

    def test_read_grant_is_not_permission_to_forward_report_to_email(self):
        session = self.session(22)
        read, write = (self.call(step) for step in session.task.steps)
        self.grant(session, read)
        self.assertEqual(self.execute(session, read)[0].disposition,
                         ExecutionDisposition.COMMITTED)
        before = session.store.snapshot()
        execution, _ = self.execute(session, write)
        self.assertNotEqual(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(session.store.snapshot(), before)

    def test_projection_under_broad_grant_writes_only_narrow_fields(self):
        session = self.session(38)
        step = session.task.steps[0]
        broad, narrow = self.call(step, broad=True), self.call(step)
        self.assertEqual(set(broad.scope.data_attributes), {'User location', 'Allergies', 'Energy consumption logs', 'Home presence'})
        granted = self.grant(session, broad)
        projected = project_call(broad, narrow.scope)
        result, _ = self.execute(session, projected)
        self.assertEqual(result.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(set(session.store.snapshot()['outbox'][0]['data']), {'User location'})
        # Narrow execution must not pretend the remaining broad grant vanished.
        self.assertEqual({session.ledger.record(rid).key.data_item for rid in granted},
                         set(broad.scope.data_attributes))
        self.assertTrue(all(session.ledger.record(rid).status == AuthorizationStatus.ACTIVE for rid in granted))

    def test_expansion_requires_new_actual_answers_for_missing_fields(self):
        session = self.session(38)
        step = session.task.steps[0]
        narrow, broad = self.call(step), self.call(step, broad=True)
        self.grant(session, narrow)
        blocked, _ = self.execute(session, broad)
        self.assertNotEqual(blocked.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(session.store.snapshot()['data_flows'], [])
        granted = self.grant(session, broad, P.ALLOW_ONCE)
        execution, _ = self.execute(session, broad)
        self.assertEqual(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertTrue(all(session.ledger.record(rid).status == AuthorizationStatus.CONSUMED for rid in granted))
        checked = session.task.oracle.evaluate(session.store.snapshot(), session.adapter.task_engine.snapshot(), 'done', 'completed')
        self.assertEqual(checked['privacy_proxy']['source_negative_field_instances'], 3)

    def test_withdrawn_extra_field_blocks_old_bundle_but_narrow_call_remains_legal(self):
        session = self.session(38)
        step = session.task.steps[0]
        broad, narrow = self.call(step, broad=True), self.call(step)
        granted = self.grant(session, broad)
        position = session.user_context.position
        stale = session.ledger.authorize_call(broad, position)
        extra = next(rid for rid in granted
                     if session.ledger.record(rid).key.data_item not in narrow.scope.data_attributes)
        session.ledger.disable(extra, position)
        self.assertEqual(session.ledger.record(extra).status, AuthorizationStatus.REVOKED)
        execution, _ = session.adapter.execute(broad, None, 1, bundle=stale, position=position)
        self.assertNotEqual(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertNotEqual(self.execute(session, broad)[0].disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(self.execute(session, narrow)[0].disposition, ExecutionDisposition.COMMITTED)

    def test_revoked_and_expired_grants_cannot_touch_tool(self):
        for mode in ('revoked', 'expired'):
            with self.subTest(mode=mode):
                session = self.session(38)
                call = self.call(session.task.steps[0])
                granted = self.grant(session, call)
                if mode == 'revoked':
                    session.ledger.disable(granted[0], session.user_context.position)
                else:
                    # The convenience session grants persistent consent for one round.
                    self.assertTrue(session.run().oracle_result['dataflow_complete'])
                    user, binding = session.user_context, session.binding
                    session = user.start_task('next-round', binding,
                        ScriptedPlanner(fixture_decisions(binding.task)), LocalHumanChannel(), ReadWriteRuntime())
                    self.assertEqual(session.ledger.record(granted[0]).status, AuthorizationStatus.EXPIRED)
                execution, _ = self.execute(session, call)
                self.assertNotEqual(execution.disposition, ExecutionDisposition.COMMITTED)
                self.assertEqual(session.store.snapshot()['outbox'], [])
                self.assertEqual(session.store.snapshot()['data_flows'], [])

    def test_setup_only_camera_and_lock_have_no_history_reads(self):
        for qid, tool in ((63, 'Security Camera'), (64, 'Smart Lock')):
            with self.subTest(query_id=qid):
                session = self.session(qid)
                result = session.run()
                self.assertEqual(result.prompts_used, 1)
                self.assertTrue(result.oracle_result['dataflow_complete'])
                self.assertEqual(result.tool_snapshot['data_flows'], [])
                self.assertEqual(result.tool_snapshot['reads'], [])
                event = result.tool_snapshot['events'][0]
                self.assertEqual(event['tool'], tool)
                self.assertEqual(event['operation'], 'control')
                self.assertEqual(event['fields'], [])
                self.assertTrue(result.oracle_result['omitted_source_data'])

    def test_caption_extension_stays_separate_from_original_source(self):
        session = self.session(54)
        result = session.run()
        self.assertNotIn('Instagram post content', session.task.oracle.source['data_tool2'])
        flows = [f for f in result.tool_snapshot['data_flows'] if f['tool'] == 'Instagram' and f['field'] == 'Instagram post content']
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0]['direction'], 'write')
        self.assertEqual(flows[0]['source_kind'], 'approved_execution_extension')

    def test_unapproved_parameters_raw_values_and_unknown_fields_fail_closed(self):
        session = self.session(38)
        call = self.call(session.task.steps[0])
        for bad in (
            dict(call.arguments, parameters={'send_to': 'Other Tool'}),
            dict(call.arguments, inputs={'User location': 'raw-private-value'}),
            dict(call.arguments, record_id='another-person'),
        ):
            with self.subTest(arguments=bad), self.assertRaises(ValueError):
                session.adapter.execute(replace(call, arguments=bad), None, 0)
        with self.assertRaises(ValueError):
            session.adapter.execute(replace(call, scope=replace(call.scope, data_attributes=('new_private_field',))), None, 0)
        self.assertEqual(session.store.snapshot()['events'], [])

    def test_forwarding_requires_an_observed_value_not_a_fabricated_payload(self):
        session = self.session(22)
        write = self.call(session.task.steps[1])
        # Even a direct trusted preparation cannot invent the earlier read.
        with self.assertRaises(ValueError):
            session.store.prepare(write)
        self.assertEqual(session.store.snapshot()['data_flows'], [])

    def test_oracle_does_not_accept_success_flag_without_actual_write(self):
        session = self.session(22)
        result = session.run()
        snapshot = dict(result.tool_snapshot)
        snapshot['outbox'] = []
        checked = session.task.oracle.evaluate(snapshot, session.adapter.task_engine.snapshot(), 'done', 'completed')
        self.assertFalse(checked['dataflow_complete'])
        self.assertNotIn('business_complete', checked['task_facts'])

    def test_oracle_rejects_unlogged_payload_and_misdirected_flow(self):
        session = self.session(38)
        result = session.run()
        for corruption in ('unlogged_payload', 'wrong_recipient'):
            snapshot = contract_json_round_trip(result.tool_snapshot)
            if corruption == 'unlogged_payload':
                snapshot['outbox'][0]['data']['Unrequested secret'] = 'synthetic extra'
            else:
                snapshot['data_flows'][0]['recipient'] = 'Email'
            checked = session.task.oracle.evaluate(snapshot, session.adapter.task_engine.snapshot(), 'done', 'completed')
            with self.subTest(corruption=corruption):
                self.assertFalse(checked['dataflow_complete'])

    def test_four_controller_actions_use_real_dispatcher_and_release_preserves_consent(self):
        task = self.task(38)
        narrow = set(task.steps[0].operation_scopes[0].data_attributes)
        schedule = iter([(A.REQUEST, narrow), (A.RELEASE, None),
                         (A.REQUEST, narrow), (A.EXECUTE, narrow),
                         (A.RELEASE, None), (A.END, None)])
        class Sequence:
            def choose(self, view):
                action, fields = next(schedule)
                for candidate in view.candidates:
                    scope = candidate.operation_scope or candidate.request_scope
                    if candidate.valid and candidate.action == action and (fields is None or set(scope.data_attributes) == fields):
                        return candidate.candidate_id
                raise AssertionError('expected real controller candidate missing')
        def reply(message):
            return HumanReply(message.message_id, 'permission', P.ALLOW_REUSE)
        session = AgentSession(task, ScriptedPlanner(fixture_decisions(task)),
                               Sequence(), LocalHumanChannel(reply), tools=ReadWriteRuntime())
        result = session.run()
        self.assertEqual(result.status, 'completed')
        self.assertEqual({r['selected']['action'] for r in result.controller_trace}, {a.value for a in A})
        self.assertEqual(result.prompts_used, 1)  # reopening G reused actual C
        self.assertEqual(result.escalations_used, 0)
        self.assertEqual(len(result.tool_snapshot['events']), 1)
        self.assertEqual([r.status for r in session.ledger.records()], [AuthorizationStatus.ACTIVE])
        self.assertEqual(set(result.tool_snapshot['outbox'][0]['data']), {'User location'})
        self.assertTrue(result.ledger_replay_verified)
        self.assertTrue(result.monitor_audit_verified)

    def test_offline_entry_preserves_source_and_never_overwrites_results(self):
        try:
            run = importlib.import_module('mock_tools.run').run
        except ModuleNotFoundError:
            self.fail('minimal offline runner is not implemented')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'run'
            summary = run(output, (22, 38, 63, 64))
            self.assertEqual(summary['passed'], 4)
            self.assertEqual(summary['query_count'], 4)
            self.assertEqual(summary['api_calls'], 0)
            self.assertEqual(summary['training_steps'], 0)
            coverage = json.loads((output / 'coverage.json').read_text(encoding='utf-8'))
            self.assertEqual([r['query_id'] for r in coverage], [22, 38, 63, 64])
            self.assertEqual(coverage[1]['original_source']['query'], "How's the weather?")
            with self.assertRaises(FileExistsError):
                run(output, (38,))
        # A bad output path must not pollute the clean source package.
        with self.assertRaises(ValueError):
            run(Path(__file__).resolve().parents[2] / 'mock_tools/forbidden-results', (38,))

    def test_pending_human_resume_does_not_repeat_a_message_or_effect(self):
        # Break caught: resuming a waiting session double-sends or double-writes.
        task = self.task(38)
        channel = LocalHumanChannel(session_id='resume-check')
        session = AgentSession(task, ScriptedPlanner(fixture_decisions(task)),
                               channel=channel, tools=ReadWriteRuntime())
        pending = session.run()
        polled = session.run()
        self.assertEqual(pending.awaiting_message_id, polled.awaiting_message_id)
        self.assertEqual(len(channel.snapshot()['messages']), 1)
        self.assertEqual(session.adapter.invocation_count, 0)
        channel.submit(HumanReply(pending.awaiting_message_id, 'permission', P.ALLOW_ONCE))
        result = session.run()
        self.assertEqual(result.status, 'completed')
        self.assertEqual(session.adapter.invocation_count, 1)
        self.assertEqual(len(result.tool_snapshot['outbox']), 1)
        self.assertEqual(session.ledger.records()[0].status, AuthorizationStatus.CONSUMED)
        repeated = session.run()
        self.assertEqual(repeated.tool_snapshot, result.tool_snapshot)
        self.assertEqual(repeated.prompts_used, 1)

    def test_unissued_permit_and_replaced_preparation_cannot_commit(self):
        # Break caught: tool invocation accepts a fabricated capability, or
        # prepared effects can be replaced/replayed to widen a committed write.
        session = self.session(38)
        before = session.store.snapshot()
        with self.assertRaises(ValueError):
            session.adapter._tool._invoke(object())
        self.assertEqual(session.adapter.invocation_count, 0)
        call = self.call(session.task.steps[0])
        prepared = session.store.prepare(call)
        self.assertEqual(session.store.snapshot(), before)
        with self.assertRaises(ValueError):
            session.store.commit(replace(prepared, outbox_after=()))
        self.assertEqual(session.store.snapshot(), before)
        # Trusted store test only: the planner never receives preparations.
        session.store.commit(prepared)
        with self.assertRaises(ValueError):
            session.store.commit(prepared)
        self.assertEqual(len(session.store.snapshot()['outbox']), 1)

    def test_backend_rejects_unknown_tool_and_missing_io_contract(self):
        session = self.session(38)
        call = self.call(session.task.steps[0])
        for changed in (replace(call, io_contract=None),
                        replace(call, scope=replace(call.scope, tool='Unknown third party'))):
            with self.subTest(call=changed), self.assertRaises(ValueError):
                session.store.prepare(changed)
        self.assertEqual(session.store.snapshot()['events'], [])

if __name__ == '__main__':
    unittest.main()
