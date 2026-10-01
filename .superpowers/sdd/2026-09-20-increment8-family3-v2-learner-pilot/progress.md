# SDD ledger — plan: rl_personal_assistant/docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md

Plan SHA-256: `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`
Approved specs: English `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`; Chinese `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`
Execution approval: 2026-09-20

## Current boundary — 2026-09-21 bounded Task 8

**LOCAL_BOUNDED_VERIFICATION_PASS.** Core local checks and minimal server handoff
complete, not exhaustive full-contract acceptance. Verified classified/partial
test-result recovery without reopening/reevaluating test; declared NumPy.
Recovery RED: expected one failure, 17.525 s. Focused GREEN: 12/12, 45.135 s;
minimal adjacent: 27/27, 0.311 s. Compile/freeze exit 0. Independent narrow review
found no Critical/Important issue. Exact commands are in the implementation report.

The named smoke ran once: 62.969 s, exit 0, NON_EVIDENCE_SMOKE_COMPLETE. Four
checkpoints, 1280 transitions, 28 validation rows, DDQN updates 17/17, hard-count
sum 0, stable evaluation fingerprints, no test/permit; formal root absent.
Retain the named smoke, do not rerun it. No process remains running.

Server package: docs/implementation_reports/family3-v2-server-package.zip,
386928 bytes, 100 entries. Manifest binds 99 transfer files + 42 local-smoke audit
files. Local smoke is excluded from archive. PACKAGE_HASHES_PASS (99/99) and
ARCHIVE_HASHES_PASS (100/100). Zip SHA-256 d7064176d3f2b43b2b8917e486755d9dcf80998698251662d78e801851c8cb1f;
manifest SHA-256 b81ec42be8a6ba24d09528828f1ee6fca5ff13aab74d23d1cbc0e76269375828.

Task 8 Ruling: use the bounded real-store fixture instead of the huge legacy
store test. Interior synthetic rows are batched but full 4200/6300 coordinates,
frozen criteria and real gate/permit/resume/finalization remain. Cost: exhaustive
per-row crash durability and the full runner negative matrix remain unclaimed.
Task 8 Ruling: retain fixed CLI, not stale Task 8 --config/--output examples;
keep frozen plan/spec unchanged. Cost: users must use the updated handoff commands.
Task 8 Ruling: copy only input/project files to the server, not runtime-bound
Windows learner/smoke roots. NumPy declared because real checkpoint hashing needs it.

Report: docs/implementation_reports/increment8-family3-v2-learner-pilot.md.
Handoff: docs/implementation_reports/family3-v2-server-handoff.md.
Next: user-managed server precheck, then fixed train-validate if the bounded
verification limits are accepted. No formal training/test or OpenAI API run here.
Restart record: task8/task_plan.md. Existing final-verdict-before-final-state
publication windows still require manual inspection; no exhaustive recovery claim.

## Previous boundary — 2026-09-21 minimal Task 7

**MINIMAL_EVALUATION_RUNNER_VERIFIED / FULL_ACCEPTANCE_PENDING.** Implemented
public-policy evaluation, validation sealing, explicit test-once, missing-row
resume, immutable-learner fingerprints and the fixed CLI/read-only inspect.
Final scoped command with PYTHONPATH=src:
`python -m unittest -v -f tests.test_family3_v2_evaluation_minimal tests.test_family3_v2_gate_orchestration_minimal`
passed **7/7 in 66.793 s, exit 0**. Final py_compile exit 0.

One temporary durable smoke trained four seed-17 arms x 320 transitions and
recorded 28 validation rows; no test/permit/scientific classification. The
terminal rerun and inspect left bytes/mtimes unchanged. Both named experiment
roots remain absent, all temporary smoke artifacts were cleaned, no process runs.
Earlier fast checks passed 4/4 (6.636 s) and synthetic classifier orchestration
1/1 (0.536 s). These are software checks, never DDQN performance evidence.

Scoped independent review found one Important interruption fingerprint gap.
Its regression produced one expected controlled failure (1.964 s), then passed
with the fix in the final run. No additional production fix was needed.

