# Task 4 fix round 1 no-Git review package

## Scope

- Original review: `task-4-review.md`
- Fix base: `task-4-fix-1-base.md`
- Updated report: `task-4-report.md` (SHA-256 `3977836926E853FED248AA4355E270AA167313BD733CB82DF549D2E3AF65F1E9`)
- Fixes under review: I1, I2, M1 only
- Git base/head: unavailable by recorded ruling

## Final affected files

| Path | Fix-base SHA-256 | Fix-head SHA-256 | Final size |
|---|---|---|---:|
| `src/pa_rl/family3_v2_model.py` | `315A13A37A5D8479EC3185B7082FB45E51E42A62493A374BB205CC6BC45B246A` | `F7848D2AC0343D2FFB79B24D584A81DA1FA5DAA51C7F97D35134948D90020F2C` | 23,904 |
| `tests/test_family3_v2_model_outcome.py` | `E9346686642413C9D90FA679439D76FACE47C91A61FA6071A07C1890A5D79E21` | `36A8BF08E5D0DC337FAC80447F5FF8E6BCC95FDE0293BEEBD551433886A9EFC1` | 11,357 |
| `src/pa_rl/family3_v2_authority.py` | `6392DE61318636EE092257C77040DEBF9B4A8DDA24480D55FE72C1E6DC67457C` | `0ACA9E16347A8E0C128B0DCAF632A3223556A6C9D79ADBF4C9FE776FE030588D` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | unchanged | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `08D91F72E5F8B1DC90599DEF2B4503F385C66262DD3C4882C5377496910FF4C5` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | 15,680 |
| `tests/test_family3_v2_authority_environment.py` | `5DB1B8D3FF81318EAA6231DBAB01E8B0D9C08BB3EC4BC950CDAD97F57FE7289A` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | 17,862 |

Checkpoint heads:

- project checkpoint: `42EC50F87D61E77827D0281B9E9F639698E5406ED03421AC7294C53E7D515BA4`
- result checkpoint: `70ED099120F27C5574B6DDF5297F2E7F267F27AC1F27671011E0342197A401BC`
- progress JSONL: `0C92541602CC90786EDEDD6D2731862CB80F3595356245496857A4BB6E1B0AB3`
- frozen baseline: unchanged `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`

## Review questions

1. I1: Does every caller-visible binding-evidence object now omit raw usable/quarantined authorization IDs while retaining four-scope equality and public ordinal, with the raw usable ID solely in the private environment map?
2. I2: Does every integrity anomaly use the public model-owned `transition_integrity_failure`, with no environment dependency on `_close` or duplicated outcome/closure logic, and is the new API itself correct/validated/terminal-empty-mask?
3. M1: Is branch residue drawn/appended only when the model-owned first-effect distribution is genuinely two-way, with singleton closure using no branch evidence?
4. Did the cross-task API addition preserve the existing pure model semantics and forbidden-import boundary?

The updated report records a 19-test finding-specific RED (3 failures/2 errors), 19-test affected GREEN, and 24-test Tasks 2–4 combined GREEN. Inspect code rather than trusting counts. Read the complete current contents of every affected file as the fix diff where line-level base diffs are unavailable.

