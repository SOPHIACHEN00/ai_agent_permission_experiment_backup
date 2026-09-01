# Task 3B1 Implementation Report - Deterministic Environment Kernel

## Status and scope

The Task 3B1 kernel and Fix round 1 are locally verified but are **not approved**; they await independent re-review. This report does **not** mark Task 3B1, Task 3, or G1 complete. Task 3B2 still owns sealed `EpisodeTrace` evidence, independent semantic verification, fresh-environment replay, replay mutation attacks, and the final Task 3 gate.

The increment remains dependency-free and does not add Gymnasium, NumPy/Torch, baselines, learning, Deep RL, live S-QSTN, or replay/sealing behavior.

## Files changed

- `src/pa_rl/environment.py` - deterministic environment composition, public-state/catalog construction, six-action dispatch, monitor/evaluator wiring, H+1 finalization, frozen `info`, private deterministic tool plan, and unsealed typed transition evidence.
- `tests/test_environment.py` - 28 focused environment tests covering all mandatory Task 3B1 paths and review regressions.
- `docs/implementation_briefs/task-3b1-brief.md` - Fix-round-1 clarification of service-order authorization expiry evidence versus separately sorted public expiry publication.
- `docs/implementation_reports/task-3b1-report.md` - this report.

One separately authorized prerequisite landed concurrently outside this increment: Task 1 scope matching now uses `scope_ontology_v0_1`, in which retention `external` is an explicit categorical value that covers only itself. It is neither unknown nor ranked above `session`. This was required so fixture 7's typed `external` scope could be projected through the approved authorization/public-summary APIs. The scope change and its Task 1 tests were made and reviewed separately; Task 3B1 did not introduce a raw-preference workaround or edit those APIs.

## TDD evidence

The focused environment test module was written before the production module existed. The first real RED command was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment -v
```

Observed RED: exit `1`, with the expected loader failure `ModuleNotFoundError: No module named 'pa_rl.environment'`.

An additional isolated RED was captured for the public-manifest unprotected execution case after the initial production skeleton existed:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment.EnvironmentTrajectoryAndFinalizationTests.test_unprotected_step_is_mask_valid_and_still_executes_only_through_the_monitor -v
```

Observed RED: the unprotected execute slot was incorrectly mask-false. The minimal environment-side public-manifest rule was then added; the isolated rerun passed.

Focused GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment -v
```

Result: `Ran 20 tests in 1.135s` - `OK`.

Fresh full-suite and compilation verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python -m compileall -q src tests
```

Results: `Ran 166 tests in 1.290s` - `OK`; compilation exited `0` with no output. A source import scan found no Gymnasium, NumPy, Torch, TensorFlow, JAX, Stable-Baselines, Ray, or Tianshou dependency.

## Environment lifecycle and candidate binding

`PermissionEnvironment` exposes the frozen dependency-free signatures:

- `reset(seed=None, options=None) -> (EnvironmentObservation, info)`;
- `step(action_index) -> (EnvironmentObservation, int_reward, terminated, truncated, info)`.

`seed=None` resolves to `0`; Boolean and non-integer seeds are rejected. Reset options accept only `{}` or `{scenario_id}`. Every successful reset replaces any live episode with a fresh adapter, ledger, task engine, mock tool, reference monitor, evaluator plan, public chain, maps, counters, and transition buffer. The ledger episode ID is exactly `manifest.scenario_id`; ledger and evaluation endpoints are exactly `H+1`. Invalid reset options, action types/indices, step-before-reset, and step-after-close fail before episode mutation.

The current task step is the first `PENDING` manifest step. A live catalog has four to six semantic slots: request, nullable-bound execute, deny, and escalate always exist; refresh exists only for an explicitly related eligible prior; disable exists only for an active record. Records are selected by maximum `(issued_at_step, revision, authorization_id)`. Execute prefers the newest usable covering record, then the newest related record for fail-closed monitor testing, then `None`; refresh and disable never create unbound slots. Disable uses the selected record's own scope. Candidate selection is frozen before dispatch and is never silently rebound or rewritten.

Task and authority views are derived record-by-record from trusted snapshots, ledger records, public event state, and scope relation. The environment's latest-public-authority-event map is distinct from the ledger's request source event. Pending/rejected/closed rows derive their public expiry bucket from logical time. Current step and scope become `None` after task completion.

## Exact action dispatch

