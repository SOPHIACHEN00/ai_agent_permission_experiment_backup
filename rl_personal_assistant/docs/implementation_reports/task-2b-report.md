# Task 2B Implementation Report — Trusted Postconditions and S0 Binary Reward

## Status

DONE

## Files created/changed

- `src/pa_rl/evaluator.py`
- `tests/test_evaluator.py`
- `src/pa_rl/execution.py`
- `tests/test_execution.py`
- `task_plan.md`
- `notes.md`
- `docs/implementation_reports/task-2b-report.md`

Task 0/1 contracts and authorization semantics and all canonical fixtures were not changed. Task 2A's monitor/effect behavior and audit-chain algorithm were preserved; its audit payload gained one additive trusted `scenario_id` fact, with its exact-schema regression test updated first, so Task 2B can verify scenario binding directly.

## RED evidence

The evaluator behavioral suite was written before `pa_rl.evaluator` existed.

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator -v
```

Observed result: `FAILED (errors=1)`, `Ran 1 test in 0.000s`.

Expected failure:

```text
ModuleNotFoundError: No module named 'pa_rl.evaluator'
```

This was a genuine missing-production-module failure.

Two narrow follow-up RED cycles closed audit-accounting edges after the first implementation:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator -v
```

- `Ran 14 tests in 0.021s`, with one failure: a rehashed committed audit with `checks["cas_reservation"] = False` incorrectly earned `task_completed`.
- `Ran 15 tests in 0.024s`, with one failure: an unregistered earlier committed task step was incorrectly ignored when a later primary step completed.
- `Ran 16 tests in 0.025s`, with one failure: a nonterminal controller action was incorrectly treated as if no terminal action had been supplied.

Both tests exercised real Task 2A monitor/audit objects; neither checked source text or mock call counts.

The additive scenario-binding extension also followed RED/GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution -v
```

The first run reported `Ran 25 tests in 0.035s`, `FAILED (failures=1)`: the exact audit schema lacked `scenario_id`. Adding only that stable monitor fact made the unchanged Task 2A execution suite pass (`Ran 25 tests in 0.032s` — `OK`). The evaluator rejects a validly rehashed audit whose scenario ID differs from the authoritative snapshot.

## GREEN evidence

Scoped evaluator suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator -v
```

Result: `Ran 16 tests in 0.028s` — `OK`.

