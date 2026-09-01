# Task 3B Brief — Deterministic Environment Assembly and Replay

## Entry gate and scope

Begin only after Task 3A passes independent review. Read `task-3-brief.md` completely; it remains binding. Compose the approved Task 0–3A components into:

- dependency-free Gymnasium-style `PermissionEnvironment.reset/step`;
- a private deterministic canonical tool-outcome-plan factory;
- sealed `TransitionRecord` / `EpisodeTrace` evidence;
- independent trace verification plus fresh-environment action-index replay.

Implement only focused modules such as `environment.py` and `replay.py`, tests, and `task-3b-report.md`. No live S-QSTN, Gymnasium, NumPy/Torch, baselines, learning, or Deep RL. Do not redesign approved Task 0–3A APIs; report a true blocker if composition is impossible.

Implement this brief in two separately reviewed increments:

- **Task 3B1 â€” environment kernel:** deterministic component assembly, catalog/state projection, all six dispatch paths, monitor/evaluator wiring, finalization, closed observations, public/audit `info`, and canonical fixture trajectories. It may record typed per-transition evidence but must not claim sealed replay yet.
- **Task 3B2 â€” trace and replay:** immutable transition/episode trace schemas, sealing/hash/version binding, semantic evidence verification, fresh-environment action-index replay, mutation attacks, and replay-policy firewall tests.

Task 3B2 begins only after Task 3B1 passes independent review. This split is an implementation boundary only; all contracts below remain binding.

## Frozen integration contracts

1. Instantiate `AuthorizationService(episode_id=manifest.scenario_id, episode_end_step=H+1)`. Task 2B replays authorization events against the scenario ID, so a seed/run-derived ledger episode ID is forbidden. A separate deterministic `trace_id` may bind the seed.
2. `EvaluationPlan.from_manifest(manifest)` must have the same `episode_end_step=H+1`.
3. Each reset creates fresh adapter, ledger, task engine, tool, monitor, evaluator plan, public chain, counters, histories, and audit/transition collections. Root seed `None` resolves to frozen default `0`; reject Boolean/non-integer seeds.
4. One `step` is one controller decision at `t in [1,H]`. Type/bounds/lifecycle validation occurs before mutation. Same-step retries remain legal in lower-level approved APIs even if a normal environment decision advances `t`.
5. Use the Task-3A public-event two-phase preview/commit API: prebuild a permission-request record, pass that exact `event_id` to `start_request/start_refresh`, then commit it if the ledger call succeeds.
6. Only request/refresh call `answer_permission`, exactly once. Every committed verified public record is delivered as its allowlisted `PublicEvent` to `observe_event`; observation never consumes an answer.
7. Execute only through `ReferenceMonitor.execute(ExecutionIntent)`, using the resolved wrapper's preserved Task-0 base candidate ID and exact step/scope/auth binding. An in-range masked execute with `authorization_id=None` still reaches the monitor and terminates 0 when blocked. Other in-range masked actions produce a deterministic environment fault without ledger/tool/answer mutation.
8. Evaluate only with internally owned `EvaluationPlan`, `TaskSnapshot`, monitor audits, authorization events, and optional typed terminal action. Task 2B is the sole reward authority.
9. Evaluator termination precedes truncation. If still nonterminal after decision `H`, expire active authority at `H+1`, append allowlisted expiry events, re-evaluate to bind the final ledger audit/digest, then return `(reward=0, terminated=False, truncated=True)`. For any early terminal, also finalize expiry at `H+1` and re-evaluate; the semantic outcome must not change.
10. Closed episodes expose a deterministic closed post-observation but no selectable live policy state. `terminated` and `truncated` are never both true; `step` after close raises before mutation.

## Task-3A composition freeze

The following choices remove the remaining composition ambiguity. Task 3B must not invent a different binding policy.

1. Select the current task step as the first `PENDING` step in the frozen manifest order. A live catalog has four to six slots: request, nullable-bound execute, deny, and escalate are always syntactically constructible; add refresh only when an explicitly related eligible prior exists, and add disable only when an active record exists. Build at most one semantic slot for each enabled action:
   - request: current step and current scope;
   - execute: current step and current scope, bound to the newest usable covering record; otherwise the newest related/current record for fail-closed monitor testing; otherwise `authorization_id=None`;
   - refresh: current step/scope and the newest explicitly related eligible prior;
   - disable: the newest active record, using that record's own scope;
   - deny: current scope with `public_reason_code=user_declined` after a public denial for that scope, otherwise `public_reason_code=not_needed`; never derive this code from hidden success labels;
   - escalate: current scope with `escalation_target_code=human_owner`.
   Rank records by `(issued_at_step, revision, authorization_id)`. Never silently truncate or choose from private/oracle facts. The catalog therefore contains no more than six slots.
