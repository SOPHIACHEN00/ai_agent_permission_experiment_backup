from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from pa_rl.family3_v2_pilot_criteria import (
    ROOT_ACTION_MISSING,
    ROOT_ACTION_MULTIPLE,
    EvaluationCellResult,
    EvaluationEpisodeRow,
    HardIntegrityCounts,
    TestClassificationResult,
    ValidationGateResult,
    classify_test_result,
    evaluate_validation_gate,
    load_family3_v2_pilot_config,
    verify_certified_dependency_baseline,
)


class Family3V2PilotContractTests(unittest.TestCase):
    def test_config_and_certified_baseline_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config_path = root / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline_path = root / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"

        config = load_family3_v2_pilot_config(config_path)
        self.assertEqual(
            tuple(method["id"] for method in config.methods),
            (
                "random_valid", "forecast_ablated_rule", "forecast_rule",
                "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
                "masked_ddqn_gamma1",
            ),
        )
        self.assertEqual(tuple(config.split["train"]), tuple(f"i8_f3v2_v{i}" for i in range(5)))
        self.assertEqual(tuple(config.split["validation"]), ("i8_f3v2_v5", "i8_f3v2_v6"))
        self.assertEqual(tuple(config.split["test"]), ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"))
        self.assertEqual(tuple(config.training["seeds"]), (17, 29, 43))
        self.assertEqual(config.training["transitions_per_learner_seed"], 12000)
        self.assertEqual(config.training["allocation"]["transitions_per_train_graph"], 2400)
        self.assertEqual(config.evaluation["episodes_per_graph_condition_seed"], 50)
        self.assertEqual(config.certified_environment["adapter"]["maximum_state_width"], 43)
        self.assertEqual(config.certified_environment["adapter"]["candidate_count"], 7)
        self.assertEqual(config.certified_environment["adapter"]["candidate_feature_width"], 7)

        verification = verify_certified_dependency_baseline(baseline_path)
        self.assertTrue(verification.passed, verification.mismatches)
        self.assertEqual(verification.suite_hash, "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c")
        self.assertEqual(len(verification.approved_spec_hashes), 2)

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        preflight = baseline["certified_preflight"]
        self.assertEqual(len(preflight["certificate_entries"]), 20)
        self.assertEqual(len(preflight["cache_entries"]), 20)
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["certificate_entries"]))
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["cache_entries"]))

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["unknown"] = "forbidden"
            altered_path = temporary / "unknown.json"
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config.pop("unknown")
            altered_config.pop("methods")
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["training"]["transitions_per_learner_seed"] = True
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["additional_learner_dependencies"][0]["sha256"] = "0" * 64
            tampered_path = temporary / "tampered-baseline.json"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_certified_dependency_baseline(tampered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["certificate_entries"][0]["sha256"] = "0" * 64
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)
            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["cache_entries"][0]["byte_size"] = 0
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)

            for mutation in (
                lambda value: value.__setitem__("unknown", True),
                lambda value: value.__setitem__("approved_specs", list(reversed(value["approved_specs"]))),
                lambda value: value["certified_preflight"].__setitem__("result_root", "../escape"),
                lambda value: value["certified_preflight"].__setitem__("certificate_entries", value["certified_preflight"]["certificate_entries"][:-1] + [value["certified_preflight"]["certificate_entries"][0]]),
                lambda value: value.__setitem__("certified_source_files", list(reversed(value["certified_source_files"]))),
                lambda value: value.__setitem__("additional_learner_dependencies", list(reversed(value["additional_learner_dependencies"]))),
                lambda value: value.__setitem__("pilot_config", {**value["pilot_config"], "relative_path": "src/pa_rl/ddqn.py"}),
                lambda value: value["certified_preflight"].__setitem__("artifacts", list(reversed(value["certified_preflight"]["artifacts"]))),
            ):
                tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
                mutation(tampered)
                tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(ValueError):
                    verify_certified_dependency_baseline(tampered_path)

    def test_validation_and_test_classification_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_family3_v2_pilot_config(
            root / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        )
        hard_names = (
            "invalid_action_attempts", "policy_mask_violations",
            "unauthorized_committed_effects", "monitor_blocked_attempts",
            "monitor_bypass_effects", "environment_invalid_runs",
            "scope_binding_integrity_failures", "authorization_binding_failures",
            "semantic_conformance_failures", "effect_integrity_failures",
            "adapter_contract_failures", "candidate_id_resolution_failures",
            "oracle_feature_leaks", "split_leakage_events",
            "test_access_before_unlock", "evaluation_state_mutations",
            "source_freeze_mismatches", "config_freeze_mismatches",
            "certified_dependency_hash_mismatches", "artifact_hash_mismatches",
            "checkpoint_policy_violations", "common_random_coordinate_mismatches",
            "duplicate_result_rows", "unexpected_result_rows",
            "missing_expected_result_rows", "nonfinite_events",
        )
        self.assertEqual(tuple(field.name for field in fields(HardIntegrityCounts)), hard_names)
        self.assertEqual(tuple(config.hard_zero_counts), hard_names)
        self.assertEqual(
            tuple(field.name for field in fields(EvaluationEpisodeRow)),
            ("phase", "method_id", "evaluation_seed", "graph_id", "condition",
             "episode_ordinal", "root_seed", "root_semantic_candidate_id",
             "terminal_success", "termination_kind", "decision_count",
             "prompt_count", "hard_counts"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(EvaluationCellResult)),
            ("phase", "method_id", "evaluation_seed", "graph_id", "condition",
             "episode_count", "terminal_success_count", "first_request_match_count",
             "forecast_rule_terminal_match_count", "hard_counts"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(ValidationGateResult)),
            ("phase_complete", "status", "qualifying_seed_ids", "observed_row_count",
             "hard_counts", "cell_results"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(TestClassificationResult)),
            ("phase_complete", "test_opened", "classification",
             "validation_qualified_seed_ids", "rule_parity_seed_ids",
             "credit_signal_seed_ids", "observed_row_count", "hard_counts",
             "cell_results"),
        )
        validation_signature = inspect.signature(evaluate_validation_gate)
        self.assertEqual(tuple(validation_signature.parameters), ("config", "rows", "phase_complete"))
        self.assertIs(validation_signature.parameters["phase_complete"].kind, inspect.Parameter.KEYWORD_ONLY)
        test_signature = inspect.signature(classify_test_result)
        self.assertEqual(
            tuple(test_signature.parameters),
            ("config", "rows", "validation_gate", "permitted_seed_ids",
             "test_opened", "phase_complete"),
        )
        for name in ("validation_gate", "permitted_seed_ids", "test_opened", "phase_complete"):
            self.assertIs(test_signature.parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)

        zeros = {name: 0 for name in hard_names}
        zero_counts = HardIntegrityCounts(**zeros)
        self.assertFalse(hasattr(zero_counts, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            zero_counts.invalid_action_attempts = 1  # type: ignore[misc]
        with self.assertRaises(TypeError):
            HardIntegrityCounts(**{name: 0 for name in hard_names[:-1]})
        with self.assertRaises(TypeError):
            HardIntegrityCounts(**{**zeros, "extra": 0})
        for bad in (-1, True, 1.0, "1", float("nan"), float("inf")):
            with self.subTest(bad_hard_count=bad), self.assertRaises(ValueError):
                HardIntegrityCounts(**{**zeros, "invalid_action_attempts": bad})

        methods = (
            "random_valid", "forecast_ablated_rule", "forecast_rule",
            "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
            "masked_ddqn_gamma1",
        )
        seeds = (17, 29, 43)
        conditions = ("original", "forecast_counterfactual")
        validation_graphs = ("i8_f3v2_v5", "i8_f3v2_v6")
        test_graphs = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")

        def derive_root_seed(seed: int, graph_id: str, ordinal: int) -> int:
            payload = ["family3_v2_eval_coord_v0", config.experiment_id,
                       "environment", seed, graph_id, ordinal]
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")

        def row(
            phase: object = "validation",
            method_id: object = "random_valid",
            evaluation_seed: object = 17,
            graph_id: object = "i8_f3v2_v5",
            condition: object = "original",
            episode_ordinal: object = 0,
            root_semantic_candidate_id: object = "deny",
            terminal_success: object = 0,
            termination_kind: object = "deny_with_reason",
            decision_count: object = 1,
            prompt_count: object = 0,
            hard_counts: object = zero_counts,
            root_seed: object | None = None,
        ) -> EvaluationEpisodeRow:
            actual_root_seed = (
                derive_root_seed(evaluation_seed, graph_id, episode_ordinal)  # type: ignore[arg-type]
                if root_seed is None and type(evaluation_seed) is int
                and type(graph_id) is str and type(episode_ordinal) is int
                else root_seed
            )
            return EvaluationEpisodeRow(
                phase=phase, method_id=method_id, evaluation_seed=evaluation_seed,
                graph_id=graph_id, condition=condition, episode_ordinal=episode_ordinal,
                root_seed=actual_root_seed,  # type: ignore[arg-type]
                root_semantic_candidate_id=root_semantic_candidate_id,
                terminal_success=terminal_success, termination_kind=termination_kind,
                decision_count=decision_count, prompt_count=prompt_count,
                hard_counts=hard_counts,  # type: ignore[arg-type]
            )  # type: ignore[arg-type]

        prototype = row()
        self.assertFalse(hasattr(prototype, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            prototype.phase = "test"  # type: ignore[misc]
        bad_rows = (
            {"phase": 1}, {"method_id": 1}, {"evaluation_seed": True},
            {"graph_id": 1}, {"condition": 1}, {"episode_ordinal": True},
            {"root_seed": -1}, {"root_seed": 2**64}, {"root_seed": float("nan")},
            {"root_semantic_candidate_id": 1}, {"terminal_success": True},
            {"terminal_success": 2}, {"termination_kind": "in_progress"},
            {"decision_count": -1}, {"decision_count": True},
            {"prompt_count": -1}, {"prompt_count": True}, {"hard_counts": None},
        )
        for mutation in bad_rows:
            with self.subTest(bad_episode_row=mutation), self.assertRaises(ValueError):
                row(**mutation)
        for terminal_kind in (
            "natural_completion", "horizon_exhaustion", "deny_with_reason",
            "escalate", "irreversible_failure",
        ):
            row(termination_kind=terminal_kind)
        for candidate_id in (
            "request_narrow", "request_broader", "execute_covering",
            "refresh_closed", "disable_active", "deny", "escalate",
            ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE,
        ):
            row(root_semantic_candidate_id=candidate_id)
        with self.assertRaises(ValueError):
            row(root_semantic_candidate_id="unknown")

        def build_rows(phase: str) -> tuple[EvaluationEpisodeRow, ...]:
            graphs = validation_graphs if phase == "validation" else test_graphs
            built: list[EvaluationEpisodeRow] = []
            for method_id in methods:
                for seed in seeds:
                    for graph_id in graphs:
                        for condition in conditions:
                            forecast_root = "request_narrow" if condition == "original" else "request_broader"
                            for ordinal in range(50):
                                if method_id in ("forecast_rule", "masked_ddqn_gamma1"):
                                    root_id = forecast_root
                                elif phase == "validation" and method_id in ("forecast_ablated_rule", "masked_ddqn_gamma0"):
                                    root_id = forecast_root
                                elif phase == "test" and method_id == "forecast_ablated_rule":
                                    root_id = forecast_root if ordinal < 25 else "deny"
                                elif phase == "test" and method_id == "masked_ddqn_gamma0":
                                    root_id = forecast_root if ordinal < 20 else "deny"
                                elif method_id in ("random_valid", "tabular_q_gamma1"):
                                    root_id = "escalate"
                                else:
                                    root_id = "deny"
                                if method_id in ("forecast_rule", "masked_ddqn_gamma1"):
                                    success = int(ordinal < 40)
                                elif method_id == "forecast_ablated_rule":
                                    success = int(ordinal < 25)
                                elif method_id == "masked_ddqn_gamma0":
                                    success = int(ordinal < 20)
                                elif method_id.startswith("tabular_q"):
                                    success = int(ordinal < 10)
                                else:
                                    success = int(ordinal < 5)
                                if (phase == "validation" and method_id == "masked_ddqn_gamma1"
                                        and seed == 43 and graph_id == validation_graphs[0]
                                        and condition == conditions[0] and ordinal == 0):
                                    success = 1 - success
                                built.append(row(
                                    phase=phase, method_id=method_id, evaluation_seed=seed,
                                    graph_id=graph_id, condition=condition,
                                    episode_ordinal=ordinal,
                                    root_semantic_candidate_id=root_id,
                                    terminal_success=success,
                                    termination_kind="natural_completion" if success else "deny_with_reason",
                                ))
            return tuple(built)

        def rewrite_rows(rows: tuple[EvaluationEpisodeRow, ...], predicate, transform) -> tuple[EvaluationEpisodeRow, ...]:
            return tuple(transform(item) if predicate(item) else item for item in rows)

        validation_rows = build_rows("validation")
        test_rows = build_rows("test")
        self.assertEqual(len(validation_rows), 4_200)
        self.assertEqual(len(test_rows), 6_300)

        partial_rows = (validation_rows[0], validation_rows[1])
        partial = evaluate_validation_gate(config, partial_rows, phase_complete=False)
        self.assertFalse(partial.phase_complete)
        self.assertIsNone(partial.status)
        self.assertEqual(partial.qualifying_seed_ids, ())
        self.assertEqual(partial.observed_row_count, 2)
        self.assertEqual(partial.hard_counts, zero_counts)
        self.assertEqual(partial.hard_counts.missing_expected_result_rows, 0)
        self.assertEqual(partial.cell_results, ())
        with self.assertRaises(ValueError):
            evaluate_validation_gate(config, list(partial_rows), phase_complete=False)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate_validation_gate(config, partial_rows, phase_complete=0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate_validation_gate(object(), partial_rows, phase_complete=False)  # type: ignore[arg-type]

        ordinary_nonrequests = (
            replace(validation_rows[0], root_semantic_candidate_id="deny"),
            replace(validation_rows[1], root_semantic_candidate_id="escalate"),
        )
        nonrequest_result = evaluate_validation_gate(
            config, ordinary_nonrequests, phase_complete=False
        )
        self.assertIsNone(nonrequest_result.status)
        self.assertEqual(nonrequest_result.hard_counts, zero_counts)
        for marker in (ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE):
            marked = evaluate_validation_gate(
                config,
                (replace(validation_rows[0], root_semantic_candidate_id=marker),),
                phase_complete=False,
            )
            with self.subTest(root_marker=marker):
                self.assertEqual(marked.status, "INVALID_RUN")
                self.assertEqual(marked.hard_counts.semantic_conformance_failures, 1)

        reversed_rows = evaluate_validation_gate(
            config, tuple(reversed(partial_rows)), phase_complete=False
        )
        self.assertEqual(reversed_rows.status, "INVALID_RUN")
        self.assertEqual(reversed_rows.hard_counts.unexpected_result_rows, 1)
        duplicate = evaluate_validation_gate(
            config, (validation_rows[0], validation_rows[0]), phase_complete=False
        )
        self.assertEqual(duplicate.status, "INVALID_RUN")
        self.assertEqual(duplicate.hard_counts.duplicate_result_rows, 1)
        self.assertEqual(duplicate.hard_counts.unexpected_result_rows, 1)
        wrong_root_seed = evaluate_validation_gate(
            config,
            (replace(validation_rows[0], root_seed=validation_rows[0].root_seed + 1),),
            phase_complete=False,
        )
        self.assertEqual(wrong_root_seed.status, "INVALID_RUN")
        self.assertEqual(wrong_root_seed.hard_counts.common_random_coordinate_mismatches, 1)
        wrong_coordinates = (
            replace(validation_rows[0], phase="test"),
            replace(validation_rows[0], method_id="unknown_method"),
            replace(validation_rows[0], evaluation_seed=99,
                    root_seed=derive_root_seed(99, validation_rows[0].graph_id, 0)),
            replace(validation_rows[0], graph_id="i8_f3v2_v7",
                    root_seed=derive_root_seed(17, "i8_f3v2_v7", 0)),
            replace(validation_rows[0], condition="unknown_condition"),
            replace(validation_rows[0], episode_ordinal=50,
                    root_seed=derive_root_seed(17, validation_rows[0].graph_id, 50)),
        )
        for wrong_row in wrong_coordinates:
            with self.subTest(wrong_coordinate=wrong_row):
                wrong = evaluate_validation_gate(config, (wrong_row,), phase_complete=False)
                self.assertEqual(wrong.status, "INVALID_RUN")
                self.assertGreaterEqual(wrong.hard_counts.unexpected_result_rows, 1)

        for hard_name in hard_names:
            if hard_name == "missing_expected_result_rows":
                continue
            injected_counts = HardIntegrityCounts(
                **{name: int(name == hard_name) for name in hard_names}
            )
            injected = evaluate_validation_gate(
                config,
                (replace(validation_rows[0], hard_counts=injected_counts),),
                phase_complete=False,
            )
            with self.subTest(hard_count=hard_name):
                self.assertEqual(injected.status, "INVALID_RUN")
                self.assertEqual(getattr(injected.hard_counts, hard_name), 1)

        missing = evaluate_validation_gate(
            config, validation_rows[:-1], phase_complete=True
        )
        self.assertEqual(missing.status, "INVALID_RUN")
        self.assertEqual(missing.observed_row_count, 4_199)
        self.assertEqual(missing.hard_counts.missing_expected_result_rows, 1)
        self.assertEqual(missing.cell_results, ())

        validation_ready = evaluate_validation_gate(
            config, validation_rows, phase_complete=True
        )
        self.assertTrue(validation_ready.phase_complete)
        self.assertEqual(validation_ready.status, "READY_FOR_TEST")
        self.assertEqual(validation_ready.qualifying_seed_ids, (17, 29))
        self.assertEqual(validation_ready.observed_row_count, 4_200)
        self.assertEqual(len(validation_ready.cell_results), 84)
        self.assertEqual(validation_ready.hard_counts, zero_counts)
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=(17, 29, 43))
        gamma1_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "masked_ddqn_gamma1" and cell.evaluation_seed == 17
        )
        self.assertEqual(len(gamma1_seed17), 4)
        self.assertTrue(all(
            cell.episode_count == 50
            and cell.first_request_match_count == 50
            and cell.forecast_rule_terminal_match_count == 50
            and cell.hard_counts == zero_counts
            for cell in gamma1_seed17
        ))
        gamma0_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "masked_ddqn_gamma0" and cell.evaluation_seed == 17
        )
        ablated_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "forecast_ablated_rule" and cell.evaluation_seed == 17
        )
        self.assertEqual(sum(cell.first_request_match_count for cell in gamma0_seed17), 200)
        self.assertEqual(sum(cell.first_request_match_count for cell in ablated_seed17), 200)
        self.assertTrue(
            sum(cell.terminal_success_count for cell in gamma1_seed17)
            > sum(cell.terminal_success_count for cell in gamma0_seed17)
        )
        self.assertTrue(
            sum(cell.terminal_success_count for cell in gamma1_seed17)
            > sum(cell.terminal_success_count for cell in ablated_seed17)
        )

        three_seed_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 43
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, terminal_success=1),
        )
        three_seed_gate = evaluate_validation_gate(config, three_seed_rows, phase_complete=True)
        self.assertEqual(three_seed_gate.status, "READY_FOR_TEST")
        self.assertEqual(three_seed_gate.qualifying_seed_ids, (17, 29, 43))

        root_mismatch_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        root_mismatch_gate = evaluate_validation_gate(
            config, root_mismatch_rows, phase_complete=True
        )
        self.assertEqual(root_mismatch_gate.status, "NO_TEST")
        self.assertEqual(root_mismatch_gate.qualifying_seed_ids, (17,))
        outcome_mismatch_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, terminal_success=1 - item.terminal_success),
        )
        outcome_mismatch_gate = evaluate_validation_gate(
            config, outcome_mismatch_rows, phase_complete=True
        )
        self.assertEqual(outcome_mismatch_gate.qualifying_seed_ids, (17,))
        tied_success_rows = rewrite_rows(
            validation_rows,
            lambda item: item.method_id == "forecast_ablated_rule" and item.evaluation_seed == 29,
            lambda item: replace(item, terminal_success=int(item.episode_ordinal < 40)),
        )
        tied_success_gate = evaluate_validation_gate(config, tied_success_rows, phase_complete=True)
        self.assertEqual(tied_success_gate.qualifying_seed_ids, (17,))
        tabular_changed_rows = rewrite_rows(
            validation_rows,
            lambda item: item.method_id.startswith("tabular_q"),
            lambda item: replace(item, root_semantic_candidate_id="execute_covering",
                                 terminal_success=1 - item.terminal_success),
        )
        tabular_changed_gate = evaluate_validation_gate(
            config, tabular_changed_rows, phase_complete=True
        )
        self.assertEqual(tabular_changed_gate.status, validation_ready.status)
        self.assertEqual(tabular_changed_gate.qualifying_seed_ids,
                         validation_ready.qualifying_seed_ids)

        with self.assertRaises(ValueError):
            replace(validation_ready, phase_complete=1)
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=[17, 29])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=(29, 17))
        with self.assertRaises(ValueError):
            replace(validation_ready, status=None)

        unopened = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=False,
        )
        self.assertFalse(unopened.phase_complete)
        self.assertFalse(unopened.test_opened)
        self.assertIsNone(unopened.classification)
        self.assertEqual(unopened.validation_qualified_seed_ids, (17, 29))
        self.assertEqual(unopened.rule_parity_seed_ids, ())
        self.assertEqual(unopened.credit_signal_seed_ids, ())
        self.assertEqual(unopened.observed_row_count, 0)
        self.assertEqual(unopened.hard_counts, zero_counts)
        self.assertEqual(unopened.cell_results, ())
        with self.assertRaises(ValueError):
            classify_test_result(
                config, list(test_rows[:1]), validation_gate=validation_ready,  # type: ignore[arg-type]
                permitted_seed_ids=(17, 29), test_opened=True, phase_complete=False,
            )
        with self.assertRaises(ValueError):
            classify_test_result(
                config, (), validation_gate=validation_ready,
                permitted_seed_ids=[17, 29], test_opened=False,  # type: ignore[arg-type]
                phase_complete=False,
            )
        with self.assertRaises(ValueError):
            classify_test_result(
                config, (), validation_gate=validation_ready,
                permitted_seed_ids=(17, 29), test_opened=1,  # type: ignore[arg-type]
                phase_complete=False,
            )

        wrong_permit = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 43), test_opened=False,
            phase_complete=False,
        )
        self.assertEqual(wrong_permit.classification, "INVALID_RUN")
        self.assertEqual(wrong_permit.hard_counts.artifact_hash_mismatches, 1)
        unopened_with_rows = classify_test_result(
            config, test_rows[:1], validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=False,
        )
        self.assertEqual(unopened_with_rows.classification, "INVALID_RUN")
        self.assertEqual(unopened_with_rows.hard_counts.test_access_before_unlock, 1)
        unopened_complete = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=True,
        )
        self.assertEqual(unopened_complete.classification, "INVALID_RUN")
        self.assertEqual(unopened_complete.hard_counts.test_access_before_unlock, 1)

        partial_test_rows = test_rows[::1000]
        partial_test = classify_test_result(
            config, partial_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True,
            phase_complete=False,
        )
        self.assertFalse(partial_test.phase_complete)
        self.assertIsNone(partial_test.classification)
        self.assertEqual(partial_test.observed_row_count, len(partial_test_rows))
        self.assertEqual(partial_test.rule_parity_seed_ids, ())
        self.assertEqual(partial_test.credit_signal_seed_ids, ())
        self.assertEqual(partial_test.cell_results, ())
        self.assertEqual(partial_test.hard_counts.missing_expected_result_rows, 0)

        no_test = classify_test_result(
            config, (), validation_gate=root_mismatch_gate,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertEqual(no_test.classification, "NO_TEST")
        no_test_access = classify_test_result(
            config, test_rows[:1], validation_gate=root_mismatch_gate,
            permitted_seed_ids=(), test_opened=True, phase_complete=False,
        )
        self.assertEqual(no_test_access.classification, "INVALID_RUN")
        self.assertEqual(no_test_access.hard_counts.test_access_before_unlock, 1)
        invalid_validation = evaluate_validation_gate(
            config,
            (replace(validation_rows[0], root_semantic_candidate_id=ROOT_ACTION_MISSING),),
            phase_complete=False,
        )
        invalid_precedence = classify_test_result(
            config, (), validation_gate=invalid_validation,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertEqual(invalid_precedence.classification, "INVALID_RUN")
        self.assertEqual(invalid_precedence.hard_counts.semantic_conformance_failures, 1)
        validation_partial = classify_test_result(
            config, (), validation_gate=partial,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertIsNone(validation_partial.classification)

        parity = classify_test_result(
            config, test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertTrue(parity.phase_complete)
        self.assertEqual(parity.classification, "RULE_PARITY_SIGNAL")
        self.assertEqual(parity.validation_qualified_seed_ids, (17, 29))
        self.assertEqual(parity.rule_parity_seed_ids, (17, 29))
        self.assertEqual(parity.credit_signal_seed_ids, (17, 29))
        self.assertEqual(parity.observed_row_count, 6_300)
        self.assertEqual(len(parity.cell_results), 126)
        self.assertEqual(parity.hard_counts, zero_counts)
        with self.assertRaises(ValueError):
            replace(
                parity,
                classification="NO_CREDIT_SIGNAL",
                rule_parity_seed_ids=(),
                credit_signal_seed_ids=(),
            )

        one_parity_rows = rewrite_rows(
            test_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == test_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        one_parity = classify_test_result(
            config, one_parity_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(one_parity.rule_parity_seed_ids, (17,))
        self.assertEqual(one_parity.credit_signal_seed_ids, (17, 29))
        self.assertEqual(one_parity.classification, "CREDIT_SIGNAL_BELOW_RULE")
        below_rule_rows = rewrite_rows(
            one_parity_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 17
                          and item.graph_id == test_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        below_rule = classify_test_result(
            config, below_rule_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(below_rule.rule_parity_seed_ids, ())
        self.assertEqual(below_rule.credit_signal_seed_ids, (17, 29))
        self.assertEqual(below_rule.classification, "CREDIT_SIGNAL_BELOW_RULE")
        with self.assertRaises(ValueError):
            replace(below_rule, rule_parity_seed_ids=(17,))

        first_match_tie_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id == "masked_ddqn_gamma1" and item.evaluation_seed == 29,
            lambda item: replace(
                item,
                root_semantic_candidate_id=(
                    ("request_narrow" if item.condition == "original" else "request_broader")
                    if item.episode_ordinal < 25 else "deny"
                ),
            ),
        )
        first_match_tie = classify_test_result(
            config, first_match_tie_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(first_match_tie.credit_signal_seed_ids, (17,))
        self.assertEqual(first_match_tie.classification, "NO_CREDIT_SIGNAL")
        success_tie_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id == "masked_ddqn_gamma1" and item.evaluation_seed == 29,
            lambda item: replace(item, terminal_success=int(item.episode_ordinal < 25)),
        )
        success_tie = classify_test_result(
            config, success_tie_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(success_tie.credit_signal_seed_ids, (17,))
        self.assertEqual(success_tie.classification, "NO_CREDIT_SIGNAL")

        tabular_test_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id.startswith("tabular_q"),
            lambda item: replace(item, root_semantic_candidate_id="execute_covering",
                                 terminal_success=1 - item.terminal_success),
        )
        tabular_test = classify_test_result(
            config, tabular_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(tabular_test.classification, parity.classification)
        self.assertEqual(tabular_test.rule_parity_seed_ids, parity.rule_parity_seed_ids)
        self.assertEqual(tabular_test.credit_signal_seed_ids, parity.credit_signal_seed_ids)

        incomplete_test = classify_test_result(
            config, test_rows[:-1], validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(incomplete_test.classification, "INVALID_RUN")
        self.assertEqual(incomplete_test.observed_row_count, 6_299)
        self.assertEqual(incomplete_test.hard_counts.missing_expected_result_rows, 1)
        hard_test_rows = (
            replace(test_rows[0], hard_counts=HardIntegrityCounts(
                **{name: int(name == "nonfinite_events") for name in hard_names}
            )),
        ) + test_rows[1:]
        hard_precedence = classify_test_result(
            config, hard_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(hard_precedence.classification, "INVALID_RUN")
        self.assertEqual(hard_precedence.hard_counts.nonfinite_events, 1)
        self.assertEqual(hard_precedence.cell_results, ())

        with self.assertRaises(ValueError):
            replace(parity, phase_complete=1)
        with self.assertRaises(ValueError):
            replace(parity, rule_parity_seed_ids=(29, 17))
        with self.assertRaises(ValueError):
            replace(parity, credit_signal_seed_ids=(17,))
        with self.assertRaises(ValueError):
            replace(parity, classification=None)

    def test_checkpoint_ledger_permit_and_test_once_state_machine(self) -> None:
        self._exercise_checkpoint_store(minimal=False)

    def test_minimal_checkpoint_roundtrip_and_ledger_guards(self) -> None:
        self._exercise_checkpoint_store(minimal=True)

    def _exercise_checkpoint_store(self, *, minimal: bool) -> None:
        import os
        import platform
        from unittest.mock import patch

        import torch

        from pa_rl.baselines import TabularQLearner
        from pa_rl.ddqn import DDQNHyperparameters, _ReplayTransition
        from pa_rl.family3_v2_learning import (
            FAMILY3_V2_DDQN_MODEL_SPEC,
            Family3V2LearnerRngDeriver,
            Family3V2MaskedDoubleDQN,
            derive_family3_v2_eval_environment_seed,
        )
        import pa_rl.family3_v2_pilot_checkpoints as checkpoint_module
        from pa_rl.family3_v2_pilot_checkpoints import (
            ConflictingCoordinateError,
            DuplicateCoordinateError,
            Family3V2PilotArtifactStore,
            FinalCheckpointRef,
            PilotBoundary,
        )

        project = Path(__file__).resolve().parents[1]
        config_path = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline_path = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
        config_bytes = config_path.read_bytes()
        baseline_bytes = baseline_path.read_bytes()
        config = load_family3_v2_pilot_config(config_path)
        baseline = json.loads(baseline_bytes)
        methods = (
            "random_valid", "forecast_ablated_rule", "forecast_rule",
            "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
            "masked_ddqn_gamma1",
        )
        trained = (
            "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
            "masked_ddqn_gamma1",
        )
        seeds = (17, 29, 43)
        train_graphs = tuple(f"i8_f3v2_v{index}" for index in range(5))
        validation_graphs = ("i8_f3v2_v5", "i8_f3v2_v6")
        test_graphs = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")
        conditions = ("original", "forecast_counterfactual")
        hard_names = tuple(field.name for field in fields(HardIntegrityCounts))
        zero_counts = HardIntegrityCounts(**{name: 0 for name in hard_names})

        def canonical(value: object) -> bytes:
            return json.dumps(
                value, ensure_ascii=False, allow_nan=False,
                separators=(",", ":"), sort_keys=False,
            ).encode("utf-8")

        def file_ref(relative_path: str) -> list[object]:
            content = (project / relative_path).read_bytes()
            return [relative_path, hashlib.sha256(content).hexdigest(), len(content)]

        source_entries = [
            [entry["relative_path"], entry["sha256"], entry["byte_size"]]
            for entry in (
                baseline["certified_source_files"]
                + baseline["additional_learner_dependencies"]
            )
        ]
        source_entries.extend(file_ref(relative_path) for relative_path in (
            "src/pa_rl/family3_v2_learning.py",
            "src/pa_rl/family3_v2_pilot_criteria.py",
            "src/pa_rl/family3_v2_pilot_checkpoints.py",
        ))
        source_manifest_bytes = canonical({
            "schema_version": "family3_v2_pilot_source_manifest_v0",
            "entries": source_entries,
        })

        runtime_values = {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "torch_version": str(torch.__version__),
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "device_type": "cpu",
        }

        def device_digest(values: dict[str, str]) -> str:
            return hashlib.sha256(canonical({
                "python_implementation": values["python_implementation"],
                "python_version": values["python_version"],
                "torch_version": values["torch_version"],
                "platform_system": values["platform_system"],
                "platform_machine": values["platform_machine"],
                "device_type": values["device_type"],
            })).hexdigest()

        def make_boundary(
            *, evidence_mode: str = "FORMAL", training_seeds: tuple[int, ...] = seeds,
            arm_budget: int = 260, graph_budget: int = 52,
            episodes: int = 50, runtime: dict[str, str] | None = None,
        ) -> PilotBoundary:
            actual_runtime = runtime_values if runtime is None else runtime
            return PilotBoundary(
                schema_version="family3_v2_pilot_boundary_v0",
                evidence_mode=evidence_mode,
                experiment_id="increment8_family3_v2_learner_pilot_v0",
                config_relative_path="config.json",
                config_sha256=hashlib.sha256(config_bytes).hexdigest(),
                config_byte_size=len(config_bytes),
                source_manifest_relative_path="source_manifest.json",
                source_manifest_sha256=hashlib.sha256(source_manifest_bytes).hexdigest(),
                source_manifest_byte_size=len(source_manifest_bytes),
                certified_dependency_manifest_relative_path="certified_dependency_manifest.json",
                certified_dependency_manifest_sha256=hashlib.sha256(baseline_bytes).hexdigest(),
                certified_dependency_manifest_byte_size=len(baseline_bytes),
                certified_suite_version="increment8_family3_v2_forecast_scope_reservation_v0",
                certified_suite_sha256="98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c",
                certified_final_verdict_relative_path="results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/final_verdict.json",
                certified_final_verdict_sha256="ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552",
                english_spec_sha256="f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9",
                chinese_spec_sha256="0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20",
                method_ids=methods,
                trained_method_ids=trained,
                training_seeds=training_seeds,
                train_graph_ids=train_graphs,
                validation_graph_ids=validation_graphs,
                test_graph_ids=test_graphs,
                condition_ids=conditions,
                transitions_per_arm=arm_budget,
                transitions_per_train_graph=graph_budget,
                episodes_per_evaluation_cell=episodes,
                python_implementation=actual_runtime["python_implementation"],
                python_version=actual_runtime["python_version"],
                torch_version=actual_runtime["torch_version"],
                platform_system=actual_runtime["platform_system"],
                platform_machine=actual_runtime["platform_machine"],
                device_type=actual_runtime["device_type"],
                device_identity_sha256=device_digest(actual_runtime),
                durability_profile="file_fsync_atomic_replace_atomic_exclusive_link_dirsync_v0",
            )

        boundary_fields = (
            "schema_version", "evidence_mode", "experiment_id",
            "config_relative_path", "config_sha256", "config_byte_size",
            "source_manifest_relative_path", "source_manifest_sha256",
            "source_manifest_byte_size",
            "certified_dependency_manifest_relative_path",
            "certified_dependency_manifest_sha256",
            "certified_dependency_manifest_byte_size", "certified_suite_version",
            "certified_suite_sha256", "certified_final_verdict_relative_path",
            "certified_final_verdict_sha256", "english_spec_sha256",
            "chinese_spec_sha256", "method_ids", "trained_method_ids",
            "training_seeds", "train_graph_ids", "validation_graph_ids",
            "test_graph_ids", "condition_ids", "transitions_per_arm",
            "transitions_per_train_graph", "episodes_per_evaluation_cell",
            "python_implementation", "python_version", "torch_version",
            "platform_system", "platform_machine", "device_type",
            "device_identity_sha256", "durability_profile",
        )
        ref_fields = (
            "schema_version", "method_id", "training_seed", "attempt_number",
            "checkpoint_kind", "payload_relative_path", "payload_sha256",
            "payload_byte_size", "manifest_relative_path", "manifest_sha256",
            "manifest_byte_size", "boundary_sha256", "transition_count",
            "per_graph_transition_counts", "semantic_state_sha256",
            "evaluation_fingerprint_sha256",
        )
        self.assertEqual(tuple(field.name for field in fields(PilotBoundary)), boundary_fields)
        self.assertEqual(tuple(field.name for field in fields(FinalCheckpointRef)), ref_fields)
        self.assertEqual(PilotBoundary.__slots__, boundary_fields)
        self.assertEqual(FinalCheckpointRef.__slots__, ref_fields)
        self.assertNotIn("_task5_test_fault_injection", checkpoint_module.__all__)
        signatures = {
            "create_or_validate": ("output_root", "boundary", "config_bytes", "source_manifest_bytes", "certified_dependency_manifest_bytes"),
            "begin_training_attempt": ("self", "method_id", "training_seed", "command", "manual_restart_of_attempt"),
            "commit_final_checkpoint": ("self", "method_id", "training_seed", "attempt_number", "learner", "transition_count", "per_graph_transition_counts", "learner_update_count", "initial_state_hashes", "command"),
            "load_verified_final_checkpoint": ("self", "reference"),
            "evaluation_fingerprint": ("self", "reference", "learner"),
            "append_evaluation_row": ("self", "row"),
            "load_verified_rows": ("self", "phase"),
            "write_validation_gate": ("self", "result", "command"),
            "write_test_permit": ("self", "result", "command"),
            "open_test_once": ("self", "resume", "command"),
            "missing_test_coordinates": ("self",),
            "commit_final_verdict": ("self", "result", "command"),
            "record_failure": ("self", "failure_kind", "failure_code", "message", "method_id", "training_seed", "attempt_number", "command", "next_action"),
        }
        for name, expected in signatures.items():
            actual = inspect.signature(getattr(Family3V2PilotArtifactStore, name))
            with self.subTest(signature=name):
                self.assertEqual(tuple(actual.parameters), expected)

        formal = make_boundary(arm_budget=12_000, graph_budget=2_400)
        self.assertEqual((formal.transitions_per_arm, formal.transitions_per_train_graph), (12_000, 2_400))
        with self.assertRaises(FrozenInstanceError):
            formal.evidence_mode = "NON_EVIDENCE_SMOKE"  # type: ignore[misc]
        for mutation in (
            {"schema_version": "wrong"}, {"training_seeds": (29, 17, 43)},
            {"method_ids": methods[::-1]}, {"config_byte_size": True},
            {"config_sha256": "A" * 64}, {"train_graph_ids": train_graphs[::-1]},
            {"transitions_per_arm": 11_999}, {"transitions_per_train_graph": 2_399},
            {"device_type": "cuda"}, {"python_version": "C:/absolute"},
        ):
            with self.subTest(boundary_mutation=mutation), self.assertRaises(ValueError):
                replace(formal, **mutation)

        def learner_for(method_id: str, seed: int, budget: int) -> object:
            gamma = 0.0 if method_id.endswith("gamma0") else 1.0
            if method_id.startswith("tabular"):
                learner = TabularQLearner(alpha=0.2, gamma=gamma)
                learner.set_value("state-b", "deny", -0.25)
                learner.set_value("state-a", "request_narrow", 0.5)
                learner.set_value("state-a", "deny", 0.125)
                return learner
            hyperparameters = DDQNHyperparameters(
                gamma=gamma, learning_rate=0.001, batch_size=64,
                replay_capacity=20_000, warmup_transitions=256,
                optimize_every=4, target_update_every=250, gradient_clip=5.0,
            )
            learner = Family3V2MaskedDoubleDQN(
                rng_deriver=Family3V2LearnerRngDeriver(
                    experiment_id=formal.experiment_id,
                    learner_family="masked_ddqn", base_seed=seed,
                ),
                hyperparameters=hyperparameters,
                model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
            )
            transition = _ReplayTransition(
                state=torch.zeros(43, dtype=torch.float32),
                candidates=torch.zeros((7, 7), dtype=torch.float32),
                mask=torch.tensor((True, False, False, False, False, False, False)),
                action_row=0, action_candidate_id="request_narrow", reward=0.0,
                next_state=torch.zeros(43, dtype=torch.float32),
                next_candidates=torch.zeros((7, 7), dtype=torch.float32),
                next_mask=torch.zeros(7, dtype=torch.bool), done=True,
            )
            for _ in range(budget):
                learner._buffer.add(transition)
            expected_updates = 0 if budget < 256 else 1 + (budget - 256) // 4
            for _ in range(expected_updates):
                for parameter in learner.online_network.parameters():
                    parameter.grad = torch.zeros_like(parameter)
                learner._optimizer.step()
                learner._optimizer.zero_grad(set_to_none=True)
            learner.environment_steps = budget
            learner.optimizer_steps = expected_updates
            learner.last_loss = None if expected_updates == 0 else 0.125
            learner._buffer._rng.random()
            return learner

        def initial_hashes(method_id: str, seed: int) -> tuple[tuple[str, str], ...]:
            if method_id.startswith("tabular"):
                return ((
                    "tabular_empty_table",
                    hashlib.sha256(f"tabular:{seed}".encode()).hexdigest(),
                ),)
            return tuple(
                (name, hashlib.sha256(f"{name}:{seed}".encode()).hexdigest())
                for name in ("ddqn_online", "ddqn_target", "ddqn_optimizer")
            )

        seen_seams: set[str] = set()
        crash_on: list[str | None] = [None]

        class InjectedCrash(RuntimeError):
            pass

        def hook(seam_name: str, relative_path: str) -> None:
            self.assertTrue(relative_path and "\\" not in relative_path)
            seen_seams.add(seam_name)
            if crash_on[0] == seam_name:
                crash_on[0] = None
                raise InjectedCrash(seam_name)

        def create_store(
            root: Path, boundary: PilotBoundary,
        ) -> Family3V2PilotArtifactStore:
            return Family3V2PilotArtifactStore.create_or_validate(
                root, boundary=boundary, config_bytes=config_bytes,
                source_manifest_bytes=source_manifest_bytes,
                certified_dependency_manifest_bytes=baseline_bytes,
            )

        def train_all(
            root: Path, boundary: PilotBoundary, *, exercise_restart: bool,
        ) -> tuple[Family3V2PilotArtifactStore, tuple[FinalCheckpointRef, ...]]:
            store = create_store(root, boundary)
            refs: list[FinalCheckpointRef] = []
            with self.assertRaises(ValueError):
                store.begin_training_attempt(
                    "random_valid", 17, command=("unit-test",)
                )
            with self.assertRaises(ValueError):
                store.begin_training_attempt(
                    trained[1], 17, command=("unit-test",)
                )
            for method_id in trained:
                for seed in boundary.training_seeds:
                    command = ("unit-test", "train", method_id, str(seed))
                    attempt = store.begin_training_attempt(
                        method_id, seed, command=command
                    )
                    if exercise_restart and not refs:
                        with self.assertRaises(ValueError):
                            store.begin_training_attempt(
                                method_id, seed, command=command
                            )
                        store.record_failure(
                            "RESTARTABLE_ARM_FAILURE", "synthetic_interrupt",
                            "synthetic restart boundary", method_id=method_id,
                            training_seed=seed, attempt_number=attempt,
                            command=command,
                            next_action="MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO",
                        )
                        self.assertTrue((
                            root
                            / f"training/{method_id}/{seed}/attempts/0001/failure.json"
                        ).is_file())
                        attempt = store.begin_training_attempt(
                            method_id, seed, command=command,
                            manual_restart_of_attempt=1,
                        )
                        self.assertEqual(attempt, 2)
                    learner = learner_for(
                        method_id, seed, boundary.transitions_per_arm
                    )
                    expected_updates = (
                        boundary.transitions_per_arm
                        if method_id.startswith("tabular")
                        else (
                            0 if boundary.transitions_per_arm < 256
                            else 1 + (boundary.transitions_per_arm - 256) // 4
                        )
                    )
                    reference = store.commit_final_checkpoint(
                        method_id, seed, attempt, learner=learner,
                        transition_count=boundary.transitions_per_arm,
                        per_graph_transition_counts=tuple(
                            (graph_id, boundary.transitions_per_train_graph)
                            for graph_id in train_graphs
                        ),
                        learner_update_count=expected_updates,
                        initial_state_hashes=initial_hashes(method_id, seed),
                        command=command,
                    )
                    refs.append(reference)
                    with self.assertRaises(ValueError):
                        store.begin_training_attempt(
                            method_id, seed, command=command
                        )
            return store, tuple(refs)

        def rows_for(
            phase: str, *, no_test: bool = False,
        ) -> tuple[EvaluationEpisodeRow, ...]:
            graphs = validation_graphs if phase == "validation" else test_graphs
            built: list[EvaluationEpisodeRow] = []
            for method_id in methods:
                for seed in seeds:
                    for graph_id in graphs:
                        for condition in conditions:
                            forecast = (
                                "request_narrow"
                                if condition == "original"
                                else "request_broader"
                            )
                            for ordinal in range(50):
                                root_id = (
                                    forecast
                                    if method_id in (
                                        "forecast_rule", "masked_ddqn_gamma1",
                                    )
                                    else "deny"
                                )
                                if method_id == "forecast_ablated_rule":
                                    root_id = (
                                        forecast
                                        if phase == "validation" or ordinal < 25
                                        else "deny"
                                    )
                                if method_id == "masked_ddqn_gamma0":
                                    root_id = (
                                        forecast
                                        if phase == "validation" or ordinal < 20
                                        else "deny"
                                    )
                                success = (
                                    int(ordinal < 40)
                                    if method_id in (
                                        "forecast_rule", "masked_ddqn_gamma1",
                                    )
                                    else int(ordinal < 25)
                                    if method_id == "forecast_ablated_rule"
                                    else int(ordinal < 20)
                                    if method_id == "masked_ddqn_gamma0"
                                    else int(ordinal < 10)
                                    if method_id.startswith("tabular")
                                    else int(ordinal < 5)
                                )
                                if (
                                    phase == "validation"
                                    and method_id == "masked_ddqn_gamma1"
                                    and seed == 43
                                    and graph_id == validation_graphs[0]
                                    and condition == conditions[0]
                                    and ordinal == 0
                                ):
                                    success = 1 - success
                                if (
                                    no_test and phase == "validation"
                                    and method_id == "masked_ddqn_gamma1"
                                    and seed == 29
                                    and graph_id == validation_graphs[0]
                                    and condition == conditions[0]
                                    and ordinal == 0
                                ):
                                    root_id = "deny"
                                built.append(EvaluationEpisodeRow(
                                    phase=phase, method_id=method_id,
                                    evaluation_seed=seed, graph_id=graph_id,
                                    condition=condition,
                                    episode_ordinal=ordinal,
                                    root_seed=derive_family3_v2_eval_environment_seed(
                                        experiment_id=formal.experiment_id,
                                        evaluation_seed=seed,
                                        graph_id=graph_id,
                                        episode_ordinal=ordinal,
                                    ),
                                    root_semantic_candidate_id=root_id,
                                    terminal_success=success,
                                    termination_kind=(
                                        "natural_completion"
                                        if success else "deny_with_reason"
                                    ),
                                    decision_count=1, prompt_count=0,
                                    hard_counts=zero_counts,
                                ))
            return tuple(built)

        validation_rows = rows_for("validation")
        no_test_rows = rows_for("validation", no_test=True)
        test_rows = rows_for("test")
        self.assertEqual((len(validation_rows), len(test_rows)), (4_200, 6_300))
        self.assertEqual(
            len({
                (
                    row.method_id, row.evaluation_seed, row.graph_id,
                    row.condition, row.episode_ordinal,
                )
                for row in test_rows
            }),
            6_300,
        )

        with tempfile.TemporaryDirectory(dir=project) as directory:
            temporary = Path(directory).resolve()
            link_target = temporary / "link-target"
            link_target.mkdir()
            link_alias = temporary / "link-alias"
            junction_probe = False
            try:
                link_alias.symlink_to(link_target, target_is_directory=True)
            except OSError as error:
                if os.name != "nt" or getattr(error, "winerror", None) != 1314:
                    raise
                # A junction is a real reparse point and needs no symlink privilege.
                import _winapi

                _winapi.CreateJunction(str(link_target), str(link_alias))
                junction_probe = True
                self.assertTrue(link_alias.lstat().st_file_attributes & 0x400)
            try:
                with self.assertRaises(ValueError):
                    with checkpoint_module._task5_test_fault_injection(
                        link_alias, hook
                    ):
                        pass
            finally:
                if junction_probe:
                    # Remove only the link; its target is owned by TemporaryDirectory.
                    link_alias.rmdir()

            unavailable = temporary / "unavailable-link"
            unavailable.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                unavailable, hook
            ):
                with patch.object(
                    os, "link", side_effect=OSError("no hard links")
                ):
                    with self.assertRaises(RuntimeError):
                        create_store(unavailable, make_boundary())
                self.assertEqual(tuple(unavailable.iterdir()), ())

            wrong_runtime = dict(runtime_values)
            wrong_runtime["python_version"] = "0.0.0"
            runtime_root = temporary / "runtime-mismatch"
            runtime_root.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                runtime_root, hook
            ):
                with self.assertRaises(ValueError):
                    create_store(
                        runtime_root, make_boundary(runtime=wrong_runtime)
                    )
                self.assertEqual(tuple(runtime_root.iterdir()), ())

            for seam in (
                "after_temp_file_fsync_before_immutable_link",
                "after_immutable_link_before_directory_fsync",
                "after_jsonl_write_before_file_fsync",
                "after_jsonl_file_fsync_before_return",
                "after_temp_file_fsync_before_snapshot_replace",
                "after_snapshot_replace_before_directory_fsync",
            ):
                crash_root = temporary / seam
                crash_root.mkdir()
                with checkpoint_module._task5_test_fault_injection(
                    crash_root, hook
                ):
                    crash_on[0] = seam
                    with self.subTest(
                        crash_seam=seam
                    ), self.assertRaises(InjectedCrash):
                        create_store(crash_root, make_boundary())
                    recovered = create_store(crash_root, make_boundary())
                    self.assertTrue((crash_root / "boundary.json").is_file())
                    self.assertEqual(
                        json.loads(
                            (crash_root / "progress.json").read_bytes()
                        )["state"],
                        "BOUNDARY_FROZEN",
                    )
                    del recovered

            main_root = temporary / "main"
            main_root.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                main_root, hook
            ):
                boundary = make_boundary()
                store, refs = train_all(
                    main_root, boundary, exercise_restart=True
                )
                self.assertEqual(len(refs), 12)
                self.assertEqual(
                    tuple(
                        (reference.method_id, reference.training_seed)
                        for reference in refs
                    ),
                    tuple(
                        (method_id, seed)
                        for method_id in trained
                        for seed in seeds
                    ),
                )
                self.assertFalse(any(
                    (main_root / "training" / method_id).exists()
                    for method_id in methods[:3]
                ))
                checkpoint_set = json.loads(
                    (main_root / "training/checkpoint_manifest.json").read_bytes()
                )
                self.assertEqual(checkpoint_set["checkpoint_count"], 12)
                self.assertEqual(
                    json.loads(
                        (main_root / "training/train_complete.json").read_bytes()
                    ),
                    {
                        "schema_version": "family3_v2_train_complete_v0",
                        "boundary_sha256": refs[0].boundary_sha256,
                        "checkpoint_manifest_sha256": hashlib.sha256(
                            (
                                main_root
                                / "training/checkpoint_manifest.json"
                            ).read_bytes()
                        ).hexdigest(),
                        "transition_budget_summary_sha256": hashlib.sha256(
                            (
                                main_root
                                / "training/transition_budget_summary.json"
                            ).read_bytes()
                        ).hexdigest(),
                        "completed_arm_count": 12,
                        "completion_status": "TRAINING_COMPLETE",
                    },
                )

                tabular_ref = refs[0]
                ddqn_ref = next(
                    reference
                    for reference in refs
                    if reference.method_id == "masked_ddqn_gamma0"
                )
                tabular_payload = json.loads(
                    (main_root / tabular_ref.payload_relative_path).read_bytes()
                )
                self.assertEqual(
                    tabular_payload["q_rows"],
                    sorted(
                        tabular_payload["q_rows"],
                        key=lambda row: (row[0], row[1]),
                    ),
                )
                manifest = json.loads(
                    (main_root / ddqn_ref.manifest_relative_path).read_bytes()
                )
                self.assertEqual(
                    tuple(manifest["algorithm_metadata"]),
                    (
                        "model_spec", "hyperparameters",
                        "online_state_sha256", "target_state_sha256",
                        "optimizer_state_sha256", "replay_capacity",
                        "replay_size", "replay_cursor",
                        "replay_content_sha256",
                        "replay_rng_state_sha256",
                    ),
                )
                self.assertEqual(
                    manifest["algorithm_metadata"]["replay_size"], 260
                )
                self.assertEqual(
                    manifest["algorithm_metadata"]["replay_cursor"], 260
                )
                self.assertEqual(
                    manifest["training_metadata"]["optimizer_steps"], 2
                )
                self.assertEqual(
                    manifest["training_metadata"]["last_loss_hex"],
                    (0.125).hex(),
                )
                self.assertEqual(
                    tuple(
                        pair[0]
                        for pair in manifest["initial_state_hashes"]
                    ),
                    ("ddqn_online", "ddqn_target", "ddqn_optimizer"),
                )

                torch_load_calls: list[tuple[object, object]] = []
                real_torch_load = torch.load

                def safe_load(*args: object, **kwargs: object) -> object:
                    torch_load_calls.append((
                        kwargs.get("map_location"),
                        kwargs.get("weights_only"),
                    ))
                    return real_torch_load(*args, **kwargs)

                with patch.object(torch, "load", side_effect=safe_load):
                    loaded_ddqn = store.load_verified_final_checkpoint(
                        ddqn_ref
                    )
                self.assertTrue(torch_load_calls)
                self.assertTrue(all(
                    call == ("cpu", True) for call in torch_load_calls
                ))
                loaded_tabular = store.load_verified_final_checkpoint(
                    tabular_ref
                )
                self.assertIs(type(loaded_tabular), TabularQLearner)
                self.assertEqual(
                    loaded_tabular.q_values,
                    learner_for("tabular_q_gamma0", 17, 260).q_values,
                )
                self.assertEqual(loaded_ddqn.replay_size, 0)
                self.assertEqual(
                    store.evaluation_fingerprint(ddqn_ref, loaded_ddqn),
                    ddqn_ref.evaluation_fingerprint_sha256,
                )
                self.assertEqual(
                    store.evaluation_fingerprint(
                        tabular_ref, loaded_tabular
                    ),
                    tabular_ref.evaluation_fingerprint_sha256,
                )
                with self.assertRaises(ValueError):
                    store.load_verified_final_checkpoint(
                        replace(ddqn_ref, payload_sha256="0" * 64)
                    )
                with self.assertRaises(ValueError):
                    replace(
                        ddqn_ref,
                        payload_relative_path="../checkpoint.pt",
                    )
                with self.assertRaises(ValueError):
                    replace(
                        ddqn_ref,
                        payload_relative_path=str(
                            (main_root / "escape.pt").resolve()
                        ),
                    )

                if minimal:
                    row = validation_rows[0]
                    store.append_evaluation_row(row)
                    reopened = create_store(main_root, boundary)
                    self.assertEqual(reopened.load_verified_rows("validation"), (row,))
                    ledger_path = main_root / "validation/rows.jsonl"
                    before = ledger_path.read_bytes()
                    with self.assertRaises(DuplicateCoordinateError):
                        reopened.append_evaluation_row(row)
                    with self.assertRaises(ConflictingCoordinateError):
                        reopened.append_evaluation_row(replace(
                            row, terminal_success=1 - row.terminal_success,
                        ))
                    with self.assertRaises(ValueError):
                        reopened.append_evaluation_row(replace(
                            row, root_seed=row.root_seed + 1,
                        ))
                    with self.assertRaises(ValueError):
                        reopened.open_test_once(
                            resume=False, command=("unit-test", "unpermitted-open"),
                        )
                    self.assertEqual(ledger_path.read_bytes(), before)
                    self.assertFalse((main_root / "test/start_marker.json").exists())
                    return

                for index, row in enumerate(validation_rows):
                    store.append_evaluation_row(row)
                    if index == 0:
                        ledger_path = main_root / "validation/rows.jsonl"
                        before = ledger_path.read_bytes()
                        with self.assertRaises(DuplicateCoordinateError):
                            store.append_evaluation_row(row)
                        with self.assertRaises(
                            ConflictingCoordinateError
                        ):
                            store.append_evaluation_row(replace(
                                row,
                                terminal_success=1 - row.terminal_success,
                            ))
                        self.assertEqual(ledger_path.read_bytes(), before)
                        with self.assertRaises(ValueError):
                            store.append_evaluation_row(replace(
                                row, root_seed=row.root_seed + 1
                            ))
                self.assertEqual(
                    store.load_verified_rows("validation"),
                    validation_rows,
                )
                validation_ledger = (
                    main_root / "validation/rows.jsonl"
                ).read_bytes()
                self.assertNotIn(b"\r", validation_ledger)
                self.assertTrue(validation_ledger.endswith(b"\n"))
                first_record = json.loads(
                    validation_ledger.splitlines()[0]
                )
                self.assertEqual(
                    tuple(first_record),
                    (
                        "schema_version", "phase", "segment_number",
                        "sequence", "boundary_sha256", "coordinate_key",
                        "previous_record_sha256", "payload_sha256",
                        "payload", "record_sha256",
                    ),
                )
                self.assertEqual(first_record["sequence"], 0)
                self.assertEqual(
                    first_record["previous_record_sha256"], "0" * 64
                )

                ready = evaluate_validation_gate(
                    config, validation_rows, phase_complete=True
                )
                self.assertEqual(ready.status, "READY_FOR_TEST")
                store.write_validation_gate(
                    ready, command=("unit-test", "validation")
                )
                self.assertFalse(
                    (main_root / "final_verdict.json").exists()
                )
                store.write_test_permit(
                    ready, command=("unit-test", "permit")
                )
                permit = json.loads(
                    (main_root / "test_permit.json").read_bytes()
                )
                self.assertEqual(
                    permit["qualifying_seed_ids"], [17, 29]
                )
                self.assertEqual(
                    len(permit["final_checkpoint_file_hashes"]), 12
                )
                self.assertEqual(permit["test_state"], "UNOPENED")

                crash_on[0] = (
                    "after_test_open_event_fsync_before_marker"
                )
                with self.assertRaises(InjectedCrash):
                    store.open_test_once(
                        resume=False, command=("unit-test", "open")
                    )
                self.assertFalse(
                    (main_root / "test/start_marker.json").exists()
                )
                store.open_test_once(
                    resume=False, command=("unit-test", "open")
                )
                unlock_lines = (
                    main_root / "test/unlock_ledger.jsonl"
                ).read_bytes().splitlines()
                self.assertEqual(len(unlock_lines), 1)
                with self.assertRaises(ValueError):
                    store.open_test_once(
                        resume=False, command=("unit-test", "open")
                    )

                sparse = test_rows[::1000]
                for row in sparse:
                    store.append_evaluation_row(row)
                store.open_test_once(
                    resume=True, command=("unit-test", "resume-1")
                )
                missing = store.missing_test_coordinates()
                self.assertEqual(
                    len(missing), 6_300 - len(sparse)
                )
                self.assertNotIn(
                    (
                        sparse[0].method_id,
                        sparse[0].evaluation_seed,
                        sparse[0].graph_id,
                        sparse[0].condition,
                        sparse[0].episode_ordinal,
                    ),
                    missing,
                )
                indexed_test = {
                    (
                        row.method_id, row.evaluation_seed, row.graph_id,
                        row.condition, row.episode_ordinal,
                    ): row
                    for row in test_rows
                }
                for coordinate in missing:
                    store.append_evaluation_row(
                        indexed_test[coordinate]
                    )
                self.assertTrue((
                    main_root / "test/rows.resume.0001.jsonl"
                ).is_file())
                self.assertEqual(
                    store.missing_test_coordinates(), ()
                )
                store.open_test_once(
                    resume=True,
                    command=("unit-test", "resume-complete"),
                )
                with self.assertRaises(DuplicateCoordinateError):
                    store.append_evaluation_row(test_rows[0])

                parity = classify_test_result(
                    config, test_rows, validation_gate=ready,
                    permitted_seed_ids=(17, 29), test_opened=True,
                    phase_complete=True,
                )
                self.assertEqual(
                    parity.classification, "RULE_PARITY_SIGNAL"
                )
                store.commit_final_verdict(
                    parity, command=("unit-test", "verdict")
                )
                verdict = json.loads(
                    (main_root / "final_verdict.json").read_bytes()
                )
                self.assertEqual(
                    verdict["run_status"], "RULE_PARITY_SIGNAL"
                )
                self.assertEqual(
                    verdict["scientific_classification"],
                    "RULE_PARITY_SIGNAL",
                )
                self.assertTrue(all(
                    verdict[name] is not None
                    for name in (
                        "test_rows_manifest_sha256",
                        "test_result_sha256",
                        "test_paired_comparison_sha256",
                        "test_hard_integrity_sha256",
                    )
                ))
                with self.assertRaises(ValueError):
                    store.commit_final_verdict(
                        parity, command=("unit-test", "verdict")
                    )
                with self.assertRaises(ValueError):
                    store.append_evaluation_row(test_rows[0])

                test_segment = (
                    main_root / "test/rows.resume.0001.jsonl"
                )
                original_segment = test_segment.read_bytes()
                test_segment.write_bytes(original_segment + b"{")
                corrupted = test_segment.read_bytes()
                with self.assertRaises(ValueError):
                    store.load_verified_rows("test")
                self.assertEqual(
                    test_segment.read_bytes(), corrupted
                )
                test_segment.write_bytes(original_segment)

                validation_path = (
                    main_root / "validation/rows.jsonl"
                )
                original_validation = validation_path.read_bytes()
                lines = original_validation.splitlines(keepends=True)
                validation_path.write_bytes(
                    lines[1] + lines[0] + b"".join(lines[2:])
                )
                reordered = validation_path.read_bytes()
                with self.assertRaises(ValueError):
                    store.load_verified_rows("validation")
                self.assertEqual(
                    validation_path.read_bytes(), reordered
                )
                validation_path.write_bytes(original_validation)

                payload_path = (
                    main_root / ddqn_ref.payload_relative_path
                )
                original_payload = payload_path.read_bytes()
                payload_path.write_bytes(original_payload + b"tamper")
                tampered_payload = payload_path.read_bytes()
                with self.assertRaises(ValueError):
                    store.load_verified_final_checkpoint(ddqn_ref)
                self.assertEqual(
                    payload_path.read_bytes(), tampered_payload
                )
                payload_path.write_bytes(original_payload)

                manifest_path = (
                    main_root / ddqn_ref.manifest_relative_path
                )
                original_manifest = manifest_path.read_bytes()
                manifest_path.write_bytes(original_manifest.replace(
                    b"family3_v2_checkpoint_manifest_v0",
                    b"family3_v2_checkpoint_manifest_X0",
                    1,
                ))
                tampered_manifest = manifest_path.read_bytes()
                with self.assertRaises(ValueError):
                    store.load_verified_final_checkpoint(ddqn_ref)
                self.assertEqual(
                    manifest_path.read_bytes(), tampered_manifest
                )
                manifest_path.write_bytes(original_manifest)

            no_test_root = temporary / "no-test"
            no_test_root.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                no_test_root, hook
            ):
                no_test_store, _ = train_all(
                    no_test_root, make_boundary(),
                    exercise_restart=False,
                )
                for row in no_test_rows:
                    no_test_store.append_evaluation_row(row)
                no_test_result = evaluate_validation_gate(
                    config, no_test_rows, phase_complete=True
                )
                self.assertEqual(no_test_result.status, "NO_TEST")
                no_test_store.write_validation_gate(
                    no_test_result,
                    command=("unit-test", "no-test-gate"),
                )
                with self.assertRaises(ValueError):
                    no_test_store.write_test_permit(
                        no_test_result,
                        command=("unit-test", "forbidden-permit"),
                    )
                no_test_verdict = classify_test_result(
                    config, (), validation_gate=no_test_result,
                    permitted_seed_ids=(), test_opened=False,
                    phase_complete=False,
                )
                no_test_store.commit_final_verdict(
                    no_test_verdict,
                    command=("unit-test", "no-test-verdict"),
                )
                self.assertEqual(
                    json.loads(
                        (
                            no_test_root / "final_verdict.json"
                        ).read_bytes()
                    )["run_status"],
                    "NO_TEST",
                )

            invalid_root = temporary / "invalid"
            invalid_root.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                invalid_root, hook
            ):
                invalid_store, _ = train_all(
                    invalid_root, make_boundary(),
                    exercise_restart=False,
                )
                invalid_gate = evaluate_validation_gate(
                    config, (), phase_complete=True
                )
                self.assertEqual(
                    invalid_gate.status, "INVALID_RUN"
                )
                invalid_store.write_validation_gate(
                    invalid_gate,
                    command=("unit-test", "invalid-gate"),
                )
                invalid_verdict = classify_test_result(
                    config, (), validation_gate=invalid_gate,
                    permitted_seed_ids=(), test_opened=False,
                    phase_complete=False,
                )
                invalid_store.commit_final_verdict(
                    invalid_verdict,
                    command=("unit-test", "invalid-verdict"),
                )
                self.assertEqual(
                    json.loads(
                        (
                            invalid_root / "final_verdict.json"
                        ).read_bytes()
                    )["run_status"],
                    "INVALID_RUN",
                )

            smoke_root = temporary / "smoke"
            smoke_root.mkdir()
            with checkpoint_module._task5_test_fault_injection(
                smoke_root, hook
            ):
                smoke_boundary = make_boundary(
                    evidence_mode="NON_EVIDENCE_SMOKE",
                    training_seeds=(17,), arm_budget=5,
                    graph_budget=1, episodes=1,
                )
                smoke_store, smoke_refs = train_all(
                    smoke_root, smoke_boundary,
                    exercise_restart=False,
                )
                self.assertEqual(len(smoke_refs), 4)
                smoke_gate = evaluate_validation_gate(
                    config, (), phase_complete=False
                )
                smoke_store.write_validation_gate(
                    smoke_gate, command=("unit-test", "smoke-gate")
                )
                with self.assertRaises(ValueError):
                    smoke_store.write_test_permit(
                        smoke_gate,
                        command=("unit-test", "smoke-permit"),
                    )
                smoke_result = classify_test_result(
                    config, (), validation_gate=smoke_gate,
                    permitted_seed_ids=(), test_opened=False,
                    phase_complete=False,
                )
                smoke_store.commit_final_verdict(
                    smoke_result,
                    command=("unit-test", "smoke-verdict"),
                )
                smoke_verdict = json.loads(
                    (smoke_root / "final_verdict.json").read_bytes()
                )
                self.assertEqual(
                    smoke_verdict["run_status"],
                    "NON_EVIDENCE_SMOKE_COMPLETE",
                )
                self.assertIsNone(
                    smoke_verdict["scientific_classification"]
                )
                self.assertFalse(
                    (smoke_root / "test_permit.json").exists()
                )
                self.assertFalse((smoke_root / "test").exists())

            required_seams = {
                "after_temp_file_fsync_before_snapshot_replace",
                "after_snapshot_replace_before_directory_fsync",
                "after_temp_file_fsync_before_immutable_link",
                "after_immutable_link_before_directory_fsync",
                "after_jsonl_write_before_file_fsync",
                "after_jsonl_file_fsync_before_return",
                "after_checkpoint_payload_publish",
                "after_checkpoint_manifest_publish",
                "after_checkpoint_ref_publish",
                "after_validation_result_publish",
                "after_validation_gate_publish",
                "after_test_permit_publish",
                "after_test_open_event_fsync_before_marker",
                "after_test_start_marker_publish",
                "after_test_result_publish",
                "after_final_verdict_publish",
            }
            self.assertEqual(seen_seams, required_seams)
            durability = json.loads(
                (main_root / "durability.json").read_bytes()
            )
            self.assertEqual(
                durability["immutable_publish"],
                "same_directory_hard_link_exclusive",
            )
            self.assertIn(
                durability["directory_fsync"],
                ("supported_and_used", "unavailable_recorded"),
            )
            self.assertNotIn(
                "\\",
                (
                    main_root / "boundary.json"
                ).relative_to(main_root).as_posix(),
            )

        self.assertFalse((
            project / "results/increment8_family3_v2_learner_pilot_v0"
        ).exists())
        self.assertFalse((
            project
            / "results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke"
        ).exists())


if __name__ == "__main__":
    unittest.main()