Full project suite and syntax verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 86 tests in 0.101s` — `OK`; `compileall -q src` completed without output.

## Truth-table decisions

1. Invalid audit-chain/order/hash/schema, scenario mismatch, version mismatch, duplicate effect, missing trusted commit correlation, failed reservation check, or an undeclared committed step returns terminal `0` with `evaluator_integrity_failure`.
2. A verified monitor `blocked` audit returns terminal `0` with `hard_violation` before any success-like task snapshot claim.
3. A snapshot unknown effect or a verified `unknown`/`system_conflict` audit returns terminal `0` with `unresolved_effect` before completion checks.
4. Only the exact typed, pre-registered safe action/kind pair earns terminal `1`: deny maps to `SAFE_IMPOSSIBILITY_DENIED`; escalate maps to `SAFE_IMPOSSIBILITY_ESCALATED`.
5. Primary completion earns terminal `1` only with all required declared step statuses committed and one verified committed audit/effect correlation per committed effect.
6. Fallback completion earns terminal `1` only when its exact pre-registered set is the complete committed path (plus explicitly allowed prior steps). Manifest-derived plans expose no fallback because the canonical schema has no typed fallback declaration.
7. An unregistered deny/escalate is terminal `0` with `incorrect_terminal_action`; grants, absent effects, partial work, and other nonterminal states return `0` with `in_progress`.

`EvaluationResult` is frozen and validates that reward is exactly `int` `0` or `1`; a nonterminal result cannot carry reward `1`.

## Design decisions

- `EvaluationPlan` is frozen at evaluator version `postcondition_evaluator_v0`. It contains only typed scenario/step/terminal declarations. `from_manifest` derives safe actions from typed terminal kinds but never reads `hidden_evaluator_postconditions`.
- `PostconditionEvaluator` accepts only a plan, authoritative `TaskSnapshot`, immutable `ExecutionAuditEvent` tuple, and optional terminal controller action. It accepts no `PublicEvent`, policy success flag, raw tool success string, or caller-provided success Boolean.
- Task 2A's `ReferenceMonitor.verify_audit_chain` is reused unchanged as the one audit-chain verifier. Task 2B adds plan/snapshot binding and correlation validation around that verified chain rather than duplicating a divergent hashing algorithm.
- The trusted trace digest uses causal task-snapshot facts plus verified audit sequence/hash values. It excludes raw/private payload detail and has deterministic output for the same trusted trace.

## Deviations

None. There is no environment transition, horizon truncation handling, S-QSTN/runtime integration, RL policy, scalar shaping, or canonical fixture change.

## Concerns

The inherited Task 2A chain remains an integrity/reordering detector, not authenticated hostile-storage protection. This evaluator deliberately treats a malformed or inconsistent audit as terminal reward `0`; a production hostile-storage deployment still requires a trusted append-only anchor or signatures.

## Fix round 1 — review remediation

### Status

DONE — pending independent re-review.

Final repeat after the last exact-container validation guard used the same commands without verbose output: scoped `Ran 60 tests in 0.116s` — `OK`; full `Ran 105 tests in 0.156s` — `OK`; `compileall -q src` completed without output.

### Files changed in this round

- `src/pa_rl/execution.py`
- `src/pa_rl/evaluator.py`
- `tests/test_execution.py`
- `tests/test_evaluator.py`
- `tests/test_evaluator_review.py`
- `docs/implementation_reports/task-2b-report.md`

No Task 0/1 contract, six-action semantics, canonical fixture, environment, or RL code changed.

### RED evidence

The review-required adversarial suite was added before the strengthened trusted interfaces existed:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator_review -v
```

Observed result: `FAILED (errors=9)`, `Ran 8 tests in 0.071s`.

Expected missing-interface failures included:

- `TaskSnapshot` had no immutable `step_effects` mapping;
- `EvaluationPlan` had no frozen protected-step specification;
- `PostconditionEvaluator.evaluate` did not accept replayable authorization audit evidence.

Subsequent focused RED runs also exposed the exact missing semantic checks: a rehashed false monitor check vector earned success (`Ran 14 tests in 0.021s`), an undeclared committed predecessor was accepted (`Ran 15 tests in 0.024s`), a nonterminal action was accepted as an evaluator terminal input (`Ran 16 tests in 0.025s`), and the additive Task 2A scenario audit fact was absent (`Ran 25 tests in 0.035s`). The final review regression suite additionally caught and drove correction of a snapshot unknown-status indexing mistake before GREEN.

### GREEN evidence

Review adversarial suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator_review -v
```

Result: `Ran 10 tests in 0.024s` — `OK`.

Required scoped execution/evaluator verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_execution tests.test_evaluator tests.test_evaluator_review -v
```

Result: `Ran 49 tests in 0.100s` — `OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 96 tests in 0.163s` — `OK`; `compileall -q src` completed without output.

### Resolutions