2. A permission request has its own deterministic `permission_request_<16 lowercase hex>` ID derived from scenario ID, logical step, resolved-candidate ID, request kind, and per-episode request ordinal. It is not a public-event ID. The adapter request is exact:
   - new request: `{request_id, scope_identity, logical_step, request_kind="request"}`;
   - refresh: the same fields plus `authorization_id=<prior ID>` and `request_kind="refresh"`.
   The adapter receives the pre-action tuple of verified `PublicEvent` projections, excluding the just-previewed/current request. Never pass `PublicEventRecord` to the adapter.
3. Refresh publication order is frozen. On approval append `permission_granted{authorization_id=new_id}` and then `authorization_refreshed{authorization_id=new_id, prior_authorization_id=prior_id}`. On rejection append only `permission_denied{authorization_id=new_id}`. Update the environment's latest-public-event map for every affected authorization ID.
4. A masked non-execute action or adapter/protocol failure is an environment-owned terminal fault: append `verified_error` with an allowlisted code, do not call the tool, and return reward 0. The evaluator still supplies its structural result/digest, but only the evaluator may award success/reward 1. A masked execute alone is sent to the reference monitor and publishes its returned `execution_result`; do not synthesize `execution_blocked`.
5. Public task and authority projections are explicit. Task phase is derived only from the trusted `TaskSnapshot`; remaining steps are the count of `PENDING` statuses; current step/scope comes from the frozen manifest; last execution code comes from the monitor's public outcome. Project every ledger record with its exact public lifecycle/grant/use/expiry fields and `relation(record.scope, current_scope)`. Derive the candidate-scope re-ask relation through `AuthorizationService.public_summary(...)`; never expose raw preferences or authorization audit payloads.
6. The default private tool plan maps every typed task step's first attempt to `("committed", "completed", deterministic_detail)`. An omitted plan entry represents an unknown outcome; do not invent an unsupported third `MockTool` tuple status. Hash a canonically sorted tuple of plan entries and bind only its version/hash in trusted trace metadata.
7. Finalization appends expiry events in authorization-ID order at `H+1`, delivers them to the adapter, re-evaluates with the same terminal action, and always returns the closed Task-3A observation at `logical_step=H+1`, including early terminal cases.
8. Task 3B owns explicit `fixture_set`, `tool_plan`, and `trace_schema` version constants. Bind them with `scenario_hash(manifest)`, `DEFAULT_CONFIG` environment/contracts/authorization versions, `adapter.version`, and `EVALUATOR_VERSION`. Constructor injection may select the trusted manifest/adapter/tool plan; `reset(options=...)` accepts only `{}` or `{scenario_id}` and never accepts a tool plan or oracle through public options.

## Exact action dispatch

- `REQUEST_AUTHORIZATION`: preview permission-request record; `start_request(scope,t,event_id,H+1)`; commit request; call adapter once with prior public history; `apply_permission_choice(new_id,choice,t)`; append grant/deny event.
- `REQUEST_REFRESH`: same flow through `start_refresh(prior_id,scope,t,event_id,H+1)`. Related EXACT/NARROWER/BROADER prior only; DISJOINT requires a new request. Refresh always creates a new record.
- `DISABLE_LOCAL_AUTHORIZATION`: `disable(bound_active_id,t)` only; append public disable event; no answer.
- `EXECUTE_WITH_AUTHORIZATION`: build the exact `ExecutionIntent`; call monitor once; append only its allowlisted public result; no direct ledger reservation/tool/task mutation.
- `DENY_WITH_REASON` / `ESCALATE`: append allowlisted public action event and pass the exact typed terminal action to evaluator.

Maintain an environment-owned public `authorization_id -> latest PublicEventRecord ID` map. Do not mistake the ledger record's `source_public_event_id` for the latest public authority event, and never expose ledger audit IDs/payloads as public history.

## Deterministic mock-tool plan

Canonical fixtures contain no typed tool outcome plan; bare `MockTool()` makes execution unknown. Define an internal trusted versioned factory that maps each typed canonical `TaskStep` to a deterministic first-attempt committed outcome. It must derive only from typed scenario/task data, never hidden postcondition or legal/prohibited prose, and must be inaccessible to observation/mask/public info. Bind tool-plan version/hash only in audit/trace metadata. Allow test injection of deterministic absent/commit/unknown plans without widening the policy interface.

