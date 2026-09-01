# Task 1 Implementation Report — Increment 1 Scope Matcher and Authorization Ledger

## Status

DONE

## Files created/changed

- `src/pa_rl/scope_matching.py`
- `src/pa_rl/authorization.py`
- `tests/test_authorization.py`
- `docs/implementation_reports/task-1-report.md`

## RED evidence

The Increment 1 behavioral suite was written before either production module existed.

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected failure:

```text
ModuleNotFoundError: No module named 'pa_rl.authorization'
```

The failure was caused by the missing authorization implementation, rather than a test assertion or test-discovery error.

## GREEN evidence

Increment 1 task suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Result: `Ran 15 tests in 0.009s` — `OK`.

Full project suite and syntax command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; python -m compileall -q src
```

Result: `Ran 35 tests in 0.023s` — `OK`; compilation completed with no output.

## Lifecycle and ontology decisions

- The versioned structural matcher is `scope_ontology_v0`. It implements exact scalar matching, grant-only suffix-resource wildcards, attribute-set containment, and the frozen retention ordering `none < transient < episode < session`. An operation resource containing `*` never obtains coverage.
- `exact` applies only to structurally identical scopes. `narrower` and `broader` are derived solely through the same deterministic coverage rules; all remaining combinations are `disjoint`.
- The ledger begins each request as `pending` and can mint active authority only through `apply_permission_choice` with `allow_once` or `allow_reuse`. Denials create rejected records and separate episode-bounded re-ask preferences.
- Requests, transitions, preferences, reservations, and public summaries use frozen dataclasses. The service’s only mutable state is private record/preference/event storage.
- Reservation is a compare-and-swap transition from `active` to `reserved`. Commit, abort, and reconciliation transitions are terminal or restoring exactly as specified; stale tokens and expected revisions fail closed.
- Refresh creates a distinct pending record linked to the prior ID. A prior active record is superseded only after the refreshed record becomes active; terminal prior records are never revived.
- Every state transition appends a deterministic, payload-hashed logical event. Replay validates event sequence, step order, ID/hash, actor/version, typed payload, revision chain, immutable fields, and lifecycle transition before reconstructing state.
- Services default to the v0 episode boundary (step 8); callers may declare an earlier episode-bounded expiry. No state, grant, or re-ask preference transfers to a new service/episode.

## Deviations

None. No fixtures, design documents, reference monitor, environment, tools, reward logic, Gymnasium integration, or policy/learning code were changed or added.

## Concerns

No blocking concern. The default boundary of step 8 reflects the frozen v0 maximum scenario horizon; a later environment integration should pass each scenario’s actual horizon to `AuthorizationService(episode_end_step=...)`.

## Fix round 1/5 — review remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/authorization.py`
- `tests/test_authorization.py`
- `docs/implementation_reports/task-1-report.md`

### RED evidence

The review-required behavioural cases were added before modifying the ledger: self-consistent forged request replay, named multi-grant reservation, monotonic and episode-bound logical time, settlement token boundaries, denial-preference lifetime, refreshed-summary selection, terminal prior refreshes, and deep snapshot immutability.

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Observed result: `FAILED (failures=3, errors=2)`, `Ran 21 tests in 0.016s`.

Expected failure summaries:

- `AuthorizationEvent` lacked `previous_event_hash`/`event_hash`.
- Omitted-ID reservation selected one of two active grants instead of failing closed.
- Live decreasing steps were accepted; early-expiry denial preferences ended before the episode boundary.
- `public_summary(..., step=...)` was unsupported, so it could not be step-aware.

### GREEN evidence

Review-round task suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Result: `Ran 21 tests in 0.015s` — `OK`.

