# Task 5 fix round 2 base (no Git)

Captured after the fresh fix-round-1 review and before the original implementer
resumes. Authorized production/test changes are limited to the two open
Critical findings in `task-5-fix-1-review.md`.

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_environment.py` | `20FC2B7BDF42382508650FBC3D8E4143F8004CCE4D787D17FEA2B9C7C70F5AB8` | 15,947 |
| `tests/test_family3_v2_authority_environment.py` | `DAF5E80AEA4569AC9FE8E007A5CF7A2F2EB680B69F6D28DA78D5A0916DE1D092` | 18,793 |
| `src/pa_rl/family3_v2_audit.py` | `1BA1DC3B660892410BB31BEC9AF3CB1A0D145F479851FFB58EE954EC049B98D5` | 57,282 |
| `tests/test_family3_v2_policy_audit.py` | `2ED2837D0E081947643E4DEF4B7893D431FACAA5A631A23EC0F6B19B2FE708D0` | 19,073 |
| `task-5-report.md` | `6FFA5E8F6B0A40E54698081A88B47AF93D075C48A90F50A4B9E1DD3B8FB275EE` | 8,227 |
| SDD `progress.md` | `0B03D03433C6D9E9FFA11DB6D63A71D40616A14FDDFC6DCC6594E25C5B068913` | 11,783 |
| project checkpoint | `48D1ACF32EB8CD58AA55D4EABF6000F7EE2E0D2D121C7EA5C731C351BB4E851D` | 52,851 |
| result checkpoint | `D0924BAE5B899914F153EE494D2585700DAC418BD7DD512393AE74424E0C5C14` | 2,989 |
| result JSONL | `30F095E00913AB89F550C0A16457DFC8A4690BFBC691A2718E1FE3E38A5DCFC8` | 10,765 |

The independently accepted C3/I1/I2/I3/I4/M1 code must not be redesigned.
Task 2/3, authority, policy, environment, environment test, legacy sources and
results, scientific parameters, output root, and gates are immutable in this
round. The independently clarified Task 6 brief is also out of scope and must
remain SHA-256
`7D57AB70C77BE1FD8ADD1A68F7232C6FD6373FD85A69A14155A707F064F61581`.

Frozen baseline remains
`D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`.
Checkpoint authority must remain `BASELINE_FROZEN / 0 / 1`.
