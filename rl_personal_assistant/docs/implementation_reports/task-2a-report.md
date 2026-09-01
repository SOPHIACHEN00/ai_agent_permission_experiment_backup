# Task 2A Implementation Report — Complete Mediation, Mock Effects, and Task Progress

## Status

DONE_WITH_CONCERNS

## Files created/changed

- `src/pa_rl/effects.py`
- `src/pa_rl/execution.py`
- `tests/test_execution.py`
- `docs/implementation_reports/task-2a-report.md`

Task 0/1 contracts, authorization implementation, fixtures, and design records were not changed.

## RED evidence

The execution behavioral suite was created before either 2A production module existed.

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected failure:

```text
ModuleNotFoundError: No module named 'pa_rl.effects'
```

This establishes the initial RED was caused by the missing 2A implementation.

One follow-up RED added stale-logical-step coverage after the initial green pass:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Observed result: `FAILED (errors=1)`, `Ran 15 tests in 0.018s`. The monitor propagated `ValueError: logical step must be monotonic and within the current episode` from Task 1 expiry processing. The minimal repair converts that invalid/stale intent into a fail-closed blocked result before reservation or tool invocation.

## GREEN evidence

Task 2A suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Result: `Ran 15 tests in 0.018s — OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 60 tests in 0.053s — OK`; `compileall` completed without output.

## Effect, permit, and audit decisions

- `ExecutionIntent` accepts only the frozen `EXECUTE_WITH_AUTHORIZATION` action, a canonical candidate binding, an explicit task step, a typed `Scope`, positive logical step, and explicit environment/policy versions.
- `TaskEngine` accepts a manifest or immutable task-step tuple; it treats ordered manifest step identity, scope, and protection as authoritative. Only the first pending step can execute. Committed and unknown effect receipts are idempotent by effect ID; an unknown receipt is absorbing.
- `ReferenceMonitor.execute` is the sole execution entrypoint. It validates intent/candidate/version, resolves the authoritative step, expires ledger authority, requires the exact named active record, uses Task 1's CAS reservation at the authoritative revision, mints one permit, calls the mock tool once, and settles in the same logical step.
- `MockTool` is synthetic and plan-driven. Missing, malformed, timeout, or exception plans fail closed as `unknown`; only explicit `absent_before_effect` returns `absent`. It tracks invocations and committed synthetic effect IDs and cannot update ledger, task, reward, or public events.
- A monitor-private permit issuer integrity-tags permits using call ID, task step, scope hash, reservation correlation, and logical step. The tool rejects forged, changed, or reused permits without adding an effect.
- Commit failure after a reported effect never aborts the reservation. The monitor attempts Task 1 reconciliation lock, records an unknown task receipt, returns `system_conflict`, and raises a terminal fault.
- Execution audit entries are immutable, append-only, payload-hashed, and hash-chained. Public results are independently built from the positive allowlist: task step, coarse outcome, and coarse reason only.

## Coverage summary

The 15 tests cover forced masked execution; named missing/revoked/expired/consumed/reserved authority; scope/version/candidate/stale-step failures; one-time and reusable settlement; absent retry; unknown outcome locks; ordered task progress; forged/reused/mismatched permits; duplicate receipts; commit-conflict reconciliation; audit corruption/reordering; public/private separation; deterministic replay semantics; and the unchanged six-action catalog.

## Deviations

None. No evaluator, environment, reward, UserAdapter, action mask, Gymnasium integration, policy, or RL implementation was added.

## Concerns

- As documented for Task 1, the audit chain detects corruption and reordering but is not an authenticated hostile-storage primitive; a deployment needing adversarial storage resistance requires a trusted append-only anchor or signatures.
- Python cannot make a capability type cryptographically inaccessible to same-process code. The permit issuer and tool binding are module-private by convention, while integrity tags and one-shot tracking enforce the runtime boundary used by this deterministic experiment.

## Fix round 1/5 — independent review remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/effects.py`
- `src/pa_rl/execution.py`
- `tests/test_execution.py`
- `docs/implementation_reports/task-2a-report.md`

Task 0/1 APIs and implementation, fixtures, design documents, evaluator, environment, and RL code remain unchanged.

### RED evidence

Attack-oriented tests were added before the remediation production changes:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected failure:

```text
ImportError: cannot import name 'TaskEffectReceipt' from 'pa_rl.execution'
```

The test imports the required trusted-receipt boundary, which did not exist. The same RED set also introduces a recreated-issuer permit forgery, actual throwing tool, active wrong-scope named grant, post-unknown receipt, unprotected manifest step, exact public/audit schema, malformed identifier, and malformed/wrong-call outcome cases.

### GREEN evidence

Task 2A suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Result: `Ran 22 tests in 0.037s — OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 67 tests in 0.063s — OK`; `compileall` completed with no output.

### Resolutions