Full project suite and syntax command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; python -m compileall -q src
```

Result: `Ran 41 tests in 0.028s` — `OK`; compilation completed with no output.

### Resolutions

- Replay now validates the complete initial pending-record invariant, deterministic authorization ID, request logical-step consistency, exact payload shape, and every legal mutable-field delta for permission and lifecycle events. A recomputed hash/ID/event-hash rewrite that attempts to mint an initial active record is rejected.
- Events include `previous_event_hash` and deterministic `event_hash`. Replay validates the sequence/hash chain in addition to event IDs, payload hashes, revisions, typed payloads, and transitions. Each live event is fully built before its single append; no event is popped or replaced.
- `reserve` accepts an optional `authorization_id`. A named record must be exactly active, covering, and CAS-current; an omitted selector succeeds only with exactly one active covering grant.
- Every live state change validates monotonic, in-episode logical time. Reservation tokens bind their reservation step; commit, abort, and reconciliation must settle at that same step, preventing later restoration or consumption.
- Denial preferences always last to the episode end. Public summaries accept a logical step and omit expired preferences; they prefer a usable active covering authorization over superseded or terminal fallback records.
- Event and record snapshots remain deeply immutable under externally observable mutation attempts.

### Remaining concern

The hash chain detects accidental corruption, truncation/reordering, and illegal transitions, but it is not an authenticated adversarial trust anchor: a party able to replace the entire event stream and recompute every public hash can still rewrite a semantically valid history. A future deployment requiring hostile-storage resistance must anchor the chain in a trusted append-only store or sign checkpoints.

## Fix round 2/5 — replay lifecycle remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/authorization.py`
- `tests/test_authorization.py`
- `docs/implementation_reports/task-1-report.md`

### RED evidence

Tests were added before the production changes for typed reservation context, self-consistent rehashed late settlement, self-consistent rehashed reserve-at-expiry and early-expiry events, expiry-bound allow choices, and passive public-summary expiry projection.

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Observed result: `FAILED (failures=3, errors=1)`, `Ran 25 tests in 0.018s`.

Expected failure summaries:

- `reserved` events did not expose a reservation logical step, selected ID, or canonical operation scope/hash.
- Replay accepted fully rehashed late settlement, reserve-at-expiry, and early-expiry histories.
- An allow response at pending expiry minted active authority; fallback summary exposed an expired active record as `ACTIVE`.

### GREEN evidence

Review-round task suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Result: `Ran 25 tests in 0.020s` — `OK`.

Full project suite and syntax command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; python -m compileall -q src
```

Result: `Ran 45 tests in 0.032s` — `OK`; compilation completed with no output.

### Resolutions

- `reserved` events now carry immutable typed reservation context: `reservation_logical_step`, selected authorization ID, complete canonical operation scope, and its canonical hash.
- Replay maintains per-authorization reservation context. It rejects a reservation at or after authority expiry, early `expired` events, and commit/abort/reconciliation events not settled at the recorded reservation step. Negative tests rehash every downstream event in the modified stream before replay.
- Live and replayed allow choices reject at or after a pending record's expiry, before any active record can be emitted.
- Public summary never reports an expired active record as active. It passively projects its status as `expired` without mutating the authoritative record or creating a new grant/event.

### Remaining concern

The deterministic hash chain remains deliberately unkeyed. It detects corruption, reordering, and structurally invalid lifecycle histories, but does not authenticate a fully replaced event stream whose public hashes have all been recomputed. Hostile-storage deployments require an external trusted append-only anchor or signed checkpoints.

## Ontology erratum â€” categorical external retention

### Status and version

DONE. The matcher version is advanced from `scope_ontology_v0` to `scope_ontology_v0_1` because this is an observable ontology correction needed by the frozen `persistent_denial` scenario.

### Decision and rationale

- The ordered retention lattice remains frozen as `none < transient < episode < session`.
- `external` is recognized as a separate categorical value, not inserted above or below that lattice. It covers only another `external` value.
- Consequently, an otherwise identical `external` scope covers itself and has relation `exact`; `external` versus any ranked retention is `disjoint` in both directions.
- Treating `external` as ranked would be unsafe: it could let a ranked storage-duration grant authorize external disclosure, or let an external-transfer grant authorize an unrelated local-retention operation. The self-only rule preserves authority boundaries.
- Values outside the five declared terms remain invalid and raise `ValueError`, including when the two unknown strings are identical. No other Task 1 API or lifecycle rule changed.

### RED evidence

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization.ScopeMatchingTests -v
```

Observed result before the production patch: `Ran 5 tests in 0.001s` â€” `FAILED (failures=1, errors=1)`.

- Exact `external` coverage raised `ValueError` because the value was absent from the ranked map.
- `relation` incorrectly returned `exact` for two identical unknown retention strings before validating the ontology.

### GREEN evidence

The same focused command after the minimal matcher patch: `Ran 5 tests in 0.001s` â€” `OK`.

Task 1 command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization -v
```

Result: `Ran 27 tests in 0.025s` â€” `OK`.

Full project and syntax commands:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Final result: `Ran 166 tests in 1.266s` â€” `OK`; compilation completed with no output. An earlier full-suite run overlapped another Increment 3 file update and transiently observed one unrelated unprotected-mask assertion failure; the isolated test immediately passed, and the clean rerun above passed all 166 tests.