| Action | Environment dispatch | Adapter answers | Tool/authority boundary |
|---|---|---:|---|
| `REQUEST_AUTHORIZATION` | Save prior verified public history; preview request; `start_request(..., event_id, H+1)`; commit/deliver request; answer once; apply choice; publish grant or denial | 1 | No monitor/tool call |
| `REQUEST_REFRESH` | Same order through `start_refresh`; always creates a new record; approval publishes grant then refresh; rejection publishes only denial | 1 | No monitor/tool call |
| `DISABLE_LOCAL_AUTHORIZATION` | Disable the frozen active binding and publish the disable event | 0 | Ledger only |
| `EXECUTE_WITH_AUTHORIZATION` | Build the exact `ExecutionIntent` from the frozen resolved/base binding; call `ReferenceMonitor.execute` once; publish only its returned allowlisted result | 0 | Monitor is the sole path to ledger reservation, tool, and task mutation |
| `DENY_WITH_REASON` | Publish the allowlisted reason and pass the exact typed terminal action to the evaluator | 0 | No ledger/tool mutation |
| `ESCALATE` | Publish the allowlisted target and pass the exact typed terminal action to the evaluator | 0 | No ledger/tool mutation |

Permission request IDs use `permission_request_<16 lowercase hex>` and deterministically bind scenario, step, resolved candidate, request kind, and request ordinal. The ledger source ID is the exact previewed/committed public-event ID. `answer_permission` receives only the prior tuple of verified `PublicEvent` projections: it excludes the current request and never receives `PublicEventRecord` or audit data. Every committed record, including sorted final expiry records, is delivered through `observe_event`.

A bound protected execute and a nullable unprotected execute both remain monitor-mediated. Forced missing, stale, revoked, consumed, wrong, superseded, and mismatched bindings reach the monitor unchanged and cannot commit an unauthorized effect. A masked non-execute action faults before ledger, tool, or answer mutation.

## Evaluation, faults, and H+1 finalization

Evaluation receives only the internally owned `EvaluationPlan`, current `TaskSnapshot`, complete monitor audits, complete authorization events, and optional typed terminal action. Task 2B remains the sole success/reward authority. Evaluator termination precedes horizon truncation, and `terminated`/`truncated` are mutually exclusive.

Every closure performs this order exactly once:

1. Preserve the pre-finalization evaluation and the same typed terminal action.
2. Call `expire_eligible(H+1)` once.
3. Sort only the returned records by authorization ID.
4. Append and deliver `authorization_expired` public events and update the latest-event map.
5. Re-evaluate against the finalized ledger/audit evidence with the same terminal action.
6. Fail closed with `finalization_semantic_change` if the semantic outcome changes.
7. Return the exact closed observation at `logical_step=H+1`, `horizon_remaining=0`, with empty catalog and mask.

Environment-owned faults publish `verified_error` with a fixed allowlisted code: `masked_action`, `adapter_protocol_failure`, `environment_invariant_failure`, or `finalization_semantic_change`. Exception text is never copied to public events or public info. Fault closure returns reward `0`, `terminated=True`, and `truncated=False`. If an adapter itself fails while observing, the verified error remains committed even though that failed adapter cannot receive it.

## Public schemas and firewall

Every observation has exactly these top-level fields:

`scenario_id`, `environment_version`, `logical_step`, `horizon`, `horizon_remaining`, `request_context`, `task_view`, `authorization_views`, `interaction_history`, `candidate_catalog`, `catalog_hash`, and `action_mask`.

The task projection is exactly:

`phase`, `next_required_step_id`, `next_required_scope_identity`, `remaining_step_count`, `primary_complete`, `has_unknown_effect`, and `last_public_execution_result_code`.

Each authorization row is exactly:

`status`, `grant_type`, `remaining_uses`, `expiry_bucket`, `expiry_step`, `scope_relation`, `last_public_authority_event_id`, and `reask_relation`.

`info` is deeply frozen and has exactly `{public, audit}`. Its public branch is exactly:

`observation_hash`, `catalog_hash`, `public_event_head_hash`, `selected_action_index`, `selected_resolved_candidate_id`, `public_reason_code`, `new_public_event_ids`, `terminal_reason`, and `truncation_reason`.

