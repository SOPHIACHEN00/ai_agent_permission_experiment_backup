# Task Plan: RL Personal Assistant v0.10 — Increments 0–8

## Goal

Implement the deterministic authority-aware foundation, the frozen held-out context pilot, and a preflight-certified stochastic budgeted-lifecycle Increment 8, without adding PPO or the live S-QSTN runtime.

## Binding scope

- Code root: `ai_agent_permission_experiment/rl_personal_assistant/`.
- Design record root: `RL_Personal_Assistant_Design/`.
- Enabled controller actions: the frozen six v0.10 actions only.
- Deferred actions: `CLARIFY` and `PROPOSE_NARROW_SCOPE` have no slot.
- Tools and sensitive data are synthetic; no real external effects.
- Reward is terminal S0 binary task success.
- Increment 5 includes one rough Masked Double DQN prototype. Live S-QSTN, PPO, richer rewards, constraints, Security LLM, and Constitutional AI remain out of scope.

## Phases

- [x] Task 0 — Increment 0: scaffold, contracts, schemas, canonical fixtures, and contract tests.
- [x] Task 1 — Increment 1: scope matcher, authorization ledger, reserve/commit/abort, and invariant tests.
- [x] Task 2 — Increment 2: reference monitor, mock tool, task engine, evaluator, binary reward, and integration tests.
  - [x] Task 2A: complete mediation, mock effects, task progress, and audit chain (independently approved).
  - [x] Task 2B: trusted postcondition evaluator, frozen plan/result, and S0 binary reward (independently approved).
- [x] Task 3 — Increment 3 minimal prototype: scripted user, candidate catalog/mask, public observation firewall, deterministic environment, sealed traces, and canonical/default fresh replay. Hardened replay remains deferred below.
  - [x] Task 3R: rough research environment through the approved deterministic 3B1 kernel; sufficient for the first tabular RL smoke experiment.
  - [x] Task 3A: scripted user, verified public-event chain, resolved catalog/mask, and exact public observation firewall (independently approved; fresh suite 144/144).
  - [x] Task 3B1: deterministic environment kernel and canonical trajectories (independently approved; root fresh suite 174/174).
  - [x] Task 3B2 minimal prototype: sealed episode trace plus deterministic canonical/default fresh-environment replay.
    - [x] Task 3B2A: strict trace schema, closed-only sealing, structural validation, and policy replay firewall (independently approved; root fresh suite 198/198).
    - [x] Task 3B2P: one-environment/one-reset action-index replay, exact closure, resealing, and whole-trace equality for default scripted fixtures (three focused tests).
    - [ ] Task 3B2B: hardened independent semantics and configurable-factory fresh replay.
      - [ ] Task 3B2B1: trusted static context, cross-chain semantics, authorization replay, and evaluator recomputation (**deferred hardening; round-0 findings retained**).
      - [ ] Task 3B2B2: single-use factory binding, fresh action-index replay, and exact resealed-trace comparison (**deferred hardening**).
- [ ] Task 4 — Increment 4: random/rule/tabular baselines and matched `gamma=0` versus `gamma>0` RL-necessity diagnostic.
  - [x] Task 4R: rough tabular smoke on the 3B1 kernel (3 seeds; equal budgets; `gamma=0` gap 0.000 versus `gamma=0.9` gap 0.900).
  - [ ] Task 4F: formal preregistered G2 protocol, uncertainty analysis, sensitivities, and report bundle (deferred until the prototype direction is confirmed).
- [x] Task 5 — Increment 5: minimal candidate-scoring Masked Double DQN and rough baseline comparison (**ROUGH PASS**).
  - [x] Task 5A: public-only fixed feature encoder and masked Double-DQN target/update.
  - [x] Task 5B: replaceable JSON evaluation criteria profile.
  - [x] Task 5C: Random/Rule/Tabular/DDQN rough comparison on `one_time_grant_success`.
  - [x] Task 5D: two focused tests, one fixed three-seed run, report, and PASS checkpoint.
