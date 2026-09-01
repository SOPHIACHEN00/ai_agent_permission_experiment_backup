# Increment 6 Multi-scenario Full-action Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved ten-scenario, full-action protocol-compliance pilot without modifying the authority, reference-monitor, core evaluator, replay, or fixture kernel.

**Architecture:** A separate public policy projection exposes structured scope features while excluding scenario/oracle/audit data. A trusted pilot-only outcome tracker converts the existing base result plus canonical trace conformance into a binary protocol reward. Random, Rule, Tabular-Q, and a dimension-configurable Masked DDQN use identical full-catalog observations and the authoritative environment mask.

**Tech Stack:** Python 3.12, PyTorch 2.x CPU, standard-library `unittest`, existing `pa_rl` deterministic environment.

## Global Constraints

- Work only under `ai_agent_permission_experiment/rl_personal_assistant/` and the existing RL design/log folders.
- Use `apply_patch` for source, test, config, and Markdown edits; the Week67 root is not a valid Git repository, so do not commit or create a worktree.
- Do not modify `authorization.py`, `execution.py`, `environment.py`, `evaluator.py`, `replay.py`, `policy_interface.py`, `scenarios.py`, or canonical fixture JSON.
- Policy inputs must exclude scenario ID, legal/prohibited traces, scripted future responses, hidden postconditions, evaluator output, audit data, private tool detail, and raw ID/hash digits.
- Use the exact environment candidate catalog and mask; no scenario-specific or toy action filter.
- Keep protocol reward binary. Criteria are evaluation-only and must never affect training.
- Exactly three focused test methods are allowed in `tests/test_increment6_pilot.py`.
- Run the frozen default pilot once. If classification is `NO_GO`, record raw results and stop without changing features, seeds, budgets, thresholds, or hyperparameters.
- Preserve Increment-5 default DDQN behavior and its focused tests.

---

### Task 1: Public observation v1 and full-action semantic decision view

**Files:**
- Create: `src/pa_rl/multiscenario_policy.py`
- Create: `tests/test_increment6_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `project_public_observation(manifest)`, `EnvironmentObservation`, `PublicFeatureEncoder`, `canonical_hash`.
- Produces:
  - `PublicScenarioContext.from_public_projection(projection) -> PublicScenarioContext`
  - `MultiScenarioFeatureEncoder.encode(context, observation) -> PolicyDecisionV1`
  - `PolicyDecisionV1.resolve_slot(semantic_candidate_id) -> int | None`
  - constants `MULTISCENARIO_FEATURE_VERSION`, `STATE_DIM_V1=75`, `CANDIDATE_DIM_V1=36`, `MAX_CANDIDATES_V1=16`.

- [ ] **Step 1: Add focused test method 1**

Create `Increment6PilotTests.test_public_v1_full_mask_and_firewall` that loads all ten manifests, resets each environment, builds context only through `project_public_observation`, and asserts:

```python
self.assertEqual(tuple(decision.state.shape), (75,))
self.assertEqual(tuple(decision.candidate_features.shape), (len(observation.candidate_catalog), 36))
self.assertEqual(tuple(decision.mask.tolist()), observation.action_mask)
self.assertEqual(len(set(decision.semantic_candidate_ids)), len(decision.semantic_candidate_ids))
for semantic_id, slot in zip(decision.semantic_candidate_ids, decision.slot_indices):
    self.assertEqual(decision.resolve_slot(semantic_id), slot)
```

Recursively inspect `decision.policy_metadata()` and assert forbidden keys/values such as scenario IDs, `legal_action_trace`, `scripted_permission_responses`, `audit`, and hidden canaries are absent. Assert at least one reset has more than two mask-valid actions.

- [ ] **Step 2: Run the focused test to capture RED**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_public_v1_full_mask_and_firewall -v
```

Expected: import failure for `pa_rl.multiscenario_policy`.

- [ ] **Step 3: Implement the strict public projection**

Implement frozen dataclasses with deep CPU tensor snapshots. `PublicScenarioContext` accepts only the public projection and stores only request/task text plus task-step scopes; it must discard `scenario_id` before constructing policy metadata. Match the current scope by public `next_required_step_id` but never encode the ID.

Use the exact frozen state[75] and candidate[36] vocabularies from the approved spec. Unknown values go only to an explicit `other` bucket. Build semantic candidate IDs from action plus abstract public binding/status/grant/relation/use/expiry/reason/target categories; exclude slot and raw IDs. Reject duplicates.

`PolicyDecisionV1` stores semantic IDs, action values, slot indices, tensors, mask, and safe public metadata. `resolve_slot` returns a slot only for a unique current semantic ID.

- [ ] **Step 4: Run test method 1 and targeted compilation**

Run the focused command above and:

```powershell
python -m compileall -q src\pa_rl\multiscenario_policy.py tests\test_increment6_pilot.py
```

Expected: test method 1 passes; compilation exits 0.

- [ ] **Step 5: Record the RED/GREEN boundary**

Update `docs/CONTINUATION_CHECKPOINT.md` with the exact command, result, changed files, and next task. Do not add more tests.