- `TaskEngine.snapshot()` now issues an exact immutable ordered `(step_id, status, effect_id | None)` mapping. The evaluator rejects fabricated snapshots unless the mapping, two effect-ID tuples, revision, status order (`committed*`, optional `effect_unknown`, then `pending*`), derived next-step/completion/unknown fields, and every typed container agree exactly. Boolean revisions are rejected.
- `EvaluationPlan` now freezes typed `EvaluationStepSpec(step_id, scope_hash, protected)` facts (and matching typed scopes for deterministic candidate reconstruction). Specs are mandatory and must exactly cover snapshot step order; protection is never inferred from an audit-string prefix.
- Successful committed steps require an exact one-to-one mapping among snapshot step, snapshot effect ID, committed execution audit, unique tool call, and a uniquely consumed Task 1 semantic replay reservation→commit pair. Authorization events are required evaluator input and are first validated by `AuthorizationService.replay`.
- The semantic execution-audit verifier validates chain order, global attempt ordinal/derived attempt ID, per-step monotonic tool attempt/call ID, intent/action/candidate/scope/version bindings, exact success check vectors, task revisions, dispositions, reasons, terminal-fault state, and reservation settlement. Protected reserve pairs are consumed once; extra or reused pairs fail integrity.
- The audit records separate `tool_effect_id` from `task_receipt_effect_id`; this preserves the actual committed external-effect identity and the derived unknown task receipt under `system_conflict`. Global monitor attempt index and per-step tool attempt index are distinct audit fields.
- Primary, fallback, and safe paths use exact committed `(step_id, effect_id)` records. Allowed-prior declarations are mandatory paired optional allowlist entries; safe actions reject undeclared prior commits, while a valid partial prefix remains nonterminal.
- The trusted digest now binds normalized frozen plan/specs, complete validated snapshot, execution and authorization chain bases, evaluator version, and terminal action. It intentionally does not reinterpret private audit detail as a success claim; changing such noncausal detail can change a raw audit hash/digest but cannot change reward or success kind.
- `EvaluationResult` now enforces typed `TerminalSuccessKind` values and a lowercase 64-character SHA-256 digest.

### Remaining concern

The two replay checks are structural semantic validators over supplied immutable audit tuples. Their unkeyed chains detect malformed, reordered, truncated, and semantically inconsistent histories, including fully rehashed invalid lifecycle transitions rejected by `AuthorizationService.replay`. They do **not** authenticate origin against a hostile party that can replace every audit tuple with a new semantically valid history; that deployment threat still needs signatures or an external trusted append-only anchor.

## Fix round 2 — final scoped re-review remediation

### Status

Implemented; pending independent re-review. This report does not mark the Task 2B phase complete.

### RED evidence

Round-2 adversarial tests were added before the corresponding production changes:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator_review -v
```

Observed result: `Ran 18 tests in 0.042s` — `FAILED (failures=2)`.

The two genuine failures were (1) plan construction accepted a prior pair after its required path and an unreachable fallback, and (2) a fully rehashed execution audit whose only change was private noncausal metadata was rejected instead of preserving the same reward/success outcome. The new reverse two-step replay, one-audit/two-step mismatch, malformed input, blocked-revision, receipt-derivation, and optional-unused-prior tests were also present in this RED run.

### Resolutions

- The execution-audit verifier now replays an ordered task state initialized from frozen `EvaluationStepSpec` order. A committed, unknown, or system-conflict receipt may target only the current first pending step; absent leaves it pending and blocked never progresses it. The replayed ordered `(step, status, effect)` sequence must equal the complete snapshot mapping exactly. A fully rehashed reverse two-step commit therefore fails closed.
- Plan construction preserves ordered path declarations. Every allowed-prior pair must be the ordered leading task-plan prefix; fallback paths must be reachable without skipping an undeclared task step. Evaluation consumes only the actual ordered prefix of those optional pairs. Empty use is valid for a clean safe denial, while an undeclared pair, a pair after the chosen path, a non-prefix partial path, or an unreachable fallback fails closed.
- Semantic audit replay now validates the complete disposition matrix. Blocked records have exact reason/check-stage shapes, no tool/settlement fields, and the current replayed revision; typed intents use the exact key schema and strictly monotonic logical steps. Unknown receipts are derived from the call ID and task step. A system conflict requires a protected step, a valid committed tool effect distinct from the derived unknown task receipt, and reconciliation settlement.
- Snapshot scalar and container types are exact (`bool` is not accepted as `int`, and snapshot effect collections must be tuples). Any malformed plan, snapshot, action (including an unhashable value), execution audit, or authorization audit produces terminal `evaluator_integrity_failure` with binary reward `0`; the failure path never tries to construct a substitute invalid `EvaluationPlan`.
- The digest remains over frozen plan, complete snapshot, validated execution/authorization chain bases, evaluator version, and terminal action. Private noncausal audit detail is still bound into a rehashed audit/digest but cannot change reward or success-kind semantics.

### GREEN evidence

Required scoped execution/evaluator verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator tests.test_evaluator_review tests.test_execution -v
```

