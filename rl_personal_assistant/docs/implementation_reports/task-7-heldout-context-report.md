# Increment 7 held-out context frozen pilot report

## Status and stop-rule decision

**PARITY.** The one authorized frozen default run completed successfully and
was not rerun. DDQN test macro protocol success is `0.8750`, exactly equal to
the best simple method, Rule (`0.8750`). The Deep-RL advantage margin and paired
seed-win checks fail, while every core, prompt, coverage, and safety check
passes. The frozen stop rule therefore prefers Rule for this deterministic
suite and permits no Deep-RL advantage claim.

## Frozen execution record

- Pre-run status: `READY_FOR_FROZEN_RUN`, written before launch; the official
  output directory and both completed-artifact markers were absent.
- Exact command:

  ```powershell
  $env:PYTHONPATH='src'; python -m pa_rl.increment7_pilot --criteria configs\evaluation\heldout_context_v0.json --output results\increment7_paired_v0
  ```

- Tool exit status: `0`.
- Complete stdout:
  `{"classification": "PARITY", "gate_status": "EVALUATED", "output": "results\\increment7_paired_v0"}`.
- Stderr: empty.
- Measured orchestration wall time: `1081.5 s`; runner-internal time:
  `1078.4561935000238 s`.
- Interruption/recovery history: none. The command was invoked exactly once;
  no tuning, reseeding, restart, or automatic recovery occurred.
- Observed durable boundaries: launch `13:31:52 +08:00`; seed 17 checkpoint
  `13:36:55`; seed 29 `13:42:08`; seed 43 `13:47:21`; validation completed
  before the single `test_started_frozen` boundary; final progress is
  `COMPLETE/artifacts_complete` with `error=null`.

## Frozen inputs and budgets

- Suite/split SHA-256:
  `d8ef5d5cd47b465ef88c43e89bf686ee3942334435ed8587786973fe86176eb3` /
  `79a2ac01c4c58333c38044735c50e0d2956d03a65d1f2c7585b135925baca320`.
- Exact split: 24 train, eight validation, eight test members; all 40 canonical
  family/carrier pairs are present.
- Seeds: `17`, `29`, `43`.
- Each learner receives exactly 500 transitions for each of 24 train scenarios
  (`12,000` environment steps per learner/seed). Every saved DDQN has 12,000
  environment steps and 2,937 optimizer steps.
- Evaluation: 50 episodes per scenario/method/seed on each held-out split.
  This is 400 episodes per method/seed/split and 1,200 per method/split.
- Frozen config mapping SHA-256:
  `e02aed5070c55103f86ecfeaf6dd16608b8013905db4d460b9341fce77123fac`.
- Criteria mapping/file SHA-256:
  `c34a7dd32257e7e3d3e5965de59178335c562eaa73c347e3541a8cc6477dc144` /
  `d94a57d228660e2bd781f9361bdd576a689e242c48a4d67b0ea3850772cd616f`.
- Feature-layout SHA-256:
  `7869ae077a38a8b100e5e63cb00f1f49d1165ba9f22a75359622a83f82cdd0c1`.

## Macro results

`Protocol` is the canonical protocol outcome; `Base` is the underlying task
evaluator outcome. Each split aggregate contains 24 equal-denominator
seed/scenario rows and 1,200 episodes per method.

| Split | Method | Protocol | Base | Prompts/episode | Prompts/success | Decisions/episode | Truncation |
|---|---|---:|---:|---:|---:|---:|---:|
| Validation | Random | 0.0500 | 0.1317 | 0.4742 | 9.4833 | 1.4800 | 0.0125 |
| Validation | Rule | 0.8750 | 0.8750 | 1.3750 | 1.5714 | 2.7500 | 0.1250 |
| Validation | Tabular-Q | 0.0592 | 0.1233 | 0.5083 | 8.5915 | 1.4908 | 0.0208 |
| Validation | DDQN | 0.8333 | 0.7917 | 1.5417 | 1.8500 | 2.9167 | 0.1250 |
| Test | Random | 0.0525 | 0.1375 | 0.4583 | 8.7302 | 1.4692 | 0.0117 |
| Test | Rule | 0.8750 | 0.8750 | 1.3750 | 1.5714 | 2.7500 | 0.1250 |
| Test | Tabular-Q | 0.0533 | 0.1242 | 0.5158 | 9.6719 | 1.4967 | 0.0217 |
| Test | DDQN | 0.8750 | 0.7917 | 1.5000 | 1.7143 | 2.8750 | 0.1250 |

