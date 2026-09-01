# Task 3A Implementation Report — Public Interaction and Policy Interface Kernel

## Status

Task 3A is implemented and verified. This report does **not** mark Task 3 complete: Task 3B still owns the live environment, monitor/evaluator dispatch, horizon finalization, episode trace/replay, and all RL/baseline work.

## Files changed

- `src/pa_rl/scripted_user.py` — deterministic `ScriptedUserAdapter` and typed fail-closed boundary error.
- `src/pa_rl/public_events.py` — immutable public records, canonical SHA-256 chain, verification, and two-phase `preview`/`commit` API.
- `src/pa_rl/policy_interface.py` — `ResolvedCandidate`, `CandidateCatalog`, explicit-public `PublicMaskState`, action mask, and `EnvironmentObservation` builder.
- `tests/test_scripted_user.py` — adapter FIFO/reset/public-input tests.
- `tests/test_policy_interface.py` — event chain, resolved catalog/mask, event prebinding, monitor-forced unbound execute, and observation-firewall tests.
- `tests/test_contracts.py` — fixture-10 migration and one-answer-for-third-request rejection regression.
- `fixtures/scenarios/10_timeout_truncation.json` — authorized three-decision/two-answer migration only.
- `docs/implementation_reports/task-3a-report.md` — this report.

No Task 0–2B production contract was changed. No `environment.py`, environment `reset`/`step`, evaluator dispatch, reward computation, trace replay, baseline, RL, live S-QSTN, design document, or task plan was added or edited.

## TDD evidence

Initial observable RED was run after adding the new tests and before either Task-3A production module existed:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_policy_interface -v
```

Observed result: `Ran 2 tests`, `FAILED (errors=2)`. Both failures were expected `ModuleNotFoundError`s for the absent `pa_rl.scripted_user` and `pa_rl.policy_interface` modules.

The Task-3B preflight additions also followed a real RED/GREEN cycle. Before the final minimal changes, the focused policy suite reported `Ran 9 tests`, `FAILED (failures=2, errors=3)`: `PublicEventChain.preview` was absent, valid no-head chain verification failed, stale public fields were accepted by the observation/mask interfaces, and an unbound execute-shaped resolved slot was rejected instead of becoming mask-invalid.

## GREEN verification

Scoped suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_policy_interface tests.test_contracts -v
```

Result: `Ran 35 tests in 0.036s` — `OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
python -m compileall -q src
```

Result: `Ran 125 tests in 0.200s` — `OK`; `compileall -q src` exited `0` with no output.

## Public schemas and firewall

`PublicEventRecord` has exactly these frozen fields: `sequence`, `event_id`, `logical_step`, `event_type`, immutable `payload`, `payload_hash`, `previous_event_hash`, and `event_hash`. Records are generated with canonical JSON/SHA-256. `preview(...)` builds a head-bound record without mutation; `commit(record)` accepts only the exact next sequence and current previous head, allowing Task 3B to bind the same event ID into `AuthorizationService.start_request` or `start_refresh` before publication.

The chain verifier rejects malformed types, sequence/linkage faults, duplicate/reordered records, invalid event types/payload fields, changed hashes, and truncation when an expected head or length is supplied. It detects supplied-history corruption and invalid transitions, but is deliberately **not** a MAC, signature, or hostile-storage origin-authentication claim.

`ResolvedCandidate` wraps the unchanged Task-0 `ActionCandidate` and preserves its exact base candidate ID. Its canonical binding includes slot, action, public scope identity/hash, task step, selected authorization, prior authorization, and positive allowlisted reason/escalation codes. Catalog construction sorts independent of caller ordering, renumbers deterministic slots, rejects duplicate semantics, and rejects more than `16` slots. An execute-shaped candidate with no authorization ID is intentionally representable solely for Task-3B forced-mask monitor mediation; its public mask is false and no constructor grants it authority.

The mask accepts only `PublicMaskState` public task/ledger summaries and resolved slots. It never accepts a permission choice, tool result, evaluator result/digest, raw audit, authorization reservation, or oracle object. Terminal deny/escalate slots stay selectable. The observation builder produces only the following top-level keys:

`scenario_id`, `environment_version`, `logical_step`, `horizon`, `horizon_remaining`, `request_context`, `task_view`, `authorization_views`, `interaction_history`, `candidate_catalog`, `catalog_hash`, and `action_mask`.

