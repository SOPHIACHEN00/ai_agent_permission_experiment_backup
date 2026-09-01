# Increment 8 Phase A Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and certify the Increment 8 stochastic budgeted-lifecycle research environment through the reduced preflight boundary, without starting the frozen five-seed experiment.

**Architecture:** A new research-only lifecycle layer owns the stochastic workload, public budgets, directive state, and terminal outcome while reusing the existing typed `Scope`, `AuthorizationService`, `ReferenceMonitor`, `MockTool`, and semantic six-action vocabulary. A pure exact-rational model is the source of truth for graph generation, DP, and Markov certification; an authority-backed environment implements the same transition contract and exposes a strictly public observation-v2 decision. Phase A ends after the three frozen focused tests and an independent synthetic smoke-only run pass; the full training/evaluation runner is a separate Phase B plan.

**Tech Stack:** Python 3.12, standard-library dataclasses/enums/Fraction/hashlib/json, NumPy/PyTorch already present in the project, `unittest`, existing `pa_rl` authority/monitor/DDQN modules.

**Spec:** `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design_zh.md` and synchronized English counterpart.

## Global Constraints

- Suite/version names are exactly `increment8_budgeted_lifecycle_v0`, `public_budgeted_lifecycle_v2`, and `budgeted_lifecycle_v0`.
- Preserve all Increment 7 source, checkpoints, results, and frozen test artifacts; do not import its test split into smoke or training.
- Keep the existing six `ControllerAction` values; add no WAIT, CLARIFY, or new controller slot.
- Policy input and replay exclude scenario/family/carrier/topology/graph/split IDs, audit, evaluator/DP values, future draws, raw ID/hash numerics, and terminal feasibility.
- Candidate count is at most 16; active authorization count is at most three; raw authorization IDs are equality/join handles only.
- Terminal learning reward is binary with no shaping.
- All stochastic probabilities and certification calculations use exact `Fraction`; rollout sampling uses the frozen stateless SHA-256 coordinates.
- The three focused pre-run test methods are the only Increment 8 focused methods; use `subTest` blocks rather than creating extra methods.
- No official validation/test rollout, five-seed training, result directory, or `TEST_STARTED_FROZEN` marker is created in Phase A.
- The repository has no valid Git worktree. Preserve unrelated files and record file hashes/checkpoints instead of commit steps.

---

### Task 1: Frozen Typed Suite and Split Generator

**Files:**
- Create: `src/pa_rl/increment8_suite.py`
- Create: `tests/test_increment8_preflight.py`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `Scope`, `canonical_hash`, and the five public carrier definitions mirrored from the approved Increment 7 carrier vocabulary.
- Produces: `LikelihoodLevel`, `LifecycleGraphRole`, `LifecycleGraphSpec`, `Increment8SuiteMember`, `Increment8Suite`, and `build_increment8_suite() -> Increment8Suite`.

- [x] **Step 1: Write the failing suite/split test**

```python
class Increment8PreflightTests(unittest.TestCase):
    def test_suite_split_markov_and_firewall(self) -> None:
        suite = build_increment8_suite()
        self.assertEqual(len(suite.members), 48)
        self.assertEqual(suite.split_counts(), {"train": 24, "validation": 8, "test": 16})
        self.assertEqual(suite.role_split_counts(), {
            "strategic": {"train": 20, "validation": 8, "test": 12},
            "mandatory": {"train": 4, "validation": 0, "test": 4},
        })
        self.assertEqual(len({m.graph.graph_id for m in suite.members}), 48)
        self.assertEqual(tuple(m.graph.graph_id for m in suite.members), tuple(sorted(m.graph.graph_id for m in suite.members)))
```

- [x] **Step 2: Run the single focused method and verify RED**

Run: `$env:PYTHONPATH='src'; python -m unittest tests.test_increment8_preflight.Increment8PreflightTests.test_suite_split_markov_and_firewall -v`

Expected: import failure for `pa_rl.increment8_suite`.

- [x] **Step 3: Implement exact typed graph inputs**

