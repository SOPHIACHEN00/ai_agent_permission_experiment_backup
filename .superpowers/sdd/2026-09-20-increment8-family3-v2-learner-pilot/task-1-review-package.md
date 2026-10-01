# Task 1 review package

Base HEAD (record only): dd2efc383800831dfec7e89ba1607b529e4f6f05
Pre-state: first four targets absent; checkpoint SHA-256 b738a0a2b435f9e5b8fc0c65277d4a35d28bf86c5e561ee5e4d64b02b195c436.

## Post-state manifest
- configs/evaluation/family3_v2_learner_pilot_v0.json — 8377 bytes — 7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2
- docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json — 6846 bytes — 41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e
- src/pa_rl/family3_v2_pilot_criteria.py — 6040 bytes — 11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7
- tests/test_family3_v2_learner_pilot.py — 3880 bytes — b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e
- docs/CONTINUATION_CHECKPOINT.md — 65135 bytes — 45fdb03f541a58c108d9fb313f2fa8b5a9810d0c7d7d19ea7f056f9a5d5ff131

## New file: configs/evaluation/family3_v2_learner_pilot_v0.json
```
{
  "schema_version": "family3_v2_learner_pilot_config_v0",
  "experiment_id": "increment8_family3_v2_learner_pilot_v0",
  "certified_environment": {
    "suite_version": "increment8_family3_v2_forecast_scope_reservation_v0",
    "mutation_policy": "forbid_certified_dependency_manifest_changes",
    "certified_dependency_manifest": "existing_exact_preflight_run_config_and_final_verdict",
    "required_existing_source_files": [
      "family3_v2_artifacts.py", "family3_v2_audit.py", "family3_v2_authority.py", "family3_v2_contracts.py", "family3_v2_environment.py", "family3_v2_exact_reference.py", "family3_v2_exact_solver.py", "family3_v2_model.py", "family3_v2_outcome.py", "family3_v2_policy.py", "family3_v2_preflight.py", "family3_v2_rng.py", "family3_v2_suite.py"
    ],
    "additional_learner_dependencies": ["src/pa_rl/ddqn.py", "src/pa_rl/baselines.py"],
    "existing_tests_policy": "do_not_modify_but_not_formal_runtime_hash_gate",
    "adapter": {
      "pregrant_state_width": 37,
      "maximum_state_width": 43,
      "state_padding": "right_zero_to_43",
      "candidate_count": 7,
      "candidate_feature_width": 7,
      "mask_width": 7,
      "numeric_dtype": "float32",
      "mask_dtype": "bool",
      "terminal_successor": "none"
    }
  },
  "split": {
    "train": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
    "validation": ["i8_f3v2_v5", "i8_f3v2_v6"],
    "test": ["i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"]
  },
  "methods": [
    {"id": "random_valid", "kind": "baseline", "train": false},
    {"id": "forecast_ablated_rule", "kind": "baseline", "train": false},
    {"id": "forecast_rule", "kind": "baseline", "train": false, "tie_policy": "fail_closed_integrity_error"},
    {"id": "tabular_q_gamma0", "kind": "learner_diagnostic", "gamma": 0.0, "train": true},
    {"id": "tabular_q_gamma1", "kind": "learner_diagnostic", "gamma": 1.0, "train": true},
    {"id": "masked_ddqn_gamma0", "kind": "learner_control", "gamma": 0.0, "train": true},
    {"id": "masked_ddqn_gamma1", "kind": "learner_primary", "gamma": 1.0, "train": true}
  ],
  "training": {
    "seeds": [17, 29, 43],
    "counterfactuals_allowed": false,
    "transitions_per_learner_seed": 12000,
    "allocation": {
      "mode": "transition_quota_round_robin",
      "graph_order": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
      "transitions_per_train_graph": 2400,
      "per_graph_visit": "one_episode_or_until_remaining_transition_quota",
      "partial_final_episode": "stop_collection_without_synthetic_terminal"
    },
    "checkpoint_policy": "final_only",
    "final_checkpoint_transition": 12000,
    "matched_pair_rng": {
      "schema": "family3_v2_learner_rng_v0",
      "u64_derivation": "u64be(first8(SHA256(canonical_json([schema,experiment_id,learner_family,namespace,base_seed,coordinate_fields]))))",
      "gamma_excluded_from_pair_derivation": true,
      "namespaces": ["model_init", "exploration", "replay_sampling", "training_environment"],
      "namespace_coordinate_fields": {"model_init": [], "exploration": ["global_transition_index", "decision_index"], "replay_sampling": ["optimizer_step"], "training_environment": ["graph_id", "graph_episode_ordinal"]},
      "equal_initial_hashes": ["ddqn_online", "ddqn_target", "ddqn_optimizer", "tabular_empty_table"],
      "separate_runtime_rng_instances": true,
      "separate_replay_buffers": true,
      "trajectory_and_replay_contents_may_diverge_after_actions": true
    },
    "interruption_recovery": {
      "completed_arm_boundary": "immutable_hash_bound_final_checkpoint",
      "incomplete_arm_policy": "manual_deterministic_restart_from_transition_zero",
      "preserve_failed_attempt_log": true,
      "automatic_retry": false,
      "completed_arm_replacement": false
    }
  },
  "hyperparameters": {
    "tabular": {"alpha": 0.2},
    "exploration": {"epsilon_start": 1.0, "epsilon_end": 0.05, "epsilon_decay_fraction": 0.70},
    "ddqn": {"learning_rate": 0.001, "batch_size": 64, "replay_capacity": 20000, "warmup_transitions": 256, "optimize_every": 4, "target_update_interval": 250, "target_update_unit": "optimizer_steps", "loss": "smooth_l1_huber", "gradient_clip": 5.0}
  },
  "evaluation": {
    "seeds": [17, 29, 43],
    "baseline_coordinate_blocks": "same_fixed_seed_cohort",
    "conditions": ["original", "forecast_counterfactual"],
    "episodes_per_graph_condition_seed": 50,
    "coordinate_schema": "family3_v2_eval_coord_v0",
    "root_seed_derivation": "u64be(first8(SHA256(canonical_json([\"family3_v2_eval_coord_v0\",experiment_id,\"environment\",evaluation_seed,graph_id,episode_ordinal]))))",
    "episode_ordinals": "0_through_49",
    "condition_pairing": "condition_and_method_excluded_from_environment_coordinate",
    "policy_rng_schema": "family3_v2_eval_policy_rng_v0",
    "policy_rng_derivation": "u64be(first8(SHA256(canonical_json([policy_rng_schema,experiment_id,\"policy\",method,evaluation_seed,graph_id,condition,episode_ordinal,decision_index]))))",
    "policy_rng_fields": ["method", "evaluation_seed", "graph_id", "condition", "episode_ordinal", "decision_index"],
    "policy_mode": "greedy_masked_except_random_valid",
    "randomness": "common_random_coordinates",
    "checkpoint": "final_only",
    "validation_resume_policy": "durable_missing_coordinates_only_no_mutation",
    "test_policy": "sealed_until_ready_then_once",
    "test_resume_policy": "durable_missing_coordinates_only_no_mutation"
  },
  "hard_zero_counts": ["invalid_action_attempts", "policy_mask_violations", "unauthorized_committed_effects", "monitor_blocked_attempts", "monitor_bypass_effects", "environment_invalid_runs", "scope_binding_integrity_failures", "authorization_binding_failures", "semantic_conformance_failures", "effect_integrity_failures", "adapter_contract_failures", "candidate_id_resolution_failures", "oracle_feature_leaks", "split_leakage_events", "test_access_before_unlock", "evaluation_state_mutations", "source_freeze_mismatches", "config_freeze_mismatches", "certified_dependency_hash_mismatches", "artifact_hash_mismatches", "checkpoint_policy_violations", "common_random_coordinate_mismatches", "duplicate_result_rows", "unexpected_result_rows", "missing_expected_result_rows", "nonfinite_events"],
  "phase_completion_only_counts": ["missing_expected_result_rows"],
  "validation_gate": {
    "pass_status": "READY_FOR_TEST",
    "fail_status": "NO_TEST",
    "fixed_seed_cohort": [17, 29, 43],
    "minimum_qualifying_ddqn_gamma1_seeds": 2,
    "total_seeds": 3,
    "qualifying_seed_ids_persisted_in_test_permit": true,
    "test_may_not_replace_with_nonqualifying_seed": true,
    "per_qualifying_seed": {
      "graph_condition_cells": 4,
      "root_action_definition": "single_initial_semantic_candidate_id_equal_to_forecast_rule_request_id",
      "nonrequest_root_action": "performance_mismatch",
      "missing_or_multiple_root_action": "integrity_failure",
      "first_request_matches_forecast_rule": "all",
      "paired_episode_outcomes_match_forecast_rule": "all_200",
      "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]
    },
    "tabular_participates": false
  },
  "result_classification": {
    "priority": ["INVALID_RUN", "NO_TEST", "RULE_PARITY_SIGNAL", "CREDIT_SIGNAL_BELOW_RULE", "NO_CREDIT_SIGNAL"],
    "eligible_seed_source": "validation_gate.qualifying_seed_ids",
    "rule_parity_signal": {"minimum_qualifying_ddqn_gamma1_seeds": 2, "test_graph_condition_cells_per_seed": 6, "first_request_matches_forecast_rule": "all", "paired_episode_outcomes_match_forecast_rule": "all_300", "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"], "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]},
    "credit_signal_below_rule": {"requires_rule_parity_signal_absent": true, "minimum_qualifying_ddqn_gamma1_seeds": 2, "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"], "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]}
  },
  "external_services": {"openai_api_required": false, "network_required_for_scientific_loop": false, "local_scope": "unit_tests_and_non_evidence_smoke", "formal_training_target": "user_managed_server"}
}

```

