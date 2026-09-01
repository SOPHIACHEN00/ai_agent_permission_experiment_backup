# Task 2A Brief — Complete Mediation, Mock Effects, and Task Progress

## Role

Implement the deterministic execution chain:

`ExecutionIntent → ReferenceMonitor → AuthorizationService reserve → one-shot MockTool permit → effect triage → ledger settlement → TaskEngine progress → audit/public result`

This task does not calculate reward and does not implement the environment, UserAdapter, action mask, Gymnasium, or learning.

## Binding constraints

- Reuse Task 0 six-action/Scope/PublicEvent/version contracts and Task 1 scope/ledger APIs.
- Only `EXECUTE_WITH_AUTHORIZATION` may enter protected execution.
- Action masks are not a security boundary; tests must inject invalid execute intents directly into the monitor.
- No real tools or sensitive data. Standard library runtime and `unittest` only.
- Task manifest `TaskStep` is authoritative for step ID, scope, order, and `protected`; controller-supplied scope/protection is never trusted.
- An execution action names an explicit `authorization_id`; monitor must reserve exactly that record.

## Effects and immutable types

Create `effects.py` with:

- `ProtectedEffectStatus`: `absent`, `committed`, `unknown`.
- `ExecutionDisposition`: `blocked`, `absent`, `committed`, `unknown`, `system_conflict`.
- Frozen `ExecutionIntent`: candidate ID, action, task step ID, explicit authorization ID or `None`, supplied operation Scope, logical step, environment version, authorization policy version. Constructor must reject non-execute actions and malformed identifiers/types.
- Frozen private one-shot `ExecutionPermit`: deterministic call/attempt ID, step ID, scope hash, authorization/reservation correlation, logical step, and integrity tag minted by a private permit issuer shared only by monitor/tool.
- Frozen `MockToolOutcome`: call ID, effect status, allowlisted public result code, immutable private audit detail/effect ID.
- Frozen `MonitoredExecution`: disposition, sanitized `PublicEvent`, audit event ID, immutable task snapshot, attempted-hard-violation flag, terminal-fault flag. It must not expose reservation tokens, ledger revision, full audit payload, permit, or private tool detail.

Timeout, connection reset, generic exception, missing outcome plan, and malformed outcome default/fail closed to `unknown`. Only an explicit `absent_before_effect` plan entry may produce `absent`.

## Deterministic Mock Tool

Implement a synthetic tool driven by a private outcome plan:

`(scenario_id, task_step_id, attempt_index) -> planned status/result/private detail`.

- Missing plan → `unknown`.
- Tool accepts only a valid, integrity-checked, unused permit bound to call ID, task step, scope hash, reservation, and logical step.
- Reused/forged/mismatched permit causes no effect and fails closed.
- Track invocation count and committed effect IDs for tests/audit.
- Tool cannot create grants, update ledger/task/reward, create PublicEvent, or accept a policy-provided protected flag.
- Public result codes use a fixed allowlist; raw/private detail is never copied into PublicEvent.

## Task Engine

Create authoritative ordered task progress from a `ScenarioManifest` or an explicit tuple of `TaskStep` values.

Step status: `pending`, `committed`, `effect_unknown`.

- Only the first pending step is executable.
- Unknown/duplicate/out-of-order/finished step is rejected before tool invocation.
- Supplied scope must equal the manifest-declared operation scope exactly; no controller scope substitution.
- `absent` and blocked attempts leave the step pending.
- Trusted committed receipt changes current pending → committed.
- Trusted unknown receipt changes current pending → effect_unknown, which is absorbing and blocks further progress.
- Receipts are idempotent by effect ID; duplicate receipt cannot advance another step.
- Same-scope steps remain distinct by step ID.

Frozen `TaskSnapshot` includes scenario ID, revision, ordered `(step_id,status)` values, committed/unknown effect IDs, next required step ID, `primary_complete`, and `has_unknown_effect`.

## Reference Monitor

`ReferenceMonitor.execute(intent) -> MonitoredExecution` is the only public execution entrypoint.

