"""Authored offline planner, disjoint length splits and honest pilot artifacts."""
import importlib
import json
from pathlib import Path
import tempfile
import unittest

from pa_rl.contracts import ControllerAction as A
from agent_permission_harness_v1.learning_contracts import EpisodeConfig
from agent_permission_harness_v1.learning_environment import AgentLearningEnvironment
from agent_permission_harness_v1.human_channel import LocalHumanChannel
from agent_permission_harness_v1.runner import AgentSession
from agent_permission_harness_v1.run_agent import fixture_responder
from test_learning_environment import select


class PilotTests(unittest.TestCase):
    def test_fixed_fixture_ids_produce_reproducible_grant_bindings(self):
        def run():
            channel = LocalHumanChannel(fixture_responder, session_id='repeatable-fixture')
            from agent_permission_harness_v1.scenarios import adaptive_read_task
            from agent_permission_harness_v1.planner import ScriptedPlanner, fixture_decisions
            task = adaptive_read_task()
            env = AgentLearningEnvironment(AgentSession(task, ScriptedPlanner(fixture_decisions(task)),
                channel=channel), EpisodeConfig(2, 20), episode_id='repeatable-episode')
            first = env.start()
            transition = env.step(select(first, A.REQUEST_AUTHORIZATION, 2), decision_token=first.token)
            return transition.next_decision
        self.assertEqual(run(), run())

    def scenarios(self):
        try:
            return importlib.import_module('agent_permission_harness_v1.learning_scenarios')
        except ModuleNotFoundError:
            self.fail('authored learning scenarios are missing')

    def test_split_lengths_disjoint_and_oracles_cover_every_stage(self):
        module = self.scenarios()
        self.assertEqual(module.SPLIT_TAILS, {'train': (3, 4), 'validation': (5,), 'test': (6,)})
        for split, tails in module.SPLIT_TAILS.items():
            for tail in tails:
                task = module.staged_note_task(tail)
                self.assertEqual(len(task.steps), tail + 2)
                self.assertEqual(set(task.oracle.necessary_by_step), {s.step_id for s in task.steps})
                self.assertTrue(all(len(s.operation_scopes) == (1 if i == 1 else 2) for i, s in enumerate(task.steps)))

    def test_authored_scope_shrink_witness_improves_exposure_at_extra_prompt_cost(self):
        module = self.scenarios()
        def run(shrink):
            task = module.staged_note_task(6)
            env = AgentLearningEnvironment(AgentSession(task, module.ReactiveReadPlanner(),
                channel=LocalHumanChannel(fixture_responder), max_planner_turns=32), EpisodeConfig(2, 14))
            boundary = env.start()
            steps = [(A.REQUEST_AUTHORIZATION, 2), (A.EXECUTE_WITH_AUTHORIZATION, 1),
                     (A.EXECUTE_WITH_AUTHORIZATION, 2)]
            if shrink:
                steps.append((A.REQUEST_REFRESH, 1))
            steps.extend([(A.EXECUTE_WITH_AUTHORIZATION, 1)] * 6)
            for action, width in steps:
                transition = env.step(select(boundary, action, width), decision_token=boundary.token)
                boundary = transition.next_decision
                if transition.done:
                    return transition.end
            self.fail('task did not close')
        shrinking, fixed_broad = run(True), run(False)
        self.assertEqual((shrinking.reward, shrinking.exposure_used, shrinking.result.prompts_used), (1, 12, 2))
        self.assertEqual((fixed_broad.reward, fixed_broad.exposure_used, fixed_broad.result.prompts_used), (0, 16, 1))
        self.assertEqual(shrinking.result.oracle_result['privacy_proxy']['excess_exposed_field_instances'], 0)

    def test_short_pilot_writes_seeded_train_only_checkpoint_and_frozen_evaluations(self):
        self.scenarios()
        module = importlib.import_module('agent_permission_harness_v1.run_ddqn_pilot')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'pilot'
            self.assertEqual(module.main(['--output', str(output), '--episodes', '2', '--seeds', '17', '--device', 'cpu']), 0)
            manifest = json.loads((output / 'manifest.json').read_text())
            self.assertEqual(manifest['planner'], 'reactive_offline_fixture_not_llm')
            self.assertEqual(manifest['checkpoint_selection'], 'final_train_only')
            self.assertTrue(manifest['source_sha256'])
            self.assertEqual(len((output / 'train-17.jsonl').read_text().splitlines()), 2)
            rows = [json.loads(line) for line in (output / 'evaluation.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 54)  # 2 splits x 9 cells x 3 policies
            self.assertEqual({r['arm'] for r in rows}, {'ddqn', 'rule', 'random_valid'})
            self.assertTrue(all(r['optimizer_steps_before'] == r['optimizer_steps_after'] for r in rows))
            self.assertEqual(json.loads((output / 'summary.json').read_text())['status'], 'completed')
            with self.assertRaises(FileExistsError):
                module.main(['--output', str(output), '--episodes', '2', '--seeds', '17', '--device', 'cpu'])


if __name__ == '__main__':
    unittest.main()
