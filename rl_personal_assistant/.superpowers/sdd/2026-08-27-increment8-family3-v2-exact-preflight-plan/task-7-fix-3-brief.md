# Task 7 readiness fix round 3/5 brief

Read this first: it is the complete round-3 requirements authority together
with `task-7-fix-2-review.md`. This is a scoped review-fix round, not a new
scientific task.

## Permitted files

- `tests/test_family3_v2_preflight.py`
- `tests/test_family3_v2_artifacts.py`
- `src/pa_rl/family3_v2_preflight.py`
- `src/pa_rl/family3_v2_artifacts.py` only if the real atomic-boundary behavior
  cannot be corrected in the runner alone
- the existing Task-7 implementation report and a new round-3 review package
- authorized checkpoint/ledger bookkeeping after RED/GREEN

Do not edit any other production/test file. Do not change the spec, plan,
scientific parameters, Gate predicates except the reviewed Gate-3 assurance,
solver/reference, graph suite, threshold, or output root.

## C1 observable contract

1. A primary external `KeyboardInterrupt` must never be replaced by a
   `RuntimeError` or normal 0/2/3 mapping merely because persistence of its
   recovery transition also failed. If no terminal/final checkpoint became
   durable, re-raise the same `KeyboardInterrupt` object. Preserve the already
   accepted exception that a strictly validated durable `CERTIFIED_PASS` wins
   after a late final-progress interruption.
2. A structured `GATE_FAILED`, `INTERRUPTED`, `RESOURCE_CAP_EXCEEDED`, or
   `CERTIFIED_PASS` result may be returned only when strict disk validation
   proves that durable state. Never return a terminal-looking mapping while
   disk remains active/non-resumable `GATE_PASSED`.
3. If recovery persistence fails before a durable transition for an ordinary
   exception, fail closed with an internal exception carrying primary error,
   recovery error, operation, attempted gate, and strictly read durable
   coordinates. Do not invent a new persisted status. Do not fabricate 0/1.
4. Public fallback may emit initialization coordinates 0/1 only after proving
   the durable checkpoint is exactly the untouched Gate-0 baseline. If the
   root progressed or strict validation cannot prove Gate 0, propagate the
   original/dedicated failure instead of fabricating coordinates.
5. Strictly validated durable `RESOURCE_CAP_EXCEEDED` maps to exit code 3;
   `GATE_FAILED`/integrity failure maps to 2; `CERTIFIED_PASS` maps to success.
6. `final_verdict.json` written before the final checkpoint is uncommitted and
   must not imply success. Recovery/resume must follow the checkpoint as sole
   authority. Final checkpoint written before final progress remains accepted
   durable success.
7. Existing terminal non-resumability, committed refs, baseline/config
   validation, and exact durable next-action/evidence behavior must not weaken.

## I4 required real-behavior negatives

Add independently derived, typed, real-handler tests that prove Gate 3 rejects
each of the following separately before solver entry:

- successful-cell `unauthorized_committed_effects > 0`;
- successful-cell `monitor_blocked_attempts > 0`;
- semantic classification/failure-reason mismatch;
- every required role name present but total role count non-positive.

Add real-store atomic-boundary tests for:

- recovery artifact/checkpoint persistence failing before the recovery
  transition is durable, for ordinary exception and `KeyboardInterrupt`;
- progressed-root public fallback validation failure never producing 0/1;
- exact resource-cap exit 3;
- `final_verdict.json` durable before final checkpoint, followed by recovery
  or identical resume;
- retain regression coverage for recovery checkpoint durable before progress
  failure and final checkpoint durable before final progress failure.

Tests must assert real caller-visible results, durable checkpoint bytes/status,
and restart authority. Do not assert only mock calls. Test fixtures must mirror
the complete typed structures and use literal hand-derived expected values.

## One grouped TDD cycle

Before editing production, add all scoped tests and run exactly once:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v
```

The RED is valid only if every new failing case is an expected C1/I4 behavior
assertion and there are zero fixture/import/syntax errors. If any error or
unrelated failure appears, stop immediately, write the breakpoint, and do not
edit production or rerun.

After a valid RED, make the minimum production change and run the identical
grouped command exactly once for GREEN. If it is not completely green, stop
immediately and record that first real failure; do not iterate. Do not run
adjacent tests, compile, DP, or the real preflight.

## Report contract

Append round-3 RED/GREEN evidence to `task-7-implementation-report.md` and
create `task-7-fix-3-review-package.md`. Record commands, exit codes, method/
failure/error counts, elapsed time, final hashes/bytes, changed-line mapping,
root inventory, JSON/JSONL parse result, and the unchanged Gate authority.
Set status to `READINESS_FIX_3_GREEN_REVIEW_REQUIRED` only after a clean GREEN;
do not claim readiness approval. Return only DONE/BLOCKED, the compact test
summary, paths, hashes, and concerns. Do not spawn subagents or reviewers.
