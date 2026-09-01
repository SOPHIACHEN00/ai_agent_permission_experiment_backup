# Task 6 base (no Git)

Captured after Task 5 fresh focused review returned Spec PASS / Quality PASS /
APPROVE and before any Task 6 production/test path exists. The workspace has no
Git repository; this hash manifest is the immutable review base.

## Frozen Task 2–5 inputs

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `C6CEB984C319A7A8FA407CB5ABE730FB75C31BA7513C36346C9695302985EEEB` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `B9DEF623BD0EB025754C458A4289D8A7C96E18C0AAAE5AA586A521D9DD0E8D54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `BF0F9CB388C883D20C77848C0CB8E94E73DA9D0F8769395440949FBEFFC46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `B4AAFF4856194966823380DCC1B34AF3CECEE3C2DA0ED5B0FA169C7F712318D6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `F7848D2AC0343D2FFB79B24D584A81DA1FA5DAA51C7F97D35134948D90020F2C` | 23,904 |
| `src/pa_rl/family3_v2_authority.py` | `0ACA9E16347A8E0C128B0DCAF632A3223556A6C9D79ADBF4C9FE776FE030588D` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `20FC2B7BDF42382508650FBC3D8E4143F8004CCE4D787D17FEA2B9C7C70F5AB8` | 15,947 |
| `src/pa_rl/family3_v2_audit.py` | `92EF0F7794536581A5FBB51719EA8B4A79436B61B4B0BC61EB3632A020B45921` | 64,280 |
| `tests/test_family3_v2_suite_rng.py` | `4755E05DDBA9E3BE84C875656F02CBDBB84917C1C3A12B8FD7C60FD7A9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36A8BF08E5D0DC337FAC80447F5FF8E6BCC95FDE0293BEEBD551433886A9EFC1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `DAF5E80AEA4569AC9FE8E007A5CF7A2F2EB680B69F6D28DA78D5A0916DE1D092` | 18,793 |
| `tests/test_family3_v2_policy_audit.py` | `DE07886C8609204B0A9539F1A514E85BCFE6E9B69E9FEA10CEFFD845CD37FE48` | 22,466 |

## Authority and handoff inputs

| Path | SHA-256 | Bytes |
|---|---|---:|
| `task-5-fix-2-review.md` | `ECBC39F3C765C7991F9E4588E7E5A07F1CE56B5AC94E46C2B82FF25FF230F4B6` | 1,839 |
| `task-6-brief.md` | `7D57AB70C77BE1FD8ADD1A68F7232C6FD6373FD85A69A14155A707F064F61581` | 11,788 |
| project checkpoint | `28C610CFC9ABF012B4440963726B8B39FCE801026AC076D89A35883CC77E637A` | 53,915 |
| result checkpoint | `AB06A3B0A2A027CF42C47C61E8766F0CDA5BF1E65B48FC85DD4328506D7DAF29` | 3,414 |
| result JSONL | `FEDD9C1687483EA2549123CCC54EAE420584ED32BF9F3780D35138044C26B849` | 13,153 |
| frozen baseline manifest | `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055` | 15,208 |

Checkpoint authority is exactly
`BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; Task 6 must not create
Gate 1, a real cache, certificate, or run config under the fixed result root.

## Expected-new paths verified absent

- `src/pa_rl/family3_v2_exact_solver.py`
- `src/pa_rl/family3_v2_exact_reference.py`
- `src/pa_rl/family3_v2_artifacts.py`
- `tests/test_family3_v2_exact_solver.py`
- `tests/test_family3_v2_exact_reference.py`
- `tests/test_family3_v2_artifacts.py`

The implementer may create exactly these six files, then update only Task 6
report/checkpoint records after focused GREEN. All tests must use isolated
temporary roots. No Task 2–5 or frozen legacy input may change.