The audit branch contains immutable version/hash bindings, snapshots, evaluator results/digests, public records, authorization events/heads, execution audits/heads, committed effect IDs, endpoint, seed/trace ID, and transition count. It contains no adapter, ledger, monitor, tool, evaluator-plan, reservation, permit, or other live capability. Public construction and action masking never read `info.audit`. Recursive oracle/private/tool-plan/evaluator/audit canaries are absent from observations, masks, public info, and public event payloads.

## Tool plan and transition evidence

The private tool plan version is `deterministic_tool_plan_v0`. Its default schema maps every typed `(scenario_id, task_step_id, attempt_index=1)` key to:

```text
("committed", "completed", deterministic_detail)
```

where detail contains only the tool-plan version, scenario ID, task-step ID, and attempt index. At reset, injected entries are validated and normalized into the same deeply immutable tuple/mapping representation passed to `MockTool`; the canonical hash is computed from that exact runtime snapshot. Only the version and hash enter audit metadata. Missing entries use the existing monitor `UNKNOWN` path and produce terminal reward `0`, never false success. The policy-visible surface cannot access the plan.

`TransitionRecord` is frozen typed evidence containing pre/post observations and hashes, selected slot/index, public/authorization/execution evidence, evaluator result, reward, flags, and reason. It is deliberately unsealed. `TRACE_SCHEMA_VERSION = "transition_evidence_v0"` names this handoff format but does not claim an `EpisodeTrace`, replay verifier, origin authentication, or semantic replay guarantee.

## Canonical trajectory and attack coverage

All ten fixture trajectories are selected by semantic action/step binding and reach their typed outcomes. The focused suite additionally covers the fixture-2 reusable grant, fixture-4/5/6 refresh/new-record/supersede behavior, fixture-7 persistent denial, fixture-8/9 correct and swapped terminal actions, and fixture-10's exact request/execute/disjoint-new-request truncation. A legacy one-answer fixture-10 adapter exhausts on the second request and closes as an adapter fault rather than silently truncating.

Two fresh environments with identical scenario, seed, and action-index sequence produce equal semantic transition evidence despite distinct random private monitor keys. Every canonical fixed-seed declared trace is deterministic. Forced binding attacks cover nullable, unknown, genuinely expired, revoked, consumed, wrong-scope, superseded, and manifest-scope-mismatched execution without unauthorized effects. Every current canonical `prohibited_action_trace` is a single execute-shaped binding; all ten are now exercised table-wise and shown to close reward-zero without a committed effect. Reset replacement, sorted expiry publication/latest-map updates, request and refresh history timing, exception-text firewalling, selected-binding preservation, and finalization semantic-change fail-closed behavior also have direct regressions.

## Frozen-contract tensions and remaining limitations

- Fixtures 7, 8, and 9 expose mask-valid `DENY_WITH_REASON`/`ESCALATE` slots at reset, and the approved Task 2B evaluator can award their registered safe terminal reward without requiring a preceding permission denial. Therefore a shorter immediate-success path exists alongside each declared request-then-terminal legal trace. Task 3B1 preserves the approved mask and reward APIs and tests the declared traces; it does not rewrite either contract. The delayed-credit G2 toy must use `TASK_COMPLETED`-only success so this shortcut cannot determine its result.
- The approved Task 3A `EnvironmentObservation` direct constructor accepts Boolean `horizon_remaining` through Python equality semantics. The Task 3B1 builder always emits exact integers and does not alter the approved API; explicit direct-constructor hardening is deferred to Task 3B2/review scope.
- The public, authorization, and execution hash chains establish deterministic integrity/linkage for supplied evidence, not cryptographic origin authentication against wholesale replacement with a new semantically valid history.
- Python underscore-private state and constructor-injected trusted factories are capability boundaries for this prototype, not process- or OS-level isolation. Forced catalog-binding attacks in tests use trusted private injection solely to verify fail-closed monitor behavior; the policy interface still selects only an in-range catalog index.
- `scope_ontology_v0_1` is now a required bound dependency for fixture semantics. Task 3B2 must bind/verify the final ontology/config/version surface when sealing traces.
- No replay, sealed trace verification, baselines, RL, or Task 3/G1 completion claim is made in this increment.

## Fix round 1 - independent-review remediation

### Status

All five requested resolution areas are implemented and freshly verified, but Task 3B1 remains pending the same reviewer's re-review. Task 3B2 must not begin on the basis of this local result alone.

### Review resolutions

