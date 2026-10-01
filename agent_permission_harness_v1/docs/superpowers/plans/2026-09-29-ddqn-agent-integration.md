# Single-Agent DDQN integration implementation plan

**Goal:** Implement the approved real-DDQN bridge, constrained terminal reward, offline training and frozen evaluation in the existing single-Agent execution path.

**Architecture:** Preserve the existing authority kernel and expose one controller decision at a time from AgentSession. A learning environment manages resource accounting and pending transitions; a numeric encoder and policy adapter call the existing MaskedDoubleDQN.

**Tech Stack:** Python/PyTorch CPU or CUDA, unittest. Per later user steering, execute tests/training only on the supplied SSH server under agenticAI; no paid model calls.

**Spec:** ../specs/2026-09-29-ddqn-agent-integration-design.md

## Global constraints
- User explicitly requested implementation; proceed inline without repeating review/permission gates.
- New model schema: state 38, candidate 35, max candidates 64. Preserve all old Family3 files/checkpoints.
- Six parameterized actions, authoritative masks, matching human replies, factual ledger/monitor effects.
- Nonterminal reward 0; terminal success 1 only with business oracle, semantic integrity and budgets.
- Human wait is suspension; no duplicate dispatch, cost, replay or terminal credit.
- S-QSTN is not a source for this task-Agent RL implementation.
- Preserve unrelated dirty changes. Existing feature branch contains the untracked harness; work in place.

## Tasks

### 1. Public features and resource contracts
- [x] Write behavioral tests in tests/test_ddqn_features.py; observed five expected failures.
- [x] Add learning_contracts.py (EpisodeConfig, PublicEpisodeContext, DecisionBoundary, transition/end records), exposure.py and ddqn_features.py (DDQNFeatureEncoder, EncodedDecision).
- [x] Prove public-state meaning, grant-vs-operation distinction, hidden-value invariance, mask consistency, mutation/schema/bound rejection.
- [x] Five numeric-feature tests pass. Subsequent verification moved to the server per user steering.

### 2. One execution path, transitions and outcome
- [x] Add tests/test_learning_environment.py before implementing runner advance/dispatch and learning_environment.py.
- [x] Retain AgentSession.run() through shared advance()/dispatch_control(); add exact-once pending transition and budget stops.
- [x] Add integrity.py and learning_outcome.py; reconcile ledger reservations, monitor audits, receipts and local effects, and require an authored oracle.
- [x] Prove final credit, wait/resume, refresh/disable, deny/replan, escalation, truncation, forged actions, budget guards and corrupt evidence; run v1 available-code suite (98 pass; 5 metadata-dependent catalog tests excluded and disclosed).

### 3. Native DDQN policy and checkpoints
- [x] Add tests/test_ddqn_learning.py before ddqn_policy.py and learning_checkpoints.py.
- [x] Use MaskedDoubleDQN.select_candidate/observe with independent evaluation RNG; validate schemas and transition delivery.
- [x] Check real optimizer updates, legal selection, exactly-once replay, frozen evaluation state and checkpoint round-trip/legacy rejection.

### 4. Authored learning scenarios and repeatable pilot
- [x] Add tests/test_ddqn_pilot.py before learning_scenarios.py and run_ddqn_pilot.py.
- [x] Build reactive public-input planner, staged narrow/detail/narrow-tail task, fixed user responder, named splits and 9-cell budgets.
- [x] Add offline CLI with final checkpoints, raw per-episode outputs, full source/config identities, fresh output directories and no hidden retries.
- [x] Wire frozen DDQN into the existing Agent CLI for authored tasks with scripted or existing OpenAI planners.

### 5. Verification, small training run and report
- [x] Run v1, v0 and appropriate core regressions; inspect any failures. Legacy replay-semantics failures remain disclosed, not fixed as unrelated work.
- [x] Run the specified remote pilot: 300 complete episodes each for seeds 17/29/43; preserve all outcomes even if learning is weak.
- [x] Conduct fresh final code review as directed by executing-plans; fix meaningful findings with regression tests.
- [x] Update README, recap and verification report with actual evidence and remaining limitations.

