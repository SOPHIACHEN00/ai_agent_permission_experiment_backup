# Task 7 base — approved runner handoff (no Git)

Captured after Task 6 fix round 1 fresh scoped review returned **Spec PASS /
Task Quality PASS / APPROVE**, before either Task 7 implementation path exists.
This no-Git manifest is the immutable handoff base for the ordered twelve-gate
preflight runner.

## Handoff authority

| Item | SHA-256 | Bytes |
|---|---|---:|
| `task-7-brief.md` | `b678d05a6e2417c215cda1b0978195ef69ee8a2e1e4835e6c68b71410a0cc711` | 19,196 |
| `task-7-brief-draft.md` (preserved history) | `812d7452c7bb40c35910fc9cdee5dc88f7add3443d91e11a0d5c69b34d7055e4` | 18,625 |
| `task-7-recon.md` | `ed05f92b5bc7b08dcc1dbe5f4eeaae14cef3ebe99e46c118b1d43215522ea27a` | 17,620 |
| `task-6-fix-1-review.md` | `bdb1e827229d51eb9dc928282a45b6b461ea038d958c9cb553591d3f96ecf0db` | 13,846 |

The formal brief freezes the exact gate order, CLI, fixed output path,
versioned atomic `run_config.json`, exact JSON projection, Gate-2 pre-solver
algebra report, v0/v1 reference barrier, names, exits, stop behavior, and test
commands. An external `KeyboardInterrupt` must first mark the current
uncommitted gate interrupted and then be re-raised; only normal returns use
exit 0, 2, or 3.

## Frozen Task 2–6 production and test inputs

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c` | 23,904 |
| `src/pa_rl/family3_v2_authority.py` | `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` | 15,947 |
| `src/pa_rl/family3_v2_audit.py` | `92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921` | 64,280 |
| `src/pa_rl/family3_v2_exact_solver.py` | `b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0` | 37,078 |
| `src/pa_rl/family3_v2_exact_reference.py` | `7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575` | 12,684 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` | 34,232 |
| `tests/test_family3_v2_suite_rng.py` | `4755e05ddba9e3be84c875656f02cbdbb84917c1c3a12b8fd7c60fd7a9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092` | 18,793 |
| `tests/test_family3_v2_policy_audit.py` | `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` | 22,466 |
| `tests/test_family3_v2_exact_solver.py` | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` | 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` | 5,247 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` | 16,745 |

## Result-root base

Gate authority is exactly `BASELINE_FROZEN / last_completed_gate=0 /
next_gate=1`. The frozen baseline and Task-6-closeout result files are:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json` | `07cfaf05de1ef35dc4e38796b22dfbe72fdfc09276f3dd689dc75e8aa2c5addd` | 4,475 |
| `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/progress.jsonl` | `8d86c81b47ef84c2d4d31f04bd4e31c169d5a836ed9dd0d8693b8198e7ef0d32` | 19,680 |

The fixed result root contains exactly those three regular files and no
directories. In particular, no `run_config.json`, Gate report/evidence,
SQLite cache, certificate, failure/interruption artifact, or verdict exists.

## Expected-new Task 7 paths

Verified absent at this base:

- `src/pa_rl/family3_v2_preflight.py`
- `tests/test_family3_v2_preflight.py`

Task 7 may create only those two code/test paths. Only after Task 7 GREEN may
it update its approved logs and result artifacts as prescribed by the formal
brief. It must not modify Task 2–6 production/tests, specs, plan, baseline, or
the frozen Gate-0 authority.
