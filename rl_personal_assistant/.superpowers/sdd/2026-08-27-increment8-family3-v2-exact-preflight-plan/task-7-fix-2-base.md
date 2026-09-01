# Task 7 readiness fix round 2/5 base (no Git)

Captured after fix-round-1 fresh scoped re-review returned `DO_NOT_RUN`.
Adjacent regressions, compile, and real preflight remain blocked.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `task-7-fix-1-review.md` | `97766cc00a55119f97bdbe7ffed2ff2fa35025b23a9842ffb0ba4038f2d4c1a3` | 13,270 |
| `src/pa_rl/family3_v2_preflight.py` | `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9` | 56,228 |
| `tests/test_family3_v2_preflight.py` | `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037` | 46,672 |
| `src/pa_rl/family3_v2_artifacts.py` | `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4` | 38,935 |
| `tests/test_family3_v2_artifacts.py` | `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4` | 22,915 |

Open: C1 complete persistence/durable-pass protocol; I2 per-graph committed
Gate-4 report/evidence/result/certificate binding; I4 real-handler per-predicate
negative matrix. I1, I3, and M1 are accepted as addressed. Gate authority is
`BASELINE_FROZEN / 0 / 1`; fixed root remains three files.
