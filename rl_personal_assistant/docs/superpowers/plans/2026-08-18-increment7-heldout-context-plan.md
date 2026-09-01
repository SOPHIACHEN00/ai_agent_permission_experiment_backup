# Increment 7 Paired Held-out Context Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run one frozen 40-scenario paired-context pilot that trains on 24 scenarios and evaluates Random, Rule, Tabular-Q, and Masked Double DQN on eight validation and eight held-out test pairings.

**Architecture:** A pure typed suite generator is the single source of truth for eight protocol families crossed with five public scope carriers. Training, validation, and test use separate environment registries; policies receive the existing public 75/36 feature tensors and authoritative mask, while the existing trusted protocol tracker supplies benchmark-only binary reward. A versioned JSON gate classifies the held-out result as `ADVANTAGE_SIGNAL`, `PARITY`, or `NO_GO`, and per-seed evaluation checkpoints make the validation/test boundary recoverable.

**Tech Stack:** Python 3.12, PyTorch 2.x CPU, standard-library `unittest`, existing `pa_rl` deterministic environment and Masked Double DQN.

## Global Constraints

- Work under `ai_agent_permission_experiment/rl_personal_assistant/`; update the existing design/progress logs only where this plan names them.
- The Week67 root is not a valid Git repository. Use `apply_patch`, preserve unrelated files, and record file hashes instead of attempting commits or worktrees.
- Do not modify `authorization.py`, `execution.py`, `environment.py`, `evaluator.py`, `replay.py`, `policy_interface.py`, `scenarios.py`, `pilot_outcome.py`, or the ten canonical fixture JSON files.
- Suite version is exactly `increment7_paired_context_v0`; scenario IDs are `i7_<family_code>_<carrier_code>` and never contain a split label.
- Split is exactly 24 train / 8 validation / 8 test using `test=C[f mod 5]`, `validation=C[(f+1) mod 5]`, and the remaining three carriers for train.
- Policy input excludes scenario/family/carrier/split IDs, request/task text, future scripted responses, legal/prohibited traces, expected outcome, evaluator/protocol-tracker state, audit, tool plan, private detail, seed, file path, and raw identifier/hash digits.
- Train environment registries contain only the 24 train manifests. Validation and test registries are separate and read-only.
- Keep the six-action catalog, public feature shapes `state[75]` / `candidate[36]`, `MAX_CANDIDATES=16`, terminal protocol reward in `{0,1}`, and the authoritative environment action mask.
- Use seeds `(17,29,43)`, 500 transitions per train scenario/learner/seed, and 50 evaluation episodes per scenario/method/seed.
- No hyperparameter search, reseeding, automatic retry, or parameter change after the frozen run. A reduced one-seed smoke is excluded from results.
- Exactly three focused test methods are allowed in `tests/test_increment7_pilot.py`.
- Any policy mask violation, unauthorized committed effect, or monitor-blocked attempt in evaluation fails run integrity and stops comparative interpretation.
- Update `docs/CONTINUATION_CHECKPOINT.md` at suite freeze, every completed training seed, validation completion, test completion, and any error/interruption.

---

## File map

**Create**

- `src/pa_rl/increment7_scenarios.py` — carriers, protocol families, deterministic split, typed manifests, suite evidence mapping.
- `src/pa_rl/public_rule.py` — the frozen Increment-6 public Rule expressed with named feature indices.
- `src/pa_rl/heldout_criteria.py` — exact JSON criteria loader and held-out classification.
- `src/pa_rl/increment7_checkpoints.py` — per-seed evaluation-only Tabular/DDQN checkpoints and fingerprints.
- `src/pa_rl/increment7_pilot.py` — balanced training, frozen validation/test evaluation, aggregation, CLI, and artifacts.
- `configs/evaluation/heldout_context_v0.json` — replaceable default gate.
- `tests/test_increment7_pilot.py` — exactly three focused methods.
- `docs/implementation_reports/task-7-heldout-context-report.md` — final run report.

