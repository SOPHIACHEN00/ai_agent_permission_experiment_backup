"""Budget termination and exact planner projections remain safe under four actions."""
import unittest
from dataclasses import replace
from test_user_session import user_session, start
from personal_assistant.config import FUNCTIONAL_LIMITS
from personal_assistant.contracts.task import ControlView
from personal_assistant.contracts.permission import ControllerAction as A
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from personal_assistant.integration.wu import load_wu_binding

class RuntimeLimitTests(unittest.TestCase):
    def test_candidate_overflow_after_consent_has_bounded_release_window(self):
        user = user_session('overflow')
        user.runtime_limits = replace(FUNCTIONAL_LIMITS, max_candidates=6)
        session = start(user, 55)
        result = session.run()
        self.assertEqual(result.status, 'candidate_limit')
        self.assertFalse(result.oracle_result['success'])
        self.assertEqual(session.adapter.invocation_count, 0)
        self.assertEqual(session.terminal_active_gate_keys, ())
        self.assertGreater(len(user.ledger.records()), 0)

    def test_total_control_bound_includes_reserved_cleanup_window(self):
        user = user_session('control')
        user.runtime_limits = replace(FUNCTIONAL_LIMITS, max_control_steps=1, max_release_steps=2)
        session = start(user, 55)
        result = session.run()
        self.assertEqual(result.status, 'controller_limit')
        self.assertLessEqual(result.controller_steps, session.max_total_control_steps)
        self.assertEqual(session.idle_gate_key_checkpoints, 9)
        self.assertEqual(len(session.terminal_active_gate_keys), 9)
        self.assertFalse(session.gate.active_keys(user.ledger, user.position))

    def test_exact_narrow_planner_proposal_is_not_expanded(self):
        user = user_session('narrow')
        binding = load_wu_binding(55)
        scope = binding.task.steps[0].operation_scopes[0]
        task = replace(binding.task, steps=(replace(binding.task.steps[0], operation_scopes=(scope,),
            arguments=binding.task.steps[0].io_contract.public_contract(scope)['argument_bindings']),))
        session = start(user, 55)
        session.planner = ScriptedPlanner(fixture_decisions(task))
        view = session.advance()
        for candidate in view.candidates:
            proposed = candidate.request_scope or candidate.operation_scope
            if proposed is not None:
                self.assertEqual(proposed, scope)
        self.assertTrue(session.run().oracle_result['success'])

if __name__ == '__main__':
    unittest.main()