Task 7 Ruling: following the user's minimal-work preference, keep new focused
tests separate from the expensive legacy full-store test, use a temporary
fixed-budget smoke, and do not reopen spec/approval/worktree/commit workflows.
Cost: the original full Task 7 acceptance matrix remains unclaimed.
Task 7 Ruling: smoke evaluates seed 17 only (28 rows), using phase_complete=False
and no scientific category; formal evaluation retains all seeds and 4200/6300
rows, independent of the qualifying cohort. Frozen criteria were not changed.

Next is Task 8 readiness/server handoff: close full-store positive test-once and
relevant crash gaps before formal training. TEST_CLASSIFIED without final verdict
currently stops for manual inspection. See task-7-minimal-report.md and
task-7-minimal-continuation.md for hashes, restart boundary and remaining scope.

## Previous boundary — 2026-09-21 minimal Task 6

User-requested focused recheck (2026-09-21): **2/2 passed in 92.073s,
exit 0**. Executed once with `PYTHONPATH=src`:
`python -m unittest -v -f tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_minimal_checkpoint_roundtrip_and_ledger_guards tests.test_family3_v2_training_minimal.Family3V2MinimalTrainingTests.test_real_training_checkpoints_and_manual_restart`.
The first launch was prevented by the known sandbox-helper ACL error before
Python started; the permitted fallback ran the tests successfully. No source
or test edits were made. Checked source/test hashes match the Task 5/6 minimal
reports. This recheck covers only the two minimal paths, not full acceptance
or policy effectiveness; the pending Task 7/formal-readiness boundary is unchanged.

The user accepted the proposed minimal training runner. Task 6 now connects
the real environment to Tabular-Q/Masked DDQN, native rewards, fixed quotas,
matched RNG/initialization and Task 5 final checkpoints. It records per-attempt
progress and interruption, requires explicit restart from zero, and verifies
completed arms before skipping. New code/test are isolated from frozen sources.

One small real-environment test passed **1/1 in 38.524s**; compile exited 0.
The test completes four arms x 320 transitions with seed 17 and 17 optimizer
updates per DDQN arm, plus one discarded pre-interruption transition. Four
final checkpoints, manual restart and completed-arm immutability pass. Artifacts
were temporary; no named formal/smoke root, validation/test, server job or API.
Status: **MINIMAL_TRAINING_RUNNER_VERIFIED**. See `task-6-minimal-report.md`.

The independent scoped read-only review found no material issue in Task 5 API
integration, native reward/done handling, matched RNG/initialization, or explicit
restart/completed-arm skipping. No review test rerun or source edit followed.

Task 5 full-store acceptance and exhaustive Task 6 failure-path verification
remain open. Next implementation is the minimal Task 7 evaluation/CLI entry;
formal training/evaluation must wait for the remaining readiness checks.

## Previous boundary — 2026-09-21 minimal Task 5

Tasks 1–4 are independently complete per the historical entries below. On the
user's request to keep Task 5 minimal, the Windows symlink fixture was made
portable and one scalar optimizer serialization bug was fixed. The new minimal
checkpoint/ledger test passed 1/1 in 16.891s; two-module compile exited 0.
Status: **MINIMAL_CORE_VERIFIED / FULL_STORE_ACCEPTANCE_PENDING**.

The full test first exposed the scalar bug (12.798s, exit 1); its post-fix run
was interrupted during thousands of durable validation-row writes to respect
the small-test scope. That run is not counted as passing. Full positive
permit/test-once, complete recovery and final-verdict verification remain open.
No new review loop, Task 6 implementation, formal training/evaluation or result
root was started. Report: `task-5-minimal-report.md`; scope decision and retained
failure history: `task-5-minimal-continuation.md`.

Final source SHA-256 `025cee8f435793b667d529f189347f4e590a77ab93b7f3fb73c3adb635a4a4c9`
(181,656 bytes); shared test SHA-256
`ad08fd3971b6ee4b15fdf0fd2032e52216b971d5a41cf8f0c926e134a859491f` (93,067 bytes).

## Pre-flight rulings