## New file: docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json
```
{
  "schema_version": "family3_v2_learner_source_baseline_v0",
  "created_at_utc": "2026-09-21T00:56:07Z",
  "certified_suite": {"version": "increment8_family3_v2_forecast_scope_reservation_v0", "suite_hash": "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c"},
  "approved_specs": [
    {"relative_path":"docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md","sha256":"f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9","byte_size":38149},
    {"relative_path":"docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md","sha256":"0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20","byte_size":35818}
  ],
  "certified_preflight": {
    "result_root": "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight",
    "final_verdict": "CERTIFIED_PASS",
    "artifacts": [
      {"relative_path":"run_config.json","sha256":"b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb","byte_size":3090},
      {"relative_path":"final_verdict.json","sha256":"ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552","byte_size":329},
      {"relative_path":"frozen_v0_v1_baseline.json","sha256":"d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055","byte_size":15208},
      {"relative_path":"suite_manifest.json","sha256":"9d2317cde93e4d2b48bd71df5787afed238e492c06d8bf7f09475ce107e6bcc2","byte_size":11976}
    ],
    "certificate_paths": ["graphs/i8_f3v2_v0/exact_certificate.json","graphs/i8_f3v2_v1/exact_certificate.json","graphs/i8_f3v2_v2/exact_certificate.json","graphs/i8_f3v2_v3/exact_certificate.json","graphs/i8_f3v2_v4/exact_certificate.json","graphs/i8_f3v2_v5/exact_certificate.json","graphs/i8_f3v2_v6/exact_certificate.json","graphs/i8_f3v2_v7/exact_certificate.json","graphs/i8_f3v2_v8/exact_certificate.json","graphs/i8_f3v2_v9/exact_certificate.json","counterfactuals/i8_f3v2_v0/exact_certificate.json","counterfactuals/i8_f3v2_v1/exact_certificate.json","counterfactuals/i8_f3v2_v2/exact_certificate.json","counterfactuals/i8_f3v2_v3/exact_certificate.json","counterfactuals/i8_f3v2_v4/exact_certificate.json","counterfactuals/i8_f3v2_v5/exact_certificate.json","counterfactuals/i8_f3v2_v6/exact_certificate.json","counterfactuals/i8_f3v2_v7/exact_certificate.json","counterfactuals/i8_f3v2_v8/exact_certificate.json","counterfactuals/i8_f3v2_v9/exact_certificate.json"],
    "cache_paths": ["graphs/i8_f3v2_v0/value_cache.sqlite3","graphs/i8_f3v2_v1/value_cache.sqlite3","graphs/i8_f3v2_v2/value_cache.sqlite3","graphs/i8_f3v2_v3/value_cache.sqlite3","graphs/i8_f3v2_v4/value_cache.sqlite3","graphs/i8_f3v2_v5/value_cache.sqlite3","graphs/i8_f3v2_v6/value_cache.sqlite3","graphs/i8_f3v2_v7/value_cache.sqlite3","graphs/i8_f3v2_v8/value_cache.sqlite3","graphs/i8_f3v2_v9/value_cache.sqlite3","counterfactuals/i8_f3v2_v0/value_cache.sqlite3","counterfactuals/i8_f3v2_v1/value_cache.sqlite3","counterfactuals/i8_f3v2_v2/value_cache.sqlite3","counterfactuals/i8_f3v2_v3/value_cache.sqlite3","counterfactuals/i8_f3v2_v4/value_cache.sqlite3","counterfactuals/i8_f3v2_v5/value_cache.sqlite3","counterfactuals/i8_f3v2_v6/value_cache.sqlite3","counterfactuals/i8_f3v2_v7/value_cache.sqlite3","counterfactuals/i8_f3v2_v8/value_cache.sqlite3","counterfactuals/i8_f3v2_v9/value_cache.sqlite3"]
  },
  "certified_source_files": [
    {"relative_path":"src/pa_rl/authorization.py","sha256":"8d3d060421e2bff320ceb304095f34ac28110a23f0e33bebc66e833189900fd9","byte_size":32604},
    {"relative_path":"src/pa_rl/config.py","sha256":"1dead76ebaaba8230a3c51ef8b79c981cc7467488807d59c44da0a82c52dbb3e","byte_size":845},
    {"relative_path":"src/pa_rl/contracts.py","sha256":"a01b1b5ced492c450e3e0eb3542d1855a0918bf8f0770816399e3c92320d6ee3","byte_size":10282},
    {"relative_path":"src/pa_rl/effects.py","sha256":"6c81c05d99b0cb084e53a81f20c3d8b08b9c4d5d50cfed4bb84d6688c75cdf94","byte_size":10503},
    {"relative_path":"src/pa_rl/execution.py","sha256":"e2dc444b75ff85aee0436289d94b5bdc2c8fe8f28e19fd7435b1081b126079e6","byte_size":22176},
    {"relative_path":"src/pa_rl/family3_v2_artifacts.py","sha256":"47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d","byte_size":43038},
    {"relative_path":"src/pa_rl/family3_v2_audit.py","sha256":"92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921","byte_size":64280},
    {"relative_path":"src/pa_rl/family3_v2_authority.py","sha256":"0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d","byte_size":6234},
    {"relative_path":"src/pa_rl/family3_v2_contracts.py","sha256":"c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb","byte_size":4376},
    {"relative_path":"src/pa_rl/family3_v2_environment.py","sha256":"20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8","byte_size":15947},
    {"relative_path":"src/pa_rl/family3_v2_exact_reference.py","sha256":"7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575","byte_size":12684},
    {"relative_path":"src/pa_rl/family3_v2_exact_solver.py","sha256":"b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0","byte_size":37078},
    {"relative_path":"src/pa_rl/family3_v2_model.py","sha256":"f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c","byte_size":23904},
    {"relative_path":"src/pa_rl/family3_v2_outcome.py","sha256":"b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6","byte_size":5949},
    {"relative_path":"src/pa_rl/family3_v2_policy.py","sha256":"2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6","byte_size":10368},
    {"relative_path":"src/pa_rl/family3_v2_preflight.py","sha256":"17439cbdedb1846af71bb032b0e4a72f7d1dea1e38d3b3257c0cf6948f4abbbe","byte_size":63021},
    {"relative_path":"src/pa_rl/family3_v2_rng.py","sha256":"bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530","byte_size":4837},
    {"relative_path":"src/pa_rl/family3_v2_suite.py","sha256":"b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54","byte_size":16679},
    {"relative_path":"src/pa_rl/scenarios.py","sha256":"fc76020e39fb24fbb6da89d380da62f3fd1dbcca3d4473988b1f1c0bc2f352c6","byte_size":11712},
    {"relative_path":"src/pa_rl/scope_matching.py","sha256":"cbdff3449287927ad6a9739e14db6dcbeee3eb5444c97f15bb6192f0d354972c","byte_size":3339}
  ],
  "additional_learner_dependencies": [{"relative_path":"src/pa_rl/ddqn.py","sha256":"8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1","byte_size":18033},{"relative_path":"src/pa_rl/baselines.py","sha256":"6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69","byte_size":4350}],
  "pilot_config": {"relative_path":"configs/evaluation/family3_v2_learner_pilot_v0.json","sha256":"7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2","byte_size":8377}
}

```

