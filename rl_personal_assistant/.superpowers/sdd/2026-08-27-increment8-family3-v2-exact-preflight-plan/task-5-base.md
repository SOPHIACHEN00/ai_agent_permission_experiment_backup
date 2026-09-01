# Task 5 base manifest (no Git repository)

Captured after Task 4 fix-round re-review APPROVE and before Task 5 dispatch.

Expected-new paths were absent:

- `src/pa_rl/family3_v2_audit.py`
- `tests/test_family3_v2_policy_audit.py`

## Frozen Task 2–4 inputs

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `C6CEB984C319A7A8FA407CB5ABE730FB75C31BA7513C36346C9695302985EEEB` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `B9DEF623BD0EB025754C458A4289D8A7C96E18C0AAAE5AA586A521D9DD0E8D54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `BF0F9CB388C883D20C77848C0CB8E94E73DA9D0F8769395440949FBEFFC46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `B4AAFF4856194966823380DCC1B34AF3CECEE3C2DA0ED5B0FA169C7F712318D6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `F7848D2AC0343D2FFB79B24D584A81DA1FA5DAA51C7F97D35134948D90020F2C` | 23,904 |
| `src/pa_rl/family3_v2_authority.py` | `0ACA9E16347A8E0C128B0DCAF632A3223556A6C9D79ADBF4C9FE776FE030588D` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | 15,680 |
| `tests/test_family3_v2_suite_rng.py` | `4755E05DDBA9E3BE84C875656F02CBDBB84917C1C3A12B8FD7C60FD7A9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36A8BF08E5D0DC337FAC80447F5FF8E6BCC95FDE0293BEEBD551433886A9EFC1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | 17,862 |

## Checkpoint/baseline inputs

| Path | SHA-256 |
|---|---|
| `docs/CONTINUATION_CHECKPOINT.md` | `42EC50F87D61E77827D0281B9E9F639698E5406ED03421AC7294C53E7D515BA4` |
| result `continuation_checkpoint.json` | `70ED099120F27C5574B6DDF5297F2E7F267F27AC1F27671011E0342197A401BC` |
| result `progress.jsonl` | `0C92541602CC90786EDEDD6D2731862CB80F3595356245496857A4BB6E1B0AB3` |
| frozen baseline | `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055` |

No Git base/head exists. The complete contents of the two expected-new paths are the Task 5 code/test diff. All inputs above must remain unchanged.

