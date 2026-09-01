# Increment 8 Family-3 v2 Exact Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and run only the approved ten-graph Family-3 v2 exact
preflight, producing a certificate or stopping on the first failed gate.

**Architecture:** Add an isolated, standard-library-only `family3_v2_*`
subsystem beside frozen Increment 8 v0/v1 code. A pure typed kernel supplies
exact transitions; a separate authority environment verifies real user/ledger/
monitor/tool mediation; exact observation audits and two independent solvers
feed one ordered, checkpointed twelve-gate runner.

**Tech Stack:** Python 3.12 standard library (`dataclasses`, `enum`, `fractions`,
`hashlib`, `json`, `sqlite3`, `ctypes`, `unittest`), plus existing project
authority/effect components. Do not import PyTorch in the v2 preflight import
graph.

**Spec:**
`docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` and
`docs/superpowers/specs/2026-08-27-increment8-family3-v2-design_zh.md`

## Global Constraints

- Suite version is exactly
  `increment8_family3_v2_forecast_scope_reservation_v0`; graph-row schema is
  `family3_v2_graph_row_v0`.
- Create only new `src/pa_rl/family3_v2_*.py` production modules. Do not modify
  any existing v0/v1 Python file, `__init__.py`, cache, certificate, or result.
- Reuse unchanged `ControllerAction`, `Scope`, `AuthorizationService`,
  `ReferenceMonitor`, `MockTool`, `covers`, and `relation`.
- Do not import or subclass `LifecycleModel`, `BudgetedLifecycleEnvironment`,
  `LifecycleObservation`, `BudgetedLifecycleFeatureEncoder`, or either old
  exact solver.
- Policy/preflight modules are standard-library-only and must not import
  `torch` or `increment8_policy`.
- Exact graph limits are 250,000 cached nonterminal states per graph and
  512 MiB process RSS. Limits are constants, not CLI options.
- The only permitted output root is
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight`.
  `--output-root` remains explicit for auditability, but its resolved path must
  equal that fixed project-relative directory or the runner fails before any
  write.
- Gate 6 RNG evidence uses frozen internal inputs `root_seed=17` and
  `episode_ordinal=0`, records them in `run_config.json`, and offers no CLI
  override. Original and forecast-counterfactual kernels must produce the same
  coupling UID, payload, accepted uint64, attempt, and residue.
- Every graph must return exact `V*=4/5`; first-request Q-values must be unique
  `{4/5,1/5}` with exact gap `3/5` in the forecast-specified order.
- The runner stops on the first schema, algebra, witness, binding,
  counterfactual, Markov, firewall, solver, value, safety, artifact, or resource
  failure. It must not continue to a later gate.
- Do not run the other forty strategic graphs, smoke training, learner
  training, validation, official test, parameter search, or baseline/DDQN
  comparison.
- Run one RED and one focused GREEN per task. If an expected RED has a different
  cause, or GREEN fails, write the exact checkpoint and stop for human review.
- No Git repository metadata is available in this workspace. Replace commit
  steps with atomic continuation-checkpoint updates and SHA-256 file records.

## File Structure

| File | Responsibility |
|---|---|
| `src/pa_rl/family3_v2_contracts.py` | Shared enums, profiles, operational request/response types |
| `src/pa_rl/family3_v2_suite.py` | Five copied carrier literals, ten graph rows, algebra, hashes, counterfactual wrapper |
| `src/pa_rl/family3_v2_rng.py` | Exact unbiased mod-5 counter-based branch residue |
| `src/pa_rl/family3_v2_outcome.py` | Strict natural-completion-only binary outcome |
| `src/pa_rl/family3_v2_model.py` | Pure finite-horizon state, seven-row catalog, exact transition kernel |
| `src/pa_rl/family3_v2_authority.py` | Deterministic reusable user and four-way scope-binding gateway |
| `src/pa_rl/family3_v2_policy.py` | Label-free public observation and exact tuple encoder |
| `src/pa_rl/family3_v2_environment.py` | Real ledger/monitor/tool mediated environment and runtime audit evidence |
| `src/pa_rl/family3_v2_audit.py` | Markov, firewall, binding, witness, no-repair, and safety audits |
| `src/pa_rl/family3_v2_exact_solver.py` | SQLite-backed value-first solver with state/RSS caps and root Q-values |
| `src/pa_rl/family3_v2_exact_reference.py` | Independent terminal-free bottom-up reference for v0/v1 |
| `src/pa_rl/family3_v2_artifacts.py` | Frozen-baseline verification, atomic evidence, gate checkpoint state machine |
| `src/pa_rl/family3_v2_preflight.py` | Fixed twelve-gate CLI orchestration and final verdict |

Focused tests are split by the same boundaries:

```text
tests/test_family3_v2_suite_rng.py
tests/test_family3_v2_model_outcome.py
tests/test_family3_v2_authority_environment.py
tests/test_family3_v2_policy_audit.py
tests/test_family3_v2_exact_solver.py
tests/test_family3_v2_exact_reference.py
tests/test_family3_v2_artifacts.py
tests/test_family3_v2_preflight.py
```

The output root is fixed to:

```text
results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight
```

---

### Task 1: Freeze the v0/v1 baseline before v2 source exists

**Files:**

- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/frozen_v0_v1_baseline.json`
- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json`
- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/progress.jsonl`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**