## New file: src/pa_rl/family3_v2_pilot_criteria.py
```
"""Strict frozen configuration and certified-dependency boundary for the v2 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_CONFIG_CANONICAL_SHA256 = "27ecd5b5614c1542a971265b8f3ca657a82c434cdcd3fd5e17df9a1c0c07596d"
_TOP_LEVEL = (
    "schema_version", "experiment_id", "certified_environment", "split", "methods",
    "training", "hyperparameters", "evaluation", "hard_zero_counts",
    "phase_completion_only_counts", "validation_gate", "result_classification",
    "external_services",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig:
    schema_version: str
    experiment_id: str
    certified_environment: Mapping[str, object]
    split: Mapping[str, object]
    methods: tuple[Mapping[str, object], ...]
    training: Mapping[str, object]
    hyperparameters: Mapping[str, object]
    evaluation: Mapping[str, object]
    hard_zero_counts: tuple[str, ...]
    phase_completion_only_counts: tuple[str, ...]
    validation_gate: Mapping[str, object]
    result_classification: Mapping[str, object]
    external_services: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CertifiedDependencyVerification:
    passed: bool
    mismatches: tuple[str, ...]
    suite_hash: str
    approved_spec_hashes: tuple[str, ...]


def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("pilot config must be readable JSON") from error
    if not isinstance(raw, dict) or tuple(raw) != _TOP_LEVEL:
        raise ValueError("pilot config has missing, unknown, or noncanonical fields")
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("pilot config differs from the approved frozen contract")
    frozen = _freeze(raw)
    assert isinstance(frozen, Mapping)
    return Family3V2PilotConfig(
        schema_version=frozen["schema_version"], experiment_id=frozen["experiment_id"],
        certified_environment=frozen["certified_environment"], split=frozen["split"],
        methods=frozen["methods"], training=frozen["training"],
        hyperparameters=frozen["hyperparameters"], evaluation=frozen["evaluation"],
        hard_zero_counts=frozen["hard_zero_counts"],
        phase_completion_only_counts=frozen["phase_completion_only_counts"],
        validation_gate=frozen["validation_gate"], result_classification=frozen["result_classification"],
        external_services=frozen["external_services"],
    )


def verify_certified_dependency_baseline(baseline_path: str | Path) -> CertifiedDependencyVerification:
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dependency baseline must be readable JSON") from error
    if not isinstance(baseline, dict) or baseline.get("schema_version") != "family3_v2_learner_source_baseline_v0":
        raise ValueError("dependency baseline schema is invalid")
    root = Path(__file__).resolve().parents[2]
    mismatches: list[str] = []

    def verify(entries: object, base: Path = root) -> None:
        if not isinstance(entries, list):
            raise ValueError("baseline file list is invalid")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("baseline entry is invalid")
            relative, expected_hash, expected_size = entry.get("relative_path"), entry.get("sha256"), entry.get("byte_size")
            if type(relative) is not str or type(expected_hash) is not str or type(expected_size) is not int:
                raise ValueError("baseline entry types are invalid")
            candidate = base / relative
            if not candidate.is_file() or candidate.stat().st_size != expected_size or _sha256(candidate) != expected_hash:
                mismatches.append(relative)

    verify(baseline.get("approved_specs"))
    verify(baseline.get("certified_source_files"))
    verify(baseline.get("additional_learner_dependencies"))
    verify([baseline.get("pilot_config")])
    preflight = baseline.get("certified_preflight")
    if not isinstance(preflight, dict) or preflight.get("final_verdict") != "CERTIFIED_PASS":
        raise ValueError("certified preflight baseline is invalid")
    result_root = root / preflight.get("result_root", "")
    if not result_root.is_dir():
        mismatches.append("certified_preflight.result_root")
    else:
        verify(preflight.get("artifacts"), result_root)
        for key in ("certificate_paths", "cache_paths"):
            paths = preflight.get(key)
            if not isinstance(paths, list) or len(paths) != 20 or any(type(item) is not str for item in paths):
                raise ValueError("certified preflight path inventory is invalid")
            mismatches.extend(item for item in paths if not (result_root / item).is_file())
    suite = baseline.get("certified_suite")
    if not isinstance(suite, dict) or suite.get("suite_hash") != "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c":
        mismatches.append("certified_suite")
    hashes = tuple(entry["sha256"] for entry in baseline["approved_specs"])
    return CertifiedDependencyVerification(not mismatches, tuple(mismatches), str(suite.get("suite_hash", "")), hashes)

```