---

### Task 2: Canonical protocol binary outcome tracker

**Files:**
- Create: `src/pa_rl/pilot_outcome.py`
- Modify: `tests/test_increment6_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: trusted `ScenarioManifest`, the selected candidate public row, base reward/flags, and post-step trusted audit mapping.
- Produces:
  - `CanonicalProtocolTracker(manifest: ScenarioManifest)`
  - `CanonicalProtocolTracker.observe(selected_row, *, base_reward, terminated, truncated, audit) -> ProtocolOutcome`
  - frozen `ProtocolOutcome(reward, base_reward, conforming_prefix, complete, expected_termination_matched, reason_code)`.

- [ ] **Step 1: Add focused test method 2**

Create `test_protocol_wrapper_rejects_shortcuts_and_accepts_canonical_traces`. Add small test helpers that resolve actions by public action/task binding, execute declared traces, and feed every selected row/result into a fresh tracker.

Assert:

```python
self.assertEqual(run_canonical(manifest).reward, 1)
self.assertEqual(run_shortcut("local_disable_revocation").reward, 0)
self.assertEqual(run_new_request_instead_of_refresh("consumed_one_time_refresh").reward, 0)
self.assertEqual(run_new_request_instead_of_refresh("broader_scope_refresh").reward, 0)
self.assertEqual(run_immediate_terminal("persistent_denial").reward, 0)
self.assertEqual(run_immediate_terminal("safe_impossibility_deny").reward, 0)
self.assertEqual(run_immediate_terminal("safe_impossibility_escalate").reward, 0)
```

All ten canonical traces must receive protocol reward 1. Scenario 10 must do so only with exact clean truncation.

- [ ] **Step 2: Run method 2 to capture RED**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_protocol_wrapper_rejects_shortcuts_and_accepts_canonical_traces -v
```

Expected: import failure for `pa_rl.pilot_outcome`.

- [ ] **Step 3: Implement trace conformance and oracle isolation**

Freeze expected signatures as `(ControllerAction, scope_step_id | None)` and expected permission choices inside the tracker. On every call, append the selected action signature, compare the entire observed sequence with the expected prefix, and return intermediate reward 0.

At closure:

- scenarios 1--9 require exact complete action trace, matching public/user permission choices reconstructed from trusted authorization audit events, base reward 1, `terminated=True`, and `truncated=False`;
- scenario 10 requires exact complete trace, matching responses, base reward 0, `terminated=False`, and `truncated=True`.

Any divergence returns reward 0 with a stable public-safe reason code. Do not expose the expected trace through any public method.

- [ ] **Step 4: Run methods 1--2 and compile**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_public_v1_full_mask_and_firewall tests.test_increment6_pilot.Increment6PilotTests.test_protocol_wrapper_rejects_shortcuts_and_accepts_canonical_traces -v
python -m compileall -q src\pa_rl\pilot_outcome.py tests\test_increment6_pilot.py
```

Expected: 2/2 pass; compilation exits 0.

- [ ] **Step 5: Update the checkpoint**

Record shortcut cases, canonical conformance results, and the next exact action.

---

### Task 3: Dimension-configurable DDQN with Increment-5 compatibility

**Files:**
- Modify: `src/pa_rl/ddqn.py`
- Test: `tests/test_increment5_rough.py`
- Test: `tests/test_increment6_pilot.py` (do not add a fourth method)

**Interfaces:**
- Produces `DDQNModelSpec(state_dim=23, candidate_dim=16, max_candidates=16)`.
- `CandidateQNetwork(model_spec: DDQNModelSpec | None = None)` preserves old defaults.
- `MaskedDoubleDQN(..., model_spec: DDQNModelSpec | None = None)` accepts `PolicyDecisionV1` through a structural decision protocol.

- [ ] **Step 1: Generalize dimensions without changing learning semantics**

Replace hard-coded network input/padding dimensions with `DDQNModelSpec` values. Keep Increment-5 defaults, optimizer behavior, masked selection, replay snapshots, Double-DQN target, terminal no-bootstrap logic, and target-copy schedule unchanged.

Do not add a new registry, framework dependency, checkpoint format, or network architecture.

- [ ] **Step 2: Run the Increment-5 regression and existing Increment-6 tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough tests.test_increment6_pilot -v
```

Expected: the existing two Increment-5 tests and current two Increment-6 tests pass.

- [ ] **Step 3: Compile the modified learner**

Run:

```powershell
python -m compileall -q src\pa_rl\ddqn.py src\pa_rl\multiscenario_policy.py src\pa_rl\pilot_outcome.py
```

Expected: exit 0.

---

### Task 4: Hot-swappable gate and full-action four-policy runner