- Permit tags now use a `secrets.token_bytes(32)` per-issuer HMAC key and constant-time comparison. The public monitor instance ID is not key material. Permits bind scenario ID, tool call ID, task step, scope hash, reservation correlation, attempt index, and logical step. The random tag/key are never placed in audit or public results, preserving semantic audit determinism for equal inputs and IDs.
- The effect method is narrowed to module-private `MockTool._invoke(permit)`; the caller cannot pass a scenario. A recreated issuer built with the known instance ID produces a tag that the already-bound tool rejects without a committed effect.
- `TaskEffectReceipt` is capability-bound to a monitor-private object. `TaskEngine.apply_receipt` accepts only a receipt issued by its bound monitor, validates typed IDs/status, treats duplicate effect IDs idempotently, and rejects all non-duplicate receipts after `effect_unknown`.
- The monitor catches real `Exception` values from the tool boundary, malformed/non-`MockToolOutcome` returns, and wrong returned call IDs. Each becomes an unknown same-step settlement (Task 1 reconciliation for protected steps), an absorbing task receipt, audit entry, and allowlisted public result.
- `MockToolOutcome` now validates call/effect identifier syntax, effect-status/result-code combinations, effect-ID presence, mapping detail type, and canonical serializability. Planned malformed/unserializable data fails closed to unknown.
- Audit payloads now carry deterministic `attempt_id`, `attempt_index`, `tool_call_id`, and `reservation_correlation`, alongside the existing immutable/hash-chained fields. Tests assert the exact audit-key schema and the exact public allowlist `{task_step_id, outcome, reason_code}`.
- Authoritative unprotected task steps still execute only through the monitor/permit/tool chain but intentionally skip ledger reservation; supplied controller intent cannot substitute protectedness.
- `ExecutionIntent` now rejects malformed candidate, task-step, authorization, and version identifier syntax at construction while monitor-side candidate/version/authority semantic checks remain in force.

### Remaining concern

The execution boundary is capability-controlled within this standard-library, same-process deterministic model. Python module-private names are not an OS process isolation boundary; a hostile in-process actor with arbitrary object introspection could still interfere with private runtime objects. The prior reproducible-secret bypass is closed: knowing the public instance ID cannot mint a permit accepted by the bound tool. The append-only audit hash chain remains intentionally unkeyed and therefore is not hostile-storage authentication.

## Fix round 2/5 — scoped re-review remediation

### Status

DONE

### Files changed in this round

- `src/pa_rl/effects.py`
- `src/pa_rl/execution.py`
- `tests/test_execution.py`
- `docs/implementation_reports/task-2a-report.md`

No Task 0/1 production API or fixture/design/evaluator/environment/RL file changed.

### RED evidence

The residual-boundary tests were written before this round's production changes:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Observed result: `FAILED (failures=2, errors=1)`, `Ran 25 tests in 0.032s`.

Expected failure details:

- An unbound `TaskEngine` accepted a `TaskEffectReceipt(..., _capability=None)` instead of raising.
- A manifest-valid Task 0 step ID (`"agenda step / local"`) was rejected by `ExecutionIntent`'s narrower regex.
- A stale logical step on a manifest-authoritative unprotected task invoked the tool and returned `committed` instead of blocking.

An implementation typo during the first GREEN attempt (`NameError: re is not defined`) was immediately corrected by restoring the local `re` import; no behavioral contract was changed by that correction.

### GREEN evidence

Task 2A suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

Result: `Ran 25 tests in 0.029s — OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 70 tests in 0.075s — OK`; `compileall` completed with no output.

### Resolutions

- Receipt application and issuance now fail closed while `TaskEngine` is unbound, and also reject `None` capability values after binding. The explicit pre-bind `None` forgery test verifies no task progress occurs.
- The recreated-issuer attack now mints a permit whose scenario, call ID, step ID, 64-character scope hash, reservation correlation, attempt index, and logical step are all syntactically valid. It proves the attacker issuer validates its own tag while the monitor-bound issuer rejects it, then observes no committed tool effect.
- `AuthorizationService.expire_eligible(intent.logical_step)` now runs for every authoritative execution attempt before the protected/unprotected branch. Thus unprotected steps reject stale and out-of-episode logical steps before the tool, while valid unprotected attempts still expire otherwise-active ledger authority without reserving it.
- `validate_task_step_id` preserves Task 0's canonical `TaskStep` domain: any non-empty trimmed string. `ExecutionIntent`, private permit validation, and `TaskEffectReceipt` share that rule, while candidate/authorization/version syntactic validation remains strict. The compatibility test executes a manifest-valid ID containing spaces and a slash successfully.

### Remaining concern

As in the prior round, this is a same-process capability boundary rather than OS isolation, and the audit hash chain is intentionally not hostile-storage authentication. The public-ID-derived permit forgery and unbound receipt forgery are closed.
