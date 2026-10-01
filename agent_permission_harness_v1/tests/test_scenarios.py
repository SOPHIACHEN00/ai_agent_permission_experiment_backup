"""Authored task oracles check real local effects, not Agent claims."""

import importlib
import json
from pathlib import Path
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import ControllerAction as A, PermissionChoice, Scope, contract_json_round_trip
from agent_mock_harness_v0.agent_protocol import parse_agent_decision
from agent_permission_harness_v1.human_channel import HumanReply, LocalHumanChannel
from agent_permission_harness_v1.runner import AgentSession
from agent_permission_harness_v1.contracts import CompiledCall, TaskDefinition, TaskStepSpec
from agent_permission_harness_v1.monitor_adapter import ExecutionAdapter


class ScriptPlanner:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.observations = []

    def next_decision(self, goal, history, available):
        self.observations.append((goal, history, available))
        return next(self.decisions)


def tool_decision(step, scope_index=0, arguments=None):
    selected = step.operation_scopes[scope_index]
    return parse_agent_decision({"kind": "tool", "tool": selected.tool, "operation": selected.operation,
        "resource": selected.resource, "requested_fields": list(selected.data_attributes),
        "arguments": contract_json_round_trip(step.arguments) if arguments is None else arguments,
        "answer": None, "answer_status": None})


def finish():
    return parse_agent_decision({"kind": "finish", "tool": None, "operation": None, "resource": None,
        "requested_fields": [], "arguments": {}, "answer": "The local synthetic task is complete.", "answer_status": "completed"})


def allowing(message):
    return HumanReply(message.message_id, "permission", PermissionChoice.ALLOW_REUSE)


class ExactSequencePolicy:
    def __init__(self, actions):
        self.actions = iter(actions)

    def choose(self, view):
        action, fields = next(self.actions)
        for candidate in view.candidates:
            selected = candidate.operation_scope or candidate.request_scope
            if candidate.valid and candidate.action == action and (fields is None or set(selected.data_attributes) == set(fields)):
                return candidate.candidate_id
        raise AssertionError("expected control candidate missing")