Implement strict frozen dataclasses whose constructors reject bool-as-int, unknown likelihood/role/split values, noncanonical scopes, invalid horizon/budgets, and mismatched graph IDs. `build_increment8_suite()` must generate exact strategic IDs `i8_s<f>_v<v>` and mandatory IDs `i8_m_v<v>`, exact parameter rows/family transforms, neutral purposes, carrier rotation, and 24/8/16 assignments from the spec.

- [x] **Step 4: Extend the same test with exact vectors and leakage invariants**

Assert every strategic and mandatory row against independent formulas; assert split-disjoint IDs, family counts, purpose crossing, public vocabulary coverage, no split token in policy-visible graph parameters, deterministic suite/split hashes, and construction independence from caller ordering.

- [x] **Step 5: Run GREEN and targeted compile**

Run the single method above, then `python -m compileall -q src/pa_rl/increment8_suite.py tests/test_increment8_preflight.py`.

- [x] **Step 6: Record the RED/GREEN boundary**

Update `task_plan.md` and `docs/CONTINUATION_CHECKPOINT.md` with approval, exact commands, outcomes, suite/split hashes, and the next task. Do not claim topology/Markov certification yet.

---

### Task 2: Exact Lifecycle State, Directive FSM, Accounting, and Outcome

**Files:**
- Create: `src/pa_rl/increment8_model.py`
- Modify: `tests/test_increment8_preflight.py`

**Interfaces:**
- Consumes: `LifecycleGraphSpec`, `Scope`, `ControllerAction`, `AuthorizationStatus`, `GrantType`, and `Fraction`.
- Produces: `PublicDirectiveState`, `LifecycleAuthorization`, `LifecycleTask`, `LifecycleState`, `LifecycleCandidate`, `LifecycleTransition`, `LifecycleModel.initial_state()`, `.candidates()`, `.transition_distribution()`, and `.sample_transition()`.

- [x] **Step 1: Write failing lifecycle-accounting subtests**

```python
def test_hand_checkable_lifecycle_accounting(self) -> None:
    model = LifecycleModel()
    state = model.initial_state(mandatory_graph)
    state = choose(model, state, ControllerAction.REQUEST_AUTHORIZATION)
    self.assertEqual(state.prompts_used, 1)
    self.assertEqual(state.directive.state, "disable_required")
    self.assertGreater(state.exposure_used, 0)
    self.assertFalse(model.is_success(state))
```

Add independent paths for reusable exposure persistence, one-time consumption, revoked exposure zero, prompt counting, utility credit once, budget overflow, early DENY/ESCALATE reward zero, and two different constraint-valid strategic success paths.

- [x] **Step 2: Verify RED**

Run only `test_hand_checkable_lifecycle_accounting`; expect missing model import/type failure.

- [x] **Step 3: Implement immutable state and exact global kernel**

Use `Fraction(1,5)`, `Fraction(1,2)`, and `Fraction(4,5)` for low/medium/high. Only committed execution draws EXACT/BROADER/DISJOINT; request/refresh/disable hold the task. Update utility, prompt, interval exposure, forecast, task identity, credited-task set, and terminal flags in the exact spec order.

- [x] **Step 4: Implement the mandatory directive FSM**

The public objective starts as `reusable_then_one_time_replacement`; first request grants reusable and publishes a bound `disable_required/refresh_required` directive. Before verified disable, bound execute and superseding request/refresh candidates are masked. After disable, only refresh of the revoked bound grant is valid; fresh request remains masked. Expiry/consume/supersede/terminal-before-compliance closes with reward zero.

- [x] **Step 5: Implement binary outcome evaluation**

`reward=1` only when utility target, no pending task, accepted termination, prompt/exposure budgets, directive compliance, and all safety counts pass. Credit each task once. Strategic DENY/ESCALATE always returns zero.

- [x] **Step 6: Verify lifecycle GREEN**

Run the single lifecycle method and targeted `compileall` for model/test.

---