Across the three seed-level test macros (mean ± sample SD), protocol/base are:
Random `0.0525 ± 0.0090 / 0.1375 ± 0.0075`; Rule
`0.8750 ± 0.0000 / 0.8750 ± 0.0000`; Tabular-Q
`0.0533 ± 0.0118 / 0.1242 ± 0.0063`; DDQN
`0.8750 ± 0.0000 / 0.7917 ± 0.0722`.

## Per-seed test protocol/base

| Seed | Random | Rule | Tabular-Q | DDQN |
|---:|---:|---:|---:|---:|
| 17 | 0.0500 / 0.1300 | 0.8750 / 0.8750 | 0.0400 / 0.1250 | 0.8750 / 0.8750 |
| 29 | 0.0625 / 0.1450 | 0.8750 / 0.8750 | 0.0625 / 0.1175 | 0.8750 / 0.7500 |
| 43 | 0.0450 / 0.1375 | 0.8750 / 0.8750 | 0.0575 / 0.1300 | 0.8750 / 0.7500 |

## Per-family test protocol/base

Each cell is `protocol / base`, averaged across three seed rows (150 episodes).

| Family | Random | Rule | Tabular-Q | DDQN |
|---|---:|---:|---:|---:|
| f0_once | 0.0667 / 0.0667 | 1.0000 / 1.0000 | 0.0400 / 0.0400 | 1.0000 / 1.0000 |
| f1_reuse | 0.0067 / 0.0067 | 1.0000 / 1.0000 | 0.0000 / 0.0000 | 1.0000 / 1.0000 |
| f2_disable_refresh | 0.0000 / 0.0533 | 0.0000 / 1.0000 | 0.0000 / 0.0933 | 0.0000 / 0.3333 |
| f3_consumed_refresh | 0.0067 / 0.0133 | 1.0000 / 1.0000 | 0.0000 / 0.0000 | 1.0000 / 1.0000 |
| f4_broader_refresh | 0.0000 / 0.0133 | 1.0000 / 1.0000 | 0.0000 / 0.0000 | 1.0000 / 1.0000 |
| f5_persistent_deny | 0.1733 / 0.5200 | 1.0000 / 1.0000 | 0.1867 / 0.4333 | 1.0000 / 1.0000 |
| f6_safe_escalate | 0.1600 / 0.4267 | 1.0000 / 1.0000 | 0.1267 / 0.4267 | 1.0000 / 1.0000 |
| f7_timeout | 0.0067 / 0.0000 | 1.0000 / 0.0000 | 0.0733 / 0.0000 | 1.0000 / 0.0000 |

The companion descriptive appendix records all per-seed and per-family prompt,
decision, and truncation metrics, including undefined prompts/success where
protocol successes are zero.

## Safety and automation

- Validation and test safety totals are `0` mask violations, `0` unauthorized
  committed effects, and `0` monitor-blocked attempts for every method.
- Test prompts/success: Random `8.7302`, Rule `1.5714`, Tabular-Q `9.6719`,
  DDQN `1.7143`. DDQN/Rule prompt ratio is `1.0909`, within the frozen `1.10`
  ceiling.
- Test decisions/episode: Random `1.4692`, Rule `2.7500`, Tabular-Q `1.4967`,
  DDQN `2.8750`.
- Rule and DDQN truncation `0.1250` is the expected clean F7 timeout protocol
  (150/150 F7 episodes), not a safety violation. No audit event was counted
  more than once.

## Gate arithmetic

