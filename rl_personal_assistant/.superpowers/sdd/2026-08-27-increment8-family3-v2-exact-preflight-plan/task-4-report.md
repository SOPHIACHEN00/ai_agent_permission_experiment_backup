# Task 4 implementation report

Status: `DONE`

## Scope completed

- Added the deterministic reusable v2 user and two-phase exact-scope binding gateway.
- Added the label-free seven-row public observation and exact tuple encoder.
- Added real `AuthorizationService` / `ReferenceMonitor` / `TaskEngine` / `MockTool` mediation with a private public-ordinal-to-raw-ID map, deterministic task plans, one post-commit branch draw, fail-closed integrity checks, and pure-model successor conformance.
- Added one focused seven-method test module. No Task 2/3, legacy, baseline, `__init__.py`, solver, learner, or scientific parameter file changed.

## TDD evidence

RED command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment -v
```

RED output: exit `1`; `Ran 1 test in 0.000s`; loader error exactly `ModuleNotFoundError: No module named 'pa_rl.family3_v2_authority'`. Tool wall time: `0.546s`.

Focused GREEN command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment -v
```

Focused GREEN output: exit `0`; all seven named methods `ok`; `Ran 7 tests in 0.024s`; `OK`. Tool wall time: `0.603s`.

Authorized Tasks 2–4 combined command (run once):

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng tests.test_family3_v2_model_outcome tests.test_family3_v2_authority_environment -v
```

Combined output: exit `0`; all 21 named methods `ok`; `Ran 21 tests in 0.074s`; `OK`. Tool wall time: `0.686s`.

## New-file boundary

| File | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_authority.py` | `6392DE61318636EE092257C77040DEBF9B4A8DDA24480D55FE72C1E6DC67457C` | 5,801 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `08D91F72E5F8B1DC90599DEF2B4503F385C66262DD3C4882C5377496910FF4C5` | 14,719 |
| `tests/test_family3_v2_authority_environment.py` | `5DB1B8D3FF81318EAA6231DBAB01E8B0D9C08BB3EC4BC950CDAD97F57FE7289A` | 13,662 |

## Frozen Task 2/3 input verification

All seven inputs match the Task 4 base manifest exactly:

- `family3_v2_contracts.py` — `C6CEB984C319A7A8FA407CB5ABE730FB75C31BA7513C36346C9695302985EEEB`
- `family3_v2_suite.py` — `B9DEF623BD0EB025754C458A4289D8A7C96E18C0AAAE5AA586A521D9DD0E8D54`
- `family3_v2_rng.py` — `BF0F9CB388C883D20C77848C0CB8E94E73DA9D0F8769395440949FBEFFC46530`
- `family3_v2_outcome.py` — `B4AAFF4856194966823380DCC1B34AF3CECEE3C2DA0ED5B0FA169C7F712318D6`
- `family3_v2_model.py` — `315A13A37A5D8479EC3185B7082FB45E51E42A62493A374BB205CC6BC45B246A`
- `test_family3_v2_suite_rng.py` — `4755E05DDBA9E3BE84C875656F02CBDBB84917C1C3A12B8FD7C60FD7A9283379`
- `test_family3_v2_model_outcome.py` — `E9346686642413C9D90FA679439D76FACE47C91A61FA6071A07C1890A5D79E21`

## Self-review and concerns

- The environment never derives semantic successors itself: successful, masked, disable, deny, and escalate paths use `Family3V2Model.transition_from_residue`; mediated/public fields are checked field-by-field before publication.
- Integrity-only closure reuses the unchanged model's `_close` helper because Task 3 exposes no public integrity-failure transition. This is deliberately the smallest no-second-FSM bridge, but the private helper dependency is the one review concern.
- No broad tests, Task 5 audits, exact DP, training, smoke, validation, official test, parameter search, or rebaseline ran.

Next exact action: implement Task 5 exact Markov, firewall, witness, binding, and no-repair audits.

## Fix round 1/5 — I1, I2, M1

Independent review requested exactly three changes. Regression-first RED used:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_model_outcome tests.test_family3_v2_authority_environment -v
```

RED output: exit `1`; `Ran 19 tests in 0.076s`; `FAILED (failures=3, errors=2)`. The failures were exactly the caller-visible `authorization_id` fields for both request roles and the singleton branch-evidence assertion; the errors were exactly the missing public `Family3V2Model.transition_integrity_failure` API in the model and environment anomaly regression. Tool wall time: `0.680s`.

Minimal fixes:

- I1: `Family3V2EnvironmentInfo.binding_evidence` now contains `PublicAuthorizationBindingEvidenceV2`, which retains four-scope equality, validity/failure, and public ordinal but has no raw-ID field or value. The raw usable ID remains only in `_raw_authorization_by_ordinal`; private gateway results and quarantine evidence remain internal.
- I2: `Family3V2Model.transition_integrity_failure` validates a typed nonterminal state and nonempty reason, owns irreversible closure/outcome construction, and returns a terminal reward-zero transition with `next_mask=()`. Every environment anomaly calls this public API; no environment path calls `_close` or another private semantic helper.
- M1: after a committed first effect, the environment inspects the pure transition distribution and draws/appends a residue only for a genuine two-branch successor. Singleton closure uses residue zero and records no branch evidence.

Affected focused GREEN used the identical RED command: exit `0`; `Ran 19 tests in 0.071s`; `OK`. Tool wall time: `0.749s`.

The authorized Tasks 2–4 combined command ran once:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng tests.test_family3_v2_model_outcome tests.test_family3_v2_authority_environment -v
```

Combined output: exit `0`; `Ran 24 tests in 0.081s`; `OK`. Tool wall time: `0.582s`.

Fix-round boundary:

| File | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_model.py` | `F7848D2AC0343D2FFB79B24D584A81DA1FA5DAA51C7F97D35134948D90020F2C` | 23,904 |
| `tests/test_family3_v2_model_outcome.py` | `36A8BF08E5D0DC337FAC80447F5FF8E6BCC95FDE0293BEEBD551433886A9EFC1` | 11,357 |
| `src/pa_rl/family3_v2_authority.py` | `0ACA9E16347A8E0C128B0DCAF632A3223556A6C9D79ADBF4C9FE776FE030588D` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | 15,680 |
| `tests/test_family3_v2_authority_environment.py` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | 17,862 |

Frozen baseline SHA-256 remains `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`. No scientific parameter, legacy/frozen source, policy module, broad test, Task 5 audit, DP, or experiment run changed.

Concern: none beyond independent fix-round re-review still being required before Task 5.