class ScenarioTests(unittest.TestCase):
    def scenarios(self):
        try:
            return importlib.import_module("agent_permission_harness_v1.scenarios")
        except ModuleNotFoundError:
            self.fail("authored synthetic task scenarios are not implemented")

    def test_q22_uses_exact_original_query_and_real_effect_matches_goal(self):
        task = self.scenarios().q22_report_share()
        query_path = Path(__file__).resolve().parents[2] / "external" / "ai-agent-permissions" / "queries.json"
        original = next(row for row in json.loads(query_path.read_text(encoding="utf-8")) if row["id"] == 22)
        self.assertEqual(task.goal, original["query"])
        planner = ScriptPlanner([*(tool_decision(step) for step in task.steps), finish()])
        result = AgentSession(task, planner, channel=LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.oracle_result["success"])
        self.assertTrue(result.oracle_result["task_facts"]["message_matches_goal"])
        self.assertEqual(result.tool_snapshot["outbox"][0]["attachment_content"], "Synthetic Q1 revenue report")
        self.assertEqual(result.oracle_result["privacy_proxy"]["excess_exposed_field_instances"], 0)
        self.assertTrue(result.ledger_replay_verified)
        self.assertTrue(result.monitor_audit_verified)
        self.assertEqual(result.prompts_used, 3)

    def test_q22_wrong_subject_records_real_send_but_fails_business_oracle(self):
        task = self.scenarios().q22_report_share()
        args = contract_json_round_trip(task.steps[-1].arguments)
        args["data"]["subject"] = "Wrong subject"
        planner = ScriptPlanner([tool_decision(task.steps[0]), tool_decision(task.steps[1]),
                                 tool_decision(task.steps[2], arguments=args), finish()])
        result = AgentSession(task, planner, channel=LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "oracle_failed")
        self.assertFalse(result.oracle_result["success"])
        self.assertTrue(result.oracle_result["task_facts"]["message_sent_locally"])
        self.assertFalse(result.oracle_result["task_facts"]["message_matches_goal"])
        self.assertEqual(len(result.tool_snapshot["outbox"]), 1)
        self.assertEqual(result.tool_snapshot["version"], 3)

    def test_completed_claim_without_tools_is_rejected(self):
        task = self.scenarios().q22_report_share()
        result = AgentSession(task, ScriptPlanner([finish()]), channel=LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "oracle_failed")
        self.assertFalse(result.oracle_result["task_facts"]["primary_complete"])
        self.assertEqual(result.tool_snapshot["version"], 0)
        self.assertEqual(result.oracle_result["privacy_proxy"]["exposed_field_instances"], 0)

    def test_actual_payroll_exposure_invalidates_q22_even_when_message_is_correct(self):
        task = self.scenarios().q22_report_share()
        session = AgentSession(task, ScriptPlanner([*(tool_decision(step) for step in task.steps), finish()]),
                               channel=LocalHumanChannel(allowing))
        self.assertTrue(session.run().oracle_result["success"])
        extra_scope = Scope("Work & Productivity", "Cloud Drive", "file_payroll", ("content",),
                            "read", "unrelated_payroll_probe", "local_user", "session")
        extra_step = TaskStepSpec("unrelated_read", (extra_scope,), (extra_scope,), {"record_id": "file_payroll"})
        extra_task = TaskDefinition("payroll_probe", "Separate synthetic exposure probe", (extra_step,), task.records, None)
        ledger = AuthorizationService(extra_task.scenario_id, 8)
        pending = ledger.start_request(extra_scope, 1, "explicit_probe_reply")
        ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_ONCE, 1)
        adapter = ExecutionAdapter(extra_task, session.store, ledger)
        adapter.execute(CompiledCall("unrelated_read", extra_scope, {"record_id": "file_payroll"}), pending.authorization_id, 2)
        evaluated = task.oracle.evaluate(session.store.snapshot(), session.adapter.task_engine.snapshot(), "Complete", "completed")
        self.assertFalse(evaluated["success"])
        self.assertTrue(evaluated["task_facts"]["message_matches_goal"])
        self.assertTrue(evaluated["task_facts"]["payroll_exposed"])
        self.assertEqual(evaluated["privacy_proxy"]["excess_exposed_field_instances"], 1)

    def test_adaptive_narrow_then_broad_reads_have_zero_excess_stage_fields(self):
        task = self.scenarios().adaptive_read_task()
        planner = ScriptPlanner([tool_decision(task.steps[0], scope_index=1), tool_decision(task.steps[1]), finish()])
        policy = ExactSequencePolicy([(A.REQUEST_AUTHORIZATION, ("title",)),
            (A.EXECUTE_WITH_AUTHORIZATION, ("title",)),
            (A.REQUEST_REFRESH, ("title", "private_notes")),
            (A.EXECUTE_WITH_AUTHORIZATION, ("title", "private_notes"))])
        result = AgentSession(task, planner, policy, LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.tool_snapshot["events"][0]["fields"], ["title"])
        proxy = result.oracle_result["privacy_proxy"]
        self.assertEqual(proxy["exposed_field_instances"], 3)
        self.assertEqual(proxy["unique_exposed_fields"], 2)
        self.assertEqual(proxy["excess_exposed_field_instances"], 0)
        self.assertEqual(proxy["unique_excess_exposed_fields"], 0)

    def test_stage_one_broad_access_is_excess_even_if_later_needed(self):
        task = self.scenarios().adaptive_read_task()
        planner = ScriptPlanner([tool_decision(task.steps[0], scope_index=1), tool_decision(task.steps[1]), finish()])
        policy = ExactSequencePolicy([(A.REQUEST_AUTHORIZATION, ("title", "private_notes")),
            (A.EXECUTE_WITH_AUTHORIZATION, ("title", "private_notes")),
            (A.EXECUTE_WITH_AUTHORIZATION, ("title", "private_notes"))])
        result = AgentSession(task, planner, policy, LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "completed")
        proxy = result.oracle_result["privacy_proxy"]
        self.assertEqual(proxy["exposed_field_instances"], 4)
        self.assertEqual(proxy["excess_exposed_field_instances"], 1)
        self.assertEqual(proxy["unique_excess_exposed_fields"], 1)
        self.assertIn("empirical", proxy["interpretation"])

    def test_oracle_necessity_annotations_never_enter_planner_observations(self):
        task = self.scenarios().adaptive_read_task()
        planner = ScriptPlanner([tool_decision(task.steps[0]), tool_decision(task.steps[1]), finish()])
        result = AgentSession(task, planner, channel=LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, "completed")
        self.assertNotIn("necessary_by_step", str(planner.observations))
        self.assertNotIn("excess_exposed", str(planner.observations))


if __name__ == "__main__":
    unittest.main()
