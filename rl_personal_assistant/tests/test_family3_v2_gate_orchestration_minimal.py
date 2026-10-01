"""Fast orchestration checks with real frozen classifiers and synthetic rows.

These catch auto-opening test, using the qualifying cohort to shrink test rows,
and dropping classification persistence. Durable permit/crash acceptance is
deliberately not claimed: only the filesystem store is doubled here.
"""

from dataclasses import fields, replace
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from pa_rl import family3_v2_learner_pilot as runner
from pa_rl.family3_v2_pilot_criteria import EvaluationEpisodeRow, HardIntegrityCounts


class Family3V2GateOrchestrationTests(unittest.TestCase):
    def test_ready_does_not_open_test_and_explicit_test_classifies_all_seed_rows(self):
        project = Path(__file__).resolve().parents[1]
        config_path = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
        config, boundary, *_ = runner._prepare_training(config_path, baseline, smoke=False)
        zero = HardIntegrityCounts(**{field.name: 0 for field in fields(HardIntegrityCounts)})

        def rows(phase):
            graphs = boundary.validation_graph_ids if phase == "validation" else boundary.test_graph_ids
            result = []
            for method in boundary.method_ids:
                for seed in (17, 29, 43):
                    for graph in graphs:
                        for condition in boundary.condition_ids:
                            for ordinal in range(50):
                                preferred = "request_narrow" if condition == "original" else "request_broader"
                                strong = method in ("forecast_rule", "masked_ddqn_gamma1")
                                success = int(ordinal < (40 if strong else 20))
                                if method == "masked_ddqn_gamma1" and seed == 43 and phase == "validation":
                                    success = 0  # Exactly seeds 17 and 29 qualify.
                                result.append(EvaluationEpisodeRow(
                                    phase, method, seed, graph, condition, ordinal,
                                    runner.derive_family3_v2_eval_environment_seed(
                                        experiment_id=config.experiment_id, evaluation_seed=seed,
                                        graph_id=graph, episode_ordinal=ordinal),
                                    preferred if strong else "deny", success,
                                    "natural_completion" if success else "deny_with_reason", 3, 1, zero,
                                ))
            return tuple(result)

        validation_rows, test_rows = rows("validation"), rows("test")
        self.assertEqual((len(validation_rows), len(test_rows)), (4200, 6300))
        state = ["TRAINING_COMPLETE"]
        store = Mock()
        store._boundary = boundary
        store._config = config
        store._state.side_effect = lambda: state[0]
        store._completed_refs.return_value = ()
        store.write_validation_gate.side_effect = lambda *args, **kwargs: state.__setitem__(0, "VALIDATION_CLASSIFIED")
        command = ("unit-test", "task7-orchestration")
        with patch.object(runner, "evaluate_split", return_value=validation_rows):
            ready = runner.run_validation(config, boundary, store, command=command)
        self.assertEqual(ready.status, "READY_FOR_TEST")
        gate = store.write_test_permit.call_args.args[0]
        self.assertEqual(gate.qualifying_seed_ids, (17, 29))
        store.open_test_once.assert_not_called()
        store.commit_final_verdict.assert_not_called()

        store._stored_validation.return_value = (gate, {})
        store._verified_permit.return_value = {"qualifying_seed_ids": [17, 29]}
        state[0] = "READY_FOR_TEST"
        with (patch.object(runner, "_open_store", return_value=(config, boundary, store)),
              patch.object(runner, "_terminal_verdict", return_value=None),
              patch.object(Path, "is_file", return_value=True),
              patch.object(runner, "evaluate_split", return_value=test_rows) as evaluate):
            result = runner.run_test_once(config_path, baseline, project / "unused-synthetic-root", command=command)
        store.open_test_once.assert_called_once_with(resume=False, command=command)
        self.assertEqual(evaluate.call_args.args[3], "test")
        self.assertEqual(result.status, "RULE_PARITY_SIGNAL")
        classified = store.commit_final_verdict.call_args.args[0]
        self.assertEqual(classified.observed_row_count, 6300)
        self.assertEqual(classified.validation_qualified_seed_ids, (17, 29))

        # Failed validation closes without a permit or touching the test split.
        store.reset_mock()
        state[0] = "TRAINING_COMPLETE"
        failed = tuple(replace(row, terminal_success=0) if row.method_id == "masked_ddqn_gamma1" else row
                       for row in validation_rows)
        with patch.object(runner, "evaluate_split", return_value=failed):
            closed = runner.run_validation(config, boundary, store, command=command)
        self.assertEqual(closed.status, "NO_TEST")
        store.write_test_permit.assert_not_called()
        store.open_test_once.assert_not_called()
        self.assertEqual(store.commit_final_verdict.call_args.args[0].classification, "NO_TEST")


if __name__ == "__main__":
    unittest.main()