- [x] Task 6 — Increment 6: multi-scenario full-action pilot (**PARITY; frozen run complete**).
  - [x] Task 6A: audit canonical scenarios, reward shortcuts, observation aliases, and implementation boundaries.
  - [x] Task 6B: freeze public observation v1 and canonical-protocol outcome contract (spec approved; implementation plan written).
  - [x] Task 6C: implement full-action Random/Rule/Tabular/DDQN runner and replaceable pilot gate.
  - [x] Task 6D: focused tests, one frozen pilot run, report, and **PARITY** checkpoint. DDQN met required performance/safety gates but not the Deep-RL advantage margin; prefer Rule on this deterministic suite.
- [x] Task 7 — Increment 7: all-40 canonical context suite and frozen held-out pilot (**PARITY; frozen run complete**).
  - [x] Task 7A: immutable 24/8/8 family/carrier split and public-observation firewall.
  - [x] Task 7B: canonical all-40 replay, negative controls, named v1 layout, and public-only Rule.
  - [x] Task 7C: strict replaceable held-out criteria and three-way gate.
  - [x] Task 7D: balanced runner, evaluation-only checkpoints, test-once boundary, and atomic artifacts.
  - [x] Task 7E: one frozen seeds-17/29/43 run, read-only recomputation, descriptive analysis bundle, and **PARITY** stop-rule decision. Rule and DDQN both reached test macro protocol success `0.875`; prefer Rule and make no Deep-RL advantage claim.
- [ ] Task 8 — Increment 8 stochastic budgeted-lifecycle study.
  - [x] Task 8A: diagnose Increment 7 and freeze independently approved bilingual design.
  - [x] Task 8B: obtain consolidated user approval and write the Phase A preflight implementation plan.
  - [x] Task 8C: typed 48-graph suite and exact split generator (focused RED/GREEN; clean targeted compile; suite/split hashes recorded).
  - [x] Task 8D: exact lifecycle model, directive FSM, accounting, and outcome evaluator (focused GREEN; five review findings closed and independently re-reviewed PASS).
  - [x] Task 8E: authority-backed environment and public observation/encoder v2 (focused GREEN).
  - [ ] Task 8F: exact reachability, Markov/firewall certification, DP oracle, and counterfactual manifest (**`INVALID_RUN_BLOCKED` at frozen DP gate; 42/48 exact graphs completed, counterfactual manifest not built**).
    - [x] Task 8F-D: read-only exact failure decomposition for `i8_s0_v9`, `i8_s1_v8`, `i8_s3_v7`, and `i8_s3_v9`; all oracle residual loss crosses a stochastic first-zero frontier, budgets explain infeasibility, and `s0_v9` exposes controller-clock padding.
  - [ ] Task 8G: eight-method smoke-only registry and Phase A review gate.
  - [ ] Task 8H: separate Phase B full-run plan, frozen training, validation, official test, and analysis; blocked until Phase A approval.
  - [ ] Task 8V1: separately versioned repair after v0 `INVALID_RUN_BLOCKED`.
    - [ ] Task 8V1A: freeze bilingual v1 spec and exact Phase A implementation plan; controller-independent workload index, family-level calibration, additive oracle-regret contract.
      - [x] Task 8V1A-S: disk-backed, memory-controlled value-first exact DP solver completed with witnessed RED/GREEN; the one fixed `i8_s3_v9` candidate returned `45569/125000 = 0.364552 < 3/5`, so classification is **`CERTIFIED_FAIL`**.
      - [x] Task 8V1A-T: the one subsequently approved Family-3 target-reduction candidate `(prompt, exposure, target, horizon)=(3,24,6,12)` returned exact `7953/10000 = 0.7953 > 3/5`, so the key graph is **`CERTIFIED_PASS`** without parameter search.
      - [x] Task 8V1A-P: completed conditional fixed-formula Family-3 gate decision — **BLOCKED**. Eight certificates pass, `s3_v3=13/25 < 3/5` is an exact FAIL, and `s3_v4` is state-limit BLOCKED without a certificate; all-forty was not run.
      - [x] Task 8V1A-R: independent Family-3 definition/computation review complete. `s3_v3` is a likely construct/task-definition defect driven by prompt/one-time feasibility rather than disable→refresh; `s3_v4` is expected combinatorial growth amplified by value-equivalent terminal-history caching.
      - [x] Task 8V1A-R2: approved isolated terminal-cache-bypass diagnostic complete. Seven focused tests passed; exact controls reproduced `s3_v5=1` and `s3_v3=13/25`; the single fresh `s3_v4` run certified value `1` using 193,537 cached nonterminal rows and 1,053,226 terminal returns. Artifact review verdict VALID. This resolves v4 computation only; Family-3 v1 remains rejected because v3 is below `3/5`.
      - [ ] Task 8V1A-D: blocked; it requires a passing Task 8V1A-P. Do not freeze synchronized English/Chinese v1 specs or the minimal implementation plan.
    - [ ] Task 8V1B: blocked pending a new research decision and Task 8V1A-D; TDD implementation in isolated v1 modules/tests without modifying v0 source or artifacts.
    - [ ] Task 8V1C: blocked pending 8V1B and a new research decision; exact 48-graph suite/Markov/firewall/DP preflight and stop-rule decision; no smoke or training.