### Task 3: Authority-Backed Budgeted Lifecycle Environment

**Files:**
- Create: `src/pa_rl/increment8_environment.py`
- Modify: `tests/test_increment8_preflight.py`

**Interfaces:**
- Consumes: `LifecycleModel`, `AuthorizationService`, `TaskEngine`, `ReferenceMonitor`, `MockTool`, `ScriptedUserAdapter`-compatible public choices, and `ExecutionIntent`.
- Produces: `BudgetedLifecycleEnvironment.reset(graph_id, root_seed)`, `.step(slot_index)`, immutable `LifecycleObservation`, and `LifecycleInfo` with split public/audit mappings.

- [x] **Step 1: Add failing real-authority lifecycle subtests**

Execute one strategic request/execute path and one mandatory request/disable/refresh/execute path through the live environment. Assert ledger states, monitor disposition, utility/prompt/exposure, directive state, reward, closure, and zero unauthorized effects.

- [x] **Step 2: Verify RED**

Run the lifecycle method; expect missing `increment8_environment` import/API.

- [x] **Step 3: Implement authority composition**

Keep one `AuthorizationService`, `LifecycleTaskEngine(TaskEngine)`, `ReferenceMonitor`, and `MockTool` for the episode. Initialize the engine with `task_001`; after a committed task and workload draw, `install_next_task(TaskStep)` appends the unique next task while preserving prior statuses/effects and the bound monitor capability. The existing `TaskEngine.authoritative_step/apply_receipt/snapshot` and the single monitor audit chain remain authoritative. Request/refresh/disable use the ledger service and produce verified public lifecycle events. No direct protected effect mutation is allowed outside `ReferenceMonitor.execute`.

- [x] **Step 4: Implement dynamic candidates and guards**

Create at most one request, three execute, three refresh, three disable, one deny, and one escalate candidates. Apply issuance ordinals independent of authorization-ID content, exact selection/truncation order, unique semantic IDs, active-grant cap three, directive mask guards, and forced-index fail-closed behavior before ledger/tool mutation.

- [x] **Step 5: Verify authority-backed GREEN**

Run the lifecycle method, existing focused monitor/authorization regressions needed by touched interfaces, and targeted compile.

---

### Task 4: Public Observation V2 and Candidate-Scoring Encoder

**Files:**
- Create: `src/pa_rl/increment8_policy.py`
- Modify: `tests/test_increment8_preflight.py`

**Interfaces:**
- Consumes: `LifecycleObservation` only.
- Produces: immutable named layouts `PUBLIC_STATE_INDEX_V2`, `PUBLIC_CANDIDATE_INDEX_V2`, `PolicyDecisionV2`, and `BudgetedLifecycleFeatureEncoder.encode(observation) -> PolicyDecisionV2` compatible with `MaskedDoubleDQN`'s decision protocol.

- [x] **Step 1: Add failing observation/firewall assertions to focused method 1**

Assert fixed float32 shapes, at most 16 rows, exact environment mask equality, unique semantic IDs resolvable to current slots, and named indices for budgets, forecasts, directive, authorization lifecycle, recent-event projection, and current task utility/sensitivity.

- [x] **Step 2: Verify RED**

Run focused method 1; expect missing v2 encoder.

- [x] **Step 3: Implement a named, versioned v2 layout**

Encode normalized time/utility/budget scalars; exact categorical one-hots for forecasts/objective/directive; public scope vocabulary; lifecycle authorization aggregates; and four allowlisted recent-event records. Candidate rows encode action, binding role/rank, task relation, grant/status/relation/use/expiry/sensitivity/attribute-count/directive bits. Raw ID/hash bytes never become features.

- [x] **Step 4: Implement recursive firewall validation**

Reject forbidden keys/leaves and unsupported public event types. Add taint tests showing graph/family/split/oracle/audit/future-draw mutations cannot change state tensors, candidate tensors, masks, semantic candidate roles, or replay bytes.

- [x] **Step 5: Verify v2 GREEN and DDQN compatibility**