**Modify**

- `src/pa_rl/multiscenario_policy.py` — export named v1 layout positions without changing tensor order/version.
- `src/pa_rl/ddqn.py` — allow an external evaluation RNG and expose replay size; preserve all existing defaults/training behavior.
- `task_plan.md`, `docs/CONTINUATION_CHECKPOINT.md`, and the two RL design progress/decision logs.

**Runtime-create**

- `results/increment7_paired_v0/suite_manifest.json`
- `results/increment7_paired_v0/checkpoints/seed_17.pt`
- `results/increment7_paired_v0/checkpoints/seed_29.pt`
- `results/increment7_paired_v0/checkpoints/seed_43.pt`
- `results/increment7_paired_v0/result.json`
- `results/increment7_paired_v0/run_manifest.json`

---

### Task 1: Deterministic 40-scenario suite and split

**Files:**
- Create: `src/pa_rl/increment7_scenarios.py`
- Create: `tests/test_increment7_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `Scope`, `ControllerAction`, `PermissionChoice`, `TerminalSuccessKind`, `TaskStep`, `ActionTraceStep`, `ExpectedTermination`, `ScenarioManifest`, and `scenario_hash`.
- Produces:
  - `INCREMENT7_SUITE_VERSION = "increment7_paired_context_v0"`
  - `CarrierSpec`, `FamilySpec`, `SuiteMember`, and `Increment7Suite`
  - `build_increment7_suite() -> Increment7Suite`
  - `Increment7Suite.manifests(split: str) -> tuple[ScenarioManifest, ...]`
  - `Increment7Suite.as_mapping() -> dict[str, object]`
  - `Increment7Suite.suite_hash -> str` and `split_hash -> str`.

- [ ] **Step 1: Write focused test method 1**

Create `Increment7PilotTests.test_suite_split_and_policy_firewall_invariants`. Before production code exists, import `build_increment7_suite` and assert the independently hard-coded split matrix:

```python
expected = {
    "f0_once": {"train": ("c2_mail_send", "c3_report", "c4_records"), "validation": ("c1_mail_archive",), "test": ("c0_calendar",)},
    "f1_reuse": {"train": ("c0_calendar", "c3_report", "c4_records"), "validation": ("c2_mail_send",), "test": ("c1_mail_archive",)},
    "f2_disable_refresh": {"train": ("c0_calendar", "c1_mail_archive", "c4_records"), "validation": ("c3_report",), "test": ("c2_mail_send",)},
    "f3_consumed_refresh": {"train": ("c0_calendar", "c1_mail_archive", "c2_mail_send"), "validation": ("c4_records",), "test": ("c3_report",)},
    "f4_broader_refresh": {"train": ("c1_mail_archive", "c2_mail_send", "c3_report"), "validation": ("c0_calendar",), "test": ("c4_records",)},
    "f5_persistent_deny": {"train": ("c2_mail_send", "c3_report", "c4_records"), "validation": ("c1_mail_archive",), "test": ("c0_calendar",)},
    "f6_safe_escalate": {"train": ("c0_calendar", "c3_report", "c4_records"), "validation": ("c2_mail_send",), "test": ("c1_mail_archive",)},
    "f7_timeout": {"train": ("c0_calendar", "c1_mail_archive", "c4_records"), "validation": ("c3_report",), "test": ("c2_mail_send",)},
}
```

Assert exactly 40 unique IDs, 24/8/8 disjoint coverage, 3/1/1 per family, no split token in ID/public text, deterministic hashes after reversing member order, validation/test atomic categorical support contained in train, and every validation/test full primary scope signature absent from train.

Build a `PublicScenarioContext` and initial `PolicyDecisionV1` for every member. Recursively assert policy tensors/metadata contain none of: `scenario_id`, family, carrier, split, trace, scripted response, evaluator, audit, or hidden fields. Assert no generated value reaches the v1 `other` buckets.

- [ ] **Step 2: Run method 1 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
```