## `info` and trace boundary

Return a deeply frozen mapping with exactly `public` and `audit` branches.

- `public`: observation/catalog/event-head hashes, selected index/resolved slot ID, public reason/new public event IDs, and terminal/truncation reason only.
- `audit`: immutable logger/evaluator evidence and hashes, never live handles. It may include snapshots, evaluator result/digest, and full/delta authorization/execution events.

Neither observation construction nor policy replay inputs may read `info.audit`.

`EpisodeTrace` must bind scenario/fixture/config/contracts/auth-policy/adapter/evaluator/tool-plan versions and hashes; seed/trace ID/endpoint; initial and each pre/post observation hash; catalog/mask; action index/resolved/base IDs; public chain; reward/flags/reason; final evaluator result/digest/task snapshot; authorization/execution chains and heads; and a canonical trace hash. Exclude permit/HMAC keys, object identities, and repr values.

## Replay algorithm

1. Strictly validate trace types/schema/hash/version and canonical manifest binding.
2. Independently verify the public-event chain, `AuthorizationService.replay(manifest.scenario_id, events)`, `ReferenceMonitor.verify_audit_chain`, and `PostconditionEvaluator.evaluate` against the supplied final typed evidence.
3. Instantiate a fresh environment from canonical scenario + recorded seed and replay **only** the recorded action indices.
4. At every transition compare semantic pre/post observations, catalog/mask, resolved/base binding, public and trusted audit deltas, reward/flags/reason. Require close at the exact recorded step and no trailing actions.
5. Seal the fresh trace and compare every deterministic semantic field/hash. Random monitor permit secrets are deliberately excluded, so independent fresh monitors must replay identically.

Any mutation, deletion, duplication, reorder, seed/scenario/version mismatch, index/binding/catalog/mask/observation mismatch, reward/flag/evaluator/snapshot/audit mismatch, or fully rehashed semantically invalid history raises a precise `ReplayFailure`. Do not silently repair. A wholly replaced new semantically valid history remains outside this prototype's origin-authentication claim.

## Mandatory TDD tests

Write real failing tests first. At minimum cover:

1. Reset/options/seed/lifecycle, fresh component isolation, scenario-ID ledger binding, and exact `H+1` endpoint.
2. Request/allow-once event-ID two-phase binding; pre-observation contains no answer; one adapter answer; grant alone open/reward 0.
3. Six-action spy matrix: answer counts request/refresh=1, all other actions/reset/observe/masked paths=0; execute calls monitor only; deny/escalate pass typed action.
4. Fixture 1 terminal task success; fixture 2 reusable two-step; fixtures 4/5/6 disable/refresh/new-record/supersede; fixture 7 persistent denial; fixtures 8/9 exact safe outcomes and wrong terminal action 0.
5. Forced masked execute with no/stale/revoked/wrong/superseded/mismatched authority reaches monitor and has no protected effect. Other masked action faults without adapter/ledger/tool mutation. Bad index/type/lifecycle raises before any hash/cursor/audit change.
6. Terminal/truncation matrix; early terminal and horizon expiry at `H+1`; final evaluator digest uses final ledger events.
7. Corrected fixture 10: request first, execute first, new request for disjoint second scope; consume second answer; truncate exactly at decision 3 with reward 0, no second execution/task success. A legacy one-response injection faults on exhaustion rather than truncating.
8. All ten canonical legal traces selected by semantic slot binding, not hard-coded indices; prohibited execute paths mask/fail closed without unauthorized effect.
9. Deterministic tool plan succeeds; bare/missing plan becomes unknown terminal 0, never false success. Private/oracle/tool-plan canaries never enter observation/public info/mask.
10. Two fresh envs with identical scenario/seed/indices produce identical semantic traces despite distinct random permit secrets.
11. Happy replay for all ten traces; table-driven mutation of every bound trace field fails precisely.
12. Fully rehashed invalid authorization lifecycle, reversed/false-check execution audit, and illegal public-event sequence fail semantic replay; wholesale valid replacement limitation is documented.
13. `info.audit` canaries are recursively absent from observation, `info.public`, public event payloads, and replay-policy inputs.
14. All prior suites remain green; standard-library dependency set remains unchanged.

## Verification and report

Run focused environment/replay tests, full discovery, and `python -m compileall -q src`. Write `docs/implementation_reports/task-3b-report.md` with RED/GREEN evidence, exact dispatch and finalization choices, tool-plan schema/version, public/audit boundary, replay evidence, test counts, deviations, and concerns. Do not mark Task 3 complete before independent review.
