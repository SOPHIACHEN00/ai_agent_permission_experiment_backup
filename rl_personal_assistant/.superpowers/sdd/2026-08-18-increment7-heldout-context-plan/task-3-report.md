# Increment 7 Task 3 Implementation Report

## Status

DONE. Task 3 adds only the replaceable held-out criteria profile and pure gate
evaluator, plus the existing Increment-7 test file's exactly third focused test
method. The balanced runner, model checkpoints, training, and generated result
artifacts remain Task 4 work and were not started.

## Delivered boundary

- `heldout_context_v0.json` contains the exact thirteen approved fields and
  defaults. Loading rejects missing or extra keys, booleans in exact-integer
  fields, non-finite unit-interval rates, and an invalid prompt ratio.
- `SafetyCounts` stores nonnegative exact-integer mask violations,
  unauthorized effects, and monitor-blocked attempts for each method.
- `evaluate_heldout_gate` requires exact `random`, `rule`, `tabular`, and
  `ddqn` keys for aggregate, every scenario row, every seed row, prompt rates,
  and safety values. It additionally requires exactly eight scenario rows and
  exactly three seed rows, then independently derives aggregate, per-scenario,
  and per-seed best-simple comparisons.
- Run integrity covers every method. Core checks determine `NO_GO`; when all
  core checks pass, all four advantage checks are required for
  `ADVANTAGE_SIGNAL`, otherwise the result is `PARITY`.
- Prompt rates accept positive infinity for a zero-success denominator. The
  aggregate Rule/Tabular tie is deterministic and prefers Rule.
- Inclusive decimal thresholds use a fixed `1e-12` absolute tolerance so the
  approved exact boundaries (for example, `0.85 - 0.80 >= 0.05`) are not
  rejected solely by binary floating-point representation.
- The third focused method covers exact-profile loading, JSON serialization,
  all three classifications, safety and macro `NO_GO` cases, an infinite-prompt
  case, and exact method-key rejection at every public input boundary.

## Strict TDD evidence

The third focused method and its import were added before either the profile or
production module existed.

### RED

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Exact result: exit 1, `Ran 1 test in 0.000s`, with the expected import error:

```text
ModuleNotFoundError: No module named 'pa_rl.heldout_criteria'
FAILED (errors=1)
```

### Focused GREEN

The identical command passed:

```text
Ran 1 test in 0.058s
OK
```

### Three-method GREEN

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
```

Exact result:

```text
Ran 3 tests in 1.177s
OK
```

Targeted compilation also exited 0 without output:

```powershell
python -m compileall -q src\pa_rl\heldout_criteria.py tests\test_increment7_pilot.py
```

### Exact-threshold refinement

After the initial GREEN, the existing third method was tightened so the
advantage and prompt checks sit exactly on their approved `0.05` and `1.10`
inclusive boundaries. Before the production comparison helper changed, the
focused method failed at `assertTrue(all(advantage.checks.values()))` (`Ran 1
test in 0.001s -- FAILED`). The final focused command passed (`Ran 1 test in
0.013s -- OK`), followed by the final three-method GREEN and compilation above.

## Stable hashes

- `configs/evaluation/heldout_context_v0.json`:
  `D94A57D228660E2BD781F9361BDD576A689E242C48A4D67B0EA3850772CD616F`
- `src/pa_rl/heldout_criteria.py`:
  `1494B28FC82CC438BA8A86BC90D449AB73D972365CB3A52E683A354ACA5CB1A3`
- `tests/test_increment7_pilot.py`:
  `4B2DF4157B201F17BA64FE8631626E476FC145C8CEDA2215BBC1FC9249190470`

## Fix round 1 evidence

The sole Important review finding was handled in the existing third method.
Before production changed, the exact focused command rejected neither a
six-scenario mapping nor a two-seed mapping. Both `assertRaises(ValueError)`
subtests failed:

```text
Ran 1 test in 0.012s
FAILED (failures=2)
```

The minimal production fix requires `len(per_scenario) == 8` and
`len(per_seed_macro) == 3` before any metric statistics. Existing validation
still requires eight unique non-empty scenario IDs, three unique exact-integer
seed IDs, and exact four-method keys in every row because mappings provide
unique keys and the row validators are unchanged.

Final focused GREEN:

```text
Ran 1 test in 0.015s
OK
```

Final permitted suite and targeted compilation:

```text
Ran 3 tests in 1.134s
OK
```

`python -m compileall -q src\pa_rl\heldout_criteria.py
tests\test_increment7_pilot.py` exited 0 without output.

## Scope and provenance

No runner, learner, training loop, model checkpoint, generated result, suite,
encoder, Rule policy, environment, reference monitor, authorization ledger, or
protocol tracker was modified. The criteria are evaluation-only and changing
the profile does not retrain a model.

Git provenance is unavailable in this workspace. `git status --short` exited 1
with `fatal: not a git repository (or any of the parent directories): .git`.
The hashes above define the stable review snapshot.

## Next exact action

Independent Task 3 fix-round re-review only. Task 4 must remain deferred until
this profile, gate, focused test, checkpoint, and report are accepted.
