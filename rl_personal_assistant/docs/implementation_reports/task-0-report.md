# Task 0 Implementation Report — Increment 0 Contracts and Canonical Fixtures

## Status

DONE

## Files created/changed

- `pyproject.toml`
- `src/pa_rl/__init__.py`
- `src/pa_rl/config.py`
- `src/pa_rl/contracts.py`
- `src/pa_rl/scenarios.py`
- `tests/test_contracts.py`
- `fixtures/scenarios/01_one_time_grant_success.json`
- `fixtures/scenarios/02_reusable_grant_two_steps.json`
- `fixtures/scenarios/03_execution_without_grant.json`
- `fixtures/scenarios/04_local_disable_revocation.json`
- `fixtures/scenarios/05_consumed_one_time_refresh.json`
- `fixtures/scenarios/06_broader_scope_refresh.json`
- `fixtures/scenarios/07_persistent_denial.json`
- `fixtures/scenarios/08_safe_impossibility_deny.json`
- `fixtures/scenarios/09_safe_impossibility_escalate.json`
- `fixtures/scenarios/10_timeout_truncation.json`
- `task_plan.md`
- `docs/implementation_reports/task-0-report.md`

## RED evidence

The test was written before the `pa_rl` package and fixtures existed.

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected failure reason:

```text
ModuleNotFoundError: No module named 'pa_rl'
```

This was the intended missing-production-module failure, rather than a test typo or a pre-existing behavior passing unexpectedly.

## GREEN evidence

Task contract suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Result: `Ran 13 tests in 0.008s` — `OK`.

Project suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Result: `Ran 13 tests in 0.009s` — `OK`.

Syntax check command:

```powershell
python -m compileall -q src
```

Result: successful with no output.

## Decisions and deviations

- The implementation is an independent Python 3.12 project and runtime code imports only the standard library.
- The candidate catalog sorts both scopes and enabled actions before assigning SHA-256-derived identifiers; neither source list insertion order changes the result.
- Scenario horizon validation intentionally lives in the scenario contract, not global configuration, because each fixture supplies its own horizon.
- `allow_once`/`allow_reuse` remain user choices. This increment defines the grant-type contract only; it does not encode authority transitions.
- Public observation projection includes only scenario ID, public request/task context, and horizon. Scripted responses and evaluator postconditions remain non-public.
- No Gymnasium, learning code, ledger transitions, reference monitor, tool execution, live S-QSTN use, or external dependency was added.
- No deviation from the task brief was made.

## Self-review and remaining concerns

- All required observable contract tests are present and pass, including the six-action restriction, deferred-action parse rejection, permission-response actions, JSON serialization, validation boundaries, canonical ordering/hashing, visibility conflicts, fixtures, visibility projection, and reproducible hashes.
- The package deliberately provides contracts only. Increment 1+ must consume these types without widening the action catalog or exposing private/oracle fields.
- No remaining blocker for Increment 0.

## Fix round 1/5 — review remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/contracts.py`
- `src/pa_rl/scenarios.py`
- `tests/test_contracts.py`
- all ten `fixtures/scenarios/*.json` manifests
- `docs/implementation_reports/task-0-report.md`

### RED evidence

Tests were expanded before changing production code to cover the review findings and the two controller-confirmed gaps (canonical eight-field scopes, full authorization-status lifecycle, typed fixture traces, and separate truncation termination).

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected missing-contract failure:

```text
ImportError: cannot import name 'ExpectedTermination' from 'pa_rl.scenarios'
```

The new test module required the not-yet-implemented termination/typed-scenario contract, so the failure was caused by missing behavior rather than a test assertion mismatch.

### GREEN evidence

Task contract suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Result: `Ran 19 tests in 0.014s` — `OK`.

Project suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Result: `Ran 19 tests in 0.015s` — `OK`.

Syntax check command:

```powershell
python -m compileall -q src
```

Result: successful with no output.

### Decisions

- `Scope` now structurally requires immutable canonical `domain`, `tool`, `resource`, `data_attributes`, `operation`, `purpose`, `recipient`, and `retention` fields. Attributes are sorted, deduplicated, and cannot be empty.
- Candidate construction and factory inputs reject all non-`ControllerAction` values; identifiers are verified against the canonical action/scope digest.
- `AuthorizationStatus` now covers exactly pending, active, reserved, consumed, expired, revoked, superseded, rejected, and reconciliation-required states. No state transition behavior was added.
- A frozen scenario visibility schema is now bound to ingestion/projection. Only schema-classified public fields are projected; scripted responses are private and evaluator/traces/terminal labels are oracle.
- Contract mappings are recursively frozen with standard-library immutable containers; canonical JSON traverses frozen dataclasses/mappings and rejects non-finite floats.
- Each fixture now declares typed protected task steps (with full scopes) plus executable legal and prohibited controller-action traces. Scripted permission choices must align one-for-one with legal request/refresh trace steps.
- `ExpectedTermination.TRUNCATED` is separate from `TerminalSuccessKind`; timeout fixture 10 has no legal terminal success kinds.
- The former hash self-comparison was replaced with independently constructed/reordered mappings and a fixed SHA-256 digest assertion.

### Remaining concerns

The contracts intentionally validate declaration and visibility only; authority transitions, monitor enforcement, and task execution remain out of scope for subsequent increments.

## Fix round 2/5 — fixture relation and trace-scope remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/scenarios.py`
- `tests/test_contracts.py`
- `fixtures/scenarios/02_reusable_grant_two_steps.json`
- `fixtures/scenarios/06_broader_scope_refresh.json`
- `docs/implementation_reports/task-0-report.md`

### RED evidence

The tests were extended before production/fixture changes to require exact-scope reuse, a real strict narrow-to-broader attribute relation, request/refresh scope references, and fake-adapter received values.

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Observed result: `FAILED (failures=3)`, `Ran 20 tests in 0.015s`.

Expected failure summaries:

- `ValueError not raised` for both request and refresh traces built without a scope-step reference.
- fixture 02's first and second protected `Scope` values differed (`calendar_api/read` versus `mail_api/send`).

### GREEN evidence

Task contract suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_contracts -v
```

Result: `Ran 20 tests in 0.011s` — `OK`.

Project suite command:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Result: `Ran 20 tests in 0.013s` — `OK`.

Syntax check command:

```powershell
python -m compileall -q src
```

Result: successful with no output.

### Decisions

- `ActionTraceStep` now requires non-null scope-step references for both `REQUEST_AUTHORIZATION` and `REQUEST_REFRESH`, in addition to requiring their permission responses.
- Fixture 02 now uses one complete `calendar_api/calendar.events/read` scope for both protected steps. It demonstrates reusable same-scope authority only; it no longer implies cross-tool reuse.
- Fixture 06 now expresses a genuine narrower-to-broader relation: all scalar scope fields are identical and the refreshed scope's `data_attributes` is a strict superset (`time` to `time,title`). Its legal trace is request/execute narrow followed by refresh/execute broader.
- The adapter test now asserts the reset seed, exact verified event list, and exact public history received by `answer_permission`.

### Remaining concerns

No Increment 0 contract blocker remains. Later increments must implement actual scope-matching and authority transitions against these declarative fixtures.
