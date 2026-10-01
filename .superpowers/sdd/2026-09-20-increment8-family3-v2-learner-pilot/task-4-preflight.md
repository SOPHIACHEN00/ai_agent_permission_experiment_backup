# Task 4 read-only preflight

## Verdict

**READY** for Task 4 brief/dispatch after the mandatory Task 3 completion and
review gate. Task 4 is **not authorized to start yet**. There is no
specification contradiction, stale production path, frozen-dependency drift,
or file-level overlap with Task 3.

No production or test file was edited and no test command was run during this
preflight.

## Authorities checked

- Approved plan:
  `rl_personal_assistant/docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md`
  — 30,311 bytes; SHA-256
  `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`.
- Task 4 and the plan's Global Constraints agree with both approved specs and
  the frozen config.
- `task-4-brief.md` is currently absent. This is not a stale-path failure: the
  controller explicitly made the brief optional for this preflight and Task 3
  review is still pending. Create/approve the brief before dispatch.
- Task 3 touches only `src/pa_rl/family3_v2_learning.py` and
  `tests/test_family3_v2_learning.py`; Task 4 touches only the two files below.
  There is no direct write overlap. The controller's stricter serial review
  gate still applies.

## Task 4 target bases

| Target | Bytes | SHA-256 |
|---|---:|---|
| `rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py` | 8,984 | `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` |
| `rl_personal_assistant/tests/test_family3_v2_learner_pilot.py` | 6,332 | `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` |

These match the approved Task 1 closeout boundary. The source currently
contains only the strict config/baseline dataclasses, loader, and verifier; the
test currently contains only
`test_config_and_certified_baseline_are_exact`. Preserve that behavior and
extend it rather than replacing it.

The following Task 4 surfaces are absent, as expected before its RED:
`HardIntegrityCounts`, `EvaluationEpisodeRow`, `EvaluationCellResult`,
`ValidationGateResult`, `TestClassificationResult`,
`evaluate_validation_gate`, `classify_test_result`, and
`test_validation_and_test_classification_contract`.

## Contract/readiness findings

- The fixed authority is coherent: seven configured method IDs, evaluation
  seeds `17/29/43`, validation graphs `v5/v6`, test graphs `v7/v8/v9`, exact
  conditions `original/forecast_counterfactual`, and 50 episodes per cell imply
  exactly 4,200 validation rows and 6,300 opened-test rows.
- The 26 `hard_zero_counts` names in the config are authoritative.
  `missing_expected_result_rows` is the sole phase-completion-only count.
  Missing/extra fields, Boolean/non-integer/negative counts, duplicate or
  unexpected coordinates, wrong method/seed/graph/condition/phase, malformed
  rows, nonfinite values, and incomplete *completed* phases must fail before
  performance calculations.
- Validation semantics agree across the plan/spec/config: qualifying
  `masked_ddqn_gamma1` seeds must be at least 2/3, match ForecastRule at all 200
  roots and paired terminal outcomes, and have pooled success strictly above
  matched `masked_ddqn_gamma0` and `forecast_ablated_rule`. Tabular rows are
  required for a complete phase but do not affect the gate.
- Test precedence is consistently `INVALID_RUN`, `NO_TEST`,
  `RULE_PARITY_SIGNAL`, `CREDIT_SIGNAL_BELOW_RULE`,
  `NO_CREDIT_SIGNAL`. Only validation-permit eligible seed IDs may contribute
  to either positive test category. Both positive categories require pooled
  success and first-request-match-count superiority; Rule parity additionally
  requires all six cells and all 300 paired outcomes to match ForecastRule.
- The plan deliberately leaves the exact fields of `EvaluationCellResult`,
  `ValidationGateResult`, and `TestClassificationResult`, plus the full
  classifier parameter lists, as ellipses. The Task 4 brief/RED must freeze a
  minimal immutable, auditable interface before GREEN; do not guess a second
  API in later Tasks 5 or 7.
- The same RED must make phase-completion handling observable so a legitimate
  partial durable ledger is not invalidated solely for missing rows, and must
  make missing/multiple root actions an integrity failure rather than silently
  coercing them into the single `root_semantic_candidate_id: str` field. This
  is an interface/test clarification, not a change to approved semantics.

## Frozen dependencies: do not edit in Task 4

1. Approved/frozen learner-pilot inputs:

   - `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md`
     — 38,149 bytes; SHA-256
     `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`.
   - `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md`
     — 35,818 bytes; SHA-256
     `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`.
   - `configs/evaluation/family3_v2_learner_pilot_v0.json` — 8,377
     bytes; SHA-256
     `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`.
   - `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`
     — 11,338 bytes; SHA-256
     `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`.

2. Additional frozen learner dependencies:

   - `src/pa_rl/ddqn.py`
   - `src/pa_rl/baselines.py`

3. Complete certified source fingerprint set:

   - `src/pa_rl/authorization.py`
   - `src/pa_rl/config.py`
   - `src/pa_rl/contracts.py`
   - `src/pa_rl/effects.py`
   - `src/pa_rl/execution.py`
   - `src/pa_rl/family3_v2_artifacts.py`
   - `src/pa_rl/family3_v2_audit.py`
   - `src/pa_rl/family3_v2_authority.py`
   - `src/pa_rl/family3_v2_contracts.py`
   - `src/pa_rl/family3_v2_environment.py`
   - `src/pa_rl/family3_v2_exact_reference.py`
   - `src/pa_rl/family3_v2_exact_solver.py`
   - `src/pa_rl/family3_v2_model.py`
   - `src/pa_rl/family3_v2_outcome.py`
   - `src/pa_rl/family3_v2_policy.py`
   - `src/pa_rl/family3_v2_preflight.py`
   - `src/pa_rl/family3_v2_rng.py`
   - `src/pa_rl/family3_v2_suite.py`
   - `src/pa_rl/scenarios.py`
   - `src/pa_rl/scope_matching.py`

4. Entire certified exact-preflight root:

   - `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/`
   - This includes frozen `run_config.json` (3,090 bytes, SHA-256
     `b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb`),
     `final_verdict.json` (329 bytes, SHA-256
     `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`),
     `frozen_v0_v1_baseline.json`, `suite_manifest.json`, all 20 exact
     certificates, and all 20 SQLite caches.

5. Task 3 lane outputs, once reviewed, are out of Task 4 scope and must not be
   edited: `src/pa_rl/family3_v2_learning.py` and
   `tests/test_family3_v2_learning.py`.

## Read-only boundary checks

- Frozen baseline hash/size mismatches: **0**.
- Certified suite hash:
  `98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
- Formal root `results/increment8_family3_v2_learner_pilot_v0`: absent.
- Smoke root
  `results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke`: absent.

## Dispatch hold

Before Task 4 starts: (1) Task 3 must receive a passing review/closeout, (2)
the Task 4 brief must be written from the approved plan plus this preflight,
and (3) the two target hashes above must be rechecked to detect intervening
edits. No other file is authorized for Task 4.