- [ ] Task 9 — Documentation sync, broader verification, requirement audit, and deferred-hardening review after the Increment 8 research decision.

## Gate conditions

### G0 — Contract

- Six-action catalog has no deferred slots.
- Public/private/oracle fields are explicitly separated.
- Scenario, authority, event, observation, candidate, and reward contracts validate fixtures.
- Candidate IDs and ordering are deterministic.

### G1 — Authority and environment

**Status: MINIMAL PROTOTYPE COMPLETE / HARDENING PENDING.** Authority, evaluator, the deterministic kernel, sealed traces, and canonical/default fresh replay are available. Independent cross-chain semantics and configurable-factory replay (Tasks 3B2B1–B2B2) remain deferred and must be completed before hardened replay/security claims.

- Policy cannot mint a grant.
- Expired, consumed, revoked, and superseded grants cannot execute.
- One-time authorization commits at most one protected effect.
- Every execution is mediated by the reference monitor.
- Canonical trajectories are deterministic and replayable.
- Private/oracle canaries never enter policy observations.

### G2 — RL necessity

**Status: ROUGH SMOKE PASS / FORMAL G2 PENDING.** An equal-budget three-seed smoke produced mean upstream margins `0.000` (`gamma=0`) and `0.900` (`gamma=0.9`), with evaluation success `0.504` and `1.000`. This supports continuing prototype work, but it is not the preregistered formal G2 result.

- A hand-checkable delayed-credit scenario is present.
- `gamma=0` cannot establish a positive upstream action-value margin from terminal-only reward.
- `gamma>0` propagates terminal success to the necessary earlier authorization action.
- Evaluation reports success, return, and action-value margin with fixed seeds and identical budgets.
- If the sequential policy does not show a stable advantage, stop before Deep RL and revise the environment/scenarios.

### G3 — Held-out context pilot

**Status: PARITY / FROZEN RUN COMPLETE.** The exact all-40 split used 24 train,
eight validation, and eight test scenarios with seeds 17/29/43. DDQN and Rule
both reached test macro protocol success `0.875`; DDQN passed all core and
safety checks but had zero advantage margin and zero paired seed wins. Preserve
`results/increment7_paired_v0` and prefer Rule for this suite. Do not tune,
reseed, rerun, or claim statistical significance, Deep-RL superiority,
population generalization, or deployment readiness.

## Frozen implementation assumptions

