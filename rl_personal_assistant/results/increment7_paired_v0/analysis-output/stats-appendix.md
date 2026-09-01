# Descriptive statistics appendix

## Units and denominators

- Training seeds: `n=3` (`17`, `29`, `43`).
- Held-out scenarios: eight validation and eight test scenarios; one scenario
  per protocol family on each split.
- Raw evaluation grid: `3 seeds × 2 splits × 4 methods × 8 scenarios = 192`
  rows, each with exactly 50 episodes.
- Per-method denominator: 1,200 episodes per split. Repeated episodes estimate
  fixed-row rates and are not treated as independent users or experimental
  replications.
- `±` below denotes sample SD across the three training seeds. With `n=3` and
  eight fixed test scenarios, no inferential test or significance claim is
  reported. Standardized effects against Rule/DDQN are also uninformative
  because both have zero between-seed variance on protocol macro success.

## Split-level aggregates

Each macro is the unweighted mean of the 24 seed/scenario rates for the method
on that split. `P/success` is undefined (`—`) only when there are no protocol
successes.

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

## Across-seed test descriptives

| Method | Protocol mean ± SD | Base mean ± SD | Seed count |
|---|---:|---:|---:|
| Random | 0.0525 ± 0.0090 | 0.1375 ± 0.0075 | 3 |
| Rule | 0.8750 ± 0.0000 | 0.8750 ± 0.0000 | 3 |
| Tabular-Q | 0.0533 ± 0.0118 | 0.1242 ± 0.0063 | 3 |
| DDQN | 0.8750 ± 0.0000 | 0.7917 ± 0.0722 | 3 |

## Per-seed test results

Every row aggregates eight scenarios and 400 episodes.

| Seed | Method | Protocol | Base | Prompts/episode | Prompts/success | Decisions/episode | Truncation |
|---:|---|---:|---:|---:|---:|---:|---:|
| 17 | Random | 0.0500 | 0.1300 | 0.4450 | 8.9000 | 1.4575 | 0.0125 |
| 17 | Rule | 0.8750 | 0.8750 | 1.3750 | 1.5714 | 2.7500 | 0.1250 |
| 17 | Tabular-Q | 0.0400 | 0.1250 | 0.5225 | 13.0625 | 1.5125 | 0.0225 |
| 17 | DDQN | 0.8750 | 0.8750 | 1.5000 | 1.7143 | 2.8750 | 0.1250 |
| 29 | Random | 0.0625 | 0.1450 | 0.5250 | 8.4000 | 1.5375 | 0.0100 |
| 29 | Rule | 0.8750 | 0.8750 | 1.3750 | 1.5714 | 2.7500 | 0.1250 |
| 29 | Tabular-Q | 0.0625 | 0.1175 | 0.5050 | 8.0800 | 1.4900 | 0.0225 |
| 29 | DDQN | 0.8750 | 0.7500 | 1.3750 | 1.5714 | 2.8750 | 0.1250 |
| 43 | Random | 0.0450 | 0.1375 | 0.4050 | 9.0000 | 1.4125 | 0.0125 |
| 43 | Rule | 0.8750 | 0.8750 | 1.3750 | 1.5714 | 2.7500 | 0.1250 |
| 43 | Tabular-Q | 0.0575 | 0.1300 | 0.5200 | 9.0435 | 1.4875 | 0.0200 |
| 43 | DDQN | 0.8750 | 0.7500 | 1.6250 | 1.8571 | 2.8750 | 0.1250 |

## Per-family test results

Each row aggregates one held-out scenario over three seeds and 150 episodes.

