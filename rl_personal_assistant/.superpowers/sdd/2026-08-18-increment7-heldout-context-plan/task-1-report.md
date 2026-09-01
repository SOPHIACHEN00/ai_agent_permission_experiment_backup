# Increment 7 Task 1 Implementation Report

## Status

DONE. The deterministic paired-context suite is frozen at 40 typed
`ScenarioManifest` values with the approved 24/8/8 train/validation/test
rotation. No Task 2+ source was changed.

## Scope delivered

- Added `INCREMENT7_SUITE_VERSION = "increment7_paired_context_v0"`.
- Added frozen `CarrierSpec`, `FamilySpec`, `SuiteMember`, and
  `Increment7Suite` value types.
- Added the five exact carrier scopes and the fixed disjoint timeout second
  scope.
- Added eight protocol-family builders with their approved purposes,
  permission-response sequences, action traces, horizons, terminal outcomes,
  and protected task-step relations.
- Added the rotation rule `test=c[f mod 5]`,
  `validation=c[(f+1) mod 5]`, and `train=remaining`.
- Added deterministic order-independent suite and split hashes, split-filtered
  manifest access, and a JSON-serializable evidence mapping that contains
  hashes and identities but no hidden manifest content.
- Added exactly the first Increment-7 focused test method. Task 2 and Task 3
  test methods were not pre-created.

## Strict TDD evidence

The test was written before the production module. Its independently literal
split matrix and firewall assertions fail if a carrier is assigned to the
wrong family split, an ID is duplicated, a held-out primary signature appears
in training, an unsupported public category reaches an `other` bucket, or
identity/oracle material reaches policy metadata.

### RED

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
```

Observed expected failure:

```text
ModuleNotFoundError: No module named 'pa_rl.increment7_scenarios'
Ran 1 test in 0.000s
FAILED (errors=1)
```

### GREEN

The identical command then produced:

```text
test_suite_split_and_policy_firewall_invariants ... ok
Ran 1 test in 0.144s
OK
```

Targeted compilation:

```powershell
python -m compileall -q src\pa_rl\increment7_scenarios.py tests\test_increment7_pilot.py
```

Result: exit code 0 with no output.

## Frozen evidence

- Suite hash:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`
- Split hash:
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`
- Members: 40
- Train: 24
- Validation: 8
- Test: 8
- Global train carrier counts:
  `c0=5`, `c1=4`, `c2=4`, `c3=5`, `c4=6`.

Every categorical atom present in validation/test is represented in training,
while every validation/test primary scope signature is absent from training.
All initial scenario decisions retain the existing v1 tensor shapes
`state[75]` and `candidate[N,36]`, exactly reuse the environment mask, and keep
the scope `other` buckets clear.

## Changed files

- `src/pa_rl/increment7_scenarios.py`
- `tests/test_increment7_pilot.py`
- `docs/CONTINUATION_CHECKPOINT.md`
- `.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-1-report.md`

## Compatibility and claim boundary

The task did not change `ScenarioManifest`, `PermissionEnvironment`,
`CanonicalProtocolTracker`, the authority ledger, reference monitor, evaluator,
replay, existing fixtures, feature order, or frozen Increment-6 artifacts.

This suite supports a later compositional held-out public-context experiment.
It does not itself establish protocol replay correctness, learning performance,
unseen-purpose generalization, S-QSTN validity, or Deep-RL advantage. Those
remain later tasks.

## Next task

Task 2 only: replay all 40 canonical protocols, add approved negative controls,
export named v1 layout indices without changing tensor order, and add the
public-only Rule implementation.

## Fix round 1 — independent-review blockers

The initial Task 1 review returned `Spec: FAIL / Quality: CHANGES_REQUESTED`
for two bounded issues. No Task 2+ file was changed while resolving them.

### Finding 1: public text exposed protocol and future-outcome hints

The existing focused method was extended first with an independently literal
public-text contract and semantic leakage terms. Before production changed,
the focused command failed as intended:

```text
AssertionError: 'Complete one protected operation.' !=
'Complete the requested protected task.'
Ran 1 test in 0.015s
FAILED (failures=1)
```

Minimal fix: all families now share exactly:

```text
Complete the requested protected task.
```

The test also rejects public occurrences of authorization, permission,
replacement, refresh, disable, grant, denial/decline/persistence,
human-owner, and escalation terms. The former f2 authorization replacement,
f5 future persistent denial, and f6 human-owner escalation hints are absent.
The focused method then passed (`Ran 1 test in 0.158s — OK`).

### Finding 2: exported suite containers accepted inconsistent evidence

Malformed-construction assertions were added only after finding 1 was GREEN.
They independently construct wrong split, wrong family, wrong carrier, changed
scenario identity, changed manifest content, missing-product, and duplicate-
product cases. Before the constructor fix, the first wrong-split construction
did not raise:

```text
AssertionError: ValueError not raised
Ran 1 test in 0.016s
FAILED (failures=1)
```

Minimal fix:

- `SuiteMember.__post_init__` now rejects unknown family/carrier labels and
  binds those labels to the exact frozen rotation, scenario ID, and canonical
  generated manifest hash.
- `Increment7Suite.__post_init__` now requires a tuple of typed members, the
  exact 40 unique family/carrier pairs forming the 8 x 5 Cartesian product,
  unique scenario IDs, and exact 24/8/8 split counts.
- Sorting still makes reversed valid construction produce identical suite and
  split hashes.
- `as_mapping()` remains derived evidence from validated members; it does not
  acquire a second manifest, split, or hidden truth source.

### Final fix-round verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
```

Result: `Ran 1 test in 0.153s — OK`.

```powershell
python -m compileall -q src\pa_rl\increment7_scenarios.py tests\test_increment7_pilot.py
```

Result: exit code 0.

Corrected evidence:

- Suite hash:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3`
- Split hash (unchanged):
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`

Status after fix round: corrected and awaiting independent Task 1 re-review.