1. User permission choice is authoritative for grant type: `allow_once` creates one-time authority and `allow_reuse` creates reusable authority. The controller requests a scope, not an enforceable grant type.
2. `REQUEST_REFRESH` creates a new pending/request and then a new authorization record; it never enlarges or revives the previous record in place.
3. `ESCALATE` and `DENY_WITH_REASON` are terminal. They earn 1 only when the scenario manifest pre-registers that terminal outcome as safe-impossibility success; otherwise 0.
4. A fallback earns 1 only when a scenario contains a pre-registered, non-negotiated fallback operation and its postcondition is completed with valid authority.
5. v0 authority and public interaction history reset at episode boundary. Cross-session persistence is deferred.
6. The reference monitor remains mandatory even when the action mask hides an invalid execution.

## Documentation contract

- Decisions and assumptions: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`.
- Progress, tests, errors, and deviations: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`.
- Interruption/restart source of truth: `docs/CONTINUATION_CHECKPOINT.md`; update it at RED, GREEN, review, and handoff boundaries.
- Parameters: versioned config in the code project; Markdown explains rationale and links to config.
- Every experiment run writes a manifest containing config/schema hashes, seeds, platform, Python version, status, and metrics.

## Errors encountered

- 2026-08-18: the first Increment 8 spec read attempted the retired `shell_command` nested tool name and made no filesystem change. Resolution: switch to the currently exposed `exec_command` tool before continuing; the spec-writing boundary was unaffected.
- 2026-08-18: the Increment 8 design continuation initially referenced the old `openai-bundled` Superpowers cache path, so two skill files were not found. Resolution: use the current `openai-curated-remote/superpowers/6.2.0` path; both required skill files were then read successfully before continuing.

- 2026-08-17: root `git status` failed because `Week67/.git` is not a valid repository. Resolution: work directly in the user-approved folder, preserve all unrelated files, and use file inventories plus independent reviews instead of Git diffs/commits.
- 2026-08-17: Increment 0 initial review returned `Spec FAIL / Changes requested` because the first contract was too shallow for authority semantics. Resolution: two TDD fix/re-review rounds added eight-field immutable scopes, executable traces, a bound visibility firewall, complete statuses, and valid broadening/reuse fixtures.
- 2026-08-17: Increment 1 initial review found replay lifecycle and multi-grant selection gaps. Resolution: two TDD fix rounds added explicit authorization-ID reservation, ambiguity fail-closed, append-only event chaining, exact replay invariants, monotonic logical time, same-step settlement, episode-bound preferences, and expiry-aware summaries. The unkeyed hash chain is explicitly not claimed as hostile-storage authentication.
- 2026-08-17: Increment 2A required two security fix rounds. Reviews found a reproducible permit secret, unauthenticated/pre-bind task receipts, incomplete unknown-effect settlement, and an unprotected-path time-validation gap. Resolution: non-derivable HMAC capabilities, monitor-bound receipts, absorbing unknown state, correlated attempt/call audits, and uniform logical-step checks. Final review: `Spec PASS / Quality APPROVED`; fresh suite 70/70.
- 2026-08-17: Increment 2B initial review found that a typed but contradictory `TaskSnapshot` and self-consistent yet semantically incomplete audits could obtain reward 1. The repair added exact step/effect/audit bijection, complete snapshot invariants, semantic authorization-event replay/correlation, exact completion paths, and causal digest binding.
- 2026-08-17: Increment 2B passed after three TDD/re-review rounds. The final evaluator replays ordered TaskEngine state, uniquely consumes replay-valid ledger settlements, validates all disposition/time/path invariants, binds the causal digest, and fails malformed inputs closed. Final review: `Spec PASS / Quality APPROVED`; fresh suite 110/110.
- 2026-08-17: Task 3B2A initially passed 20 focused tests but independent review showed that fully rehashed Boolean values could occupy execution/auth string slots and a callable dataclass could survive inside private tool detail. Resolution: exact per-slot schemas, one shared canonical scope validator, a normalized JSON-only payload domain, and 72 RED attack cases. Final review: `Spec PASS / Quality APPROVED`; reviewer rejected 122/122 adversarial variants; root fresh focused 24/24, full 198/198, and clean `compileall`.
- 2026-08-17: Increment 3B2 was closed at a user-authorized minimal prototype boundary: schema-first validation, one canonical/default environment/reset, recorded action-index replay, exact closure, resealing, and whole-trace equality. Three focused tests pass. The five B2B1 adversarial RED findings and configurable/live factory verification remain explicitly deferred; no hardened/full-suite claim is made.
- 2026-08-18: Increment 5 focused TDD produced the required missing-API RED, then two tests passed with the frozen short configuration. The default three-seed result was DDQN `1.000`, Random `0.2333`, Rule `1.000`, and Tabular-Q `1.000`, with zero DDQN evaluation invalid selections and unauthorized committed effects. All four `rough_v0` checks passed. The first default invocation's stdout was lost by an orchestration wrapper; one identical root-authorized recovery run captured the result without any parameter change.

