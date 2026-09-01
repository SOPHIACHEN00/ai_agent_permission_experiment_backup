# Task 6 fix round 1 scoped review package

Review only the binding `task-6-brief.md`, `task-6-review.md`, this package, and the six files below. The valid regression RED was 29 methods / 8.455s / 14 behavioral failures / zero errors. The single post-fix focused GREEN was 29 methods / 7.616s / OK. Task 7 remains blocked.

## Before/after manifest

| Path | Before SHA-256 / bytes | After SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_exact_solver.py` | `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` / 36,031 | `b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0` / 37,078 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` / 11,935 | `7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575` / 12,684 |
| `src/pa_rl/family3_v2_artifacts.py` | `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` / 29,226 | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` / 34,232 |
| `tests/test_family3_v2_exact_solver.py` | `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` / 7,172 | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` / 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` / 3,400 | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` / 5,247 |
| `tests/test_family3_v2_artifacts.py` | `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` / 7,127 | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` / 16,745 |

## Finding map

| Finding | Production | Regression evidence |
|---|---|---|
| C1 | `family3_v2_artifacts.py:272-296` | `test_family3_v2_artifacts.py:104`, `:125`, `:158`, `:176` |
| I1 | `family3_v2_artifacts.py:431-568` | `test_family3_v2_artifacts.py:252`, `:280`, `:315` |
| I2 | `family3_v2_artifacts.py:536-541` | `test_family3_v2_artifacts.py:265` |
| I3 | `family3_v2_exact_solver.py:480-533` | `test_family3_v2_exact_solver.py:188` |
| I4 | `family3_v2_exact_reference.py:235-248` | `test_family3_v2_exact_reference.py:122` |
| I5 | schema validation above; existing true LRU implementation pressure-tested | `test_family3_v2_exact_solver.py:146`, `:188`, `:212` |
| I6 | C1/I1/I2 store changes above | `test_family3_v2_artifacts.py:92-324` |
| M1 | `family3_v2_exact_reference.py:94-119` | `test_family3_v2_exact_reference.py:65-87` |

## Scope and frozen state

The three production and three test files are the only Task 6 implementation files changed. All 13 Task 2–5 hashes/bytes match the review base. No scientific constant, Task 2–5 source, legacy/baseline file, Gate, real run config, cache, certificate, or result evidence changed. Gate authority is still `BASELINE_FROZEN / 0 / 1`.
