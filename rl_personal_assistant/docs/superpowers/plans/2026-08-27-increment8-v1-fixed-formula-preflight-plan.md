# Increment 8 v1 Fixed-Formula Exact Preflight Plan

## Goal

Apply the already approved v1 clock semantics and Family-3 formulas without
parameter search. First certify all ten Family-3 strategic graphs; only if all
ten reach the exact `3/5` floor, certify all forty strategic graphs.

## Global constraints

- Frozen v0 suite remains immutable.
- All strategic graphs use `_ClockFixedCalibrationModel` and exact
  `fractions.Fraction` Bellman values.
- Only Family 3 changes graph parameters:
  `exposure_v1=exposure_v0+8` and
  `target_v1=max(4,target_v0-1)`.
- Families 0–2 retain every v0 graph parameter.
- Prompt budgets, horizons, likelihoods, scopes, actions, transition
  probabilities, reward, state limit `1,000,000`, RAM LRU `4,096`, and oracle
  floor `3/5` remain fixed.
- No parameter CLI, parameter search, sampling, learner, smoke, training,
  validation, or official test.
- Every graph has an isolated resumable SQLite cache/checkpoint and an exact
  certificate. A phase summary is written only from complete validated graph
  certificates.
- If any Family-3 graph is below `3/5`, write the full ten-graph summary and
  stop before the forty-graph phase.

## Task 1 — Minimal fixed-formula runner

Create a separately versioned runner and focused test. Use TDD: witness a
missing-module RED, then implement only graph construction, one-graph exact
execution, and phase-summary validation/writing. The CLI may select exactly
one graph or summarize one declared phase; it must expose no scientific
parameter override.

## Task 2 — Family-3 ten-graph certificate

Run `i8_s3_v0` through `i8_s3_v9` in isolated graph directories, then write
and independently verify `family3_summary.json`. Continue only if all ten
certificates are exact `CERTIFIED_PASS` at `3/5`.

## Task 3 — Forty-strategic-graph certificate

If Task 2 passes, retain/reuse the ten completed Family-3 graph artifacts,
solve the remaining thirty strategic graphs, and write
`strategic_summary.json`. Do not recompute a completed graph unless its
certificate/cache validation fails.

## Task 4 — Evidence and handoff

Verify certificate/checkpoint/SQLite consistency, run focused tests and
targeted compilation, obtain independent code and artifact reviews, then
update the implementation report, task plan, continuation checkpoint, and
external decision/progress logs. Do not freeze production v1 specs or train
until this preflight result is known and recorded.