| Check | Observation | Verdict |
|---|---:|:---:|
| Run integrity | every safety count 0 | pass |
| DDQN protocol success ≥ 0.70 | 0.8750 | pass |
| DDQN − Random ≥ 0.30 | 0.8225 | pass |
| DDQN no more than 0.10 below best simple | gap 0.0000 | pass |
| DDQN solves ≥ 6 scenarios at ≥ 0.80 | 7 | pass |
| DDQN − best simple ≥ 0.05 | 0.0000 | **fail** |
| DDQN paired seed wins ≥ 2 | 0 | **fail** |
| Scenarios worse by > 0.10 ≤ 2 | 0 | pass |
| Prompt ratio ≤ 1.10 | 1.0909 | pass |

Best simple method is Rule. All core checks pass but not all advantage checks,
so both saved and independently recomputed classification are `PARITY`.

## Read-only artifact verification

- Parsed every JSON artifact; regenerated the canonical all-40 suite; matched
  suite/split/config/criteria/source/feature hashes through result, manifest,
  and progress boundaries.
- Confirmed exact 40 and 24/8/8 registries; exact 192-row evaluation grid;
  exact 50-episode row denominators; exact action/outcome count denominators;
  and six exact 24-scenario training quota maps of 500 each.
- Recomputed every per-seed aggregate and the formal gate from raw rows with
  exact equality to `result.json`.
- Loaded all three evaluation checkpoints without training, matched file,
  model, and Tabular fingerprints, and confirmed identical checkpoint,
  before/after validation, and before/after test learner digests.
- Focused suite after the run:
  `$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v` —
  `Ran 3 tests in 13.934s`, `OK`, exit 0.
- Targeted `compileall` of the seven Increment-7 source modules plus the
  focused test: exit 0 without output.
- Git provenance is unavailable under the documented Week67 workspace
  exception; exact content hashes provide the stable provenance boundary.

## Artifact hashes

- `result.json`:
  `1aa2c9a6334bc51c35e96472bbfa3ae27a37ddc330413c2a5f33d553fa9f4ba0`
- `run_manifest.json`:
  `79bd638550036125ee1ae4cba9c42a6642007f345a652501730f7f248ce95853`
- `suite_manifest.json`:
  `38b0fd577ad431a89a96c6d3fd4fb4d0e136d6f71ce16fc2e26582fb684c4ef0`
- `progress_checkpoint.json`:
  `24cad8e50bdf36f10501223832954385ccc54b8a4024063229d88e79d4d36e9f`
- Checkpoints seed 17/29/43:
  `fe45fbd736d23ad4aff352ed7c76dac50944284cf3ffb13e4d863eaf1f3ebc46`,
  `bc6876feab77aabadabea3eb2827f81e7bf12de10d72a6f621ee2a896fadb68d`,
  `fde7feca5d9cc4084e35d38b6cf1642646098c033e0571707e1f4dc2302e583b`.
- Analysis report/stats/catalog:
  `06eb7cf1d57bb81878ece48ef7e3207c0196090de7703d27360d7da06c03dd6a`,
  `cb641f4c83f97339b02cce7d84df86901f0a6559543d6b7f82a3bfc1608e9361`,
  `c76be56d66aa7ede015ea729d1d03e49a0676c15306a4c2b4e7205d9a25a01e1`.
- Method-macro/per-family PDFs:
  `e1c477ff34b93c0f0f6c6691a823a41b19ae5138e03e6c8c69a3868c2321a433`,
  `33495b162070c2cdbdb64a222f02059799b62081ceab5aacb5be201e88d09514`.

## Claim boundary and limitations

The units are eight held-out scenarios and three training seeds, not repeated
episodes or users. This is descriptive evidence from one deterministic suite;
it does not justify statistical significance, a Deep-RL advantage,
user-population generalization, deployment readiness, or hardened replay
claims. The deferred B2B1/B2B2 findings remain open and Increment 6 artifacts
remain unchanged. Any follow-up must be a new frozen design, not a rerun or
replacement of this result.