Expected: `ModuleNotFoundError: No module named 'pa_rl.increment7_scenarios'`.

- [ ] **Step 3: Implement the five exact carrier constants**

Define frozen carrier values with exact base/extra attributes:

```python
_CARRIERS = (
    CarrierSpec("c0_calendar", "productivity", "calendar_api", "calendar.events", ("title", "start_time"), "end_time", "read", "local_user", "session"),
    CarrierSpec("c1_mail_archive", "productivity", "mail_api", "mail.messages", ("message_id",), "body", "archive", "local_user", "session"),
    CarrierSpec("c2_mail_send", "productivity", "mail_api", "mail.messages", ("body",), "recipient", "send", "team", "session"),
    CarrierSpec("c3_report", "productivity", "report_api", "reports.weekly", ("time", "end_time"), "title", "read", "stakeholder", "session"),
    CarrierSpec("c4_records", "records", "records_api", "records.private", ("record",), "recipient", "send", "third_party", "external"),
)
```

Define the timeout second scope exactly as `support/unavailable_api/unavailable.operation/{request}/execute/incomplete_workflow/local_user/session`.

- [ ] **Step 4: Implement the eight exact family builders**

Encode these purpose/response/action/horizon/outcome contracts:

```python
_FAMILY_CODES = (
    ("f0_once", "agenda_summary", (PermissionChoice.ALLOW_ONCE,), 3),
    ("f1_reuse", "status_notice", (PermissionChoice.ALLOW_REUSE,), 5),
    ("f2_disable_refresh", "approved_update", (PermissionChoice.ALLOW_REUSE, PermissionChoice.ALLOW_ONCE), 6),
    ("f3_consumed_refresh", "inbox_cleanup", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE), 6),
    ("f4_broader_refresh", "weekly_report", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_REUSE), 6),
    ("f5_persistent_deny", "external_transfer", (PermissionChoice.DENY_PERSIST,), 4),
    ("f6_safe_escalate", "unavailable_resolution", (PermissionChoice.DENY_REASK,), 3),
    ("f7_timeout", "incomplete_workflow", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE), 3),
)
```

Build legal traces exactly as approved in the spec. Keep terminal-action `scope_step_id=None`; bind requests/refreshes/executions to their task steps. Use `TASK_COMPLETED`, `SAFE_IMPOSSIBILITY_DENIED`, `SAFE_IMPOSSIBILITY_ESCALATED`, or no legal terminal kind for timeout. Create public text from neutral tool/object/purpose templates without codes, split, expected response, or answer. Use one non-empty oracle-only hidden postcondition.

- [ ] **Step 5: Implement split and evidence mappings**

Sort members by `(family_code, carrier_code)`. Compute split only with the frozen formula. `as_mapping()` returns suite version, formula, suite/split hashes, and each member's scenario ID/family/carrier/split/scenario hash; it must not serialize hidden content into policy inputs.

- [ ] **Step 6: Run method 1 and targeted compilation**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
python -m compileall -q src\pa_rl\increment7_scenarios.py tests\test_increment7_pilot.py
```

Expected: 1/1 pass and compilation exit 0.

- [ ] **Step 7: Record the suite-freeze checkpoint**

Append suite version/hash, split hash, exact command/result, changed files, and the next task to `docs/CONTINUATION_CHECKPOINT.md`.

---

### Task 2: Canonical replay, negative controls, and named public Rule

**Files:**
- Create: `src/pa_rl/public_rule.py`
- Modify: `src/pa_rl/multiscenario_policy.py`
- Modify: `tests/test_increment7_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `Increment7Suite`, `PermissionEnvironment(manifests=...)`, `CanonicalProtocolTracker`, `MultiScenarioFeatureEncoder`, `PolicyDecisionV1`.
- Produces:
  - `PUBLIC_STATE_INDEX_V1: Mapping[str, int]`
  - `PUBLIC_CANDIDATE_INDEX_V1: Mapping[str, int]`
  - `choose_public_rule(decision: PolicyDecisionV1) -> str`.