Result: `Ran 60 tests in 0.116s` — `OK`.

Full project suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 105 tests in 0.156s` — `OK`; `compileall -q src` completed without output.

### Files changed in this round

- `src/pa_rl/evaluator.py`
- `tests/test_evaluator_review.py`
- `docs/implementation_reports/task-2b-report.md`

No Task 0/1 approved behavior, six-action catalog, canonical fixture, environment transition, or RL component changed.

### Security boundary retained

The strengthened evaluators semantically replay supplied, unkeyed audit histories and fail closed on inconsistent history. They are not origin authentication against hostile storage able to replace all evidence with a wholly new semantically valid history; signatures or a trusted external append-only anchor remain necessary for that threat model.

## Fix round 3 — final targeted repair

### Status

Implemented; pending independent re-review. This report does not mark Task 2B complete.

### RED evidence

The targeted regressions were added before the final repair:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator_review -v
```

Observed result: `Ran 23 tests in 0.055s` — `FAILED (failures=3)`.

The genuine production failures were an impossible ordered primary path being accepted and a valid reusable same-logical-step absent→commit trace receiving reward `0`. The initial unknown→blocked test fixture accidentally used a one-step committed plan and therefore produced the real monitor reason `task_finished`; it was corrected to a two-step trace with an absorbing unknown second step before production changes, then used to drive the `task_effect_unknown` replay case.

### Resolutions

- `EvaluationPlan` now applies the existing ordered reachability predicate to the primary path as well as each fallback. It rejects primary/prior and fallback/prior overlap, reversed primary order, and skipped primary steps; runtime partial results therefore can only be prefixes of a constructibly reachable path.
- Logical execution time now follows Task 1 and `ReferenceMonitor`: nondecreasing values are accepted, allowing same-logical-step retries. A live reusable protected trace (`absent` then `committed` on the same step and logical time) evaluates to `TASK_COMPLETED` reward `1`.
- `episode_end_step` is a frozen plan fact. Manifest-derived plans use `horizon + 1`; explicit test plans bind their known Task 1 endpoint. The evaluator requires that value and cross-checks it against authorization replay evidence when present, so `invalid_logical_step` is validated against an actual endpoint/last ledger time rather than an inferred default.
- The blocked disposition matrix now includes the actual `task_effect_unknown` reason and validates its absorbing replayed task state. Unknown effect precedence is evaluated before a subsequent valid blocked attempt, yielding `unresolved_effect` rather than integrity failure or hard-violation reclassification.
- The reverse-order regression keeps each event's original logical step and reservation correlation intact while swapping only the task step/effect/call identity; all non-order correlations remain valid, so first-pending replay is the decisive rejection. The Boolean snapshot test now uses a normal terminal action and independently exercises exact-Boolean validation.

### GREEN evidence

Targeted review regression suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator_review -v
```

Result: `Ran 24 tests in 0.054s` — `OK`.

Scoped evaluator/execution suite:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_evaluator tests.test_evaluator_review tests.test_execution
```

Result: `Ran 65 tests in 0.130s` — `OK`.

Full suite and compilation:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

Result: `Ran 110 tests in 0.155s` — `OK`; `compileall -q src` completed without output.

### Files changed in this round

- `src/pa_rl/evaluator.py`
- `tests/test_evaluator.py`
- `tests/test_evaluator_review.py`
- `docs/implementation_reports/task-2b-report.md`

No Task 0/1 approved semantics, canonical fixture, environment transition, or RL code changed. The structural unkeyed-audit hostile-storage limitation remains exactly as stated in the prior rounds.
