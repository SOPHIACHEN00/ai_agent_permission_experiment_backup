# Task 2 fix round 1 no-Git review package

## Fix range

- Fix base: `task-2-fix-1-base.md`
- Full prior findings: `task-2-review.md`
- Appended fix evidence: final section of `task-2-report.md`

## Changed in this fix

| Path | Fix base | Fix head |
|---|---|---|
| `src/pa_rl/family3_v2_suite.py` | `530244305D1C36A3973277810369ECA756DC4BC17990535C4F733F5909DB16C4` | `B9DEF623BD0EB025754C458A4289D8A7C96E18C0AAAE5AA586A521D9DD0E8D54` |
| `tests/test_family3_v2_suite_rng.py` | `6CE4F5623B7E4CF973826753E75830B1E668FA50A5B3C71EC3D437BD4663EF9F` | `4755E05DDBA9E3BE84C875656F02CBDBB84917C1C3A12B8FD7C60FD7A9283379` |
| result checkpoint | `873248C...` | `1EA5716AAAC0C19BDE259CBB8D973B14BB0EEE9F534B7BED6E38D50743A20351` |
| result progress | `C65EF8C...` | `DFEC520A915CC4F3F66A04ED483EC34A9D6F0960CA85B87AFB492DDA5F68D68C` |
| project checkpoint | `A349C41...` | `FB603CA14F91551FFA93F167831103AD819272DAE6CCB5599FEE21CD17E54CBE` |

Unchanged in this fix: contracts `C6CEB984...`, RNG `BF0F9CB3...`, frozen baseline `D8B8FF2C...`.

## Scope

Re-review only I1 and I2 from `task-2-review.md` and new breakage in the changed suite/test/checkpoint lines. The current full contents of the two changed code files are the no-Git fix diff; use the fix-base hashes to confirm the range. The report records two named covering tests, exact RED (`5 tests`, eight failures) and exact GREEN (`5 tests`, `OK`).

