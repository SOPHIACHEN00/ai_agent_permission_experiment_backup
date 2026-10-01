# Stage B2 — Minimal runner / checkpoint / evaluation integration

> Current continuation: one authorized GPU1 formal run is complete,72000/6/3600,integrity passed,NO_CLEAR_SIGNAL. Full evidence downloaded;test locked. Read formal_gpu01_v1/report.md and completion_receipt.json. Latest device limit isGPU0/1 only. B2 smoke status below is historical;do not rerun or restart.

Date: 2026-09-22. Status: B2_GPU2_SMOKE_PASS_FORMAL_NOT_STARTED. User approved both repairs and superseded GPU1 with GPU2/3 authorization; only physicalGPU2 was used. Read B2_SMOKE_RESULTS_zh.md and evidence/b2_fix1_completion_receipt.json first. This plan extends task_plan.md and GOAL_AMENDMENT_zh_en.md. Historical failure evidence is preserved.

## Fixed scope

Reuse BudgetRecourseDDQN, existing CUDA update/replay and checkpoint serialization/hash helpers. Keep old source, StageA, learning parameters and criteria unchanged. The only authorized B1 changes are selected-device protection and its corresponding check, with old/new hashes in execution_profile_gpu2_v1.json. Add a small standalone runner and bounded checks. No worktree/commit, dependency installation, old test, StageA rerun, API, local learner training or parameter search.

Ruling: use the established standalone archive workspace and preserve it — the user's durable-record/minimal-work instructions override skill scratch deletion and a new Git workflow. No new design approval cycle is needed for this already approved integration.

Ruling: use one expected RED for new missing integration behavior and one focused GREEN; original nine checks are already recorded and are not rerun. Stop at the first genuine unexpected failure; this overrides skill automatic fix/retest loops. Record sandbox/tool startup failures separately from experiment failures.

## Interfaces / decisions

- New runner consumes only public State via the existing encoder and passes distinct named exploration/tie RNGs. Training uses five original graphs, exactly 2400 transitions per graph, 12000 per arm/seed; gamma0/1 and seeds101/211/307. A graph-quota cutoff preserves a real nonterminal successor; it is not a fake terminal reward.
- Checkpoints reuse tensor/state/replay normalization and store online/target/optimizer/replay/RNG/counters plus new schema/config/source hashes. Old artifact-store class is 43-dimensional Family3-v2-specific, so its old run schema is not reused or mislabelled. No old model warm start.
- Frozen policy evaluation integrates exact tie probabilities using pure transitions, while sampled evaluation uses the real authorization/monitor adapter. Training never receives Tape, DP values or oracle labels. Evaluation verifies model/optimizer/replay fingerprints before/after; it must not call observe.
- Load the saved Stage A root reference values, not rerun its preflight. Rule policies retain the frozen Solver logic. Stage B evaluation has its own bounded 100000-state/60-second/512MiB additional-host-memory budget per cell, measured above the already loaded CUDA runtime; this does not change Stage A's absolute caps. Record the baseline and cap in run metadata.
- Fresh exclusive run directory; no resume/retry/overwrite. Status and raw step/episode records retain last durable coordinates. Any error writes failure evidence and exits.
- Formal train-validation only:72000transitions/6checkpoints/3600validationrows. Validation completion gate is integrity/coverage only, never a performance filter. Test stays locked; separate test-once execution is not part of this minimal integration.
- GPU smoke is NON_EVIDENCE only: seed101/gamma1,320 transitions (64 per train graph), one checkpoint reload, train-only evaluation, no validation/test. Same hyperparameters; warmup256 and optimize-every4 must be exercised. It does not consume or certify formal experimental results.

## Steps

- [x] Read frozen design and reusable CUDA/replay/checkpoint interfaces.
- [x] Write and run one small non-learning behavior-check group: expected missing-module RED6failures/0.010s.
- [x] Implement first-version runner, checkpoint reload, exact/sampled evaluation, failure logging and test lock. Full CUDA pipeline is not yet verified.
- [x] Run the focused group once:6/6passed,2.894s. Evidence:b2_focused_green.json.
- [x] One independent read-only review stopped at first Important finding: lifetime-peak RSS subtraction is not a valid per-cell current-RSS cap. Package preparation independently failed due to one-level-too-high workspace path. Not review-approved or smoke-ready.
- [x] Notify scope; upload41verified files and run exactly one GPU2 smoke:exit0,320transitions,17updates,1checkpoint,2train-onlyrows. Formal training/test not started.
- [x] Download complete evidence and verify locally without training; update main progress/checkpoint. Hard counts0, evaluation fingerprints unchanged, weights changed from initialization.

## Recovery

Read B2_SMOKE_RESULTS_zh.md and evidence/b2_fix1_completion_receipt.json first. Root/current-RSS repairs passed10/10 checks. Before the single run, UUID prefix normalization passed1/1 guard check, retaining full identity equality. Evidence:evidence/b2_gpu2_smoke_v1;10record chains and41source/config hashes verified. Old26sources/2ZIPs/7StageAinputs stay frozen; only two device-related B1 changes were separately authorized/fingerprinted. No credentials saved. NON_EVIDENCE sampled0/2 and exact0 do not establish learning effectiveness. No new full independent review; unexamined areas remain unclaimed. Do not rerun smoke,StageA or oldv2. Formal72000/6/3600 and separate test5400 remain unstarted; use a separate formal execution record/directory.