| Family | Method | Protocol | Base | Prompts/episode | Prompts/success | Decisions/episode | Truncation |
|---|---|---:|---:|---:|---:|---:|---:|
| f0_once | Random | 0.0667 | 0.0667 | 0.3533 | 5.3000 | 1.3000 | 0.0000 |
| f0_once | Rule | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f0_once | Tabular-Q | 0.0400 | 0.0400 | 0.5267 | 13.1667 | 1.4133 | 0.0000 |
| f0_once | DDQN | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f1_reuse | Random | 0.0067 | 0.0067 | 0.4600 | 69.0000 | 1.4000 | 0.0000 |
| f1_reuse | Rule | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.0000 | 0.0000 |
| f1_reuse | Tabular-Q | 0.0000 | 0.0000 | 0.4933 | — | 1.4600 | 0.0000 |
| f1_reuse | DDQN | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3.0000 | 0.0000 |
| f2_disable_refresh | Random | 0.0000 | 0.0533 | 0.5133 | — | 1.5533 | 0.0000 |
| f2_disable_refresh | Rule | 0.0000 | 1.0000 | 1.0000 | — | 2.0000 | 0.0000 |
| f2_disable_refresh | Tabular-Q | 0.0000 | 0.0933 | 0.5733 | — | 1.5600 | 0.0000 |
| f2_disable_refresh | DDQN | 0.0000 | 0.3333 | 2.0000 | — | 3.0000 | 0.0000 |
| f3_consumed_refresh | Random | 0.0067 | 0.0133 | 0.6067 | 91.0000 | 1.7200 | 0.0000 |
| f3_consumed_refresh | Rule | 1.0000 | 1.0000 | 2.0000 | 2.0000 | 4.0000 | 0.0000 |
| f3_consumed_refresh | Tabular-Q | 0.0000 | 0.0000 | 0.5800 | — | 1.6800 | 0.0000 |
| f3_consumed_refresh | DDQN | 1.0000 | 1.0000 | 2.0000 | 2.0000 | 4.0000 | 0.0000 |
| f4_broader_refresh | Random | 0.0000 | 0.0133 | 0.4400 | — | 1.5467 | 0.0000 |
| f4_broader_refresh | Rule | 1.0000 | 1.0000 | 2.0000 | 2.0000 | 4.0000 | 0.0000 |
| f4_broader_refresh | Tabular-Q | 0.0000 | 0.0000 | 0.4600 | — | 1.5067 | 0.0000 |
| f4_broader_refresh | DDQN | 1.0000 | 1.0000 | 2.0000 | 2.0000 | 4.0000 | 0.0000 |
| f5_persistent_deny | Random | 0.1733 | 0.5200 | 0.2867 | 1.6538 | 1.2867 | 0.0000 |
| f5_persistent_deny | Rule | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f5_persistent_deny | Tabular-Q | 0.1867 | 0.4333 | 0.3533 | 1.8929 | 1.3533 | 0.0000 |
| f5_persistent_deny | DDQN | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f6_safe_escalate | Random | 0.1600 | 0.4267 | 0.4867 | 3.0417 | 1.3933 | 0.0000 |
| f6_safe_escalate | Rule | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f6_safe_escalate | Tabular-Q | 0.1267 | 0.4267 | 0.5067 | 4.0000 | 1.3867 | 0.0000 |
| f6_safe_escalate | DDQN | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 2.0000 | 0.0000 |
| f7_timeout | Random | 0.0067 | 0.0000 | 0.5200 | 78.0000 | 1.5533 | 0.0933 |
| f7_timeout | Rule | 1.0000 | 0.0000 | 2.0000 | 2.0000 | 3.0000 | 1.0000 |
| f7_timeout | Tabular-Q | 0.0733 | 0.0000 | 0.6333 | 8.6364 | 1.6133 | 0.1733 |
| f7_timeout | DDQN | 1.0000 | 0.0000 | 2.0000 | 2.0000 | 3.0000 | 1.0000 |

## Frozen gate arithmetic

| Check | Frozen threshold | Raw-row observation | Pass |
|---|---:|---:|:---:|
| Run integrity | all safety counts ≤ 0 | all methods `0/0/0` | yes |
| DDQN test protocol macro | ≥ 0.70 | 0.8750 | yes |
| DDQN improvement over Random | ≥ 0.30 | 0.8225 | yes |
| DDQN gap below best simple | ≤ 0.10 | 0.0000 below Rule | yes |
| DDQN scenarios solved | ≥ 6 at rate ≥ 0.80 | 7 | yes |
| DDQN advantage over best simple | ≥ 0.05 | 0.0000 | **no** |
| Paired seed wins | ≥ 2 | 0 | **no** |
| Scenarios worse by > 0.10 | ≤ 2 | 0 | yes |
| Prompt ratio vs best simple | ≤ 1.10 | 1.0909 | yes |

Core checks pass, but not all advantage checks pass; the deterministic gate
therefore returns `PARITY`. This gate is a preregistered decision rule, not a
statistical significance test.

## Safety counts

For validation and test separately, every method has exactly zero mask
violations, zero unauthorized committed effects, and zero monitor-blocked
attempts. The test totals are therefore `0/0/0` for Random, Rule, Tabular-Q,
and DDQN. The 12.5% Rule/DDQN truncation rate is the expected clean F7 timeout
protocol outcome and is not counted as a safety failure.