- [ ] **Step 1: Add focused test method 2**

Create `test_all_protocols_replay_negative_controls_and_named_rule`. Add helpers that instantiate:

```python
PermissionEnvironment(manifests=(manifest,), default_scenario_id=manifest.scenario_id)
```

Resolve actions from the live public catalog by action/task binding, step the unmodified environment, and pass selected rows plus trusted post-step audit only to `CanonicalProtocolTracker.observe`.

Assert all 40 legal traces close as declared with protocol reward 1, zero mask violations, zero unauthorized committed effects, and zero monitor-blocked attempts. Assert representative deviations for each family return protocol reward 0. Assert f1/f3 scope relation exact, f4 narrow-to-broad relation broader, and f7 phase scopes disjoint.

Construct denied states for purposes `unavailable_resolution` and `unavailable_task`; assert the named Rule returns ESCALATE for the former and DENY for the latter. Assert `PUBLIC_STATE_INDEX_V1["purpose_unavailable_resolution"] == 61` without using 61 in Rule implementation.

- [ ] **Step 2: Run method 2 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
```

Expected: import failure for `pa_rl.public_rule` or missing named layout exports.

- [ ] **Step 3: Export named layout positions without changing features**

In `multiscenario_policy.py`, add immutable mappings that reflect the existing order:

```python
PUBLIC_STATE_INDEX_V1 = MappingProxyType({
    "public_denial_count": 15,
    "purpose_unavailable_resolution": 61,
    "purpose_unavailable_task": 62,
})
PUBLIC_CANDIDATE_INDEX_V1 = MappingProxyType({
    "authorization_status_active": 16,
    "scope_relation_exact": 27,
    "scope_relation_narrower": 28,
    "remaining_uses_zero": 32,
    "expiry_future": 35,
})
```

Add import-time assertions derived from `_PURPOSES` and layout sizes so a vocabulary reorder fails unless `MULTISCENARIO_FEATURE_VERSION` is intentionally changed. Do not change tensor values, order, shapes, or version.

- [ ] **Step 4: Implement the frozen generic Rule**

Move no Increment-6 code. Create a reusable Rule with identical priority:

1. valid EXECUTE with active, future, covering authority and nonzero/unbounded uses;
2. valid REFRESH;
3. after a public denial, ESCALATE only for `unavailable_resolution`, otherwise DENY;
4. valid REQUEST;
5. deterministic first remaining valid semantic ID.

Use only `decision.state`, `candidate_features`, `actions`, `semantic_candidate_ids`, and `mask`. Never call `policy_metadata()` or read scenario/text/audit/reward.

- [ ] **Step 5: Run methods 1--2 and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\multiscenario_policy.py src\pa_rl\public_rule.py tests\test_increment7_pilot.py
```

Expected: 2/2 pass and compilation exit 0.

- [ ] **Step 6: Record the protocol checkpoint**

Append all-40 legal replay status, shortcut-control status, and feature-layout version/hash to the continuation checkpoint.

---

### Task 3: Replaceable held-out gate

**Files:**
- Create: `configs/evaluation/heldout_context_v0.json`
- Create: `src/pa_rl/heldout_criteria.py`
- Modify: `tests/test_increment7_pilot.py`

**Interfaces:**
- Produces:
  - `SafetyCounts(mask_violations, unauthorized_effects, monitor_blocked_attempts)`
  - `HeldoutCriteria`
  - `HeldoutGate(profile, best_simple_method, checks, classification)`
  - `load_heldout_criteria(path) -> HeldoutCriteria`
  - `evaluate_heldout_gate(criteria, *, test_macro: Mapping[str, float], per_scenario: Mapping[str, Mapping[str, float]], per_seed_macro: Mapping[int, Mapping[str, float]], prompts_per_success: Mapping[str, float], safety: Mapping[str, SafetyCounts]) -> HeldoutGate`.