Run focused method 1 and a direct `DDQNModelSpec`/`MaskedDoubleDQN.select_candidate` smoke using the v2 dimensions and full mask.

---

### Task 5: Exact Enumeration, Markov Certification, and DP Oracle

**Files:**
- Create: `src/pa_rl/increment8_preflight.py`
- Modify: `tests/test_increment8_preflight.py`

**Interfaces:**
- Consumes: `Increment8Suite`, `LifecycleModel`, `BudgetedLifecycleFeatureEncoder`.
- Produces: `ReachabilityCertificate`, `MarkovCertificate`, `DPCertificate`, `CounterfactualManifest`, and `certify_increment8_inputs(suite) -> Increment8Certification`.

- [ ] **Step 1: Add failing certification assertions to focused method 1**

Assert all 48 finite reachable graphs enumerate; strategic split counts/topology hashes and held-out non-isomorphism pass; public-state and encoded-decision collisions have exact-equal kernels for every common semantic action; counterfactual sources exist and paired optimal-action sets are disjoint; DP strategic test expectation is at least 0.85.

- [x] **Step 2: Verify RED**

Run focused method 1; expect missing certification API.

- [x] **Step 3: Implement canonical BFS reachability**

Enumerate from the complete internal state using deterministic action/edge order, exact `Fraction` transitions, stable state mappings, and canonical BFS labels. Produce topology hashes after removing carrier/purpose/raw IDs.

- [x] **Step 4: Implement two-layer Markov checks**

Group by complete public projection, then by exact policy decision representation. For every shared semantic action compare exact distributions over next public/decision representation, reward, terminated, and truncated. Any mismatch raises before training.

- [ ] **Step 5: Implement finite-horizon DP and counterfactual manifest**

Compute exact values and full optimal-action sets, not a single canonical action. Build four ordered pairs for each of 12 strategic test graphs using the predeclared source predicate/interventions; validate internal consistency, equal ordered action roles/masks, and disjoint optimal sets.

- [ ] **Step 6: Verify certification GREEN**

**STOP result (2026-08-26):** certification cannot become GREEN under the frozen inputs. Exact work completed for 42/48 graphs with zero observed Markov/encoder/optimal-set mismatches, but the 12-graph strategic-test DP macro has a best-case upper bound `61261/80000 = 0.7657625 < 0.85`. The remaining six graphs and Steps 5–6 were stopped; see `docs/implementation_reports/task-8f-exact-stop-evidence.md`.

Run focused method 1 and serialize/reload the complete certification without float probability loss.

---

### Task 6: Eight-Method Synthetic Reduced Smoke

**Files:**
- Create: `src/pa_rl/increment8_smoke.py`
- Create: `src/pa_rl/increment8_ddqn.py`
- Modify: `tests/test_increment8_preflight.py`

**Interfaces:**
- Consumes: only an independent smoke-only registry, v2 decisions, existing candidate-scoring DDQN, and exact stateless RNG helpers.
- Produces: `Increment8SmokeResult` with eight method rows, gamma-pair fingerprints, finite-loss evidence, evaluation immutability digests, checkpoint round-trip evidence, and safety counts.

- [ ] **Step 1: Write failing reduced-smoke method**

```python
def test_reduced_end_to_end_smoke(self) -> None:
    result = run_increment8_smoke(root_seed=7)
    self.assertEqual(set(result.methods), {
        "random", "rule", "rule_fsm", "tabular_g0", "tabular_g095",
        "ddqn_g0", "ddqn_g095", "dp_oracle",
    })
    self.assertTrue(result.gamma_pair_initialization_equal)
    self.assertTrue(result.all_losses_finite)
    self.assertEqual(result.mask_violations, 0)
    self.assertEqual(result.unauthorized_effects, 0)
    self.assertFalse(result.loaded_official_validation_or_test_graph)
```

- [ ] **Step 2: Verify RED**

Run only the reduced-smoke method; expect missing smoke runner.

- [ ] **Step 3: Implement frozen stateless RNG helpers and policies**