`task_view` and authorization summaries use fixed field allowlists; request contexts reject recursively named private/oracle/future/audit/evaluator/permit/reservation fields. History is exactly four padded public record views and derives prompt, choice, denial, revocation, grant, verified-error, and alpha-1.0 response statistics only from records already appended. All returned mappings/sequences are recursively frozen.

## Fixture 10 migration

The only fixture change is the authorized correction in `10_timeout_truncation.json`:

- Before: one `allow_once`; `REQUEST_AUTHORIZATION(first_step) -> EXECUTE_WITH_AUTHORIZATION(first_step)`.
- After: two `allow_once` choices; `REQUEST_AUTHORIZATION(first_step) -> EXECUTE_WITH_AUTHORIZATION(first_step) -> REQUEST_AUTHORIZATION(second_step)`.

The third action is specifically a new request, not `REQUEST_REFRESH`; the scopes are unrelated. The fixture retains horizon `3`, no legal terminal-success kinds, both protected steps, and `truncated` expected termination. The regression rejects a one-answer declaration against the now-required third request. Task 3B remains responsible for executing that path and demonstrating its truncation behavior.

## Concerns and remaining work

- The public hash chain is an integrity/replay consistency mechanism, not source authentication against wholesale replacement by a party able to recompute an entire semantically valid history.
- Task 3B must use only `preview` then `commit` for public events that need to bind a ledger request ID, pass verified `PublicEvent` projections to the adapter, and construct `ExecutionIntent` with the preserved Task-0 base candidate ID.
- No terminal/truncation/reward claim is made here; those trusted semantics remain exclusively in the already-approved evaluator and the pending environment composition.

## Fix round 1 — Task 3A review remediation

### Status

Implemented and verified; this remains only the Task 3A public-side kernel. Task 3 is not marked complete.

### Review resolutions

1. `ScriptedUserAdapter.reset` now accepts the real, non-empty `project_public_observation(manifest)` projection, including typed public `TaskStep`/`Scope` values, and rejects anything other than that exact visibility-bound shape.
2. Public mask semantics now use Task 1's `exact`/`narrower` coverage relation, accept reusable `remaining_uses=None`, require an existing non-disjoint eligible prior for refresh, permit disable only for active authority, and apply re-ask preferences by the resolved candidate's public scope identity.
3. Every exported boundary now validates and freezes recursive JSON-only public values. `PublicMaskState` validates exact task/ledger schemas, the observation validates direct construction, and history first independently verifies its entire public event chain.
4. `ResolvedCandidate` has an action-specific required/forbidden binding matrix, canonical authorization/task bindings, positive reason/target vocabularies, semantic deduplication, and direct `CandidateCatalog` canonical-order/hash validation. The sole preserved nullable binding is execute-shaped `authorization_id=None`, which remains mask-invalid for monitor mediation.
5. Public records validate exact non-Boolean positive sequence/logical steps, identifier/hash syntax and values, plus type-specific exact payload schemas. Fully recomputed invalid records fail verification.
6. The closed observation is exactly `logical_step=H+1`, `horizon_remaining=0`, empty catalog/mask, and `catalog_hash=canonical_hash(())`; it can carry the finalized verified public history.

### Event schemas supplied to Task 3B

- `permission_requested`: `{request_id}`.
- `permission_granted`, `permission_denied`, `authorization_revoked`, `local_authorization_disabled`, `authorization_expired`: `{authorization_id}`.
- `authorization_refreshed`: `{authorization_id, prior_authorization_id}`.
- `execution_result`: `{task_step_id, outcome, reason_code}`; `execution_blocked`: `{task_step_id, reason_code}`.
- `denied_with_reason`: `{public_reason_code}`; `escalated`: `{escalation_target_code}`; `verified_error`: `{error_code}`.

Authorization IDs use `authorization_` plus 20 lowercase hexadecimal characters. The positive reason vocabulary is `not_needed`, `user_declined`, and `safe_impossibility`; escalation targets are `human_owner` and `security_owner`.

### TDD evidence