- Produces an immutable baseline containing exactly 14 source entries and 72
  result entries.
- Produces Gate-0 state
  `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.
- No implementation task is allowed to rebaseline these paths.

- [ ] **Step 1: Confirm the output root and every v2 source path are absent**

Run:

```powershell
$out = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
if (Test-Path -LiteralPath $out) { throw "output root already exists: $out" }
$v2 = @(Get-ChildItem -LiteralPath 'src\pa_rl' -Filter 'family3_v2_*.py' -ErrorAction SilentlyContinue)
if ($v2.Count -ne 0) { throw "family3_v2 source exists before baseline freeze" }
```

Expected: exit `0`, no output.

- [ ] **Step 2: Emit the exact baseline mapping to stdout without writing it**

Run this from the project root:

```powershell
$project = (Resolve-Path '.').Path
$source = @(
  Get-ChildItem -LiteralPath 'src\pa_rl' -Filter 'increment8_*.py' -File
  Get-Item -LiteralPath 'src\pa_rl\authorization.py'
  Get-Item -LiteralPath 'src\pa_rl\contracts.py'
  Get-Item -LiteralPath 'src\pa_rl\effects.py'
  Get-Item -LiteralPath 'src\pa_rl\scope_matching.py'
) | Sort-Object FullName -Unique
$roots = @(
  'results\increment8_v1_fixed_formula_preflight',
  'results\increment8_v1_s3_v9_calibration',
  'results\increment8_v1_s3_v9_target6_exposure24_calibration',
  'results\increment8_v1_terminal_cache_bypass_diagnostic'
)
$result = foreach ($root in $roots) {
  if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "missing root: $root" }
  Get-ChildItem -LiteralPath $root -File -Recurse
}
if ($source.Count -ne 14) { throw "expected 14 source files, got $($source.Count)" }
if (@($result).Count -ne 72) { throw "expected 72 result files, got $(@($result).Count)" }
function Entry($file) {
  $relative = [IO.Path]::GetRelativePath($project, $file.FullName).Replace('\','/')
  [ordered]@{ relative_path=$relative; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant() }
}
[ordered]@{
  schema_version='family3_v2_frozen_baseline_v0'
  source_files=@($source | ForEach-Object { Entry $_ })
  result_roots=@($roots | ForEach-Object { $_.Replace('\','/') })
  result_files=@($result | Sort-Object FullName | ForEach-Object { Entry $_ })
} | ConvertTo-Json -Depth 6
```

Expected: one JSON mapping with 14 `source_files` and 72 `result_files`.

- [ ] **Step 3: Atomically create the baseline and Gate-0 files**

Create only the already-fixed output directory (after Step 1 proved it was
absent):

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
New-Item -ItemType Directory -Path $root | Out-Null
```

Use `apply_patch` to create `frozen_v0_v1_baseline.json` from the exact Step 2
stdout. Then run the following read-only formatter to print the complete
checkpoint with its real baseline hash:

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
$baselineHash = (Get-FileHash -Algorithm SHA256 -LiteralPath "$root\frozen_v0_v1_baseline.json").Hash.ToLowerInvariant()
[ordered]@{
  schema_version='family3_v2_preflight_checkpoint_v0'
  status='BASELINE_FROZEN'
  last_completed_gate=0
  next_gate=1
  next_action='Implement Task 2 contracts, suite, and exact mod-5 RNG'
  baseline_relative_path='frozen_v0_v1_baseline.json'
  baseline_sha256=$baselineHash
} | ConvertTo-Json
```

Use `apply_patch` to create `continuation_checkpoint.json` from that exact
stdout. Create `progress.jsonl` with the same state as one compact JSON line and
`flush/fsync` it during later programmatic updates.

- [ ] **Step 4: Verify the frozen baseline**

Run:

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
$b = Get-Content -Raw -LiteralPath "$root\frozen_v0_v1_baseline.json" | ConvertFrom-Json
$c = Get-Content -Raw -LiteralPath "$root\continuation_checkpoint.json" | ConvertFrom-Json
if ($b.source_files.Count -ne 14 -or $b.result_files.Count -ne 72) { throw 'baseline cardinality mismatch' }
if ($c.status -ne 'BASELINE_FROZEN' -or $c.next_gate -ne 1) { throw 'checkpoint mismatch' }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath "$root\frozen_v0_v1_baseline.json").Hash.ToLowerInvariant()
if ($hash -ne $c.baseline_sha256) { throw 'baseline hash mismatch' }
```

Expected: exit `0`, no output. Update `docs/CONTINUATION_CHECKPOINT.md` with
the baseline hash, cardinalities, stable state, and exact Task 2 next action.

---

### Task 2: Add typed contracts, literal suite, and exact branch RNG

**Files:**

- Create: `src/pa_rl/family3_v2_contracts.py`
- Create: `src/pa_rl/family3_v2_suite.py`
- Create: `src/pa_rl/family3_v2_rng.py`
- Create: `tests/test_family3_v2_suite_rng.py`

**Interfaces:**

- `build_family3_v2_suite() -> Family3V2Suite`
- `Family3V2KernelInput.from_graph(graph) -> Family3V2KernelInput`
- `Family3V2KernelInput.forecast_counterfactual() -> Family3V2KernelInput`
- `draw_family3_v2_branch_residue(root_seed, branch_coupling_uid,
  episode_ordinal) -> Family3V2BranchResidue`
- `continuation_from_residue(forecast_exact_probability,
  forecast_broader_probability, residue) -> ContinuationModeV2`

- [ ] **Step 1: Write one focused failing suite/RNG test module**

The test must include these assertions, with all ten rows checked literally:

```python
class Family3V2SuiteRngTests(unittest.TestCase):
    def test_literal_suite_and_counterfactual(self) -> None:
        suite = build_family3_v2_suite()
        self.assertEqual(tuple(g.graph_id for g in suite.graphs), tuple(f"i8_f3v2_v{i}" for i in range(10)))
        self.assertEqual([g.split for g in suite.graphs], ["train"] * 5 + ["validation"] * 2 + ["test"] * 3)
        self.assertEqual([g.exposure_budget for g in suite.graphs], [9, 12, 16, 12, 30, 15, 24, 24, 21, 30])
        self.assertEqual([g.target for g in suite.graphs], [3, 4, 4, 5, 5, 6, 6, 7, 7, 6])
        for graph in suite.graphs:
            other = Family3V2KernelInput.from_graph(graph).forecast_counterfactual()
            self.assertEqual(other.branch_coupling_uid, graph.branch_coupling_uid)
            self.assertEqual(other.forecast_exact_probability, 1 - graph.forecast_exact_probability)

    def test_rejection_sampling_is_exactly_mod_five(self) -> None:
        self.assertEqual(residue_from_uint64s(iter((2**64 - 1, 14))), 4)
        for residue in range(5):
            self.assertEqual(
                continuation_from_residue(Fraction(4, 5), Fraction(1, 5), residue),
                ContinuationModeV2.EXACT if residue < 4 else ContinuationModeV2.BROADER,
            )
            self.assertEqual(
                continuation_from_residue(Fraction(1, 5), Fraction(4, 5), residue),
                ContinuationModeV2.EXACT if residue < 1 else ContinuationModeV2.BROADER,
            )
```

In the first method, also construct one `literal_projection` tuple containing
all fields shown in Step 3—graph ID, split, carrier literal, purpose literal,
forecast numerator, `e`, `d`, target, exposure, and horizon—and compare it in
one `assertEqual` against the complete ten-row `_ROWS` tuple. The subset checks
above are diagnostic duplicates, not a substitute for the literal assertion.

- [ ] **Step 2: Run the focused test and witness the missing-module RED**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

Expected: import failure for `pa_rl.family3_v2_contracts` or
`pa_rl.family3_v2_suite`. Any other failure cause stops the task.

- [ ] **Step 3: Implement the immutable contracts and literal suite**

Define the exact profile constants and enums from the spec. The candidate order
must be:

```python
FAMILY3_V2_CANDIDATE_ORDER = (
    CandidateRoleV2.REQUEST_NARROW,
    CandidateRoleV2.REQUEST_BROADER,
    CandidateRoleV2.EXECUTE_COVERING,
    CandidateRoleV2.REFRESH_CLOSED,
    CandidateRoleV2.DISABLE_ACTIVE,
    CandidateRoleV2.DENY,
    CandidateRoleV2.ESCALATE,
)
```

Copy the five carrier literals from `increment8_suite.py`; do not import its
private `_CARRIERS`. Freeze the ten rows as:

```python
_ROWS = (
    ("i8_f3v2_v0", "train", "c0_calendar", "agenda_summary", 4, 2, 1, 3, 9, 8),
    ("i8_f3v2_v1", "train", "c1_mail_archive", "status_notice", 1, 3, 1, 4, 12, 8),
    ("i8_f3v2_v2", "train", "c2_mail_send", "inbox_cleanup", 4, 3, 2, 4, 16, 8),
    ("i8_f3v2_v3", "train", "c3_report", "weekly_report", 1, 4, 2, 5, 12, 8),
    ("i8_f3v2_v4", "train", "c4_records", "approved_update", 4, 4, 3, 5, 30, 8),
    ("i8_f3v2_v5", "validation", "c0_calendar", "inbox_cleanup", 1, 5, 3, 6, 15, 9),
    ("i8_f3v2_v6", "validation", "c1_mail_archive", "weekly_report", 4, 5, 4, 6, 24, 9),
    ("i8_f3v2_v7", "test", "c2_mail_send", "approved_update", 1, 6, 4, 7, 24, 10),
    ("i8_f3v2_v8", "test", "c3_report", "agenda_summary", 4, 6, 5, 7, 21, 10),
    ("i8_f3v2_v9", "test", "c4_records", "status_notice", 1, 5, 3, 6, 30, 9),
)
```

The fifth field is the exact-forecast numerator over denominator five, followed
by `e`, `d`, target, exposure budget, and horizon. `Family3V2GraphSpec` must
recompute `n`, `b`, target, exposure, horizon, profile strings, scope relation,
and the exact 21-field row allowlist in `__post_init__`; it rejects values that
merely happen to hash.

- [ ] **Step 4: Implement unbiased residue generation**

Use the spec's JSON-list payload and big-endian first eight digest bytes. The
testable rejection core is:

```python
def residue_from_uint64s(values: Iterator[int]) -> int:
    limit = 2**64 - (2**64 % 5)
    for value in values:
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError("draw must be an exact uint64")
        if value < limit:
            return value % 5
    raise ValueError("draw source ended before an accepted residue")
```

`draw_family3_v2_branch_residue` repeatedly hashes the frozen payload with
counter `j`, returns the accepted residue, attempt number, accepted uint64, and
payload SHA-256, and rejects Boolean/out-of-range seeds.

- [ ] **Step 5: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all methods PASS. Record the exact method
count, elapsed time, three new source hashes, test hash, and Task 3 next action
in `docs/CONTINUATION_CHECKPOINT.md` and the result-root checkpoint.

---

### Task 3: Implement the pure outcome and finite-horizon model

**Files:**

- Create: `src/pa_rl/family3_v2_outcome.py`
- Create: `src/pa_rl/family3_v2_model.py`
- Create: `tests/test_family3_v2_model_outcome.py`

**Interfaces:**

- `evaluate_family3_v2_outcome(evidence) -> Family3V2OutcomeResult`
- `Family3V2Model.initial_state(kernel) -> Family3V2State`
- `Family3V2Model.candidates(state) -> tuple[Family3V2Candidate, ...]`
- `Family3V2Model.transition_distribution(state, semantic_candidate_id) ->
  tuple[Family3V2Transition, ...]`
- `Family3V2Model.transition_from_residue(state, semantic_candidate_id,
  residue) -> Family3V2Transition`
- `Family3V2Model.is_success(state) -> bool`

- [ ] **Step 1: Write the focused model/outcome RED tests**

Include one helper that requests a chosen role, selects a specified exact or
broader transition after the first execute, then repeatedly selects
`execute_covering` until terminal. Assert all four witness cells:

```python
self.assertTrue(run_witness(graph, "request_narrow", "exact").success)
self.assertEqual(run_witness(graph, "request_narrow", "broader").failure_reason, "irreversible_no_coverage")
self.assertEqual(run_witness(graph, "request_broader", "exact").failure_reason, "exposure_budget_exceeded")
self.assertTrue(run_witness(graph, "request_broader", "broader").success)
```

Also assert:

- reset has exactly seven rows and only the two requests, deny, and escalate are
  mask-valid;
- queued future tasks are empty and continuation is `UNREALIZED` before the
  first committed effect;
- grant verification closes the window;
- request/refresh remain `offer_window_closed` thereafter;
- valid disable never reopens the window and immediately reaches the
  nonemitted no-coverage guard;
- exposure failure beats natural completion;
- valid natural completion on the last decision beats horizon exhaustion;
- only `NATURAL_COMPLETION` can yield reward one.

- [ ] **Step 2: Run the focused test for the expected missing-model RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_model_outcome -v
```

Expected: import failure for `pa_rl.family3_v2_model`.

- [ ] **Step 3: Implement the state and seven-row catalog**

Use frozen dataclasses for task, authorization, candidate, state, and transition.
The internal candidate may carry `operational_scope`; no policy type may. Every
normal action increments zero-based `decision_index` exactly once. Terminal
states return an empty catalog; every emitted nonterminal state returns the
seven roles in `FAMILY3_V2_CANDIDATE_ORDER`.

The terminal transition signature also uses the unique empty-mask sentinel
`next_mask=()`. It never fabricates seven false candidates. Every nonterminal
successor instead carries its authoritative seven-entry mask. Model,
observation, solver, and audits must use this same convention.

Reason precedence is implemented before action-specific dispatch:

```python
if state.terminated:
    return "terminal_state"
if action is ControllerAction.REQUEST_AUTHORIZATION and scope not in offered_scopes:
    return "scope_not_offered"
if state.offer.offer_window is OfferWindowV2.CLOSED and action in {
    ControllerAction.REQUEST_AUTHORIZATION,
    ControllerAction.REQUEST_REFRESH,
}:
    return "offer_window_closed"
```

Then apply `no_refreshable_authorization`, `no_covering_authorization`, or
`no_active_authorization`. Masked rows remain in the catalog with neutral
bindings.

- [ ] **Step 4: Implement transition timing and outcome precedence**

For a valid action: apply the action, take the post-action active-grant exposure
snapshot, check integrity/prompt/exposure failure, realize a branch only after
the first committed execute, install its task queue, check irreversible
no-coverage, then natural completion, then horizon exhaustion. A successful
exact path consumes `(e+2)n`; a successful broader path consumes `(d+2)b`.

Forced invalid action must terminate reward zero without changing prompt,
exposure, authority, effect index, or branch state. Store the seven-row
would-be catalog with `emitted=False` before automatic no-coverage termination.

- [ ] **Step 5: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all model/outcome methods PASS. Save hashes,
counts, and the Task 4 next action in both checkpoints.

---

### Task 4: Add real scope binding, mediated environment, and label-free encoder

**Files:**

- Create: `src/pa_rl/family3_v2_authority.py`
- Create: `src/pa_rl/family3_v2_policy.py`
- Create: `src/pa_rl/family3_v2_environment.py`
- Create: `tests/test_family3_v2_authority_environment.py`

**Interfaces:**

- `DeterministicAllowReuseUserV2.answer_permission(request) ->
  Family3V2PermissionResponse`
- `Family3V2AuthorizationBindingGateway.commit_request(
  selected_candidate_scope, request, response, expires_at_step) ->
  AuthorizationBindingResultV2`
- `project_family3_v2_observation(state, model) -> Family3V2Observation`
- `Family3V2FeatureEncoder.encode(observation) -> Family3V2EncodedDecision`
- `Family3V2Environment.reset(graph_id, root_seed, episode_ordinal,
  forecast_counterfactual=False) -> (observation, info)`
- `Family3V2Environment.step(slot_index) ->
  (observation, reward, terminated, truncated, info)`

- [ ] **Step 1: Write binding/environment RED tests**

Test narrow and broader requests, including `c4_records` sensitivity three:

```python
for role in ("request_narrow", "request_broader"):
    observation, info = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
    slot = next(i for i, row in enumerate(observation.candidates) if row.role.value == role)
    _, _, _, _, info = env.step(slot)
    evidence = info.binding_evidence[-1]
    self.assertEqual(evidence.selected_candidate_scope, evidence.dispatched_scope)
    self.assertEqual(evidence.dispatched_scope, evidence.accepted_scope)
    self.assertEqual(evidence.accepted_scope, evidence.recorded_ledger_scope)
    self.assertEqual(info.ledger_records[-1].grant_type, GrantType.REUSABLE)
    self.assertEqual(info.ledger_records[-1].expires_at_step, 9)
```

Add tests for precommit mismatch with zero ledger events, postcommit mismatch
with quarantined append-only evidence and no usable candidate, deterministic
committed `MockTool` outcome, missing/unknown/conflict/duplicate outcome as
integrity failure, forced masked action with no side effect, and a deliberately
mutated mediated successor that is rejected when it differs from the pure
kernel in state, reward, termination, or truncation.

- [ ] **Step 2: Run the focused test for the expected missing-authority RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment -v
```

Expected: import failure for `pa_rl.family3_v2_authority`.

- [ ] **Step 3: Implement the typed user and two-phase binding gateway**

The gateway sequence is fixed:

```text
candidate scope -> immutable request -> user response
-> precommit equality
-> AuthorizationService.start_request
-> AuthorizationService.apply_permission_choice(ALLOW_REUSE)
-> reread record -> postcommit equality
-> bind public issuance ordinal to private raw ID
```

A precommit mismatch returns before `start_request`. A postcommit mismatch does
not roll back append-only evidence; it quarantines the raw authorization ID,
withholds a public ordinal, terminates
`authorization_binding_integrity_failure`, and never invokes the monitor/tool.
Production constructs `AuthorizationService` with `episode_end_step=horizon+1`.

- [ ] **Step 4: Implement the label-free observation and exact encoder**

`PolicyScopeRoleViewV2` contains role, relation, attribute count, sensitivity,
cost, and optional public issuance ordinal—never a `Scope`. The fixed seven
candidate rows include role, action, mask, invalid reason, offer role, task
relation, and public ordinal; masked bindings are neutral.

`Family3V2EncodedDecision` uses exact tuples only:

```python
@dataclass(frozen=True, slots=True)
class Family3V2EncodedDecision:
    state_features: tuple[int, ...]
    candidate_features: tuple[tuple[int, ...], ...]
    mask: tuple[bool, ...]
    semantic_candidate_ids: tuple[str, ...]

    def representation_key(self) -> tuple[object, ...]:
        return (self.state_features, self.candidate_features, self.mask, self.semantic_candidate_ids)
```

Encode each `Fraction` as numerator and denominator integers. Do not retain the
raw observation inside `representation_key`.

- [ ] **Step 5: Implement the real mediated environment**

Use `AuthorizationService`, `ReferenceMonitor`, `TaskEngine`, and `MockTool`.
Create one deterministic committed plan for each possible declared task. Every
execute must pass the reference monitor; blocked, absent, unknown, conflict,
missing plan, duplicate effect, or model/ledger revision disagreement sets
`run_valid=False` and terminates as an integrity failure.

The environment must not implement a second transition FSM. After mediation
and side-effect validation, it delegates the semantic successor exclusively to
the same `Family3V2Model.transition_from_residue` used to define the exact-DP
kernel, then checks the returned state, reward, terminated, and truncated
fields against its public result. Environment-private ledger/monitor/tool
evidence may be added to `info`, but may not change the semantic successor.

The branch residue is drawn exactly once after the first actual committed
effect. If branch installation causes immediate no-coverage, install the task
in `TaskEngine`, record the nonemitted catalog, and then terminate. A masked row
never calls user, ledger, monitor, or tool.

- [ ] **Step 6: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all authority/environment methods PASS. Run
Tasks 2–4 focused tests together once; record counts/hashes and the Task 5 next
action in both checkpoints.

---

### Task 5: Implement exact Markov, firewall, witness, binding, and no-repair audits

**Files:**

- Create: `src/pa_rl/family3_v2_audit.py`
- Create: `tests/test_family3_v2_policy_audit.py`

**Interfaces:**

- `audit_family3_v2_markov(suite, model, encoder) ->
  Family3V2MarkovAuditReport`
- `audit_family3_v2_kernel_environment_conformance(suite) ->
  Family3V2KernelEnvironmentConformanceReport`
- `audit_family3_v2_firewall(suite, encoder) -> Family3V2FirewallReport`
- `audit_family3_v2_witnesses(suite, model) -> Family3V2WitnessReport`
- `audit_family3_v2_binding_no_repair(suite) ->
  Family3V2BindingNoRepairReport`

- [ ] **Step 1: Write audit RED and negative-mutation tests**

The positive test requires 20 original/counterfactual analyses, nonzero state,
group, row, and action counts, no mismatches, 480 transformed manifests, and
4,800 row checks. Negative tests must prove failure when:

- offer-window or tail-progress fields are dropped;
- an encoder returns one constant representation;
- invalid reasons differ while masks match;
- termination kind or next mask differs while next observation/reward match;
- a mediated transition differs from the pure kernel in successor, reward,
  termination, truncation, or expected authority/tool/effect delta;
- a sentinel purpose/carrier/raw label appears in observation, semantic ID, or
  representation key.

- [ ] **Step 2: Run the focused test for the expected missing-audit RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_policy_audit -v
```

Expected: import failure for `pa_rl.family3_v2_audit`.

- [ ] **Step 3: Implement the exhaustive Markov audit**

Enumerate all reachable internal histories for ten graphs and their ten typed
forecast counterfactuals. Group across graphs—not by graph, carrier, purpose, or
split—first by exact public projection, then by exact encoded representation.
For every group, compare all seven role/mask/reason triples. For each common
mask-valid role, aggregate exact `Fraction` distributions over:

```text
(next projection or terminal sentinel,
 scalar reward,
 termination kind,
 empty terminal mask or next seven-entry mask)
```

Require each reachable decision state to appear in exactly one group and write
nonzero membership/action counts so an empty audit cannot pass.

- [ ] **Step 4: Prove pure-kernel / mediated-environment conformance**

Across all ten original graphs and ten forecast counterfactuals, enumerate
every reachable emitted nonterminal state and every mask-valid candidate. For
the first-effect branch transition, cover all five exact residues `0..4`; for
deterministic transitions, cover the sole successor. Replay the corresponding
history through the real environment and require exact equality of semantic
next state, reward, terminated, truncated, public projection, and next-mask
sentinel convention with the shared pure-model transition.

For each role also compare the expected ledger-event, monitor-invocation,
tool-invocation, committed-effect, prompt, exposure, and branch-draw deltas.
Record nonzero state/action/transition counts and per-role coverage. Any
semantic or side-effect mismatch fails this audit before exact DP. Gate 3
consumes this report together with the four-cell witness report.

- [ ] **Step 5: Implement the 480-manifest shortcut firewall**

Enumerate all `5!` purpose permutations crossed with
`{identity,c0<->c3,c1<->c2,both}`. For every transformed suite row, prove the
operational scope changed when expected, then compare schema, algebra, copied
label-erased structural key, initial public/encoded key, seven roles/masks, and
analytic optimal role mapping. Do not call DP. Require exactly 480 manifests
and 4,800 row checks.

- [ ] **Step 6: Implement witness/binding/no-repair audit reports**

Enumerate ten graphs × four request/branch cells; classify exposure-budget
failure as a resource outcome, not an unauthorized effect. At every reachable
post-grant and nonterminal post-first-effect state, cover seven rows/six action
types. For transitions that terminate before emitting a state (including
`d=1` narrow+broader), require the recorded no-coverage catalog and exact
termination. Assert all forced invalid actions create no authority, invocation,
effect, prompt, exposure, or residue.

- [ ] **Step 7: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all audit methods PASS. Record report counts,
source/test hashes, and Task 6 next action in both checkpoints.

---

### Task 6: Implement the capped exact solver, independent reference, and artifact store

**Files:**

- Create: `src/pa_rl/family3_v2_exact_solver.py`
- Create: `src/pa_rl/family3_v2_exact_reference.py`
- Create: `src/pa_rl/family3_v2_artifacts.py`
- Create: `tests/test_family3_v2_exact_solver.py`
- Create: `tests/test_family3_v2_exact_reference.py`
- Create: `tests/test_family3_v2_artifacts.py`

**Interfaces:**

- `Family3V2ValueFirstExactSolver.solve(initial_state,
  initial_action_ids) -> Family3V2ExactSolveResult`
- `enumerate_terminal_free_reference(model, initial_state,
  initial_action_ids) -> TerminalFreeReferenceResult`
- `verify_frozen_v0_v1_baseline(project_root, baseline) -> FrozenSetAudit`
- `Family3V2PreflightStore.commit_gate(gate, report, evidence)`
- `Family3V2PreflightStore.mark_interrupted(gate, next_action)`
- `Family3V2PreflightStore.mark_terminal_failure(status, gate, evidence)`
- `Family3V2PreflightStore.finalize(verdict) -> ArtifactRef`

- [ ] **Step 1: Write the three focused RED test modules**

Solver tests require terminal-before-key behavior, exact root V and ordered Q,
strict cache signature, cycle/probability validation, stop before the 250,001st
distinct state, and exact RSS failure at 512 MiB + 1 byte through an injected
RSS reader. Reference tests use terminal objects whose hashing/serialization
raises, proving terminals never enter its state table. Artifact tests cover
missing/changed/added legacy paths, output-root escape rejection, gate order,
tampered committed evidence, interrupted resume, and finalization refusal with
only eleven gates.

- [ ] **Step 2: Run the three focused tests for the expected missing-solver RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v
```

Expected: import failure for `pa_rl.family3_v2_exact_solver`.

- [ ] **Step 3: Implement the value-first solver**

Use a fresh SQLite schema containing only `nonterminal_exact_values`; metadata
binds solver/schema/accounting-domain, kernel/source/config hashes, and all
limits. In `_value`, validate terminal binary reward and return before state
serialization, lookup, or store. Store a new nonterminal only while the row
count is below 250,000 and current RSS is at most `512*1024*1024`.

The root solve recomputes both requested first-action Q-values from successor
values even when root V resumes from cache. Each graph receives its own DB,
solver instance, and 4,096-entry LRU. Use Windows
`ctypes/GetProcessMemoryInfo`, Linux `/proc/self/statm`, and fail closed on an
unsupported RSS reader; do not add `psutil`.

- [ ] **Step 4: Implement the independent bottom-up reference**

Do not import the exact solver. BFS-enumerate only reachable nonterminal states,
compress every terminal successor immediately to a binary reward leaf, require
every nonterminal successor's `decision_index` to equal parent + 1, then compute
V/Q in reverse decision-index order. Expose this only for
`i8_f3v2_v0` and `i8_f3v2_v1`.

- [ ] **Step 5: Implement strict artifacts and checkpointing**

The store has no freeze/rebaseline API. It validates the Task 1 manifest,
writes JSON by temporary file + flush/fsync + atomic replace, hashes every
artifact, and appends a flushed progress JSONL entry only when committing a
gate. A partial artifact without a checkpoint advance is not PASS.

Only `INTERRUPTED` resumes after validating the baseline, run config, all
committed reports, and their evidence hashes. `GATE_FAILED` and
`RESOURCE_CAP_EXCEEDED` are terminal. Relative paths reject absolute paths,
`..`, and output-root escape.

- [ ] **Step 6: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all solver/reference/artifact methods PASS.
Record counts, hashes, resource-test evidence, and Task 7 next action in both
checkpoints.

---

### Task 7: Build and execute the ordered twelve-gate preflight

**Files:**

- Create: `src/pa_rl/family3_v2_preflight.py`
- Create: `tests/test_family3_v2_preflight.py`
- Create after a valid run:
  `docs/implementation_reports/task-8-family3-v2-exact-preflight.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `../../RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`
- Modify: `../../RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`

**Interfaces:**

- `run_family3_v2_preflight(output_root: Path) -> dict[str, object]`
- `build_parser() -> argparse.ArgumentParser`
- `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the runner RED tests**

Freeze this registry:

```python
GATE_ORDER = (
    (1, "suite_manifest"),
    (2, "algebra"),
    (3, "witnesses"),
    (4, "exact_values"),
    (5, "request_q_values"),
    (6, "forecast_counterfactual"),
    (7, "markov"),
    (8, "shortcut_firewall"),
    (9, "scope_binding"),
    (10, "closed_offer_no_repair"),
    (11, "invalid_action_safety"),
    (12, "frozen_v0_v1_unchanged"),
)
```

With fake gates, test exact 1→12 ordering, short-circuit at each position,
resume from N+1, and refusal to finalize eleven gates. Gate 4 must call:

```text
solve v0 -> reference v0 -> compare V/Q
solve v1 -> reference v1 -> compare V/Q
only then solve v2 through v9
```

Any v0/v1 mismatch must leave no v2–v9 cache/artifact. Test separate original
and counterfactual caches. The parser may expose only `--output-root`; it must
reject graph, gate, seed, worker, limit, probability, budget, and target
overrides. It must also reject any `--output-root` whose resolved path is not
the single fixed result directory, including an equivalent-looking path that
escapes and re-enters through `..` or a symlink/reparse point.

- [ ] **Step 2: Run the focused test for the expected missing-runner RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight -v
```

Expected: import failure for `pa_rl.family3_v2_preflight`.

- [ ] **Step 3: Implement the runner and strict certificates**

Gate artifacts are fixed at `gates/gate_01_*.json` through
`gates/gate_12_*.json`. Per-graph caches/certificates live under
`graphs/<graph_id>/`; v0/v1 reference certificates under `references/`; typed
counterfactual caches under `counterfactuals/<graph_id>/`.

Gate 3 requires both the four-cell witnesses and the exhaustive shared-kernel /
mediated-environment conformance report to pass before any solver entry. Gate
4 requires all ten initial values exactly `Fraction(4,5)`. Gate 5 reads
Gate 4 certificates and requires ordered request Q-values `4/5,1/5` or the
reverse with gap `3/5`. Gate 6 uses only the frozen `root_seed=17` and
`episode_ordinal=0`, keeps the same coupling UID, payload, accepted uint64,
attempt, and exact accepted residue while swapping the probability pair and
Q-values. Gates 7–11 consume
the exact audit reports from Task 5. Gate 12 rehashes the Task 1 exact path set;
new `family3_v2_*` files are excluded, while any new/removed/changed
`increment8_*.py` or frozen result file fails.

Write `final_verdict.json` with `CERTIFIED_PASS` only after all twelve gate
commits. Exit `0` for PASS, `2` for gate/integrity failure, and `3` for resource
cap. On an external interruption, write `INTERRUPTED` with the last committed
gate and one exact next action.

- [ ] **Step 4: Run focused GREEN, adjacent frozen regressions, and compile**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_family3_v2_*.py' -v
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization tests.test_execution tests.test_increment8_preflight tests.test_increment8_v1_preflight tests.test_increment8_terminal_cache_diagnostic -v
python -m compileall -q src\pa_rl\family3_v2_contracts.py src\pa_rl\family3_v2_suite.py src\pa_rl\family3_v2_rng.py src\pa_rl\family3_v2_outcome.py src\pa_rl\family3_v2_model.py src\pa_rl\family3_v2_authority.py src\pa_rl\family3_v2_policy.py src\pa_rl\family3_v2_environment.py src\pa_rl\family3_v2_audit.py src\pa_rl\family3_v2_exact_solver.py src\pa_rl\family3_v2_exact_reference.py src\pa_rl\family3_v2_artifacts.py src\pa_rl\family3_v2_preflight.py
```

Expected: every focused and adjacent method passes; compile exits `0`. Any
failure stops before the real preflight command and records the exact failure.

- [ ] **Step 5: Run or resume the single focused exact preflight**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.family3_v2_preflight --output-root results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight
```

Expected PASS stdout is one compact mapping containing
`status=CERTIFIED_PASS`, `committed_gates=12`, `graph_count=10`,
`all_initial_values=4/5`, and `all_q_gaps=3/5`.

If the process is interrupted, do not delete or rebaseline. Inspect
`continuation_checkpoint.json`, verify the committed prefix, and invoke the
identical command once to continue from `next_gate`. If any gate returns FAIL or
a cap is reached, stop and ask for human inspection; do not adjust a parameter.

- [ ] **Step 6: Verify artifacts read-only and write the handoff record**

Re-open every committed evidence reference, recompute its SHA-256, verify the
SQLite row counts/quick checks, confirm no v2 artifact exists outside the fixed
root, and re-run `verify_frozen_v0_v1_baseline`. Write the implementation report
with exact values, Q-values, row/RSS counts, gate statuses, hashes, commands,
and any interruption history. Update the project checkpoint and both external
design logs. Do not describe this as DDQN evidence or run a learner.

## Self-Review Matrix

| Spec requirement | Plan coverage |
|---|---|
| Separate version; frozen v0/v1 | Tasks 1, 6, 7 Gate 12 |
| Two exact request scopes and reusable user authority | Tasks 2, 4 |
| Offer-window FSM and failure precedence | Task 3 |
| Delayed exact/broader branch and unbiased fifths | Tasks 2, 3 |
| Ten literal rows and algebra | Task 2; Gates 1–2 |
| Binary outcome, no canonical path | Task 3 |
| Label-free public observation and seven rows | Task 4 |
| Exact public/encoder Markov sufficiency | Task 5; Gate 7 |
| 480-manifest shortcut firewall | Task 5; Gate 8 |
| Four witnesses, binding, no repair, safety | Tasks 3–5; Gates 3, 9–11 |
| `V*=4/5`, Q swap/gap | Tasks 6–7; Gates 4–6 |
| 250,000 states / 512 MiB | Task 6 |
| Durable checkpoint and interruption log | Tasks 1, 6, 7 |
| No all-forty/training/tuning | Global constraints and Task 7 stop rules |

Self-review outcome: every English-spec section maps to at least one task; all
types used by later tasks are introduced in an earlier task; the plan contains
no deferred implementation marker and no scientific-parameter override.
