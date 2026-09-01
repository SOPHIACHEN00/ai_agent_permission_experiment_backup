# Task 2 — Typed Contracts, Literal Suite, and Exact Branch RNG

## Status

DONE. Focused test status is FOCUSED_GREEN. No Git repository was used; no commit was attempted. Gate 0
remains `BASELINE_FROZEN`, `last_completed_gate=0`, and `next_gate=1`.

## Implementation

Created only the four scoped Task 2 source/test files:

- `src/pa_rl/family3_v2_contracts.py`: immutable v2 profile constants, typed
  candidate/offer/forecast/continuation contracts, and the fixed seven-role
  order.
- `src/pa_rl/family3_v2_suite.py`: copied carrier literals (without importing
  private legacy data), the ten literal rows, exact 21-field row mapping,
  derived algebra/scope validation, suite hash, branch coupling UID, and typed
  forecast counterfactual.
- `src/pa_rl/family3_v2_rng.py`: JSON-list SHA-256 counter draw, big-endian
  uint64 extraction, rejection sampling, recorded payload evidence, and fixed
  forecast residue thresholds.
- `tests/test_family3_v2_suite_rng.py`: literal ten-row projection,
  counterfactual coupling, rejection boundary, both probability thresholds,
  and frozen payload/byte-order evidence.

No legacy lifecycle model/encoder/solver, `increment8_policy`, PyTorch, or
private legacy `_CARRIERS` import is used. Operational `Scope` remains in the
contract/suite boundary; policy firewall work is deferred to its planned task.

## Witnessed RED

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

Output:

```text
test_family3_v2_suite_rng (unittest.loader._FailedTest.test_family3_v2_suite_rng) ... ERROR

======================================================================
ERROR: test_family3_v2_suite_rng (unittest.loader._FailedTest.test_family3_v2_suite_rng)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_family3_v2_suite_rng
Traceback (most recent call last):
  File "C:\\Users\\Sophi\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\unittest\\loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "...\\tests\\test_family3_v2_suite_rng.py", line 9, in <module>
    from pa_rl.family3_v2_contracts import ContinuationModeV2
ModuleNotFoundError: No module named 'pa_rl.family3_v2_contracts'

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

Cause: the intended missing Task 2 production module. No unrelated RED cause
occurred.

## Witnessed GREEN

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

Output:

```text
test_counter_draw_records_the_accepted_payload_and_uint64 (...) ... ok
test_literal_suite_and_counterfactual (...) ... ok
test_rejection_sampling_is_exactly_mod_five (...) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.002s

OK
```

Method count: 3. No DP, training, broad regression, or later-task test ran.

## SHA-256 evidence

| File | SHA-256 |
|---|---|
| `src/pa_rl/family3_v2_contracts.py` | `c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb` |
| `src/pa_rl/family3_v2_suite.py` | `530244305d1c36a3973277810369eca756dc4bc17990535c4f733f5909db16c4` |
| `src/pa_rl/family3_v2_rng.py` | `bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530` |
| `tests/test_family3_v2_suite_rng.py` | `6ce4f5623b7e4cf973826753e75830b1e668fa50a5b3c71ec3d437bd4663ef9f` |
| frozen baseline JSON (unchanged) | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` |

## Checkpoint evidence

`docs/CONTINUATION_CHECKPOINT.md` now records the 3-method focused GREEN,
source/test hashes, and the corrected factual statement: Gate-0 result root
exists, although no DP/cache/final result exists. Result checkpoint SHA-256 is
`873248c70854b873d62656246587ed3093fa4f8b84f233bdf0f7a0d25746f3c2`; the
appended JSONL progress file SHA-256 is
`c65ef8c72e6a40178acbac2ef12a58515b4924a1e6bb8ce5aba99c6c3a458731`.
The checkpoint preserves the frozen baseline hash and Gate fields, adds
`implementation_progress`, and advances only its implementation next action
to Task 3.

## Self-review and concerns

Validated JSON checkpoint parsing, the preserved Gate fields, the single JSONL
implementation append, and unchanged frozen-baseline SHA-256. The import scan
found no prohibited imports; the local `_CARRIERS_BY_CODE` lookup is a new
literal registry, not an import of legacy private `_CARRIERS`.

Scope boundary: Task 2 deliberately does not implement or exercise later
pure-model, authority, environment, audit, solver, or policy-firewall behavior.
Next action: implement Task 3 pure outcome and finite-horizon model with its
own required RED/GREEN.

## Fix round 1 — I1/I2

Changes: `Family3V2GraphSpec` now validates the three literal scope relations
through unchanged `scope_matching.covers` and `scope_matching.relation` while
retaining literal scope reconstruction. Every graph integer field is exact-
integer checked. `Family3V2KernelInput` now exact-checks all of its integer
fields, enforces `e>d`, target, prompt, exposure, and horizon algebra, and
requires a lowercase hexadecimal SHA-256 coupling UID.

Covering tests: `test_graph_validates_the_canonical_scope_coverage_relation`
and `test_graph_and_kernel_reject_non_exact_or_inconsistent_integer_contracts`.
The latter covers float-equivalent graph/kernel fields, Boolean prompt budget,
kernel `e==d`, zero exposure, invalid horizon, and uppercase UID.

RED command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

RED output ended exactly:

```text
Ran 5 tests in 0.005s

FAILED (failures=8)
```

Cause: the reviewed code accepted equality-equivalent non-exact graph values
and did not call the canonical matcher; the first new graph subtests reported
`AssertionError: ValueError not raised`.

GREEN command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

GREEN output:

```text
Ran 5 tests in 0.006s

OK
```

Fix-round SHA-256: contracts
`c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb`;
suite `b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54`;
RNG `bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530`;
test `4755e05ddba9e3be84c875656f02cbdbb84917c1c3a12b8fd7c60fd7a9283379`.
The baseline SHA-256 remains
`d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`;
Gate fields remain `BASELINE_FROZEN / 0 / 1`. Updated checkpoint evidence:
project checkpoint `fb603ca14f91551ffa93f167831103ad819272dae6ccb5599fee21cd17e54cbe`;
result checkpoint `1ea5716aaac0c19bde259cbb8d973b14bb0eee9f534b7bed6e38d50743a20351`;
progress JSONL `dfec520a915cc4f3f66a04ed483ec34a9d6f0960ca85b87afb492dda5f68d68c`.
