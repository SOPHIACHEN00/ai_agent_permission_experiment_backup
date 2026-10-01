# Family-3 v2 Learner/Baseline Pilot — Task 8

2026-09-21. Status: **LOCAL_BOUNDED_VERIFICATION_PASS**; formal training/test NOT RUN.
最小版 Task 8 本地检查完成，提供服务器交接；不声称完整崩溃矩阵通过。

## 本轮范围 / scope

按最小实现偏好，补关键真实存储验收与服务器交接，不改变科研合同。
Fixed seeds 17/29/43; 12 final checkpoints; 144000 training transitions;
4200 validation rows; 6300 test rows only after a READY_FOR_TEST permit.
Same-seed checkpoints, original/counterfactual pairing, zero-hard-failure
requirements and frozen scientific categories are unchanged. No OpenAI API.

## Changes

- Explicit test-once --resume can complete a partially published or already
  sealed test classification without opening test again or running episodes.
  The sealed result is recomputed from verified rows and compared byte-for-byte
  with all four artifacts and the classification's ledger bindings.
- Declared NumPy in pyproject: tensor fingerprint/checkpoint code already uses it.
- Added a compact real-store fixture. Its interior rows are pre-materialized
  synthetic hash chains (all 4200/6300 coordinates); first/last rows, missing-row
  repair, checkpoint/permit/unlock/classification/finalization use production APIs.
  It is not an exhaustive fsync/power-loss test of all 10500 individual appends.

## Verification evidence

- Deliberate recovery RED: one expected failure in 17.525 s, exit 1 at the known
  TEST_CLASSIFIED guard. Fixture retained at
  `C:/Users/Sophi/AppData/Local/Temp/task8_store_synthetic_fktz6ijj`.
- Focused GREEN: **12/12, 45.135 s, exit 0**. Learning adapter/RNG; config/baseline;
  frozen classifiers; minimal checkpoint codec/ledger; five fast Task 7 checks;
  synthetic gate orchestration; real-store permit/recovery. Recovery also covers
  tampered permit/result rejection, orphan OPEN retry, one missing test coordinate,
  partial result publication, no repeated OPEN/classification and read-only final.
  Passing synthetic fixture retained at
  `C:/Users/Sophi/AppData/Local/Temp/task8_store_synthetic_u4c83gh8`.
- Minimal adjacent regression: **27/27, 0.311 s, exit 0**, exactly the approved
  three environment/model/RNG modules plus two Tabular/DDQN regression methods.
- Independent final scoped review: no Critical/Important finding in the small
  recovery/dependency change; approved proceeding to the one fixed smoke.
- All four additive modules, six focused test files and package verifier compile,
  exit 0. Read-only check-freeze returned FREEZE_VERIFIED without result creation.
  Frozen source manifest SHA-256:
  `bcb6e02c9c276f84809b5c529b50c769e57bfd7853875d08c5a1454a1c9c5189`.
- Named smoke executed **once**, **62.969 s, exit 0**, after verifying its root
  absent: `python -m pa_rl.family3_v2_learner_pilot non-evidence-smoke`.
  Final status NON_EVIDENCE_SMOKE_COMPLETE, scientific classification null.
  Four checkpoints, 1280 transitions, 28 validation rows across seven methods;
  both DDQN arms performed 17 optimizer updates. Read-only postflight: hard-count
  sum 0, all four evaluation fingerprints stable, no test directory or permit.
  Formal result root remains absent. No process remains running.

The named smoke is preserved at
`results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke/`.
It is non-evidence and must not be used to report or tune DDQN performance.

## Reproducible check commands

Set PYTHONPATH=src. Focused command (single GREEN invocation):

```text
python -m unittest -v -f tests.test_family3_v2_learning tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_minimal_checkpoint_roundtrip_and_ledger_guards tests.test_family3_v2_evaluation_minimal.Family3V2MinimalEvaluationTests.test_cli_rejects_overrides_and_routes_explicit_test_resume tests.test_family3_v2_evaluation_minimal.Family3V2MinimalEvaluationTests.test_interrupted_mutated_learner_terminalizes_instead_of_resuming tests.test_family3_v2_evaluation_minimal.Family3V2MinimalEvaluationTests.test_mutated_evaluation_learner_terminalizes tests.test_family3_v2_evaluation_minimal.Family3V2MinimalEvaluationTests.test_real_smoke_evaluation_resumes_without_learning_or_duplicates tests.test_family3_v2_evaluation_minimal.Family3V2MinimalEvaluationTests.test_test_split_requires_verified_start_before_environment_reset tests.test_family3_v2_gate_orchestration_minimal tests.test_family3_v2_readiness_minimal
python -m unittest -v -f tests.test_family3_v2_suite_rng tests.test_family3_v2_model_outcome tests.test_family3_v2_authority_environment tests.test_g2_rough.TabularQUpdateTests.test_one_q_update_is_hand_calculable tests.test_increment5_rough.Increment5RoughTests.test_public_encoding_candidate_scoring_and_masked_target
python -m pa_rl.family3_v2_learner_pilot check-freeze
```

Do not rerun the named local smoke: its completed immutable root now exists.

## Deliberate verification limits

The very large legacy store test, every possible power-loss boundary and full
26-count runner fault matrix are not claimed as passed. The bounded real-store
fixture replaces thousands of repetitive durable appends in this local check,
not scientific sample sizes or runtime persistence semantics. The Task 7 durable
smoke unit is not rerun here: Task 8 instead uses one named smoke after review.
No old 110-test exact suite, exact DP, twelve-gate preflight or formal experiment
is rerun. A final-verdict file lacking its final state event still stops for
manual inspection; this patch does not promise recovery of every crash window.

Task 8 plan examples with --config/--baseline/--output are stale against the
approved fixed CLI. Use commands in the server handoff; frozen documents remain
unchanged. No Git commit, branch rewrite or automatic server launch was done.

## Runtime and portability

Locally checked: Python 3.12.3; Torch 2.11.0+cpu; NumPy 2.0.0; Windows 11; CPU.
Server run uses CPU too, not GPU training. Preserve project layout and bytes.
New Linux runs create their own runtime-bound roots. Never resume a Windows
pilot/smoke root under Linux or copy it into the server's fixed output paths.
Certified preflight inputs are immutable read-only dependencies, not policy
inputs or permission to rerun the solver.

The manifest distinguishes transfer files from local smoke audit files. Check
its hashes on the server before installing/importing project dependencies.
The accompanying `family3-v2-server-package.zip` contains transfer files plus
`family3-v2-server-package-manifest.json`, excluding local learner/smoke roots.
`family3-v2-server-handoff.md` gives the fixed commands and stop conditions.
The manifest records SHA-256 and byte sizes for source, tests, config/spec/
baseline, certified dependencies and every local smoke artifact. Zip/manifest
hashes and final package-verifier output are recorded in the Task 8 ledger and
the user's existing progress log (outside the package to avoid circular hashes).