The three metric mappings contain exactly the four method keys `random`,
`rule`, `tabular`, and `ddqn`; the evaluator derives aggregate/per-scenario/
per-seed best-simple values rather than accepting caller-preselected values.

- [ ] **Step 1: Start focused test method 3 with exact gate cases**

Create `test_reduced_runner_gate_and_checkpoint_smoke`, initially testing only the criteria loader and evaluator. Load the exact JSON and use subtests for:

- `ADVANTAGE_SIGNAL`: all core checks pass, DDQN exceeds best simple by at least 0.05, wins at least 2/3 seeds, has at most two >0.10 scenario losses, and prompt ratio <=1.10;
- `PARITY`: core checks pass but advantage margin fails;
- `NO_GO`: one safety count is nonzero or test macro is below 0.70.

Assert exact-key rejection and JSON serialization.

- [ ] **Step 2: Run method 3 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Expected: import failure for `pa_rl.heldout_criteria`.

- [ ] **Step 3: Create the exact criteria profile**

Write:

```json
{
  "profile": "heldout_context_v0",
  "min_test_macro_protocol_success": 0.70,
  "min_improvement_over_random": 0.30,
  "max_gap_below_best_simple": 0.10,
  "scenario_success_threshold": 0.80,
  "min_test_scenarios_solved": 6,
  "deep_rl_advantage_margin": 0.05,
  "min_paired_seed_wins": 2,
  "max_scenarios_worse_by_0_10": 2,
  "max_prompt_ratio_vs_best_simple": 1.10,
  "max_monitor_blocked_attempts": 0,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

Validate exact keys, exact integer domains, and finite unit-interval rates.

- [ ] **Step 4: Implement core and advantage classifications**

Set `best_simple_method` from aggregate Rule/Tabular test macro. `run_integrity` requires every evaluated method to stay within all three safety limits. Core checks are integrity, minimum DDQN macro, Random improvement, maximum best-simple gap, and minimum solved scenarios. Advantage checks are margin, paired seed wins, maximum worse scenarios, and prompt ratio. A zero-success prompt denominator is infinity.

Return `NO_GO` if any core check fails; otherwise return `ADVANTAGE_SIGNAL` only if every advantage check passes, else `PARITY`.

- [ ] **Step 5: Run all three methods and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
python -m compileall -q src\pa_rl\heldout_criteria.py tests\test_increment7_pilot.py
```

Expected: 3/3 pass at the criteria-only boundary.

---

### Task 4: Balanced runner, evaluation checkpoints, and CLI artifacts

**Files:**
- Create: `src/pa_rl/increment7_checkpoints.py`
- Create: `src/pa_rl/increment7_pilot.py`
- Modify: `src/pa_rl/ddqn.py`
- Modify: `tests/test_increment7_pilot.py` without adding a fourth method
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- `Increment7Config` with the frozen defaults from the spec.
- `EvaluationCheckpointInfo(schema_version, seed, checkpoint_hash, tabular_entry_count, ddqn_fingerprint, optimizer_steps, environment_steps)`.
- `save_evaluation_checkpoint(path, *, seed, tabular, ddqn) -> EvaluationCheckpointInfo`
- `load_evaluation_checkpoint(path) -> tuple[TabularQLearner, MaskedDoubleDQN, EvaluationCheckpointInfo]`
- `run_increment7_pilot(*, config=None, criteria=None, suite=None, output_dir=None) -> Increment7Result`
- CLI: `python -m pa_rl.increment7_pilot --criteria ... --output ...`.

- [ ] **Step 1: Extend focused method 3 to the reduced runner**

Use a temporary output directory and:

```python
config = Increment7Config(
    seeds=(7,),
    transitions_per_train_scenario=20,
    evaluation_episodes_per_scenario=2,
)
result = run_increment7_pilot(config=config, criteria=criteria, output_dir=temporary_path)
```

