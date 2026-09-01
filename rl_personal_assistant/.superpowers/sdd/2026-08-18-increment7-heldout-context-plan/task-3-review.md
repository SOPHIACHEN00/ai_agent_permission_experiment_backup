# Increment 7 Task 3 Independent Review

## Verdict

- **Spec: FAIL**
- **Quality: CHANGES_REQUESTED**

## Reviewed snapshot

All five SHA-256 values in `task-3-review-package.md` match the reviewed
profile, criteria source, focused test, checkpoint, and implementation report.
The permitted focused suite was rerun:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
```

Result: `Ran 3 tests in 1.186s — OK`.

## Finding

### 1. Important — the gate does not enforce the fixed 8-scenario / 3-seed metric dimensions

`evaluate_heldout_gate` accepts any non-empty `per_scenario` mapping
(`heldout_criteria.py:218-226`) and any non-empty `per_seed_macro` mapping
(`:228-235`). It therefore accepts incomplete evaluation inputs even though the
approved pilot has exactly eight held-out test scenarios and three training
seeds.

This can invalidate both advantage denominators:

- six supplied, solved scenario rows satisfy `min_test_scenarios_solved=6`,
  while the `<=2` worse-scenario check is no longer “of eight”; and
- two supplied seed rows can satisfy `min_paired_seed_wins=2`, while the
  criterion is explicitly “at least two of three seeds.”

The current third focused method exercises exact **method** keys but not these
fixed row dimensions, so the omission is unprotected.

Required Task 3 correction: reject inputs unless `per_scenario` contains
exactly eight unique non-empty scenario rows and `per_seed_macro` exactly three
unique exact-integer seed rows. Add these malformed-dimension cases to the
existing third focused method, then rerun only that method/the three-method
suite and targeted compilation. This remains gate validation work; it does not
authorize Task 4 runner or checkpoint work.

## Checked without finding a Task 3 defect

- Profile keys/defaults match the approved 13-field JSON; loader rejects an
  extra key and boolean count input.
- Criteria, safety counts, method-key schema, finite success-rate validation,
  immutable gate checks, JSON mappings, deterministic Rule-over-Tabular tie,
  and inclusive floating threshold handling are consistent with the approved
  gate contract.
- Best-simple comparisons are independently derived from aggregate,
  per-scenario, and per-seed Rule/Tabular values rather than accepted from the
  caller.
- Safety integrity is applied to all four evaluated methods against all three
  configured safety limits. Under the approved profile those limits are all
  zero.
- Classification is restricted to `NO_GO`, `PARITY`, and `ADVANTAGE_SIGNAL`;
  no unapproved `HOLD` state is emitted. No Task 4 runner/training/checkpoint
  source is present in the reviewed Task 3 snapshot.

## Fix round 1 re-review — original Important only

**Spec: PASS**

**Quality: APPROVED**

The original denominator finding is resolved. Before any scenario or seed
statistics are computed, `evaluate_heldout_gate` now rejects a
`per_scenario` mapping unless it has exactly eight rows and rejects a
`per_seed_macro` mapping unless it has exactly three rows. Its existing
mapping/key validation then guarantees eight unique non-empty scenario IDs,
three unique exact-integer seeds, and exact method keys in every retained row.

The updated criteria source/test/checkpoint/report SHA-256 values exactly match
the fix-round-1 review package. The existing third focused method explicitly
asserts rejection of six scenario rows and two seed rows. I independently
reran only that permitted method:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Result: `Ran 1 test in 0.011s — OK`.

No additional finding was assessed in this fix-round re-review.