**Files:**
- Create: `configs/evaluation/multiscenario_v0.json`
- Create: `src/pa_rl/multiscenario_criteria.py`
- Create: `src/pa_rl/increment6_pilot.py`
- Modify: `tests/test_increment6_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- `load_multiscenario_criteria(path) -> MultiScenarioCriteria`
- `evaluate_multiscenario_gate(...) -> MultiScenarioGate`
- `Increment6Config` with the frozen defaults from the spec.
- `run_increment6_pilot(config=None, criteria=None) -> Increment6Result`.

- [ ] **Step 1: Add focused test method 3**

Create `test_reduced_multiscenario_runner_smoke` with seed `(7,)`, 80 transitions per scenario, and 5 evaluation episodes per scenario. Assert:

- exactly Random, Rule, Tabular-Q, and DDQN are returned;
- each has ten per-scenario rows;
- result and gate mappings are JSON serializable;
- DDQN mask violations and unauthorized committed effects are zero;
- the criteria file loads exactly;
- no performance superiority assertion is made in this reduced smoke.

- [ ] **Step 2: Run method 3 to capture RED**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_reduced_multiscenario_runner_smoke -v
```

Expected: missing runner/criteria import failure.

- [ ] **Step 3: Implement criteria and classifications**

Create the exact JSON profile from the spec. Validate exact keys and numeric domains. Compute macro DDQN/Random/Rule/Tabular protocol success, per-scenario solved count, best-simple gap, and safety counts. Return every Boolean check plus `ADVANTAGE_SIGNAL`, `PARITY`, or `NO_GO`.

- [ ] **Step 4: Implement the balanced runner**

Use all ten canonical manifests. For Tabular and DDQN, maintain one learner per seed across scenarios and cycle scenarios round-robin until each has consumed its exact transition quota. Training uses protocol reward; evaluation records protocol reward and base reward separately.

Policy details:

- Random samples uniformly from mask-valid semantic IDs.
- Rule follows only the public priority frozen in the spec.
- Tabular uses `canonical_hash(tuple(float(x) for x in decision.state.tolist()))` and semantic IDs.
- DDQN uses `DDQNModelSpec(75,36,16)` and the exact environment mask.

At the action boundary, resolve the selected semantic ID through the current decision and verify the current environment mask before calling `step(slot)`. Count any failed resolution as a mask violation and fail the episode closed.

Trusted post-step audit may be read only for metrics: unauthorized committed effects, monitor blocks, public prompts, and outcome kind. Never feed it into a policy update.

- [ ] **Step 5: Run all three tests and targeted compilation**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot -v
python -m compileall -q src\pa_rl\multiscenario_policy.py src\pa_rl\pilot_outcome.py src\pa_rl\multiscenario_criteria.py src\pa_rl\increment6_pilot.py src\pa_rl\ddqn.py tests\test_increment6_pilot.py
```

Expected: exactly 3/3 Increment-6 tests pass; compilation exits 0.

- [ ] **Step 6: Run targeted backward regressions**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough tests.test_g2_rough -v
```

Expected: 4/4 prior rough tests pass. Do not run the known-RED B2B1 hardening suite as an Increment-6 gate.

---

### Task 5: Frozen pilot execution, report, and durable handoff

**Files:**
- Runtime-create: `results/increment6_multiscenario_v0/result.json`
- Runtime-create: `results/increment6_multiscenario_v0/run_manifest.json`
- Create: `docs/implementation_reports/task-6-pilot-report.md`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`

**Interfaces:**
- CLI: `python -m pa_rl.increment6_pilot --criteria configs/evaluation/multiscenario_v0.json --output results/increment6_multiscenario_v0`
- Artifacts contain config/version hashes, seeds, Python/PyTorch/platform, runtime, optimizer steps, per-seed/per-scenario metrics, aggregate metrics, gate checks, result classification, and SHA-256 file manifest.

- [ ] **Step 1: Execute the frozen default pilot exactly once**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.increment6_pilot --criteria configs\evaluation\multiscenario_v0.json --output results\increment6_multiscenario_v0
```

Do not change code/config while the run is active. Capture the entire command result, exit status, and wall-clock time. If output capture fails, do not silently rerun; record the failure and request explicit root authorization for an identical recovery run.

- [ ] **Step 2: Apply the stop rule**

- `ADVANTAGE_SIGNAL`: record an exploratory advantage signal only.
- `PARITY`: mark the pipeline functional and explicitly prefer the best simple baseline for the current deterministic suite.
- `NO_GO`: preserve artifacts and stop without tuning; request human inspection.

- [ ] **Step 3: Write the implementation report**

Document exact modules, feature vocabularies, protocol reward semantics, fixed budgets, raw per-seed/per-scenario metrics, action coverage, base-versus-protocol success, safety/automation diagnostics, classification checks, runtime, commands, errors, and claim limitations.

- [ ] **Step 4: Update plans and durable logs**

Mark Task 6C/6D accurately. Record the wrapper as a temporary benchmark oracle, the absence of held-out generalization, the known B2B hardening debt, every changed file/hash, and the next human decision. If the run is interrupted, update the continuation checkpoint before any restart.

- [ ] **Step 5: Final verification without retraining**

Rerun only the three focused tests, the four prior rough regressions, and targeted `compileall`. Validate saved JSON files parse and their recorded SHA-256 values match. Do not rerun the default training experiment.