The new `tests/test_task3a_review.py` suite was written before the review remediation. Its first run reported `Ran 7 tests`, `FAILED (failures=7, errors=1)`: real public projection reset failed, broader/disjoint/reusable masking was wrong, request preferences were ignored, direct/private boundary inputs were accepted, event schemas accepted cross-type payloads, and the closed observation could not be constructed. The focused GREEN rerun reported `Ran 7 tests in 0.007s` — `OK`.

### Fresh GREEN verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_policy_interface tests.test_contracts tests.test_task3a_review -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python -m compileall -q src
```

Results: scoped `Ran 42 tests in 0.038s` — `OK`; full `Ran 132 tests in 0.179s` — `OK`; compilation exited `0` without output.

### Remaining boundary

The public chain remains a deterministic supplied-history integrity check, not a signature/MAC or protection against a hostile party replacing an entire history with a new semantically valid one. Task 3B must use the event schemas and the explicit `H+1` closed-observation representation above.

## Fix round 2 — Task 3A re-review remediation

### Status and scope

All five Fix-round-2 required resolutions are implemented and verified. Task 3A remains pending reviewer acceptance; Task 3 is not marked complete, and no Task 3B environment, dispatch, replay, baseline, RL, or live S-QSTN work was started.

### Review resolutions

1. `REQUEST_REFRESH` now positively requires an existing authorization whose public scope relation is exactly one of `exact`, `narrower`, or `broader`. Missing, `None`, and `disjoint` relations fail closed. Eligible lifecycle states are `active`, `consumed`, `expired`, `revoked`, and `superseded`; `pending` and `rejected` are ineligible. Both request and refresh candidates obey the requested scope's `do_not_reask_until_scope_change` preference, so same-scope refresh cannot bypass a persistent denial preference. `EXECUTE_WITH_AUTHORIZATION` still requires active authority; reusable grants use `remaining_uses=None`.
2. Authorization summaries now use exact positive vocabularies and enforce cross-field consistency for status, grant kind, remaining uses, expiry, last public authority-event ID, scope relation, and re-ask preference. `EnvironmentObservation` direct construction now exact-validates and recursively freezes every catalog entry and every nested interaction-history structure; arbitrary JSON, mutable nested aliases, forged counts/rates, reordered history, and private data fail closed.
3. `request_context` is an exact positive public schema: `{request: <non-empty string>, task: <non-empty string>}`. It is derived from the canonical fixture projection, accepts all ten current fixture contexts, and rejects extensions—including recursive/case-variant private, oracle, future, hidden, audit, evaluator, permit, reservation, and effect canaries—even when their scalar values would otherwise be valid JSON.
4. Permission requests passed to `ScriptedUserAdapter.choose_permission` use an exact action-specific matrix. Both forms require canonical `request_id=permission_request_[0-9a-f]{16}`, `scope_identity=scope_[0-9a-f]{16}`, a positive non-Boolean integer `logical_step`, and `request_kind` in `{request, refresh}`. A new `request` must omit `authorization_id`; a `refresh` must include canonical `authorization_[0-9a-f]{20}`. Validation occurs before advancing the FIFO cursor, so malformed input cannot consume a scripted answer.
5. Isolated attacks cover absent/`None`/disjoint refresh relations, rejected persistent denials, changed-scope preference behavior, the eligible lifecycle table, private-looking strings in otherwise allowed authorization fields, direct observation catalog/history mutation and leakage, malformed request values, and a genuinely recomputed record whose invalid Boolean sequence is rejected on semantics rather than stale hashes.

The event-specific payload schemas and positive reason/target vocabularies remain exactly those documented in Fix round 1. The closed observation also remains exact: `logical_step=H+1`, `horizon_remaining=0`, empty candidate catalog and mask, and `catalog_hash=canonical_hash(())`.

### TDD evidence

The expanded review suite was run before the production fixes. Its first observable RED reported `Ran 13 tests in 0.029s`, `FAILED (failures=19, errors=1)`. The independent direct-history reorder attack was then added before its validation fix and reported `Ran 1 test in 0.004s`, `FAILED (failures=1)`. These failures exercised the requested boundaries rather than placeholder assertions.

### Fresh GREEN verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_policy_interface tests.test_contracts tests.test_task3a_review
$env:PYTHONPATH='src'; python -m unittest discover -s tests
python -m compileall -q src tests
```