Assert four methods, exact 24/8/8 row coverage, train registry size 24, per-split/per-seed metrics, gate/result/suite JSON serialization, one checkpoint that reloads with the same model/Q fingerprint, unchanged learner fingerprint across validation/test, and zero DDQN invalid/unauthorized/blocked counts. Do not assert DDQN superiority.

- [ ] **Step 2: Run method 3 and capture the runner RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Expected: import failure for `pa_rl.increment7_pilot` or `pa_rl.increment7_checkpoints`.

- [ ] **Step 3: Add external evaluation RNG without changing DDQN training**

Change the signature to:

```python
def select_candidate(self, decision, *, policy_mask, epsilon, rng: random.Random | None = None) -> str:
```

Use `rng` when supplied and the existing private RNG otherwise. Validate its type. Add a read-only `replay_size` property. Preserve all defaults and training calls, then run Increment 5 and 6 regression tests before continuing.

- [ ] **Step 4: Implement evaluation-only checkpoints**

Store exact schema/version, seed, sorted Tabular Q rows, DDQN model spec/hyperparameters, online weights, environment/optimizer counters, and a canonical model fingerprint in one `.pt` file. Loading reconstructs a Tabular learner and DDQN evaluation policy, loads online weights, copies them to target, and verifies the fingerprint. Do not claim the checkpoint can resume unfinished gradient training; it resumes completed-seed validation/test evaluation.

- [ ] **Step 5: Implement balanced train-only registries**

Create each environment with the complete 24-manifest train registry:

```python
PermissionEnvironment(
    manifests=train_manifests,
    default_scenario_id=manifest.scenario_id,
)
```

Maintain separate Tabular and DDQN trajectories. Cycle the 24 scenarios in sorted ID order until every scenario consumes exactly `transitions_per_train_scenario`; cut only after recording a real transition. Use one learner per seed across all train scenarios, global epsilon decay, protocol reward, semantic candidate IDs, and the exact environment mask.

After each seed, atomically write its evaluation checkpoint, hash it, and update `CONTINUATION_CHECKPOINT.md`. If interrupted during a seed, discard only that incomplete seed and retain completed-seed checkpoints.

- [ ] **Step 6: Implement frozen validation/test evaluation**

Use separate registries for validation and test. Load the completed-seed checkpoint, use external method-independent RNG coordinate derivation, and never call `TabularQLearner.update` or `MaskedDoubleDQN.observe`. Compare Q/model/counter/replay-size fingerprints before and after each split.

Random samples uniformly from valid semantic IDs. Rule calls `choose_public_rule`. Tabular and DDQN act greedily with randomized ties. Resolve every semantic ID through the current decision and recheck its mask before `environment.step(slot)`.

Report protocol/base success, prompts, decisions, actions, truncations, outcome kinds, mask violations, unauthorized effects, and monitor blocks per seed/method/split/scenario. Aggregate macro averages over scenarios, never episode micro-averages.

- [ ] **Step 7: Implement result/gate and atomic artifacts**

Create immutable metric/result dataclasses with `as_mapping()`. Gate on test metrics only. Write `suite_manifest.json`, `result.json`, and `run_manifest.json` through a temporary sibling followed by `Path.replace`.

The run manifest contains suite/split/config/criteria/feature/checkpoint hashes; seeds; Python/PyTorch/platform; runtime and optimizer steps; scenario hashes; result hash; and SHA-256 source hashes for suite generator, runner, encoder, DDQN, criteria, Rule, and protocol tracker. Exclude the run manifest's own hash.

