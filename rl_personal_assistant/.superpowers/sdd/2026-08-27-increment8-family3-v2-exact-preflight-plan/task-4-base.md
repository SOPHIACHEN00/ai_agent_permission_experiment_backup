# Task 4 base manifest (no Git repository)

Captured after Task 3 independent APPROVE and before Task 4 dispatch.

## Expected-new paths

All were absent:

- `src/pa_rl/family3_v2_authority.py`
- `src/pa_rl/family3_v2_policy.py`
- `src/pa_rl/family3_v2_environment.py`
- `tests/test_family3_v2_authority_environment.py`

## Frozen Task 2/3 inputs

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `C6CEB984C319A7A8FA407CB5ABE730FB75C31BA7513C36346C9695302985EEEB` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `B9DEF623BD0EB025754C458A4289D8A7C96E18C0AAAE5AA586A521D9DD0E8D54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `BF0F9CB388C883D20C77848C0CB8E94E73DA9D0F8769395440949FBEFFC46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `B4AAFF4856194966823380DCC1B34AF3CECEE3C2DA0ED5B0FA169C7F712318D6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `315A13A37A5D8479EC3185B7082FB45E51E42A62493A374BB205CC6BC45B246A` | 23,231 |
| `tests/test_family3_v2_suite_rng.py` | `4755E05DDBA9E3BE84C875656F02CBDBB84917C1C3A12B8FD7C60FD7A9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `E9346686642413C9D90FA679439D76FACE47C91A61FA6071A07C1890A5D79E21` | 10,374 |

## Checkpoint/baseline inputs

| Path | SHA-256 |
|---|---|
| `docs/CONTINUATION_CHECKPOINT.md` | `6AF2CF1D7F9A644F5EEBD8CAD779FBE50F5077B980F0E49A1C5508D6EC9B547D` |
| result `continuation_checkpoint.json` | `9F12EBF2DA4E2EE59CD4135E8344F5B7ED830F67E4ACAD48D77DD256CB15329D` |
| result `progress.jsonl` | `456AE40D35D29C330136F05A9165E75FFA1D96B37E5C9ED275FDC8F4FC80B107` |
| frozen baseline manifest | `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055` |

No Git base/head exists. The complete contents of each expected-new path will be the Task 4 production/test diff. Checkpoint changes are compared against the hashes above. The frozen baseline is immutable.