1. **Runtime-bound tool-plan commitment.** Reset now validates every plan key and entry, accepts three-item list/tuple inputs only when their status/result pair is one of the two shapes actually supported by `MockTool`, normalizes list/tuple to one tuple representation, recursively copies mappings/sequences into immutable containers, and rejects malformed/non-deterministic values. The hash is computed from that normalized mapping and the same values are passed to `MockTool`. A factory's retained nested dictionary/list can no longer alter later effect IDs or execution audits. Missing entries and explicit `None` retain the existing unknown behavior.
2. **Commit/projection/delivery ordering.** Public-chain commit and environment-owned projection updates now form the non-fallible environment phase. Authority latest-event bindings and `last_public_execution_result_code` are updated immediately after a successful commit and before `observe_event`. One-shot and persistent delivery failures on `permission_requested`, committed `execution_result`, and final `authorization_expired` therefore close reward-zero without contradicting the committed public chain. Exception text remains firewalled.
3. **Exact, fail-closed reset.** An explicitly present `scenario_id` must now be a registered non-empty string; `{"scenario_id": None}` is rejected during external validation. Once a valid reset request begins replacing an episode, the environment is marked unavailable and its catalog/mask are emptied. `_initialized=True` and `_closed=False` are published only after the complete first observation and reset info succeed. Failed first and replacement resets therefore leave no partial or stale selectable episode, while a later valid reset can recover cleanly.
4. **Two deterministic expiry orders, explicitly separated.** The binding brief now requires exactly one `AuthorizationService.expire_eligible(H+1)` call. Its authorization events remain in the approved service's deterministic record order. Only the returned records are sorted by authorization ID for `authorization_expired` public publication and adapter delivery. A regression creates two active grants in an insertion order deliberately different from authorization-ID order, spies the one H+1 call, verifies service-order authorization events through `AuthorizationService.replay`, verifies the separately sorted public chain/head, and independently recomputes the final evaluator digest from the ledger-order evidence. Task 3B2 must bind both chains separately; neither chain is an ordering oracle for the other.
5. **Mandatory matrix completion.** The action matrix now includes `DENY_WITH_REASON` in the escalation-only fixture and confirms reward zero. A real existing authorization is transitioned to `EXPIRED`, bound unchanged to forced execute, and monitor-blocked without effect. All ten canonical prohibited execute bindings are exercised table-wise. These coverage-only additions were characterization GREEN against the pre-fix production behavior; no production flaw or RED is claimed for them.

`info.audit` also now binds `SCOPE_ONTOLOGY_VERSION` explicitly as `scope_ontology_version`. This is useful B1 evidence but does not replace Task 3B2's obligation to validate and seal the ontology version.

### Fix-round-1 TDD evidence

The new behavior tests were added before production changes. After correcting the expired-record test setup itself, the authoritative focused RED was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment -v
```

Result: `Ran 28 tests in 1.467s` - `FAILED (failures=9, errors=2)`. The nine failures were the six one-shot/persistent projection-loss subcases, explicit `scenario_id=None`, list/tuple runtime divergence, and factory-owned nested mutation. The two errors exposed the failed-first-reset lifecycle leak (`AttributeError` from absent `_catalog` instead of a lifecycle rejection) and the missing ontology audit binding. The reverse safe action, real expired binding, all-ten prohibited table, and dual-order expiry evidence were already GREEN characterization cases.

A final validation-boundary audit added an unhashable non-string status case before its guard. The isolated RED ran `1` test and failed with `errors=1` because dictionary lookup leaked `TypeError`; after the minimal explicit type check, the same isolated test ran `1/1` - `OK` and malformed entries uniformly raise `ValueError`.

Each production resolution was then verified in isolation: tool-plan tests `2/2`, adapter-delivery tests `3/3` (six subcases), and reset tests `2/2`. Fresh aggregate GREEN was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python -m compileall -q src tests
```

Results: focused `Ran 28 tests in 1.508s` - `OK`; full project `Ran 174 tests in 4.062s` - `OK`; compilation exited `0` with no output.

### Remaining boundary

This round adds no sealed trace, replay verifier, Gymnasium dependency, baseline, RL, or live S-QSTN behavior. `TransitionRecord` remains explicitly unsealed internal evidence. The previously documented safe-terminal shortcut, Boolean direct-constructor limitation, unkeyed-chain origin-authentication limitation, and same-process prototype trust boundary remain unchanged. Independent Task 3B1 re-review is still required before Task 3B2.