Precheck and settlement order:

1. Validate intent action/types/versions/candidate ID binding.
2. Resolve authoritative current TaskStep; reject unknown/completed/out-of-order/scope mismatch.
3. Apply ledger expiry at the intent logical step.
4. For a protected step require explicit authorization ID, resolve that exact record, require active/unexpired/remaining authority/policy version, and structurally cover the authoritative operation scope.
5. Read the authoritative current revision and CAS-reserve that named record; never trust a policy-supplied revision.
6. Mint a private one-shot permit only after reserve succeeds; call MockTool exactly once.
7. Settle in the same logical step:
   - `absent`: ledger abort; task remains pending.
   - `committed`: ledger commit; record trusted committed effect in TaskEngine.
   - `unknown`: ledger reconciliation-required; record effect-unknown in TaskEngine.
8. Append an immutable execution audit event, then separately build an allowlisted PublicEvent.

Any precheck block performs no reserve/tool/task mutation. Unauthorized, missing auth, scope mismatch, stale/terminal auth, invalid version/schema/candidate, or forced masked execute records a blocked attempted hard violation and terminal fault.

If the tool reports `committed` but ledger commit fails, never abort/reuse the grant. Attempt reconciliation lock while the record is still reserved; record `system_conflict`, leave task incomplete/unknown as appropriate, and terminal fault.

## Audit/public separation

Execution audit is append-only and hash-chained (same documented limitation as Task 1: not authenticated hostile-storage protection). At minimum record attempt/event IDs, intent/task/auth IDs, scope hash, monitor checks, reservation correlation, tool call/effect status/effect ID, task revisions before/after, versions, disposition/fault, previous/event hash.

Build PublicEvent from a positive allowlist only:

- `task_step_id`
- public outcome: `completed`, `failed_before_effect`, `outcome_unknown`, or `blocked`
- coarse public reason code

Never expose audit check vector/payload, oracle postcondition, full Scope, auth/ledger revisions, reservation/permit, raw tool result/private detail, hidden plan, or future outcome.

## TDD tests

Write tests first, run and capture RED, then implement minimal code and run task/full suites.

Required tests:

1. Forced execute with no grant: blocked, tool count 0, task unchanged, attempted violation true.
2. Named wrong/missing/revoked/expired/consumed/reserved grant and scope/version/candidate mismatch each fail closed before tool.
3. One-time committed effect: exact reserve → one tool call/effect → commit consumed → task complete.
4. Reusable same-scope two-step task: first commit returns grant active but task incomplete; second distinct step/effect completes task.
5. Explicit absent-before-effect: abort → grant active, task pending, nonterminal; a later committed retry succeeds.
6. Missing outcome, timeout, generic exception → unknown; ledger reconciliation-required, task unknown, retry blocked.
7. Blocked/absent/unknown/duplicate/out-of-order never advance to a later task step or call tool improperly.
8. Tool rejects forged, reused, wrong-call, wrong-step, wrong-scope, or wrong-reservation permit with zero protected effect.
9. Controller cannot alter manifest `protected` or supplied scope.
10. Committed-effect then injected ledger-commit failure never aborts to active; monitor records system conflict/reconciliation and terminal fault.
11. Audit chain detects corruption/reorder and contains blocked attempts as well as successes.
12. Public event/MonitoredExecution cannot contain oracle canary, raw detail, permit/token, revision, audit payload/check vector, or future plan.
13. Same deterministic inputs produce identical semantic results/audit hashes when instance IDs/seeds are identical.
14. Six-action catalog remains unchanged and no deferred action appears.

## Out of scope

- PostconditionEvaluator/S0 reward is Task 2B.
- No environment `reset/step`, candidate mask, ScriptedUser, Q-learning, DDQN/PPO, or S-QSTN.
- No real concurrency; Task 1 CAS is the authority primitive.

## Required report

Write `docs/implementation_reports/task-2a-report.md` with status, files, exact RED/GREEN evidence/test counts, effect/permit/audit decisions, deviations, and concerns.

