# Task 5 fix round 1 base (no Git)

Captured after `task-5-review.md` and before the original implementer resumes.

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_environment.py` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | 15,680 |
| `tests/test_family3_v2_authority_environment.py` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | 17,862 |
| `src/pa_rl/family3_v2_audit.py` | `36F590A1804369F05429142479A6D51FA0D9F50A9FFBDC0BA6BB00675ED6CB2C` | 44,665 |
| `tests/test_family3_v2_policy_audit.py` | `A848B77C80F74DA487374EF3C40FE191140CEEBC520CC24746617CCA3C82D77F` | 11,815 |
| `docs/CONTINUATION_CHECKPOINT.md` | `56F40FAA18B6A1813ECA643EF721DEEE3BED8D6AE6563367BCD484DF78D6B0D4` | 51,804 |
| result `continuation_checkpoint.json` | `F6382785E28B20C0B8BC1C2D1C1B21D6256127634DEFA1274C57657A2E83EBFC` | 2,536 |
| result `progress.jsonl` | `9574E19BA7D00D50F0DE1A341117C4C790F3515B717F99332041AB7D1EC28168` | 8,802 |

Task 2/3 and other Task 4 files retain `task-5-base.md` hashes. Frozen baseline remains `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`.

The authorized fix surface is exactly C1–C3, I1–I4, and M1 from `task-5-review.md`, plus the minimal Task 4 audit-evidence fields/tests required by C1/C2.