## Review focus
- Stale/tampered decisions or repeated resumes cannot create authority or duplicate training transitions.
- End-of-task reward must attach to the last accepted action, including planner finish after tool execution.
- Narrow reads must not shrink the ledger grant or undercount its future exposure.
- Hash-valid audit records must still fail when their semantic binding to scopes/receipts/effects is wrong.
- Evaluation/checkpoint loading must not mutate training state or accept an old Family3 feature identity.

## Execution ledger
- Pre-flight: tasks 1→2 share public context/boundary; 2→3 share exact-once transitions; 3→4 share numeric model/checkpoint identity. All derive from the same approved schema.
- Ruling: use the existing feature checkout because the harness is partly untracked there; a new checkout would omit the implementation being extended. Preserve unrelated files.
- Ruling: the user explicitly requested code implementation and previously approved the specification, so no further routine permission gate is needed.
- Runtime: root .venv lacks torch; system Python 3.12 has torch 2.11.0+cpu. Use system Python with PYTHONPATH=.;rl_personal_assistant/src.
- Baseline: existing v1 suite 72/72 passed before source changes.
- Task 1: complete — five behavioral failures before implementation; five pass after implementation. These runs preceded the server-only instruction.
- User steering: GPU support is required. All subsequent tests/pilot execute remotely under agenticAI; do not run local training/tests or store the supplied login secret.
- Ruling: while SSH rejected sessions with Exceeded MaxStartups, wrote transition tests before implementation but could not execute their pre-implementation RED gate. Record this limitation; do not describe Task 2 as a fully observed TDD cycle. First remote run had 5 passes/2 failures, then source-level root causes were inspected.
- Remote: authenticated; workspace /hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001 (persistent storage, fresh subdirectory). Python 3.12.13, torch 2.11.0+cu130, four RTX 3090s. No old server directories modified.
- Task 2 first run: scope JSON lists need conversion to the native tuple contract; audit tool detail is nested under detail. Test also incorrectly assumed ledger record creation order rather than stable authorization ID sorting. Corrected bindings, not authority semantics.
- Task 3 RED observed remotely: all 5 new DDQN tests failed because ddqn_policy was not implemented. Imported TestCase caused duplicate collection of 7 environment tests; changed to module-qualified helper access.
- Ruling: preserve the frozen native DDQN loop with CPU replay and a differentiable device-network wrapper; CUDA parameters/gradients/Adam are tested remotely. This minimizes semantic drift, at the cost of CPU/GPU transfer overhead; no speedup or multi-GPU claim.
- Task 3: complete — 5/5 tests passed remotely, including actual CUDA backpropagation/parameter updates and CUDA-to-CPU checkpoint portability.
- Task 4: complete — 4/4 pilot tests pass remotely, including fixed fixture identities (observed RED before their addition), all 54 evaluation rows for a tiny smoke, and an authored contraction witness (not learned behavior).
- Reproducibility ruling: optional deterministic human session / episode IDs are scoped to isolated offline fixtures, default UUIDs unchanged. Frozen tie RNG derives from seed, scenario, budgets and decision index; no training RNG mutation.
- Regression: first combined v1 run 88/88 passed (5 OriginalCorpusCatalogTests not scheduled), v0 29/29 passed. Auto-review refused uploading questionnaire/catalog metadata; do not retry/bypass it. Only code and original queries were uploaded; synthetic catalog validation still ran.
- Additional regression found invalid candidate raises were not persistently audited; added an expected failing test and fail-closed policy_error outcome, with no fabricated replay/action. Hash-valid monitor grant tampering is independently rejected; q22 business reward test passed.
- Task 2: complete — final available-code v1 suite 98/98 passes remotely; five corpus-metadata tests remain unrun, not claimed green.
- Task 5: complete — v0 29/29, focused core 184/184 pass. Legacy replay-semantics isolated 26 tests: 8 failures + 1 error; original combined command also had one working-directory-related missing-file error that the corrected focused command resolves.
- Formal pilot: exit0,31.427s; 300 episodes each seed17/29/43; optimizer updates205/203/402; training rewards1=0/0/86; held-out test rewards1=0/0/3 of9 each. All162 evaluations retained. No API calls; no efficacy/convergence claim.
- Final: fixed consent/lifecycle audit gap — tests/test_lifecycle_integrity.py, 4 tests/9 subcase failures RED→GREEN; final suite98/98. Fresh native lifecycle replay now binds typed matching replies, scopes, candidate identities, refresh/disable and exact ledger events.
- Final: minor (deferred): native torch.manual_seed during policy construction/loading changes process-global CUDA RNG; current wrapper preserves CPU RNG only. No stochastic CUDA layer in this pilot; do not claim full RNG isolation.
- Final: Ruling: unchanged legacy replay-semantics failures — retain original source and disclose isolated failures rather than repairing an unrelated authority kernel in this bridge change — cost if wrong: unresolved old audit defects remain; strengthened harness checks do not certify the whole old core.
- Final: Ruling: efficacy/convergence set aside by reviewer — report all seeds, exact actions and negative outcome; do not alter budgets/reward or silently rerun — cost if wrong: this pilot remains insufficient for a research-effectiveness claim.
- Final: Ruling: real transport / security-semantic attack evaluation set aside by reviewer — keep trusted local-mock threat model explicit — cost if wrong: production and prompt-injection safety remain unestablished.
- Final: Ruling: all-65-query performance set aside by reviewer — distinguish catalog/tool dispatch coverage from authored-oracle and length-holdout coverage — cost if wrong: no cross-domain or full-benchmark generalization evidence.
- Recorded-action replay:1062/1062 exact results/metrics/exposure matches under final lifecycle audit; zero policy selections/optimizer updates. Not a second training run. Added verifier test observed missing-module RED then1/1 GREEN, included in final98.
- Wi-Fi reconnect: sessions reset but remote pilot/checkpoints/logs persisted. Final command initially omitted tests directory from PYTHONPATH (5 import errors); only invocation corrected, final98pass. Checkpoint CLI with final43 on adaptive fixture completes; this is mechanical wiring evidence, excluded from pilot statistics.
- Ruling: do not merge, stage or commit the broad dirty checkout and do not run finishing-branch integration — user requested implementation/testing only, native legacy suite is not wholly green — cost if wrong: changes remain uncommitted and need the user's later Git integration. Preserve execution ledger rather than deleting it as uncommitted scratch.
- Full review dispositions and costs for earlier rulings: docs/ddqn_integration/final_review.md. All source changes after server-only steering were edited locally but executed only remotely. Transfer archives contain code/synthetic outputs only; rejected questionnaire metadata was never uploaded.
- Follow-up2026-09-29: after the above handoff, user explicitly replied “是” to catalog-only transfer of two minimal de-identified CSVs. Verified exact whitelist fields,373 rows/65 query IDs each, no participant IDs/answers/preference labels; both remote targets absent before transfer. SHA256 matches local copies. OriginalCorpusCatalogTests5/5 pass remotely in0.019s, exit0,60-second timeout. First98 plus this5 provide103 distinct passing tests across two runs; no new whole-suite103-run claim.
- Follow-up evidence: results/ddqn_remote_20260929_001/catalog_followup_001/. No code/reward changes, API calls or retraining. Checkpoint hashes unchanged. Historical “never uploaded” and five-test omission above describe the pre-approval state, not a remaining blocker. Raw participant data remains local and untouched.
- Follow-up documentation sync: security review rejected uploading five internal Markdown reports/plans beyond the two-CSV authorization. Did not retry or bypass. Local documentation is current; remote generated test logs and authorized CSVs exist, while prior remote narrative documents are not synchronized. Any future internal-report upload requires explicit additional user authorization.