## Status

**Increment 7 complete — unique frozen run PARITY.** Task 5 independent review records `Run integrity: PASS / Result interpretation: APPROVED`. The single seeds-17/29/43 run is preserved in `results/increment7_paired_v0/`; its formal report is `docs/implementation_reports/task-7-heldout-context-report.md`. DDQN and Rule both reached test macro protocol success `0.875`, so Rule remains preferred and no Deep-RL advantage is claimed. Do not tune, reseed, rerun, replace, or reuse the frozen test split for model development. The recommended next research step is a new preregistered study of the shared `f2_disable_refresh` failure or genuinely new context variation, while retaining the deferred B2B1/B2B2 hardening facts and all broader generalization/deployment claim boundaries.

## Active Increment 8 design work

- [x] Preserve Increment 7 artifacts and declare them immutable inputs.
- [x] Diagnose the shared `f2_disable_refresh` failure and distinguish representation, reward-credit, and scenario-coverage causes.
- [x] Compare 2–3 long-horizon scenario designs and select one minimal research prototype.
- [x] Obtain the user's consolidated approval of the independently reviewed bilingual design spec (received 2026-08-26).
- [x] Write the Phase A implementation plan after approval: `docs/superpowers/plans/2026-08-26-increment8-phase-a-preflight-plan.md`.
- [x] Implement Task 8C with a witnessed RED/GREEN cycle.
- [x] Implement Task 8D lifecycle model, directive FSM, accounting, and outcome wrapper.
- [x] Implement Task 8E authority-backed environment and public observation/encoder v2.
- [ ] Complete Task 8F exact reachability, Markov/firewall certification, DP oracle, and counterfactual manifest (**paused: frozen `0.85` DP gate is provably unreachable**).
- [ ] Complete the remaining Phase A preflight tasks and independent review before writing the Phase B full-run plan.

**Current status:** Increment 8 v0 remains immutable and `INVALID_RUN_BLOCKED`. The exposure-only `s3_v9` repair remains an exact `CERTIFIED_FAIL` at `45569/125000`; the separately approved target-reduction candidate is an exact key-graph `CERTIFIED_PASS` at `7953/10000`. Task 8V1A-P remains **BLOCKED** because `s3_v3=13/25 < 3/5`. The subsequent isolated terminal-cache-bypass diagnostic resolved the separate v4 computational unknown: exact controls matched and `s3_v4=1` was certified with 193,537 cached nonterminal rows under the revised accounting domain. This does not repair v3 or pass the Family-3 gate, so all-forty was not run. Tasks 8V1A-D, 8V1B, 8V1C, smoke, training, validation, and official test remain blocked pending a separately approved Family-3 v2 task-definition revision. Increment 8 is not complete.