- Ruling: Work in the current checkout without creating a Git worktree or commits — the approved plan explicitly says repository metadata is not an execution authority and requires SHA-256 manifests/durable boundaries instead; Git reports a normal `main` checkout but requires a per-command safe-directory override — cost if wrong: changes are isolated by file scope and hashes rather than by a removable branch/worktree.
- Ruling: Do not run a broad baseline suite before Task 1 — the approved plan makes the existing `CERTIFIED_PASS` hashes and exact-preflight artifacts the baseline and reserves only focused/minimal verification for Task 8 — cost if wrong: an unrelated pre-existing failure may be discovered only by the approved adjacent regression rather than now.
- Ruling: For each task run only the focused RED/GREEN and compile checks named by the plan; the complete approved verification set runs once in Task 8 — this resolves the generic TDD instruction to run a whole suite against the user's explicit minimal-test plan — cost if wrong: cross-module regressions may surface later at Task 8, where the plan requires stopping on the first real failure.
- Ruling: Review packages use task target-file inventories, pre/post SHA-256 manifests, implementer reports, and direct read-only file inspection rather than commit-range diffs — the approved plan forbids reliance on commits and this checkout contains earlier user-owned changes — cost if wrong: reviewers must inspect complete task files instead of a minimal Git hunk.
- Ruling: Task 1 may serialize the approved JSON config before the first RED because configuration files are the TDD exception and the approved plan explicitly orders config creation before the missing-module RED; no production Python is written before that RED — cost if wrong: the config itself lacks a witnessed failing test until the immediately following Task 1 RED.

## Pre-flight task/interface scan

| Tasks | Producer → consumer/shared surface | Finding |
|---|---|---|
| 1 | baseline/config → strict loader and verifier | Internally consistent; config is frozen before production loader RED. |
| 2 | adapter/public policies/tabular key | Internally consistent; terminal handling and policy firewall are testable before runner work. |
| 3 | RNG/DDQN wrapper extends Task 2 module/test | Ordered in one lane; no parallel implementer may edit the shared files. |
| 4 | criteria schemas/classifiers extend Task 1 criteria/test | Runs only after Task 1; synthetic rows avoid learner dependency. |
| 5 | artifact store consumes Task 4 schemas and Task 1 boundary | Ordered after Task 4; no schema duplication allowed. |
| 6 | runner consumes Tasks 2–5 | Ordered after all producers; reduced budgets remain private and non-evidence. |
| 7 | evaluation/CLI extends Task 6 runner/test | Ordered after Task 6; validation/test criteria remain those from Task 4. |
| 8 | verification/report/logs consume Tasks 1–7 | Serial; formal training and official test remain outside completion boundary. |
| 1 ↔ 4 | `family3_v2_pilot_criteria.py`, `test_family3_v2_learner_pilot.py` | Task 4 must extend, not replace, strict config behavior from Task 1. |
| 1 ↔ 5 | config/baseline hashes → `PilotBoundary` | Task 5 must bind exactly the Task 1 serialized hashes. |
| 1 ↔ 6/7 | fixed config/split → runner registries and CLI | Runner cannot accept scientific overrides or expose test before permit. |
| 1 ↔ 8 | `CONTINUATION_CHECKPOINT.md` | Task 1 records baseline; Task 8 appends completion without erasing history. |
| 2 ↔ 3 | `family3_v2_learning.py`, its focused test | Task 3 adds RNG/wrapper only after Task 2 GREEN. |
| 2/3 ↔ 6/7 | adapter, policies, RNG, wrapper → runner/evaluator | Semantic IDs are re-resolved against the current authoritative mask; evaluation uses external RNG. |
| 4 ↔ 5 | immutable row/cell/gate schemas → artifact store | Store serializes verified schemas; it must not reimplement classifiers. |
| 4/5 ↔ 6/7 | classifiers and durable state → orchestration | Runner must verify complete coordinates before performance classification. |
| 6 ↔ 7 | `family3_v2_learner_pilot.py`, runner test | Task 7 extends the Task 6 training path; no second runner is introduced. |

Pre-flight result: no unresolved contradiction with the approved specs or Global Constraints.