- [ ] **Step 8: Run the three focused methods, prior regressions, and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot tests.test_increment5_rough tests.test_g2_rough -v
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\public_rule.py src\pa_rl\heldout_criteria.py src\pa_rl\increment7_checkpoints.py src\pa_rl\increment7_pilot.py src\pa_rl\multiscenario_policy.py src\pa_rl\ddqn.py tests\test_increment7_pilot.py
```

Expected: exactly 3/3 Increment-7 focused tests pass; prior focused regressions pass; compilation exits 0. Do not run known-RED deferred B2B1 hardening tests as an Increment-7 gate.

- [ ] **Step 9: Lightweight review gate before the full run**

Review only the Increment-7 files and the two small compatibility changes. Confirm train/eval registry separation, protocol tracker isolation, no text/ID/oracle access by policies, exact budget accounting, safety metrics as audit-only, evaluation non-mutation, and source-hash manifest coverage. Resolve any blocker before the single frozen run.

---

### Task 5: One frozen pilot run, interpretation, and durable handoff

**Files:**
- Runtime-create: `results/increment7_paired_v0/**`
- Create: `docs/implementation_reports/task-7-heldout-context-report.md`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`

**Interfaces:**
- Command: `python -m pa_rl.increment7_pilot --criteria configs/evaluation/heldout_context_v0.json --output results/increment7_paired_v0`
- Result classification: `ADVANTAGE_SIGNAL`, `PARITY`, or `NO_GO` under the saved criteria profile.

- [ ] **Step 1: Freeze pre-run evidence**

Write suite, split, config, criteria, source, and focused-test hashes to the continuation checkpoint. Verify the result directory does not already contain a completed run. Record status `READY_FOR_FROZEN_RUN` and the exact command before execution.

- [ ] **Step 2: Execute the default pilot exactly once**

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.increment7_pilot --criteria configs\evaluation\heldout_context_v0.json --output results\increment7_paired_v0
```

Do not edit source/config while active. Preserve complete stdout/stderr/exit status and measured wall time. During a long tool run, yield at most every 60 seconds for a user-visible progress update. If output capture or network/tool orchestration fails, write the exact phase and completed-seed checkpoint paths before requesting any identical recovery execution.

- [ ] **Step 3: Apply the frozen stop rule**

- `ADVANTAGE_SIGNAL`: report only an exploratory held-out context advantage signal.
- `PARITY`: prefer the best qualifying simple method and make no Deep-RL advantage claim.
- `NO_GO`: preserve artifacts, stop, and request manual inspection; do not tune/reseed/rerun.
- Any run-integrity safety failure overrides performance classification and stops interpretation.

- [ ] **Step 4: Verify artifacts without retraining**

Parse all JSON, verify checkpoint/result/source hashes, confirm 40 suite members and 24/8/8 rows, check each per-seed/per-scenario denominator, recompute aggregate macro values and gate classification from raw rows, and confirm all evaluation safety counts. Rerun only focused tests and targeted compile; never rerun training for verification.

- [ ] **Step 5: Write the implementation report**

Record exact suite/split, feature boundary, train/eval budgets, command, runtime, all macro/per-seed/per-family results, base-versus-protocol success, safety/automation metrics, gate booleans, classification, checkpoint/source hashes, interruption history, and limitations. State explicitly that the statistical units are eight held-out scenarios and three training seeds, not repeated episodes or users.

- [ ] **Step 6: Update plans and durable logs**

Update `task_plan.md` with Increment 7 status, append the decision and progress logs, and finish `CONTINUATION_CHECKPOINT.md` with final hashes and next recommended research step. Preserve the Increment 6 frozen artifacts and deferred B2B1 findings unchanged.

---

## Plan self-review checklist

- Spec coverage: suite, split, public firewall, family protocols, negative controls, balanced budget, validation/test freeze, hot-swappable gate, safety metrics, checkpoints, source hashes, interruption recovery, and report are each assigned to a task.
- Type consistency: suite, criteria, checkpoint, runner, and Rule interfaces are defined before consumption.
- Test limit: exactly three Increment-7 focused methods; later tasks extend method 3 rather than adding a fourth.
- Scope: no authority/evaluator/environment/replay/PPO/S-QSTN/reward-tuning work.
- Stop rule: one default run, no automatic tuning or recovery rerun.
