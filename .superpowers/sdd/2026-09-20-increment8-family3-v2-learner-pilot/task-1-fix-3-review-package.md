# Task 1 fix round 3 documentation review package

- D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\docs\CONTINUATION_CHECKPOINT.md — 65367 bytes — 998a3550332038d167653ef75361ab4946f65bfafb5f6336d0786bec51750537
- D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-1-report.md — 6499 bytes — af6d6a7a8670ecf5deb15fe0e95ebfb9af8be8025347a1893aef8fdf2a6bf1f5

## Current checkpoint first 105 lines
```
# RL Personal Assistant — Continuation Checkpoint

This file is the durable restart point for interrupted work. Update it at every
meaningful boundary: before production edits, after a genuine RED, after GREEN,
before independent review, and after the review verdict. It is intentionally
shorter than the implementation reports and is the first file to read after a
network interruption or context reset.

## Current checkpoint

- Updated: 2026-09-20 (America/Toronto)
- Active phase: **Family-3 v2 exact-preflight artifact remains frozen `CERTIFIED_PASS`; Learner/Baseline Pilot Task 1 is independently APPROVED and complete; Task 2 public 43/7/7 surface is next**
- Increment 8 state: **all 10 Family-3 v2 graphs remain certified at exact `V*=4/5` with request Q-gap `3/5`; the certified environment/suite/policy/solver artifacts remain immutable for the learner study**
- Experiment state: **Task 1 added only the frozen config, dependency baseline, strict criteria loader/verifier, and focused contract test; no adapter, runner, smoke, training, validation, official test, server job, or OpenAI API call has run**
- Last approved completed experiment: **Increment 7 Task 5 — Run integrity PASS / Result interpretation APPROVED; PARITY; prefer Rule; no rerun/tuning or Deep-RL advantage claim**
- Current design worker: none; Task 1 is independently approved/complete; no learner/training process is in flight
- Current read-only reviewers/calibrators: Task 1 spec+quality `APPROVED`; learner-pilot scientific closeout `APPROVE`; bilingual contract audit `PASS`; final implementation-plan audit `APPROVE`; normative JSON is byte-for-byte identical and parseable in both specs
- Learner-pilot English approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md` (SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`, 38,149 bytes)
- Learner-pilot Chinese approved spec: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md` (SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`, 35,818 bytes)
- Learner-pilot implementation plan: `docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md` (SHA-256 `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`, 30,311 bytes)
- Task 1 baseline: `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json` (SHA-256 `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`, 11,338 bytes)
- Task 1 final artifacts: config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`; criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143`; test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea`.
- Family-3 v2 English spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` (SHA-256 `1C2F173A33EE438CE15ED910EF1637536B535495C95D73F340B679291C00656F`)
- Family-3 v2 Chinese spec: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design_zh.md` (SHA-256 `82DDA83C604BE7C46276331BF4F9B65D974C167E58635407C943F8285757CEEF`)
- Family-3 v2 implementation plan: `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md` (SHA-256 `036B9690A06267099C62F78B98C973A9B283037BAB449AF074CB6A878A049658`)
- Increment 8 English spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design.md` (SHA-256 `1E75BFF12CBE72B6EB42E4F6E7D9C99DF7F426445C4EC9FD481EA6DC2EB86913`)
- Increment 8 Chinese spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design_zh.md` (SHA-256 `2CDB11522339E8950799E09A1ADDFA24EDF34A3795C49BA5CBA7156182FFF96A`)
- Final design verification: three independent read-only reviews PASS; both files have 14 main sections/29 total headings, identical parseable criteria JSON, no TODO/TBD/FIXME/placeholder, and exact agreement on split/method/seed/budget/row/cardinality/state-machine contracts.
- Phase A plan: `docs/superpowers/plans/2026-08-26-increment8-phase-a-preflight-plan.md`.
- Phase A notes/report: `docs/superpowers/notes/2026-08-26-increment8-phase-a-implementation-notes.md` and `docs/implementation_reports/task-8-phase-a-report.md`.
- Interruption boundary: **STABLE / TASK 1 INDEPENDENTLY APPROVED AND COMPLETE / NO PROCESS IN FLIGHT.** The exact twelve-gate artifact remains unchanged. The frozen config/baseline bind the literal 5/2/3 split, 43/7/7 adapter contract, seven public-only methods, matched `gamma=0/1`, seeds 17/29/43, 12,000/2,400/50 budgets, and literal certificate/cache hash-size inventory. No adapter, runner, smoke, training, validation, or test has run. Exact next action: Task 2 public 43/7/7 surface.
- Task 4 fix round 1 boundary: **STABLE / REVIEW PENDING.** Regression RED ran 19 methods in 0.076s and failed exactly I1/I2/M1 (`failures=3, errors=2`). Affected focused GREEN passed 19 methods in 0.071s; the single authorized Tasks 2–4 combined run passed 24 methods in 0.081s. Caller-visible binding evidence contains no raw authorization handle, all anomaly successors use public model-owned `transition_integrity_failure`, and singleton first-effect closure records no branch residue. SHA-256: model `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c`; model test `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1`; authority `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d`; policy unchanged `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6`; environment `764ec0132b09d2fcdcbf6339f2d6b8013e7e06ded05849f4611a2f2d532f9663`; authority/environment test `63ce6fd58a6e55b93c4293664f55ec2c73f1bfddb9ca25cc54d18a5f3dd38eeb`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is independent Task 4 fix-round re-review before Task 5.
- Task 5 boundary: **STABLE / FOCUSED GREEN.** The exact missing-audit RED was `ModuleNotFoundError: No module named 'pa_rl.family3_v2_audit'` (`Ran 1 test in 0.000s`, exit 1). Final focused GREEN passed 7 methods in 27.802s. Reports passed with: Markov 20 analyses/314 occurrences/314 public groups/314 encoded groups/2,198 rows/1,256 valid actions/1,296 transitions; real-environment conformance 20 analyses/314 states/1,256 actions/1,416 replays including exact residues `{0,1,2,3,4}` and 200 first-effect residue replays; firewall 480 manifests/4,800 row checks; witnesses 40 cells; binding/no-repair 20 bindings/2,058 catalog rows/6 action types/882 no-repair checks/4 nonemitted guards/882 forced-invalid zero-delta checks. Audit/test SHA-256 and sizes: `36f590a1804369f05429142479a6d51fa0d9f50a9ffbdc0ba6bb00675ed6cb2c` / 44,665 bytes and `a848b77c80f74da487374ef3c40fe191140ceebc520cc24746617cca3c82d77f` / 11,815 bytes. Frozen Task 2–4 hashes match the Task 5 base manifest. Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; exact next action is **Implement Task 6 capped exact solver, independent reference, and artifact store**. No broad/combined tests, DP, solver, runner, training, tuning, or rebaseline ran.
- Task 5 fix round 1/5 boundary: **STABLE / FOCUSED GREEN / RE-REVIEW REQUIRED.** Affected regression RED ran 18 methods in 31.029s with the expected six missing-evidence/API errors. The single authorized affected GREEN passed 18 methods in 71.949s. Exact safety evidence now covers 294 no-repair states, 882 closed-offer rows, 294 disable guards, 20 execute guards, 314 complete nonemitted catalogs (2,198 rows), and 882 full-channel forced-invalid zero-delta replays. Task4 evidence now publishes immutable task snapshot and user-dispatch count without changing policy observation. SHA-256: environment `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8`; environment test `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092`; audit `1ba1dc3b660892410bb31bec9af3cb1a0d145f479851ffb58ee954ec049b98d5`; audit test `2ed2837d0e081947643e4def4b7893d431facaa5a631a23ec0f6b19b2fe708d0`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 6 is blocked. Exact next action is fresh independent Task 5 fix-round re-review.
- Task 5 fix round 2/5 boundary: **STABLE / INDEPENDENTLY APPROVED.** The two new regression methods first failed in 7.078s on the expected missing literal/stable-key evidence, then the identical two-method command passed once in 14.976s. Production independently checks 294 ordered emitted literals, 314 pure and 314 real ordered no-coverage literals, and 882 complete dataclass stable keys plus 882 exact forced-invalid closures. Fresh focused review returned Spec PASS / Quality PASS / APPROVE with C1/C2 addressed and no new finding; 14/14 frozen source and 72/72 frozen result files still match. Audit SHA-256 `92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921` (64,280 bytes); audit-test SHA-256 `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` (22,466 bytes). Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 6 brief hash remains `7d57ab70c77be1fd8add1a68f7232c6fd6373fd85a69a14155a707f064f61581`. Exact next action is Task 6 capped solver/reference/artifact implementation.
- Task 6 boundary: **STOPPED / NOT GREEN / HUMAN INSPECTION REQUIRED.** The missing-solver RED was exact. Three disjoint modules were then created. The single combined GREEN attempt ran 12 methods in 5.311s: 11 passed; one error occurred only when Windows `TemporaryDirectory` tried to unlink `values.sqlite3` still held by the test's `sqlite3.Connection`. No Bellman/reference/artifact assertion failed. No fix or retry ran. Evidence: `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-6-green-failure.md`. Gate authority remains `BASELINE_FROZEN / 0 / 1`; exact next action is human approval or rejection of a minimal test-only explicit connection close and one rerun.
- Task 6 closeout: **FOCUSED GREEN / INDEPENDENT REVIEW PENDING.** Authorized test-only repair added `contextlib.closing` around the test-owned guard-tampering SQLite connection; no production code, scientific assertion, parameter, cache, certificate, run config, or gate changed. The same focused command was rerun once and passed all 12 methods in 5.260s (`OK`, no warning). Final hashes/bytes: solver `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` / 36,031; reference `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` / 11,935; artifacts `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` / 29,226; solver test `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` / 7,172; reference test `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` / 3,400; artifact test `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` / 7,127. Task 2–5 frozen manifest is unchanged. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked pending independent Task 6 spec+quality APPROVE. Evidence: `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-6-report.md`.
- Task 6 fix round 1/5 boundary: **BLOCKED / INVALID GROUPED RED.** The single prescribed command ran 29 methods in 15.407s and returned 13 expected behavioral failures plus one fixture error. The error happened before production construction because the wrong-output helper hashed a nonexistent `wrong_output/run_config.json`. The stop rule prohibited repair, production edits, or GREEN. Three production hashes remain at their reviewed base; only the three focused tests contain the new regressions. Gate authority remains `BASELINE_FROZEN / 0 / 1`, Task 7 remains blocked, and the exact next action is human authorization for a fresh round starting by repairing that fixture before a newly authorized RED.
- Task 6 fix round 1/5 continuation: **FOCUSED GREEN / SCOPED RE-REVIEW REQUIRED.** Controller ruled the pre-constructor fixture error was not a scientific failure and authorized only canonical run-config fixture setup before a replacement RED. Valid RED ran 29 methods in 8.455s with 14 behavior failures and zero errors; the single post-fix GREEN passed all 29 in 7.616s. C1/I1–I6/M1 fixes bind output ancestors/containment, restart/evidence shapes, immutable baseline SHA, canonical SQLite schema, same-graph reference traversal, mandatory pressure/negative coverage, and reference-result row invariants. Gate remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked pending review of `task-6-fix-1-review-package.md`.
- Task 6 final approval: **COMPLETE / INDEPENDENTLY APPROVED.** Fresh scoped review of fix round 1 returned Spec PASS / Task Quality PASS / APPROVE, with C1/I1–I6/M1 addressed and no new Critical, Important, or Minor finding. The review recomputed the final six Task 6 hashes/bytes, confirmed all Task 2–5 hashes unchanged, retained RED/invalid-fixture/valid-RED/GREEN history, and verified the fixed root has only checkpoint, baseline, and JSONL. Gate authority remains `BASELINE_FROZEN / 0 / 1`. Task 7 is authorized/pending under `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-7-brief.md`; its exact next action is **Implement Task 7 ordered twelve-gate preflight under frozen brief**. No Task 7 test, DP, preflight, compilation, training, run config, Gate, cache, or certificate has run/been created.
- Task 7 runner boundary: **FOCUSED GREEN / READINESS REVIEW REQUIRED.** The single RED failed only on the required missing runner import (`Ran 1 test in 0.000s`). The single focused GREEN passed 16/16 methods in 0.417s (`OK`). New hashes/bytes: runner `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` / 48,890; test `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` / 23,379. All 19 Task 2–6 hashes/bytes remain unchanged. Gate authority remains `BASELINE_FROZEN / 0 / 1`; fixed root still contains only baseline, checkpoint, and progress JSONL. No adjacent regression, compile, real ten-graph preflight, run config, Gate, cache, certificate, failure, interruption, or verdict was produced. Next action: independent Task 7 readiness review of `task-7-implementation-review-package.md`.
- Task 7 fix round 1/5 boundary: **BLOCKED / INVALID GROUPED RED.** The exact grouped command ran once: 44 methods in 14.340s, 22 failures, zero errors. Expected C1/I1–I3/M1 behavior gaps appeared, but the new typed Gate-3 I4 fixture encoded a 20/10/10 cell partition while declaring 40/0/0 counts, so one failure was caused by contradictory test setup. Stop rule enforced: no fixture repair, production edit, GREEN, adjacent regression, compile, or real preflight. Only the two focused tests changed; runner/artifact-store production hashes remain reviewed-base values. Gate remains `BASELINE_FROZEN / 0 / 1`; fixed root remains three files. Exact next action is fresh authorization to correct only those fixture counts before a new grouped RED.
- Task 7 fix round 1 continuation: **FOCUSED GREEN / SCOPED READINESS REVIEW REQUIRED.** Controller authorized the same round to change only typed witness declarations 40/0/0→20/10/10. Valid replacement RED: 44 methods / 13.108s / 21 behavioral failures / zero errors. Single grouped GREEN: 44 methods / 15.173s / `OK`. C1 added strict disk-reconciled recovery across handler/commit/finalize boundaries; I1–I4/M1 strengthen dependency closure, committed Gate4→5 binding, Gate1 proof, real-handler coverage, and Gate6 evidence. Final four hashes are recorded in `task-7-fix-1-review-package.md`; the store/test reopening is controller-authorized and the other 17 Task 2–5 entries remain unchanged. Gate remains `BASELINE_FROZEN / 0 / 1`, fixed root remains three files, and adjacent/compile/real preflight remain unrun.
- Task 7 fix round 2 boundary: **STOPPED / INDEPENDENT `DO_NOT_RUN` / FIRST REAL READINESS FAILURE.** Grouped RED was valid (54 methods / 29.720s / 12 C1/I2 behavior failures / zero errors) and grouped GREEN passed once (54 methods / 24.949s / `OK`), but fresh static review found a remaining Critical C1 recovery-before-checkpoint defect and Important I4 gaps in Gate-3 predicates and real atomic persistence boundaries; I2 is closed and I1/I3/M1 remain closed. Review SHA-256 `fb2388f506fa41c8ad00ac7bff42370de3456ce416965c38d90f1abdebfc26da` / 10,776 bytes. Per stop rule, adjacent regressions, compile, DP, and the real preflight were not run. Gate remains `BASELINE_FROZEN / 0 / 1`; exact next action is human discussion before any fix round 3.
- Task 7 final boundary: **COMPLETE / `CERTIFIED_PASS`.** Fix round 3 independently closed C1/I4 with no remaining finding. Ordered execution evidence is v2 suite 110/110, legacy adjacent 68/68, 13-module compile exit 0, and one real twelve-gate run exit 0. All 10 exact graph certificates report initial `4/5`; all request Q gaps are `3/5`. The 72-file fixed-root audit verified 20 certificates/caches, all SQLite `quick_check=ok`, 314 nonterminal rows, 29.43 MiB peak RSS, exact frozen v0/v1 preservation, and zero path escape. The first audit-helper call used the wrong assumed SQLite table name and was corrected without modifying the product or artifacts. This boundary certifies exact benchmark construction and integrity only; it is not DDQN evidence.
- Diagnostic boundary: **V4 COMPUTATIONAL UNKNOWN RESOLVED / FAMILY-3 V1 STILL REJECTED.** Terminal-history over-separation was sufficient to cause the old v4 block, but the independent `s3_v3=13/25<3/5` construct/feasibility failure remains unchanged. Therefore all-forty and v1 spec freeze remain blocked. Results: `results/increment8_v1_terminal_cache_bypass_diagnostic`; English/Chinese reports: `docs/research_audits/2026-08-27-terminal-cache-bypass-diagnostic/terminal-cache-bypass-diagnostic-report.md` and `_zh.md`. Source SHA-256 `1217EC43CE64D9B4DA12C9C1CB75DD6B8C24536EF8B3061DDEA1F60C6AABAF4F`; v4 certificate SHA-256 `964C48026DD4563992E79A3A2AA1715F37CBB66596C87F3882639403F5BC2D39`.
- Rough source files: `src/pa_rl/baselines.py`, `src/pa_rl/g2_rough.py`
- Focused rough test: `tests/test_g2_rough.py`
- Minimal replay source/test: `src/pa_rl/replay.py`, `tests/test_replay_minimal.py`
- Review source of truth: `docs/implementation_reviews/task-3b2b1-review.md`
- Rough report: `docs/implementation_reports/task-4-rough-report.md`
- Minimal replay report: `docs/implementation_reports/task-3b2-minimal-report.md`
- Increment 5 spec: `docs/superpowers/specs/2026-08-18-increment5-masked-ddqn-design.md`
- Increment 5 plan: `docs/superpowers/plans/2026-08-18-increment5-masked-ddqn-plan.md`
- Increment 5 source: `src/pa_rl/ddqn_features.py`, `src/pa_rl/ddqn.py`,
  `src/pa_rl/evaluation_criteria.py`, and `src/pa_rl/increment5_rough.py`
- Increment 5 criteria/test: `configs/evaluation/rough_v0.json` and
  `tests/test_increment5_rough.py`
- Increment 5 report: `docs/implementation_reports/task-5-rough-report.md`
- Increment 6 audit: `docs/superpowers/notes/2026-08-18-increment6-audit.md`
- Increment 6 spec: `docs/superpowers/specs/2026-08-18-increment6-multiscenario-full-action-design.md`
- Increment 6 Chinese spec: `docs/superpowers/specs/2026-08-18-increment6-multiscenario-full-action-design_zh.md`
- Increment 6 plan: `docs/superpowers/plans/2026-08-18-increment6-multiscenario-full-action-plan.md`
- Increment 6 Task 1 source/test: `src/pa_rl/multiscenario_policy.py` and
  `tests/test_increment6_pilot.py`
- Increment 6 Task 1 report:
  `docs/implementation_reports/task-6-task1-report.md`
- Increment 6 Task 2 source/report: `src/pa_rl/pilot_outcome.py` and
  `docs/implementation_reports/task-6-task2-report.md`
- Frozen Increment 6 artifacts: `results/increment6_multiscenario_v0/result.json`
  (SHA-256 `b79247f824b20ab6f16e6b4b3a733a7896608844f18e456c57daefe482c895c1`)
  and `results/increment6_multiscenario_v0/run_manifest.json` (SHA-256
  `dc7360aaf81a203f4e1e40aca9395619ed728ac8ef6db99ed414b338e10a356a`)
- Frozen criteria: `configs/evaluation/multiscenario_v0.json` (SHA-256
  `87c1a25a0b70745d66b4307ddfd3246aba50df54e960221510cb19d98eda3de3`)
- Pilot report: `docs/implementation_reports/task-6-pilot-report.md`
- Increment 7 Task 1 source/test: `src/pa_rl/increment7_scenarios.py` and
  `tests/test_increment7_pilot.py`
- Increment 7 suite hash:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`
- Increment 7 split hash:
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`
- Increment 7 Task 3 source/profile: `src/pa_rl/heldout_criteria.py` and
  `configs/evaluation/heldout_context_v0.json`
- Increment 7 Task 3 report:
  `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-3-report.md`
- Frozen Increment 7 results: `results/increment7_paired_v0/`; formal report:
  `docs/implementation_reports/task-7-heldout-context-report.md`; approved
  Task 5 review:
  `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-5-review.md`.
- Exact next action: Task 2 public 43/7/7 surface. Task 1 is independently
  approved/complete. Do not start smoke, training, validation, or test before
  their separately authorized boundaries.

## Increment 7 Task 5 READY_FOR_FROZEN_RUN boundary

- Frozen at `2026-08-18T13:30:47.136+08:00` after the Task 4 fix-round
  independent verdict `Spec: PASS / Quality: APPROVED`.
- Official output path:
  `results/increment7_paired_v0`; the directory, `result.json`, and
  `run_manifest.json` were all absent before execution. No completed official
  run exists.
- Exact one-time command:
  `$env:PYTHONPATH='src'; python -m pa_rl.increment7_pilot --criteria
  configs\evaluation\heldout_context_v0.json --output
```

## Task 1 report final 35 lines
```

- `configs/evaluation/family3_v2_learner_pilot_v0.json`: 8,377 bytes, `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`.
- `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`: 6,846 bytes, `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`.
- `src/pa_rl/family3_v2_pilot_criteria.py`: 6,040 bytes, `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`.
- `tests/test_family3_v2_learner_pilot.py`: 3,880 bytes, `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e`.

## Self-review and concerns

The loader freezes the exact canonical approved JSON, rejects unknown/missing/noncanonical values (including booleans substituted for integer fields), and exposes immutable mappings. The verifier compares literal paths, sizes, and hashes without rewriting the baseline; the focused test proves a tampered learner dependency fails. No certified artifact, `ddqn.py`, or `baselines.py` was changed, and no exact-DP/twelve-gate run occurred. Only the approved focused RED/GREEN command was run. Concern: none.

## Checkpoint supplement

The required continuation checkpoint was updated after the normal patch helper encountered its Windows ACL lock. Its final SHA-256 is `45fdb03f541a58c108d9fb313f2fa8b5a9810d0c7d7d19ea7f056f9a5d5ff131` (65,135 bytes). Final Task 1 hashes remain: config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`; baseline `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`; criteria `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`; test `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e`. The checkpoint records Task 1 review as the next step. No test was rerun.

## Fix round 1/5

RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v`.

RED result: `KeyError: 'certificate_entries'` at the new literal certificate-inventory assertion; `Ran 1 test in 0.010s`, `FAILED (errors=1)`. This demonstrated the reviewed path-only integrity gap.

GREEN command: identical focused command. GREEN result: `Ran 1 test in 0.314s` — `OK`.

The baseline now records all 20 certificates and 20 SQLite caches as literal `{relative_path, sha256, byte_size}` entries. The verifier rejects unknown/missing schema fields, noncanonical approved-spec/result-root/suite/inventories, duplicate entries, and escaped paths, while verifying every recorded hash and size. Current hashes/sizes: baseline `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` / 11,338; criteria `dea81534fd46cf5de1789c2628723dfa0e889513418e728204eb7a9c98f2a5a3` / 7,769; test `1f14128d6664362c94c1df90d008d0c307196f391f538f1ad755be99d1776617` / 5,904; checkpoint `dfad2c59eef557a9dc0efe91d5e993445c87f037a5d01a176aeaf79c2fa9ff8f` / 65,061. No test beyond the authorized focused RED/GREEN was run. Current next action: Task 1 review.

## Fix round 2/5

RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v`.

RED result: an assertion that `ValueError` must be raised for a substituted remaining inventory failed: `AssertionError: ValueError not raised`; `Ran 1 test in 0.395s`, `FAILED (failures=1)`. The final focused GREEN used the identical command and passed: `Ran 1 test in 0.453s` — `OK`.

The verifier now binds `certified_source_files`, `additional_learner_dependencies`, `pilot_config`, and preflight artifacts to fixed canonical digests in addition to exact per-entry schema and physical hash/size checks; reorder, duplicate, path, or expected-value substitution fails closed. The current checkpoint exact-next-action block now states Task 1 fix round 2/re-review and prohibits Task 2 until spec and quality approval. Final hashes/sizes: criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` / 8,984; test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` / 6,332; checkpoint `5ead68f023ee85613c6f0a5fe6a9a91d21217d02fc0273531ae53bf710ff9613` / 64,948; baseline unchanged `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` / 11,338.

## Fix round 3/5 — documentation closeout

No production or test file changed and no test was rerun. The continuation checkpoint now points to the final baseline at `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`, SHA-256 `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`, 11,338 bytes, and records the final config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`, criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143`, and test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` hashes. Current status is independently APPROVED/complete; the next allowed work is Task 2 public 43/7/7 surface, with smoke/training/validation/test still forbidden. Final checkpoint SHA-256: `998a3550332038d167653ef75361ab4946f65bfafb5f6336d0786bec51750537` (65,367 bytes).
```