Task 1 base: Git HEAD `dd2efc383800831dfec7e89ba1607b529e4f6f05` (record only; no commit-range authority). Four create-targets absent. `docs/CONTINUATION_CHECKPOINT.md` SHA-256 `b738a0a2b435f9e5b8fc0c65277d4a35d28bf86c5e561ee5e4d64b02b195c436`, 64,556 bytes.
Task 1: dispatched.
Task 1 implementation: focused RED was only `ModuleNotFoundError: pa_rl.family3_v2_pilot_criteria`; focused GREEN passed 1/1 in 0.084s. Post hashes: config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`; baseline `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`; criteria `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`; test `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e`; checkpoint `45fdb03f541a58c108d9fb313f2fa8b5a9810d0c7d7d19ea7f056f9a5d5ff131`.
Task 1 review: Spec FAIL / quality Needs fixes.
Task 1 fix round 1/5 opened:
- Critical: certificate and SQLite cache entries lack hashes/sizes and verifier checks only existence, so in-place mutation passes.
- Important: verifier does not enforce the canonical baseline schema/literal allowlisted inventories and accepts unknown fields, substituted/duplicate/traversal paths, altered roots, and missing suite/spec literal checks.
- Important: continuation checkpoint retains contradictory pre-execution approval/next-action text after recording Task 1 completion.
Task 1: fix round 1/5 (1 addressed, 2 open). Focused RED failed on missing `certificate_entries`; focused GREEN passed 1/1 in 0.314s. Critical certificate/cache path-hash-size binding is addressed. Open: literal schema/inventory enforcement for `certified_source_files`, `additional_learner_dependencies`, `pilot_config`, and preflight `artifacts`; obsolete pre-execution instruction remains at current-checkpoint line 89.
Task 1 fix round 2/5 opened.
Task 1: fix round 2/5 (2 addressed, 0 open from re-review). Focused RED reproduced accepted remaining-inventory substitution; focused GREEN passed 1/1 in 0.453s. Scoped verdict PASS / APPROVE.
Task 1 controller completion check found one explicit brief item not visible in the scoped finding list: the continuation checkpoint does not yet point to the final immutable baseline hash and still labels the review as pending. Treat as fix round 3 documentation closeout, not a production-code change.
Task 1 fix round 3/5 opened.
Task 1: fix round 3/5 (1 addressed, 0 open). Documentation-only closeout now records final baseline/config/criteria/test hashes and a consistent Task 2-next restart boundary; scoped verdict PASS.
Task 1: complete (no commits by approved ruling; spec compliant and task quality approved after three fix rounds). Final hashes: config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`; baseline `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`; criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143`; test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea`; checkpoint `998a5c86db986d2b1d21554206327f770f85aee7cdf95ad0a6106994e8750537`.
Task 2 base: both create-targets absent; frozen `ddqn.py` SHA-256 `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1`; frozen `baselines.py` SHA-256 `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69`.
Task 2: dispatched.
Task 2: Ruling: the first GREEN attempt's candidate-mask-disagreement case was an invalid fixture because it set already-true row 0 to true, so it could not exercise disagreement; authorize changing only that fixture target to masked row 2 and then one valid focused GREEN — this is not a production failure — cost if wrong: a genuine adapter defect could be misclassified, so the report and independent review must inspect the exact fixture diff and retained failure output.
Task 2 implementation: missing-module RED exact; one retained invalid fixture attempt; effective focused GREEN passed 1/1 in 0.008s; compile exit 0. Source `0ffeaff112448d3f8f93f0a2f50f73de4a93ecf28f1dbf69abec5f908be73a61`; test `39f3e99503e6b64d7ddc260b7ed1252f3db3df17b3aea61ee8f4e290730dcde8`.
Task 2 review: Spec FAIL / quality Needs fixes.
Task 2 minor (deferred): tests omit isolated wrong-mask-shape and nonfinite-candidate cases although production checks them.
Task 2 minor (deferred): RandomValid uses thirty seeded samples rather than a deterministic population assertion/stub.
Task 2 fix round 1/5 opened:
- Critical: caller can synchronously forge/mutate decision mask and candidate mask-bit so they agree with each other but enable an environment-masked row; frozen dataclass does not make tensors immutable.
- Important: resolver/rules do not bind a decision to the current observation/catalog, so stale decisions are not reliably rejected.
- Important: AST firewall omits certificate surfaces and misses normal relative environment-info imports.
- Important: candidate mask feature accepts non-bit values because Boolean conversion treats 0.5/-1.0 as true.
Task 2: fix round 1/5 addressed all four scoped findings. The retained behavioral RED reproduced synchronized mask/candidate mutation; effective focused GREEN passed 1/1 in 0.025s and compileall exited 0. Independent scoped re-review returned PASS without rerunning tests. Adapter-only construction, immutable provenance snapshots/integrity checks, current-observation freshness binding, exact finite 0/1 mask-bit validation, and the expanded AST firewall are accepted.
Task 2: complete (no commits by approved ruling; spec compliant and task quality approved after one fix round). Final hashes: source `b6ac48e3eb805935ca2e1c90e326659840a4f7e59ecb9db3de491f6874fe66b2`; test `5d97c3feb48d5415447553cc5915cc2225f87236109e0d58d49c940550fb9db2`. Deferred minor test-strengthening observations remain non-blocking and unchanged.
Task 3: Ruling: `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-3-brief.md`, the approved Family-3 v2 plan Task 3, and the controller assignment are authoritative; `rl_personal_assistant/docs/implementation_briefs/task-3-brief.md` is a stale same-name brief from an earlier increment whose explicit no-DDQN scope conflicts with the approved current task, so it is recorded but ignored and left untouched — cost if wrong: provenance could point at the wrong historical brief, mitigated by exact paths, plan hash, and task report.
Task 3: dispatched.
Task 3 implementation: valid missing-interface RED; after one documented fixture-only correction, effective focused GREEN passed 1/1 in 3.041s, the complete learning module passed 2/2 in 1.856s, target compile passed, and the 69-entry frozen baseline audit matched. Post hashes before review: source `64a8e47f629fa410673f8e358583d11767910fdab088a44df430a8b4e71455b1`; test `2499bd3806af15bf624e7ce3c2295bdcfd5fff15e2aeddea5fd8cf61abdc17a1`.
Task 3 review: FINDINGS / one P1. RNG payloads, matched initialization, external evaluation RNG, zero-based replay reseeding, finite checks, generic-DDQN delegation, and the fixture correction passed inspection; however, `Family3V2MaskedDoubleDQN.select_candidate` and inherited `observe` bypass Task-2 decision-integrity validation, so a synchronized forged decision can reach selection/replay.
Task 3 fix round 1/5 opened:
- P1: require `Family3V2LearnerDecision` and `_require_integrity()` at wrapper selection and observation boundaries; validate any non-null successor before forwarding; add focused forged-decision rejection assertions and prove it never reaches replay.
Task 3: fix round 1/5 implementation complete. Behavioral RED failed because `select_candidate` accepted a synchronized forged adapter decision; the minimal wrapper-boundary fix rejects forged current and non-null successor decisions before generic delegation and proves replay/state non-mutation. Focused GREEN passed 1/1 in 1.852s, complete learning module passed 2/2 in 1.798s, target compile passed, and frozen `ddqn.py`/`baselines.py` hashes matched. Post-fix hashes: source `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd`; test `2c2d7c03076c9f08b2c9fb4154b96339933bac4f63838d67baa4e1a2f411fd74`. Awaiting scoped re-review.
Task 3 fix round 1 re-review: production P1 PASS; one P2 test-evidence gap remains. The rejection test snapshots replay/RNG/counters/loss but does not digest online network, target network, and optimizer state, so its report-level full non-mutation claim is not yet independently demonstrated.
Task 3 fix round 2/5 opened (test-only): add deterministic online/target/recursive optimizer state digests to the existing before/after rejection assertions; no production change and no new behavioral RED are expected because inspection confirms validation already occurs before delegation — cost if wrong: the implementation could mutate unobserved learner state despite rejection, so the focused GREEN must compare these exact digests.
Task 3: fix round 2/5 implementation complete (test-only). Production remained byte-identical at `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd`. The failed-observe snapshots now include deterministic online/target network state and recursive optimizer-state digests. Per the recorded evidence-strengthening ruling no redundant RED ran; focused test passed 1/1 in 1.847s and test-file compile passed. Test hash is `cd7053a3ae066f3306f68626cf237257a04056855bd8c7938611c25f7e3ad1d2`; frozen `ddqn.py`/`baselines.py` hashes remain unchanged. Awaiting scoped re-review.
Interruption checkpoint: two controller-turn abort signals occurred after Task 3 fix round 2 had fully completed and reported final hashes; no unified command or patch was in flight, so no partial source write is known. The parallel Task 4 brief drafter was interrupted and must be resumed from its draft state after Task 3 closeout.
Task 3 fix round 2 re-review: production remains accepted and byte-identical; one residual P2 test-evidence gap remains because PyTorch `state_dict()` omits module `.training` flags and parameter `.grad` tensors.
Task 3 fix round 3/5 opened (test-only): extend the deterministic module digest with named-module training flags and named-parameter requires-grad/gradient payloads; preserve the existing full state-dict, optimizer, replay, RNG, counter, and loss snapshots. No production edit or new behavioral RED is expected under the same evidence-strengthening ruling.
Task 3: fix round 3/5 implementation complete (test-only). Production remained byte-identical. The module digest now covers full state-dict payloads, all named-module training flags, and every named parameter's requires-grad plus None-or-gradient tensor payload; the existing optimizer/replay/RNG/counter/loss checks remain. Focused test passed 1/1 in 5.632s and test-file compile passed. Final test hash `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`.
Task 3 final scoped re-review: PASS. The original P1 and both evidence-only P2 gaps are closed within the explicitly bounded learner-state surface; no tests were rerun by reviewers and production is byte-identical.
Task 3: complete (no commits by approved ruling; spec compliant and independently approved after three fix rounds, of which rounds 2–3 were test-only evidence strengthening). Final hashes: source `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd`; test `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`. Formal training remains outside local completion and has not started.
Task 4: Ruling: the controller's preflight-drafting prompt accidentally stated `5 validation cells and 15 test cells`; those numbers have no authority or aggregate meaning and are discarded. The approved specs remain controlling: per evaluation seed, validation has `2 graphs x 2 conditions = 4` graph-condition cells and test has `3 graphs x 2 conditions = 6`, each with 50 episodes — cost if wrong: classification denominators would be invalid, mitigated by freezing these exact approved counts in the Task 4 brief and synthetic RED.
Task 4 preflight: READY after Task 3 closeout; zero frozen-baseline mismatches, formal/smoke roots absent, Task 1 target hashes matched, and no Task 3 file overlap. Because the plan left schema ellipses and no authoritative SDD brief existed, a reviewed Task 4 brief draft was required before implementation.
Task 4 brief draft review: FINDINGS / one blocking contract correction. The draft's three root-marker-to-`decision_count` constraints were not authorized by the specs/config/plan and could reject valid evidence; remove them and let reserved root markers alone contribute `semantic_conformance_failures`/`INVALID_RUN`. All other reviewed schema, 26-count, phase-state, 4/6-cell, 4,200/6,300-row, eligibility, precedence, serialization, and leakage requirements passed.
Task 4 brief fix round 1 opened (documentation only); no production/test edit or test run is authorized until the corrected brief passes re-review and is promoted.
Task 4 brief fix round 1: PASS. The corrected draft removed only the unapproved root-marker/decision-count inference, retained exact integer validation, and introduced no material contract drift. The reviewer could not write its PASS because of the documented Windows sandbox-lock ACL failure; the controller transcribed the exact returned verdict into `task-4-brief-review.md`.
Task 4 authoritative brief promoted at `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-4-brief.md`, 29,423 bytes, SHA-256 `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f`. The only post-review delta is the administrative status/header change from review-only draft to controller-approved implementation authority; scientific/interface content is the reviewed corrected draft.
Task 4: dispatched after Task 3 completion and brief gate closure.
Task 4 implementation: entry gate matched Task 1 hashes. Focused RED ran once and failed only on missing `ROOT_ACTION_MISSING`; focused GREEN passed 1/1 in 2.535s; unchanged Task 1 config/baseline regression passed 1/1 in 0.905s. No other test, compile, smoke, environment, learner, training, evaluation, or solver command ran. Post hashes before review: criteria `0078979da304288efd1e004a48bef1e18cc6d7e1476eea5cb6c6ada75e23a46b` (39,594 bytes); test `bab285b84d5cd8ff5d3eb4421a68efb1b0f785d59be7a01222b3076ad4eb1da7` (39,692 bytes). Frozen dependencies and Task 3 closeout hashes matched; formal/smoke roots remained absent. Awaiting independent review.
Task 4 review: FINDINGS / one P1. Classifier outputs are correct, but completed `ValidationGateResult` and `TestClassificationResult` constructors do not recompute proof/status/category coherence from their own canonical cells, so manually forged persisted claims can be accepted.
Task 4 fix round 1/5 opened:
- Add negative synthetic cases for an extra validation qualifying seed, a parity-evidence result relabeled `NO_CREDIT_SIGNAL`, and mismatched `CREDIT_SIGNAL_BELOW_RULE` proof IDs.
- Factor the existing comparison rules into shared summary-only helpers and require completed zero-hard result objects to match the helpers exactly; do not duplicate or alter scientific rules.
Task 4: fix round 1/5 implementation complete. Behavioral RED failed because forged validation qualifiers `(17,29,43)` were accepted; shared summary helpers now drive both classifier output and completed-result coherence checks. Focused GREEN passed 1/1 in 2.599s and Task 1 regression passed 1/1. Post-fix hashes: criteria `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` (40,052 bytes); test `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423` (40,150 bytes). Frozen hashes matched and both result roots remained absent. Awaiting scoped re-review.
Task 4 final scoped re-review: PASS. The original P1 is closed by shared cell-summary helpers used by both constructors and classifiers; partial/invalid states remain representable and no validation/test scientific-rule drift was found. Reviewers did not rerun tests.
Task 4: complete (no commits by approved ruling; spec compliant and independently approved after one fix round). Final hashes: criteria `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31`; test `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423`. Formal training/evaluation and both result roots remain untouched.
Task 5 preflight: READY_FOR_BRIEF only. `task-5-brief.md` was absent, Task 5 shares the pilot test file with Task 4, and implementation was held until Task 4 independently closed at the hashes above. No production/test/result-root mutation or test run occurred.
Task 5: Ruling: the Task 5 creation-time boundary must not require the future absent Task 6 runner; bind only existing approved inputs, then Task 6 must extend/reseal its runner manifest before any formal use — cost if wrong: an unreconciled staged boundary could omit runner provenance, mitigated by making reseal an explicit Task 6/formal gate.
Task 5: Ruling: persistence code may implement exact Task-4 row/result encoding plus coordinate identity/order/root-seed derivation from the frozen schema/config, but may not copy validation/test performance rules; an opened partial test with hard failure may terminalize as classifier-driven `INVALID_RUN`, while only a clean partial remains pending — cost if wrong: either durable recovery becomes impossible or an invalid partial run could remain silently open.
Task 5: Ruling: DDQN `learner_family` is the exact derived literal `masked_ddqn`; under the frozen `ddqn.py` hash the store may access `_optimizer` and `_buffer` only for exact checkpoint serialization/restoration and must fail closed on layout drift — cost if wrong: checkpoint reconstruction could silently diverge from training state.
Task 5: Ruling: a sub-warmup non-evidence smoke checkpoint may have `last_loss=None` only with exact no-optimizer-step coherence; formal final checkpoints require finite loss. Replay size/cursor must be tied to transition count, warmup, and capacity — cost if wrong: a valid short smoke becomes unrepresentable or an incoherent checkpoint is accepted.
Task 5: Ruling: unit tests may inject crashes into formal-only store transitions inside temporary synthetic roots, but runtime/formal CLI fault hooks remain unavailable. If an immutable marker exists without its trailing state event, recovery must verify its full payload/hash and append exactly the missing idempotent event; no overwrite/repair is allowed — cost if wrong: a crash window can leave an unrecoverable or ambiguously committed state.
Task 5: Ruling: hard-link and directory-fsync support are recorded capability/deployment gates rather than assumed portable guarantees; freeze every schema version, top-level hash mapping, digest formula, dtype spelling, and canonical internal active-command value — cost if wrong: artifact identity may vary across operating systems or implementations.
Task 5 brief draft: 76,656 bytes, SHA-256 `c6445aa2ccc5c9c8efa4e9d6f5e4577a6fea68533c23e4c5840b61b8e857eaec`; Task 4 final hashes were bound, and no production/test/result-root mutation or test run occurred.
Task 5 brief independent review: FINDINGS / four blocking contract defects. (B1) boundary graph IDs used suffix shorthand instead of literal `i8_f3v2_*`; (B2) weights-only DDQN `model_spec`/`hyperparameters` nested schemas were not exact; (B3) final verdict/transaction omitted test rows-manifest, paired-comparison, and hard-integrity evidence; (B4) state-ledger transition payloads lacked a normative per-operation table, preventing exact replay/transaction digests. All previously enumerated QA blockers otherwise passed recheck.
Task 5 brief fix round 1 opened (documentation only). Promotion and implementation remain blocked until B1–B4 are corrected and independently rechecked.
Task 5 brief fix round 1 implementation: B1–B4 patched. Revised draft is 92,716 bytes, SHA-256 `e0f267272933cbe5a08184c01c8185a38115967ea512396cb81a63a7a88975b4`. The transition correction explicitly avoids state-ledger self-reference and mutable whole-file hashes, uses verified chain heads/segment refs, covers row-gap and marker/event recovery, fixes two-stage final-arm/test order, allows zero-row invalid paths, and removes source-reseal events. No production/test/result-root mutation or test run occurred. Awaiting targeted re-review.
Task 5 brief fix round 1 targeted re-review: PASS. B1–B4 are closed without contradicting previously passing contract sections. The reviewer again hit the documented patch-helper ACL lock, so the controller transcribed the returned PASS into `task-5-brief-review.md` without altering substance.
Task 5 authoritative brief promoted at `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-5-brief.md`, 92,687 bytes, SHA-256 `229c82e3ddda2cafcb4408d5af667061766bc6fec697676b57ed30c6103b1584`. The only post-review edits are administrative promotion/status wording and removal of stale draft-blocker language; the reviewed scientific/persistence contract is unchanged.
Task 5: dispatched after Task 4 completion and brief gate closure.
Task 5 entry gate: PASS at 2026-09-21T04:58:13Z. The new module/report and both real result roots were absent; shared test, criteria, authoritative brief, plan/spec/config/baseline/learning/DDQN/baselines/artifacts and Task 4 brief all matched their sealed hashes. No edit preceded the gate.
Task 5: Ruling: the exact six-field `train_complete.json` schema and normative transaction table override blanket marker prose that would otherwise add command/prior-head/transaction fields and make `TRAINING_SEAL` self-referential. The transaction digest exists only in the trailing state event, while the caller command is already bound by the final-arm checkpoint manifest/event inputs — cost if wrong: recovery could omit intended marker metadata, mitigated by the reviewed exact schema, manifest binding, and non-self-referential transaction chain.
Task 5 focused RED: valid and run exactly once. The named test parsed/collected and failed only with `ModuleNotFoundError: pa_rl.family3_v2_pilot_checkpoints`; 1 test in 6.704s. No second RED ran.
Task 5 mandatory stop at the single focused GREEN: the test failed before exercising Task-5 production behavior because Windows rejected `Path.symlink_to(..., target_is_directory=True)` in the temporary capability probe with `OSError: [WinError 1314] A required privilege is not held by the client`; unittest time 2.952s, tool wall 9.5s, failure at shared-test line 1206. Per the approved brief/user instruction, no retry, compile, test weakening, or `task-5-report.md` occurred. Current source `7f7270d0e0c6f6ea1133d2f1a50d0d1400f2a824304041c2a868fa83d679235a` (181,568 bytes); shared test `66657583038c4a4d0272205fb4d38f8b5514f37b3f96826205aa9ccc2e6fcf42` (90,925 bytes). Both real result roots remain absent. Task 5 is BLOCKING pending human choice on Windows symlink capability versus a reviewed portable reparse/junction probe.
