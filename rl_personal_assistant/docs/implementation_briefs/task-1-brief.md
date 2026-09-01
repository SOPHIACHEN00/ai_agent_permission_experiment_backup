# Task 1 Brief — Increment 1 Scope Matcher and Authorization Ledger

## Role in the project

Implement the deterministic authority kernel consumed later by the reference monitor. This task owns scope coverage and authorization lifecycle state. It must not implement policy learning, environment stepping, user simulation, tool execution, postcondition reward, or Gymnasium.

## Existing binding contracts

- Reuse the frozen `Scope`, `PermissionChoice`, `GrantType`, `AuthorizationStatus`, canonical serialization, and visibility contracts from Task 0.
- Preserve exactly the six controller actions.
- Runtime dependencies remain Python standard library only.
- User permission choice is the only source that can turn a pending request into an active grant.
- A refresh creates a new record; it never expands or revives the previous record in place.
- All v0 authority expires at the episode boundary.

## Required module 1 — versioned scope matcher

Create a scope-matching module with:

- ontology/version identifier `scope_ontology_v0`;
- `ScopeRelation` values `exact`, `narrower`, `broader`, `disjoint` where the relation describes the requested operation relative to the grant;
- `covers(grant_scope, operation_scope) -> bool`;
- `relation(grant_scope, operation_scope) -> ScopeRelation`.

Coverage rules:

1. `domain`, `tool`, `operation`, `purpose`, and `recipient` require exact equality.
2. Resource permits exact equality or one explicit suffix wildcard only: a grant resource ending in `/*` covers descendants below that prefix; an operation scope cannot create authority by containing a wildcard.
3. Grant `data_attributes` must be a superset of operation attributes.
4. Retention ordering is frozen as `none < transient < episode < session`; an operation may use equal or more conservative retention than the grant, never less conservative/longer retention.
5. No LLM/semantic/fuzzy matching.
6. `exact` means all eight fields equal; `narrower` means grant covers the operation but they are not exact; `broader` means the operation covers the grant but they are not exact; every remaining partial overlap/mismatch is `disjoint`.

## Required module 2 — authoritative ledger

Implement immutable record/event types and an `AuthorizationService` with a private mutable store and append-only event log.

### Authorization record

At minimum record:

- deterministic `authorization_id`;
- `episode_id`;
- `subject="user_self"`;
- `grantor="user_public_event"` after answer and pending grantor before answer;
- `requester="personal_assistant"`;
- full immutable `Scope`;
- optional `GrantType` while pending/rejected;
- complete `AuthorizationStatus`;
- `issued_at_step`, `expires_at_step`;
- `remaining_uses` (`1` for one-time, `None` for episode-bounded reusable, `0` after consumption);
- source public event ID;
- policy version `authorization_policy_v0`;
- monotonic `revision`;
- optional `supersedes_authorization_id`.

### Re-ask preference

Keep denial preference in a separate type/store; it can never authorize execution.

- `deny_persist` creates `do_not_reask_until_scope_change` through episode end.
- `deny_reask` creates `reask_on_new_need` through episode end.

### Required service operations

- start a pending authorization request for a declared scope;
- start a refresh as a new pending record referencing the prior authorization;
- apply one of the four public permission choices;
- disable/revoke an active local authorization;
- expire eligible active authorizations by logical step;
- reserve an active matching authorization with optional expected revision/CAS check;
- commit a reservation after a committed protected effect;
- abort a reservation when the effect definitely did not occur;
- mark a reservation `reconciliation_required` when effect status is unknown;
- return a minimal public ledger summary for a requested operation scope;
- return immutable record/event snapshots;
- reconstruct the same authoritative state from the append-only events.

### Lifecycle rules

- Request creates `pending`, never `active`.
- `allow_once` creates one-time active authority with one remaining use.
- `allow_reuse` creates reusable, episode-bounded active authority.
- Deny creates `rejected` plus a separate preference record.
- A successful refresh grant creates a new active record. An old `active` record becomes `superseded`; an already consumed/expired/revoked record remains in its terminal state.
- Reserve changes active → reserved atomically and returns an immutable reservation token bound to ID/revision.
- One-time commit changes reserved → consumed; reusable commit changes reserved → active.
- Abort changes reserved → active.
- Unknown effect changes reserved → reconciliation-required and cannot be reused.
- Consumed, expired, revoked, superseded, rejected, and reconciliation-required records never return to active. Only a new user grant can create new authority.
- A stale reservation/revision or second concurrent reserve fails closed without changing state.
- Service construction/reset for a new episode starts with no grant or preference from a previous episode.

### Append-only events and replay

- Use logical step, deterministic event IDs, actor, authorization ID, previous/new revision, event type, immutable payload, payload hash, policy/environment version.
- Event payload must contain enough typed information for replay; hash-only events are insufficient.
- Replay must validate event ordering, payload hash, revision chain, and state transitions, then reconstruct records/preferences exactly.
- Public summaries may expose only status/type/use/expiry/scope relation/last public authority event/re-ask relation. They must not expose source oracle fields, hidden reasons, future choices, or full private audit payload.

## TDD and tests

Write tests first and capture RED before production code. Use `unittest` only.

Required observable tests:

1. Scope exact, data-subset narrower, wildcard-resource narrower, retention narrowing, broader relation, and disjoint purpose/recipient/tool cases.
2. Operation wildcard never gains authority.
3. Request is pending; no direct service method accepts controller input to mint active authority.
4. All four permission choices produce the specified grant/rejection/preference behavior.
5. One-time reserve/commit consumes once; a second reserve fails.
6. Reusable reserve/commit returns active and can be reserved again within episode.
7. Abort restores active; unknown effect locks reconciliation.
8. Disable and expiry take effect before reserve and never reactivate.
9. Two reserve attempts from the same revision permit only one.
10. Refresh makes a new record and never mutates scope/ID of the old record; active old becomes superseded only when the new grant activates.
11. Replaying events reproduces the same immutable records, preferences, revisions, and event hashes.
12. Tampered/out-of-order event, payload hash, or revision chain is rejected.
13. Public summary contains no full audit payload/private/oracle canaries.
14. A new episode service starts empty.

## Out of scope

- No reference monitor wrapper yet; reserve is the authoritative primitive it will call.
- No mock tool or postcondition evaluator.
- No environment `reset/step`.
- No policies, Q-learning, DDQN, PPO, or live S-QSTN.
- No thread/process concurrency implementation is required; deterministic CAS semantics and a sequential double-reserve test are required.

## Required report

Write `docs/implementation_reports/task-1-report.md` with status, changed files, RED/GREEN exact commands and counts, lifecycle/ontology decisions, deviations, and concerns.