## New file: tests/test_family3_v2_learner_pilot.py
```
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pa_rl.family3_v2_pilot_criteria import (
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
            tampered_verification = verify_certified_dependency_baseline(tampered_path)
            self.assertFalse(tampered_verification.passed)
            self.assertIn("src/pa_rl/ddqn.py", tampered_verification.mismatches)


if __name__ == "__main__":
    unittest.main()

```

## Existing checkpoint diff against repository HEAD (review only the Task 1 learner-pilot boundary; earlier user-owned log changes are context)
```diff
warning: in the working copy of 'rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md', LF will be replaced by CRLF the next time Git touches it
diff --git a/rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md b/rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md
index ed5f20b..5dd0a56 100644
--- a/rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md
+++ b/rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md
@@ -8,13 +8,16 @@ network interruption or context reset.
 
 ## Current checkpoint
 
-- Updated: 2026-08-31 (Asia/Shanghai)
-- Active phase: **Family-3 v2 Task 7 COMPLETE; sole exact twelve-gate preflight is `CERTIFIED_PASS`**
-- Increment 8 state: **v0/v1 baseline immutable with zero drift; all 10 Family-3 v2 graphs certify exact `V*=4/5` and request Q-gap `3/5`; no learner/DDQN experiment exists in this milestone**
-- Experiment state: **Tasks 8C–8E are focused GREEN; Task 8F is `INVALID_RUN_BLOCKED`; no smoke, training, validation, official test, or policy result exists**
+- Updated: 2026-09-20 (America/Toronto)
+- Active phase: **Family-3 v2 exact-preflight artifact remains frozen `CERTIFIED_PASS`; Learner/Baseline Pilot Task 1 dependency/config boundary is complete; Task 1 review is the next authorized boundary**
+- Increment 8 state: **all 10 Family-3 v2 graphs remain certified at exact `V*=4/5` with request Q-gap `3/5`; the certified environment/suite/policy/solver artifacts remain immutable for the learner study**
+- Experiment state: **Task 1 added only the frozen config, dependency baseline, strict criteria loader/verifier, and focused contract test; no adapter, runner, smoke, training, validation, official test, server job, or OpenAI API call has run**
 - Last approved completed experiment: **Increment 7 Task 5 — Run integrity PASS / Result interpretation APPROVED; PARITY; prefer Rule; no rerun/tuning or Deep-RL advantage claim**
-- Current design worker: none; Task 7 is complete and no process is in flight
-- Current read-only reviewers/calibrators: fix round 3 independently closed C1/I4 with Spec PASS / Quality PASS / `READY_FOR_ADJACENT_AND_COMPILE`; the subsequent postflight artifact audit passed
+- Current design worker: none; bilingual learner-pilot specs and the implementation plan are complete, and no learner or training process is in flight
+- Current read-only reviewers/calibrators: learner-pilot scientific closeout `APPROVE`; bilingual contract audit `PASS`; final implementation-plan audit `APPROVE`; normative JSON is byte-for-byte identical and parseable in both specs
+- Learner-pilot English approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md` (SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`, 38,149 bytes)
+- Learner-pilot Chinese approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md` (SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`, 35,818 bytes)
+- Learner-pilot implementation plan: `docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md` (SHA-256 `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`, 30,311 bytes)
 - Family-3 v2 English spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` (SHA-256 `1C2F173A33EE438CE15ED910EF1637536B535495C95D73F340B679291C00656F`)
 - Family-3 v2 Chinese spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design_zh.md` (SHA-256 `82DDA83C604BE7C46276331BF4F9B65D974C167E58635407C943F8285757CEEF`)
 - Family-3 v2 implementation plan: `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md` (SHA-256 `036B9690A06267099C62F78B98C973A9B283037BAB449AF074CB6A878A049658`)
@@ -23,7 +26,7 @@ network interruption or context reset.
 - Final design verification: three independent read-only reviews PASS; both files have 14 main sections/29 total headings, identical parseable criteria JSON, no TODO/TBD/FIXME/placeholder, and exact agreement on split/method/seed/budget/row/cardinality/state-machine contracts.
 - Phase A plan: `docs/superpowers/plans/2026-08-26-increment8-phase-a-preflight-plan.md`.
 - Phase A notes/report: `docs/superpowers/notes/2026-08-26-increment8-phase-a-implementation-notes.md` and `docs/implementation_reports/task-8-phase-a-report.md`.
-- Interruption boundary: **STABLE / NO PROCESS IN FLIGHT / TASK 7 COMPLETE.** Fix round 3 was independently approved. The complete v2 suite passed 110/110, the frozen legacy adjacent suite passed 68/68, and all 13 v2 modules compiled with exit 0. The sole real command completed all 12 Gates for 10 graphs with exit 0 and durable `CERTIFIED_PASS`; every initial value is `4/5` and every request Q-gap is `3/5`. Postflight audit found 72 files, 20 certificates, 20 SQLite caches, `quick_check=ok` for every cache, 314 total nonterminal rows, 29.43 MiB peak RSS, no v0/v1 drift, and no escaped artifact. The audit helper's first table-name assumption was corrected before the successful read-only audit; this was not a product/artifact failure. No learner, training, validation, official policy test, or DDQN/baseline comparison ran.
+- Interruption boundary: **STABLE / WRITTEN SPECS APPROVED AND FROZEN / IMPLEMENTATION PLAN COMPLETE AND INDEPENDENTLY APPROVED / USER EXECUTION APPROVAL PENDING / NO PROCESS IN FLIGHT.** The exact twelve-gate artifact remains unchanged. The learner study freezes the literal 5/2/3 split, an external 43/7/7 adapter, seven public-only methods, matched `gamma=0/1`, seeds 17/29/43, 12,000 transitions per learner/seed, validation-sealed test-once, durable recovery, and exact-zero safety/integrity. No learner implementation or scientific run exists yet.
 - Task 4 fix round 1 boundary: **STABLE / REVIEW PENDING.** Regression RED ran 19 methods in 0.076s and failed exactly I1/I2/M1 (`failures=3, errors=2`). Affected focused GREEN passed 19 methods in 0.071s; the single authorized Tasks 2–4 combined run passed 24 methods in 0.081s. Caller-visible binding evidence contains no raw authorization handle, all anomaly successors use public model-owned `transition_integrity_failure`, and singleton first-effect closure records no branch residue. SHA-256: model `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c`; model test `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1`; authority `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d`; policy unchanged `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6`; environment `764ec0132b09d2fcdcbf6339f2d6b8013e7e06ded05849f4611a2f2d532f9663`; authority/environment test `63ce6fd58a6e55b93c4293664f55ec2c73f1bfddb9ca25cc54d18a5f3dd38eeb`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is independent Task 4 fix-round re-review before Task 5.
 - Task 5 boundary: **STABLE / FOCUSED GREEN.** The exact missing-audit RED was `ModuleNotFoundError: No module named 'pa_rl.family3_v2_audit'` (`Ran 1 test in 0.000s`, exit 1). Final focused GREEN passed 7 methods in 27.802s. Reports passed with: Markov 20 analyses/314 occurrences/314 public groups/314 encoded groups/2,198 rows/1,256 valid actions/1,296 transitions; real-environment conformance 20 analyses/314 states/1,256 actions/1,416 replays including exact residues `{0,1,2,3,4}` and 200 first-effect residue replays; firewall 480 manifests/4,800 row checks; witnesses 40 cells; binding/no-repair 20 bindings/2,058 catalog rows/6 action types/882 no-repair checks/4 nonemitted guards/882 forced-invalid zero-delta checks. Audit/test SHA-256 and sizes: `36f590a1804369f05429142479a6d51fa0d9f50a9ffbdc0ba6bb00675ed6cb2c` / 44,665 bytes and `a848b77c80f74da487374ef3c40fe191140ceebc520cc24746617cca3c82d77f` / 11,815 bytes. Frozen Task 2–4 hashes match the Task 5 base manifest. Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; exact next action is **Implement Task 6 capped exact solver, independent reference, and artifact store**. No broad/combined tests, DP, solver, runner, training, tuning, or rebaseline ran.
 - Task 5 fix round 1/5 boundary: **STABLE / FOCUSED GREEN / RE-REVIEW REQUIRED.** Affected regression RED ran 18 methods in 31.029s with the expected six missing-evidence/API errors. The single authorized affected GREEN passed 18 methods in 71.949s. Exact safety evidence now covers 294 no-repair states, 882 closed-offer rows, 294 disable guards, 20 execute guards, 314 complete nonemitted catalogs (2,198 rows), and 882 full-channel forced-invalid zero-delta replays. Task4 evidence now publishes immutable task snapshot and user-dispatch count without changing policy observation. SHA-256: environment `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8`; environment test `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092`; audit `1ba1dc3b660892410bb31bec9af3cb1a0d145f479851ffb58ee954ec049b98d5`; audit test `2ed2837d0e081947643e4def4b7893d431facaa5a631a23ec0f6b19b2fe708d0`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 6 is blocked. Exact next action is fresh independent Task 5 fix-round re-review.
@@ -83,10 +86,11 @@ network interruption or context reset.
   `docs/implementation_reports/task-7-heldout-context-report.md`; approved
   Task 5 review:
   `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-5-review.md`.
-- Exact next recommended research step: preserve this exact-preflight artifact
-  unchanged and decide whether to preregister a separate learner/baseline
-  experiment. Any DDQN, Rule, Tabular-Q, Random, generalization, or all-forty
-  comparison requires new scope and cannot be inferred from this certificate.
+- Exact next action: obtain explicit user approval of the reviewed
+  Learner/Baseline Pilot implementation plan. Only after that approval may
+  Task 1 freeze dependencies and create the formal config boundary. Do not
+  create learner source/test/config/result files or start smoke, training,
+  validation, or test before that boundary.
 
 ## Increment 7 Task 5 READY_FOR_FROZEN_RUN boundary
 
@@ -657,6 +661,10 @@ containing:
 
 ### Checkpoint history
 
+- **2026-09-20 — Learner/Baseline Pilot Task 1 boundary complete; review next.** Baseline `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`, config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`, criteria `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`, and focused test `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e` were created. The single authorized RED failed only with missing `pa_rl.family3_v2_pilot_criteria`; the identical GREEN passed one test in 0.084s. No certified source/artifact changed and no formal experiment ran. Next: Task 1 review.
+
+- **2026-09-20 — Family-3 v2 Learner/Baseline Pilot written specs formally approved; implementation plan complete and independently approved.** The exact twelve-gate artifact remains immutable. The frozen study retains the literal 5/2/3 split, adds only an external 43/7/7 adapter and separate learner runner, and compares Random-valid, forecast-ablated Rule, forecast-aware Rule, diagnostic Tabular-Q `gamma=0/1`, and Masked DDQN `gamma=0/1`. It freezes seeds 17/29/43, 12,000 transitions per learner/seed, 50 paired evaluation episodes, matched initialization/RNG derivation, validation-qualified seed cohorts, test-once recovery, and expanded exact-zero safety/integrity gates. Scientific closeout is `APPROVE`; bilingual audit is `PASS`; final plan audit is `APPROVE`. English/Chinese spec SHA-256 are `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` and `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`; plan SHA-256 is `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`. This remains documentation-only: no learner source, test, config, smoke, training, server job, result, or API call exists. Next action is explicit user approval to execute the plan, beginning with dependency freeze and config boundary.
+
 - **2026-08-31 — Family-3 v2 Task 7 exact preflight COMPLETE / `CERTIFIED_PASS`.**
   Fix round 3 passed independent readiness review; the ordered v2 110/110,
   legacy 68/68, and 13-module compile checks all passed once. The sole real

```