Results: scoped `Ran 48 tests in 0.064s` — `OK`; full `Ran 138 tests in 0.221s` — `OK`; `compileall -q src tests` exited `0` with no output.

### Files and remaining concerns

Fix round 2 changed `src/pa_rl/scripted_user.py`, `src/pa_rl/policy_interface.py`, `tests/test_scripted_user.py`, `tests/test_policy_interface.py`, `tests/test_task3a_review.py`, and this report. `src/pa_rl/public_events.py` and fixture 10 retain the reviewed Task-3A/Fix-round-1 implementations without a Fix-round-2 production change.

There is no identified Task 3B compatibility blocker. Task 3B must preserve the two-phase public-event `preview`/`commit` binding and must use the strict permission-request matrix above. The public chain's stated limitation is unchanged: it verifies deterministic internal consistency and supplied-history linkage, not cryptographic origin authentication against wholesale replacement by an attacker able to construct a wholly new semantically valid chain.

## Fix round 3 — Task 3A final-exactness remediation

### Status and scope

The four Fix-round-3 required resolutions are implemented and verified. Task 3A remains pending reviewer acceptance; Task 3 is not marked complete. No Task 3B environment, dispatch, replay, baseline, RL, or live S-QSTN work was started.

### Review resolutions

1. Every non-empty authorization row is now bound to the current public logical step in both `PublicMaskState` and direct `EnvironmentObservation` construction. `expiry_bucket` is exactly `future` iff `expiry_step > logical_step` and exactly `expired` iff `expiry_step <= logical_step`. Active and reserved lifecycle rows require a future bucket, while expired lifecycle rows require an expired bucket. An impossible active/past row is rejected before it can enable refresh; valid active/future and expired/past rows retain their documented refresh eligibility.
2. Direct interaction-history statistics now enforce the global identities `response_counts.total == counts.permission_choice`, `response_counts.allow == counts.grant`, `response_counts.total == allow + deny`, and `counts.denial >= response_counts.deny`. Every count and response category must be at least the contribution visible in the four-record suffix. When the history is all padding or its first real record has sequence 1, every count and response count is recomputed exactly from that complete visible history. Smoothed response rates remain exact. The first real record now has `previous_event_hash=None` exactly when its sequence is 1; a suffix beginning after sequence 1 must carry a non-null predecessor commitment, and subsequent visible records remain contiguous and hash-linked.
3. Direct candidate views now require `public_scope_identity == "scope_" + public_scope_hash[:16]` before accepting their recomputed resolved ID and catalog hash. A caller therefore cannot replace the identity with another syntactically valid value and rehash the surrounding view to detach preference keys from the canonical public scope hash.
4. The changed-scope preference regression now uses an otherwise eligible consumed, exact-related, unexpired prior authorization. It proves a same-scope `do_not_reask_until_scope_change` preference masks refresh while the identical preference attached to another canonical scope identity leaves refresh enabled; rejected status no longer confounds that assertion.

### TDD evidence

The six isolated regressions were added before production changes. The first focused RED reported `Ran 19 tests in 0.036s`, `FAILED (failures=7)`. Those failures were the two expiry-direction assertions, three complete-history statistic attacks, the suffix visible-count underreport, the missing predecessor commitment, and the fully rehashed scope-identity/catalog mismatch. The truly eligible changed-scope characterization was already green, confirming that no production change was needed for that positive path.

The focused GREEN rerun reported `Ran 19 tests in 0.034s` — `OK`.

### Fresh GREEN verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_policy_interface tests.test_contracts tests.test_task3a_review -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Results: scoped `Ran 54 tests in 0.078s` — `OK`; full `Ran 144 tests in 0.232s` — `OK`; `compileall -q src tests` exited `0` with no output.

### Files and remaining concerns

Fix round 3 changed `src/pa_rl/policy_interface.py`, `tests/test_task3a_review.py`, and this report. Task 0 protocol values, base candidate IDs, `ScriptedUserAdapter`, public-event schemas and two-phase chain API, fixture 10, and all Task 1–2B production contracts remain unchanged in this round.

There is no identified Task 3B compatibility blocker. The public-chain limitation is also unchanged: these checks establish exact deterministic semantics and suffix linkage for supplied public history, not cryptographic origin authentication against wholesale replacement by an attacker able to construct a wholly new valid chain.
