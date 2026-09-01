# SDD ledger — plan: docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md

Started: 2026-08-27 Asia/Shanghai
Workspace: `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/`
Spec authority: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` and `_zh.md`

## Setup rulings

- Ruling: use the current dedicated project directory instead of a Git worktree — `git rev-parse` proves there is no Git repository and the required `sdd-workspace` WSL invocation is unavailable with `E_ACCESSDENIED`; the approved plan itself replaces Git isolation/commits with new-file-only scope, frozen byte hashes, and durable checkpoints — if wrong, changes lack VCS-level isolation, mitigated by the immutable 14-source/72-result baseline and exact per-task hashes.
- Ruling: replace commit-range review packages with task-scoped manifests containing changed paths, before/after hashes where available, full new-file paths, implementer reports, and checkpoint evidence — Git commits/diffs cannot exist in this workspace — if wrong, reviewers have less convenient historical context, mitigated by all production files being new and legacy files being hash-frozen.
- Ruling: do not run a broad baseline test before Task 1 — the approved plan makes the byte freeze the first experiment action and prescribes one focused RED/GREEN per implementation task, with legacy regressions in Task 7 — if wrong, a pre-existing regression may surface later, at the explicit Task 7 regression gate rather than contaminating the freeze.

## Pre-flight interface/conflict scan

| Tasks | Producer → consumer / shared surface | Finding |
|---|---|---|
| 1 ↔ 2 | Gate-0 result checkpoint → Task 2 hash/test checkpoint | Consistent; Task 2 may advance state but cannot rebaseline. |
| 1 ↔ 3 | Gate-0 result checkpoint → Task 3 checkpoint | Consistent; immutable baseline remains authoritative. |
| 1 ↔ 4 | Gate-0 result checkpoint → Task 4 checkpoint | Consistent; environment work is new-file-only. |
| 1 ↔ 5 | Gate-0 result checkpoint → Task 5 checkpoint | Consistent; audits consume but do not alter frozen legacy files. |
| 1 ↔ 6 | Frozen manifest → `verify_frozen_v0_v1_baseline` and artifact store | Consistent; Task 6 has validation-only APIs and no rebaseline path. |
| 1 ↔ 7 | Fixed output root/checkpoint → twelve-gate runner and Gate 12 | Consistent; resolved output path is fixed and Gate 12 rehashes the exact set. |
| 2 ↔ 3 | Typed contracts, suite, kernel wrapper and RNG → pure FSM/model | Consistent; all later model inputs are introduced by Task 2. |
| 2 ↔ 4 | Scope offer/RNG/contracts → user binding, policy projection and environment | Consistent; operational Scope stays authority-side and labels stay out of policy. |
| 2 ↔ 5 | Ten graphs/counterfactual wrapper → Markov/firewall/witness enumeration | Consistent; firewall copies transforms and does not call DP. |
| 2 ↔ 6 | Kernel/source/config identity → solver cache signature | Consistent; all limits and identities are immutable metadata. |
| 2 ↔ 7 | Suite manifest/RNG coupling → Gates 1, 2 and 6 | Consistent; Gate 6 uses frozen seed 17 and episode ordinal 0. |
| 3 ↔ 4 | Pure state/transitions/outcome → mediated environment | Consistent; environment must delegate semantic successor to the same pure kernel. |
| 3 ↔ 5 | Candidates/transitions/terminal mask → exhaustive audits | Consistent; terminal successor uses `next_mask=()`, nonterminal uses seven entries. |
| 3 ↔ 6 | Finite-horizon exact model → value-first/reference solvers | Consistent; rank increases and terminal-before-key are explicit. |
| 3 ↔ 7 | Model values/Q-values → Gates 3–6 | Consistent; Gate 3 conformance precedes solver entry. |
| 4 ↔ 5 | Observation/encoder/environment evidence → conformance, Markov and binding audits | Consistent; exact operational binding and label firewall are separate surfaces. |
| 4 ↔ 7 | Mediated evidence → Gates 3, 9–11 | Consistent; no environment-only semantic transition is permitted. |
| 5 ↔ 7 | Audit reports → Gates 3 and 7–11 | Consistent; report cardinalities and mismatch emptiness are frozen. |
| 6 ↔ 7 | Solver/reference/artifact store → Gate 4 onward and resume/finalization | Consistent; v0/v1 reference barrier runs before v2–v9. |
| Task 1 internal | Files/counts/checkpoint steps | Consistent; output root absence is checked before directory creation and hashes precede v2 source. |
| Task 2 internal | Literal tests ↔ contracts/suite/RNG | Consistent; complete ten-row tuple assertion and exact mod-5 rejection are specified. |
| Task 3 internal | Witness/outcome tests ↔ transition precedence | Consistent; four cells and terminal-empty-mask convention agree. |
| Task 4 internal | Binding/environment tests ↔ shared-kernel architecture | Consistent; two-phase equality and mediated side effects are explicit. |
| Task 5 internal | Negative audits ↔ exhaustive positive audits | Consistent; non-vacuity counts and mutation failures are required. |
| Task 6 internal | Solver/reference/artifact tests ↔ hard caps/resume | Consistent; terminal-free reference and fresh SQLite schema are independent. |
| Task 7 internal | Fake-gate tests ↔ fixed runner/one real preflight | Consistent; no scientific CLI override and stop-on-first-failure are explicit. |

## Task status

- Task 1: complete
- Task 2: complete
- Task 3: complete (independent review APPROVE)
- Task 4: complete
- Task 5: complete
- Task 6: complete (fix round 1 scoped review APPROVE)
- Task 7: complete (`CERTIFIED_PASS`; exact preflight only, no learner/DDQN claim)

Task 1: dispatched — base is `task-1-base.md`; no Git commit exists by ruling.

Task 1: minor (deferred): `docs/CONTINUATION_CHECKPOINT.md:26` says no result directory was created although the Gate-0 result root now exists; Task 2 also updates this checkpoint and should make the wording exact.
Task 1: complete (base manifest `D740E2F`; result hashes `D8B8FF2/AF4FBCF/DD785A3/62E9E78`; review clean)

Ruling: before Gate 1 exists, Task 2–6 checkpoint updates retain `status=BASELINE_FROZEN`, `last_completed_gate=0`, and `next_gate=1`, and add/update an `implementation_progress` mapping plus append one JSONL record; this preserves Gate authority while making implementation resume explicit — if wrong, Task 6's strict checkpoint parser must be adjusted to this recorded pre-gate schema rather than silently reinterpreting it.

Task 2: dispatched — base is `task-2-base.md`; carry Task 1 deferred checkpoint wording correction.

Task 2: review — spec FAIL / quality needs fixes; Important I1 existing matcher not reused; Important I2 Boolean/inconsistent typed values admitted.
Task 2: minor (deferred): M1 broader negative schema/rejection matrix is incomplete; final review must triage any cases not naturally covered by I1/I2 fixes.
Task 2: fix round 1/5 dispatched to original implementer; base is `task-2-fix-1-base.md`.

Task 2: fix round 1/5 (2 addressed, 0 open — I1 matcher reuse; I2 exact typed/kernel validation; hashes `5302443/6CE4F56` → `B9DEF62/4755E05`)
Task 2: complete (no-Git base manifest → fix head hashes; scoped re-review clean; one deferred Minor remains for final triage)

Task 3: dispatched — base is `task-3-base.md`; Task 2 reviewed hashes are frozen inputs and must not be modified.

Task 3: implementer concern — open/in-progress evidence returns a nonterminal result that its own result invariant rejects; correctness concern must be resolved before review. Base is `task-3-concern-base.md`.

Task 3: complete (8-method focused GREEN; exact ten-graph four-cell witnesses; hashes `944B8D1/315A13A/2B4E130`; Gate 0 unchanged; Task 4 next)

Task 3: implementer concern resolution complete (open-outcome RED reproduced; one-line terminal-only invariant fix; 9-method focused GREEN; hashes `B4AAFF4/315A13A/E934668`; no remaining concern; Gate 0 unchanged; Task 4 next)

Task 3: independently reviewed — spec PASS / quality PASS / no Critical, Important, or Minor findings; reviewer reverified the frozen 14-source/72-result baseline with zero mismatch; review is `task-3-review.md`.

Task 4: in progress — interface reconnaissance completed read-only; fresh implementer will receive the approved Task 4 boundary and existing authority/effect API mapping.

Task 4: dispatched — no-Git base is `task-4-base.md`; full brief is `task-4-brief.md`; expected-new production/test paths were absent and Task 2/3 hashes were frozen before dispatch.

Task 4: initial implementation GREEN (7 focused; 21 Tasks 2–4 combined), but independent review is spec FAIL / quality FAIL: Important I1 caller-visible binding evidence co-locates private raw ID and public ordinal; Important I2 integrity closures depend on private model `_close`; Minor M1 branch draw precedes a model-owned stochastic-applicability check. Review: `task-4-review.md`.

Task 4: fix round 1/5 dispatched to the original implementer. Cross-task ruling: I2 necessarily reopens `family3_v2_model.py` only to add a narrow public, model-owned integrity-failure transition API and its regression; this is the reviewer-required minimal resolution because the approved Task 3 API has no candidate transition representing external integrity failure. No legacy/frozen v0/v1 path or scientific parameter changes. Re-review must cover the Task 3 API delta as well as Task 4.

Task 4: fix round 1/5 complete — I1 ADDRESSED, I2 ADDRESSED, M1 ADDRESSED; fresh scoped re-review found no new Critical/Important/Minor breakage and returned APPROVE. Final focused/combined evidence: 19/19 affected GREEN, 24/24 Tasks 2–4 GREEN. Review: `task-4-fix-1-review.md`.

Task 5: in progress — read-only audit-algorithm reconnaissance completed; brief/base and fresh implementation dispatch next.

Task 5: dispatched — brief `task-5-brief.md`, no-Git base `task-5-base.md`; audit/test paths absent at base.

Task 5: implementation final focused GREEN (7 tests, 27.802 s); reports claim exact 20 analyses, 200 residue replays, 480/4,800 firewall checks, 40 witnesses, and binding/no-repair/safety coverage. One intermediate post-implementation run failed the dropped-offer-window canary and was corrected without parameter/assertion weakening; independent review must assess both the process deviation and final code. Review package: `task-5-review-package.md`.

Task 5: independent review — spec FAIL / quality FAIL; 3 Critical, 4 Important, 1 Minor. Blocking findings: C1 only 4/314 reachable no-coverage supports certified and no exhaustive real-environment valid-disable proof; C2 forced-invalid snapshot omits authority/user/semantic branch-state channels; C3 mutation hooks self-report and encoded groups reuse public successor keys. Important findings cover semantic-successor canary, exact witness theorem oracle, full firewall schema/algebra/structural oracle, and the prior stop-rule deviation. Review: `task-5-review.md`.

Task 5: fix round 1/5 dispatched to original implementer. Cross-task evidence ruling: C1/C2 require adding audit-only `task_snapshot` and `user_dispatch_count` fields to `Family3V2EnvironmentInfo` plus focused Task 4 regressions; no policy observation, semantic transition, legacy file, or scientific parameter may change. Fresh re-review must include this Task 4 evidence-only delta.

Task 5: fix round 1/5 implementation complete — regression RED `18 tests / 6 errors / 31.029s`; single affected GREEN `18 tests / 71.949s / OK`. C1–C3, I1–I3, and M1 are addressed in code/tests; I4 is preserved as process history. Exact evidence now covers 294 no-repair states, 882 closed-offer rows, 294 disable guards, 20 execute guards, 314 nonemitted catalogs/2,198 rows, and 882 forced-invalid full-channel zero-delta replays. Task 6 remains blocked pending fresh independent re-review.

Task 5: fix round 1/5 fresh re-review — DO NOT APPROVE. C3/I1/I2/I3/I4/M1 are ADDRESSED; C1 and C2 remain OPEN because production `passed` still trusts same-model catalog/successor truth. Fix round 2/5 is authorized only to add an independent literal seven-row catalog/emitted-state theorem and a complete forced-invalid stable-state key plus exact closure increments. Base is `task-5-fix-2-base.md`; Task 6 remains blocked.

Task 5: fix round 2/5 targeted implementation complete — RED `2 tests / 2 errors / 7.078s`; same-target GREEN `2 tests / 14.976s / OK`. Production pass now includes 294 independent emitted-catalog literal checks, 314 pure plus 314 real no-coverage literal checks, and 882 complete stable-key plus 882 exact forced-invalid closure checks. Environment/Task2/3/authority/policy and Task6 brief remain frozen. Task 6 remains blocked pending fresh independent re-review.

Task 5: complete — fix round 2 fresh focused re-review returned Spec PASS / Quality PASS / APPROVE; C1 and C2 ADDRESSED, accepted C3/I1/I2/I3/I4/M1 unchanged, no new findings. Baseline independently remains 14/14 source and 72/72 result files with zero additions/removals. Task 6 is now authorized under `task-6-brief.md`; Gate authority remains `BASELINE_FROZEN / 0 / 1`.

Task 6: combined RED confirmed — three focused test modules created first; the single prescribed command produced three exact missing-`family3_v2_exact_solver` import errors in 0.001s. Test hashes are frozen in `task-6-red.md`. Three disjoint production modules are now authorized for parallel implementation; no Task 2–5 edit or real artifact is permitted.

Task 6: STOPPED at the single combined GREEN attempt — 12 methods ran in 5.311s; 11 passed and one Windows `TemporaryDirectory` cleanup raised WinError 32 because `values.sqlite3` remained open. Read-only diagnosis points to the test's `sqlite3.Connection` context manager, which does not close the connection; no scientific assertion failed. Per user stop rule, no fix or retry ran. Exact evidence and hashes: `task-6-green-failure.md`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; human inspection is next.

Task 6: FOCUSED GREEN — human authorization allowed the sole test-only repair: `contextlib.closing` explicitly closes the guard-tampering SQLite connection. No production file changed. The identical prescribed command was rerun once: 12 methods / 5.260s / OK, no warning. Full closeout: `task-6-report.md`; resolution: `task-6-test-handle-resolution.md`; independent Task 6 spec+quality review is now required. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked.

Task 6: independent review — DO NOT APPROVE (Spec FAIL / Quality Needs fixes). Open: Critical C1 reparse-ancestor output-root escape; Important I1 persisted `GATE_PASSED` restart, I2 baseline placeholder rebinding, I3 incomplete SQLite schema validation, I4 mixed-graph reference child, I5 missing solver/LRU cases, I6 missing artifact negative cases; Minor M1 weak public reference-result row validation. Review: `task-6-review.md`. Fix round 1/5 base: `task-6-fix-1-base.md`; Task 7 remains blocked.

Ruling: Task 6 fix round 1 uses one fresh cross-module implementer rather than resuming one of the three original disjoint module authors — C1/I1/I2/I6, I3/I5, and I4/M1 span all three ownership surfaces, so one owner must preserve their coupled invariants and produce one grouped RED/GREEN — if wrong, fresh context may take longer, but it avoids conflicting parallel edits and still receives the full brief/review/base.

Task 6 fix round 1/5: BLOCKED at grouped RED. The exact prescribed command ran 29 methods in 15.407s and exited 1 with 13 expected behavioral failures plus one invalid fixture error. The invalid error occurred before production construction when the wrong-output test helper attempted to hash `wrong_output/run_config.json`, which did not exist (`FileNotFoundError`). Per the one-RED stop rule, production was not edited, the test fixture was not repaired, and no GREEN was run. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked. Exact next action: authorize a fresh fix round from this breakpoint, first repairing the wrong-output test setup before a newly authorized RED.

Controller continuation ruling: the fixture error was pre-constructor and not a solver/store/scientific failure, so the same round was authorized to repair only canonical run-config fixture bytes and obtain a valid RED. Replacement RED: 29 methods / 8.455s / 14 behavioral failures / zero errors. Minimal C1/I1–I6/M1 production repair then reached the single focused GREEN: 29 methods / 7.616s / OK. Final six hashes are in `task-6-report.md`; scoped review package is `task-6-fix-1-review-package.md`. All Task 2–5 hashes/bytes remain unchanged, Gate authority stays `BASELINE_FROZEN / 0 / 1`, and Task 7 remains blocked pending independent fix-round APPROVE.

Ruling: resume fix round 1 to repair only the invalid wrong-output fixture and obtain a valid grouped RED — the user authorized continuous execution until a real failure, while this `FileNotFoundError` occurs before production construction and therefore is not a solver/store/scientific failure — if wrong, this adds one extra RED run beyond the original stop wording, but preserves strict TDD by forbidding production edits until all failures are behavioral.

Task 6 fix round 1 fresh scoped review: clean — Spec Compliance PASS / Task Quality PASS / APPROVE; C1, I1–I6, and M1 are ADDRESSED, with no new Critical, Important, or Minor finding. Review: `task-6-fix-1-review.md`.

Task 6: complete — final six Task 6 hashes/bytes, all RED/invalid-fixture/valid-RED/GREEN history, baseline authority, and three-file fixed-root inventory remain recorded. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 is authorized under its frozen formal brief.

Ruling: Task 7 owns a versioned canonical `run_config.json` atomic writer — the store requires immutable hash-bound runtime bytes before construction and exposes no public writer — if wrong, resume could bind changed configuration bytes or leave a partial config artifact.

Ruling: Task 7 uses one private exact JSON projector — runner reports/certificates/evidence contain dataclasses, `Fraction`, enums, tuples, and mappings that require deterministic lossless projection — if wrong, evidence could become noncanonical, lossy, or unparsable by the store/reviewer.

Ruling: Task 7 emits a private Gate 2 algebra reporter before any solver/cache path — existing suite construction validates constraints but has no independently reviewable algebra certificate — if wrong, a solver/cache could be created before the required theorem check or a derived-input violation could lack gate evidence.

Ruling: Task 7 permits only private keyword-only dependency-injection seams and never CLI seams — fake-gate tests need deterministic order/barrier/short-circuit coverage without exposing scientific controls — if wrong, test hooks could become user-adjustable preflight parameters.

Task 7 brief/base frozen — `task-7-brief.md` and `task-7-base.md` bind the exact Gate order, CLI/path, run-config, JSON projection, Gate-2 and v0/v1 barriers, exits, stop behavior, commands, Task 2–6 hashes, and Gate-0 root inventory. Task 7 implementation authorized; no Task 7 execution has occurred.

Task 7 runner implementation: focused RED was the exact missing runner import (`1 test / 0.000s`); the single focused GREEN passed `16/16` in `0.417s`. Runner/test hashes and evidence are in `task-7-implementation-report.md`; Gate authority remained `BASELINE_FROZEN / 0 / 1` and no real artifact was created. Readiness review was required before adjacent/compile/preflight.

Task 7 readiness review: DO_NOT_RUN (Spec FAIL / Quality Needs fixes). Open Critical C1 commit/finalize persistence boundary; Important I1 dependency fingerprint closure, I2 committed Gate-4 report consumption, I3 explicit Gate-1 manifest proof, I4 real-handler focused tests; Minor M1 Gate-6 observed-value evidence. Review: `task-7-readiness-review.md`; fix base: `task-7-fix-1-base.md`.

Ruling: Task 7 fix round 1 may reopen only `family3_v2_artifacts.py` and its focused test if the runner cannot make commit/finalize exception recovery durable through the frozen store API — C1 is load-bearing for every later Gate and the existing persisted-`GATE_PASSED` rejection creates an interface conflict at transition boundaries — if wrong, Task 6's approved hash changes and must be re-reviewed, but the change stays inside the isolated v2 subsystem and all affected tests/hashes are frozen before editing.

Task 7 fix round 1/5: invalid grouped RED — `44 tests / 14.340s / 22 failures / 0 errors`; expected C1/I1–I3/M1 failures appeared, but the new Gate-3 typed witness fixture encoded the correct `20/10/10` partition while declaring `40/0/0`. No production edit or GREEN ran; fixed root remains Gate 0 with three files.

Ruling: continue the same Task 7 fix round after changing only the contradictory Gate-3 fixture counts from `40/0/0` to the already encoded `20/10/10` — the mismatch is test data that fails before judging the real Gate-3 handler, not a scientific or production failure, and the user authorized continuous execution until a real failure — if wrong, this adds a replacement RED run, but no production edit is permitted until the replacement contains only behavioral findings.

Task 7 fix round 1/5 fresh scoped re-review: DO_NOT_RUN. I1 dependency closure, I3 explicit Gate-1 proof, and M1 truthful Gate-6 evidence are ADDRESSED. C1 remains OPEN for stale post-commit actions, failed-report/recovery-persistence boundaries, and durable-CERTIFIED_PASS KeyboardInterrupt handling; I2 remains OPEN for per-graph report/evidence/result/certificate binding; I4 remains OPEN for the full real-handler negative matrix. Review: `task-7-fix-1-review.md`; round-2 base: `task-7-fix-2-base.md`.

Task 7: FOCUSED GREEN / readiness review pending — the one prescribed RED failed only on the missing `pa_rl.family3_v2_preflight` import (`Ran 1 test in 0.000s`); the one focused GREEN passed 16/16 methods in 0.417s. New runner/test hashes are `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` and `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa`. All 19 Task 2–6 hashes/bytes remain unchanged. Gate authority remains `BASELINE_FROZEN / 0 / 1`; adjacent regressions, compile, and the real preflight have not run. Review package: `task-7-implementation-review-package.md`.

Task 7 fix round 1/5: BLOCKED at invalid grouped RED. The exact prescribed command ran once: 44 methods / 14.340s / 22 failures / zero errors. C1/I1–I3/M1 behavior failures were present, but the new I4 Gate-3 fixture contradicted its own cell partition by declaring 40/0/0 instead of 20/10/10, so one failure was fixture-caused rather than a production gap. Per the stop rule no production edit, fixture repair, GREEN, adjacent regression, compile, or real preflight followed. Only the two focused tests changed; runner and artifact-store production hashes remain at base. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is fresh authorization to correct only the typed fixture counts before a newly authorized grouped RED.

Task 7 fix round 1 continuation: FOCUSED GREEN / scoped readiness re-review required. Controller authorized only the typed witness declaration correction 40/0/0→20/10/10 in the same round. Replacement RED was valid: 44 methods / 13.108s / 21 behavior failures / zero errors. Minimal C1/I1–I4/M1 repair then reached the single grouped GREEN: 44 methods / 15.173s / OK. C1 required the authorized narrow reopening of `family3_v2_artifacts.py` and its focused test; all other 17 Task 2–5 hashes remain unchanged. Final four hashes and mappings are in `task-7-fix-1-review-package.md`. Gate remains `BASELINE_FROZEN / 0 / 1`; fixed root remains three files; adjacent regressions, compile, and real preflight remain unrun. Status: `READINESS_FIX_1_GREEN_REVIEW_REQUIRED`.

Task 7 readiness fix round 2: FOCUSED GREEN / scoped re-review required. Scope was only residual C1/I2/I4; I1/I3/M1 stayed frozen. Grouped RED: 54 methods / 29.720s / 12 C1/I2 behavior failures / zero errors; the complete new I4 negative matrix passed. Minimal production repair reached the single grouped GREEN: 54 methods / 24.949s / OK. Final four hashes and line mapping are in `task-7-fix-2-review-package.md`. Gate remains `BASELINE_FROZEN / 0 / 1`; fixed root remains three files; no adjacent regression, compile, or real preflight ran. Status: `READINESS_FIX_2_GREEN_REVIEW_REQUIRED`; approval is not claimed.

Task 7 readiness fix round 2 fresh independent review: STOPPED at the first real readiness failure. Verdict Spec FAIL / Quality Needs fixes / `DO_NOT_RUN`; C1 remains Critical because a second persistence failure before the recovery checkpoint can replace the original KeyboardInterrupt, report a terminal-looking mapping while disk stays active/non-resumable, fall back to fabricated `0/1`, or misreport resource exit 3 as 2. I2 is ADDRESSED. I4 remains Important because Gate-3 unauthorized/blocked/classification/nonvacuity negatives and real recovery/final-verdict atomic boundaries are incomplete. Review `task-7-fix-2-review.md`, SHA-256 `fb2388f506fa41c8ad00ac7bff42370de3456ce416965c38d90f1abdebfc26da`, 10,776 bytes. Per the user stop rule, no further edit/test, adjacent regression, compile, DP, or real preflight ran. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is human discussion of C1/I4 before authorizing any fix round 3.

Ruling: Task 7 fix round 3 is authorized only for the round-2 C1/I4 findings — the user approved the stated modification/test sequence and I2 plus I1/I3/M1 are already closed — if wrong, the cost is another scoped review/fix round, not scientific reparameterization.

Ruling: batch the tightly coupled C1/I4 cases into exactly one grouped RED and one grouped GREEN — this is the user-approved test order and preserves the established stop discipline — if wrong, failure localization is less granular and the run must stop rather than iteratively diagnose.

Task 7 readiness fix round 3/5: AUTHORIZED / pending grouped RED. Base `task-7-fix-3-base.md`; requirements `task-7-fix-3-brief.md`. No Git is available, so frozen hashes/bytes remain the review base. Gate authority remains `BASELINE_FROZEN / 0 / 1`; no adjacent regression, compile, DP, or real preflight is authorized before a clean focused GREEN and fresh scoped review.

Task 7 readiness fix round 3/5: focused TDD complete — valid RED `60 methods / 42.188s / 9 expected C1 failures / 0 errors`; single GREEN `60 methods / 28.843s / OK`. Fresh independent re-review returned C1 ADDRESSED / I4 ADDRESSED / Spec PASS / Quality PASS / `READY_FOR_ADJACENT_AND_COMPILE`, with no new Critical, Important, or Minor finding. Review `task-7-fix-3-review.md`, SHA-256 `46fdea91a3ad0707b2aa58e45302bcfa8c3fa858490519b965458cef46786d38`, 9,634 bytes. Gate remains `BASELINE_FROZEN / 0 / 1`; exact next action is the complete focused v2 suite once, then legacy adjacent once, then approved compile once, stopping at the first failure.

Task 7 post-readiness verification: complete focused Family-3 v2 suite passed once — exact discovery command ran 110 tests in 115.289s, exit 0, `OK`. No rerun, legacy adjacent, compile, DP, or real preflight had run at this checkpoint. Gate remains `BASELINE_FROZEN / 0 / 1`; exact next action is the frozen legacy adjacent regression suite once.

Task 7 post-readiness verification: frozen legacy adjacent suite passed once — exact five-module command ran 68 tests in 6.591s, exit 0, `OK`. The v2 discovery result remains 110/110; neither command was rerun. Compile, DP, and real preflight remain unrun. Gate remains `BASELINE_FROZEN / 0 / 1`; exact next action is the approved thirteen-module compile once.

Task 7 post-readiness verification: approved thirteen-module compile ran once and exited 0 with no output. The focused v2 suite remains 110/110 and legacy adjacent remains 68/68; no command was rerun. Gate remains `BASELINE_FROZEN / 0 / 1`. Readiness, adjacent, and compile prerequisites are complete; exact next action is the one authorized real twelve-gate preflight command.

Task 7 readiness fix round 3/5: FOCUSED GREEN / fresh scoped readiness review required. The one grouped RED ran 60 methods in 42.188s and exited 1 with 9 expected C1 behavior failures and zero errors; all new Gate-3 I4 and final-verdict atomic-boundary cases passed. Minimal runner-only production repair reached the one grouped GREEN: 60 methods / 28.843s / OK. During post-RED static review, the old progressed-`GATE_PASSED` fallback test was found to contradict the frozen C1 contract and was narrowed, without another execution, to the allowed durable `INTERRUPTED` mapping; the separate new progressed/unverifiable negatives remain intact. Final hashes and mappings are in `task-7-fix-3-review-package.md`. Gate remains `BASELINE_FROZEN / 0 / 1`; fixed root remains three files; adjacent regressions, compile, DP, and real preflight remain unrun. Status: `READINESS_FIX_3_GREEN_REVIEW_REQUIRED`; approval is not claimed.

Ruling: accept the sole twelve-gate `CERTIFIED_PASS` as an exact construction/preflight certificate only — this milestone ran exact solvers, authority/safety audits, artifact-integrity checks, and no learner, training, or baseline comparison — if wrong, later reporting could incorrectly convert benchmark feasibility into a DDQN-advantage claim.

Task 7 final completion: fix round 3 received fresh independent C1/I4 approval (`Spec PASS / Quality PASS / READY_FOR_ADJACENT_AND_COMPILE`; no Critical, Important, or Minor finding). The approved sequence then ran exactly once: complete Family-3 v2 discovery 110/110 in 115.289s (`OK`), frozen legacy adjacent 68/68 in 6.591s (`OK`), and compilation of all 13 v2 modules with exit 0. The sole real preflight invocation exited 0 and returned `CERTIFIED_PASS` after all 12 contiguous Gates for all 10 graphs; every exact initial value is `4/5` and every first-request Q gap is `3/5`. No test or real preflight rerun was used to replace this result.

Task 7 postflight audit: the fixed root contains 72 regular files, including 20 exact certificates and 20 SQLite caches. Every cache returned `PRAGMA quick_check=ok`; the caches contain 314 total nonterminal rows, and peak process RSS was 30,863,360 bytes (29.43 MiB). The immutable v0/v1 baseline remains exactly 14/14 source and 72/72 result files with no missing, added, or changed entry, and no artifact escaped the fixed root. The first invocation of the read-only audit helper assumed a generic SQLite table named `values`; the actual frozen schema uses `nonterminal_exact_values`. Correcting that helper assumption produced the successful audit and did not change source, cache, certificate, checkpoint, Gate, or scientific evidence. It was an audit-tool error, not a product/artifact failure. Task 7 is complete; the durable scientific boundary is exact preflight feasibility/integrity, not DDQN superiority.