Implement environment/action/replay/init coordinates exactly from spec in the new Increment 8 module. Reuse `DDQNModelSpec`, `CandidateQNetwork`, and `double_dqn_targets` as stable primitives, but do not modify frozen `ddqn.py`, `multiscenario_policy.py`, `increment7_pilot.py`, or Increment 7 checkpoints. Initialize gamma-paired Tabular tables identically at zero and DDQN online/target weights bit-for-bit identically. Evaluation uses epsilon zero, valid greedy actions, and only exact-maximizer tie draws.

- [ ] **Step 4: Implement smoke-only training/evaluation**

Use a separately constructed synthetic registry whose IDs/hashes cannot overlap the official 48 graphs. Exercise all eight methods with a tiny fixed transition budget, no superiority assertion, complete safety metrics, finite update checks, eval-only learner copies, immutable digest checks, and checkpoint reload fingerprints.

- [ ] **Step 5: Verify smoke GREEN and focused suite**

Run all three Increment 8 focused methods, then the narrow Increment 5/6/7 DDQN compatibility tests and targeted compileall.

---

### Task 7: Phase A Certification, Review Package, and Stop/Continue Decision

**Files:**
- Create: `configs/evaluation/budgeted_lifecycle_v0.json`
- Create: `docs/implementation_reports/task-8-phase-a-report.md`
- Create: `docs/superpowers/notes/2026-08-26-increment8-phase-a-implementation-notes.md`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`

**Interfaces:**
- Consumes: suite, certification, smoke, test, and compile evidence.
- Produces: durable Phase A input hashes and an explicit `PREFLIGHT_PASS` or `INVALID_RUN_BLOCKED` decision. It does not produce official policy results.

- [ ] **Step 1: Freeze exact hot-swappable criteria JSON**

Write the 17 exact fields from spec profile `budgeted_lifecycle_v0`; validate exact keys/types/ranges in the later Phase B criteria module, but bind the Phase A file hash now.

- [ ] **Step 2: Run the complete preflight verification**

Run exactly the three focused methods, relevant prior regressions, targeted compileall, forbidden-dependency scan, certification generation, and serialization round-trip. Record command, exit code, test count, runtime, and hashes.

- [x] **Step 3: Apply the scientific stop rule**

If suite/split, lifecycle accounting, firewall, Markov sufficiency, counterfactual construction, DP solvability, finite loss, safety, or reduced smoke fails, set `INVALID_RUN_BLOCKED`, preserve evidence, and stop for user discussion. Do not weaken the spec or start formal training.

- [x] **Step 4: Write report and durable checkpoint**

Document supported claims, forbidden claims, exact scope, all errors/fixes, and file hashes. Mark `PREFLIGHT_PASS` only with fresh evidence. State explicitly that no official validation/test or Deep-RL result exists.

- [ ] **Step 5: Request independent review before Phase B**

Review suite/kernel/firewall/Markov/DP and smoke evidence. Phase B full runner/training plan starts only after review `Spec PASS / Quality APPROVED`.

---

## Phase A Self-Review Checklist

- [ ] Every Increment 8 spec requirement needed before training maps to a task above.
- [ ] No official test rollout or five-seed training appears in Phase A.
- [ ] All new production behavior follows a witnessed RED then GREEN.
- [ ] Existing complete mediation is reused for protected effects.
- [ ] The exact model and authority-backed environment are cross-checked rather than independently invented.
- [ ] Policy/replay firewall is recursive and taint-tested.
- [ ] DP is a preflight oracle only and cannot select features/config/checkpoints.
- [ ] Failure at any preflight gate is durable and stops execution for user discussion.

## Status

**`INVALID_RUN_BLOCKED` at Task 5/8F.** Tasks 8C–8E are focused GREEN, but the frozen DP strategic-test threshold is provably unreachable (`macro <= 61261/80000 < 17/20`). Work stopped before counterfactual completion, smoke, training, validation, or official testing. Increment 7 remains immutable; user research direction is required before this plan resumes.
