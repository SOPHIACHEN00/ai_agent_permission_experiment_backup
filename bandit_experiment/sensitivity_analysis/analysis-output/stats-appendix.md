# Statistical appendix

## Design and unit

- Test rows: 3,323 from 41 held-out participants.
- Repeated unit: 10 randomized online stream seeds: 101, 211, 307, 401, 503, 601, 701, 809, 907, 1009.
- Access factorial: 4 task-utility weights x 3 unnecessary-access weights x 3 algorithms.
- Persistence factorial: 3 interruption weights x 3 over-persistence weights x 3 algorithms.
- Every cell was retrained from scratch for every seed.
- Common seeds were reused across conditions, so contrasts are paired.

## Descriptive statistics

Each summary CSV reports mean, sample standard deviation (`ddof=1`), and a t-based 95% CI across 10 seeds. These intervals describe stream-order/exploration variability on the fixed participant split.

## Inferential protocol

Four contrasts were pre-specified per algorithm. The nuisance factor was averaged within each seed before testing, leaving 10 paired observations. Because `n=10`, metrics are bounded, and normality power is limited, two-sided Wilcoxon signed-rank tests were used regardless of Shapiro-Wilk outcome. Matched-pairs rank-biserial correlation is reported as effect size. Holm correction was applied globally to all 12 p-values.

## Full contrast results

| Algorithm | Factor | n pairs | Nonzero | Mean change | 95% CI | W | Raw p | Holm p | Effect r_rb | Shapiro p |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Epsilon-greedy | task_utility_weight | 10 | 10 | +0.0148 | [+0.0130, +0.0166] | 0.000 | 0.001953 | 0.02344 | +1.000 | 0.2415 |
| Epsilon-greedy | unnecessary_access_weight | 10 | 10 | -0.3559 | [-0.3626, -0.3493] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.09158 |
| Epsilon-greedy | interruption_weight | 10 | 10 | -0.1515 | [-0.1539, -0.1491] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.6087 |
| Epsilon-greedy | over_persistence_weight | 10 | 10 | -0.2341 | [-0.2380, -0.2301] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.2999 |
| UCB | task_utility_weight | 10 | 10 | +0.0260 | [+0.0241, +0.0279] | 0.000 | 0.001953 | 0.02344 | +1.000 | 0.1644 |
| UCB | unnecessary_access_weight | 10 | 10 | -0.3355 | [-0.3474, -0.3237] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.0977 |
| UCB | interruption_weight | 10 | 10 | -0.1528 | [-0.1557, -0.1500] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.1183 |
| UCB | over_persistence_weight | 10 | 10 | -0.2334 | [-0.2365, -0.2304] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.1579 |
| Thompson sampling | task_utility_weight | 10 | 10 | +0.0205 | [+0.0180, +0.0229] | 0.000 | 0.001953 | 0.02344 | +1.000 | 0.3308 |
| Thompson sampling | unnecessary_access_weight | 10 | 10 | -0.3301 | [-0.3384, -0.3218] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.5498 |
| Thompson sampling | interruption_weight | 10 | 10 | -0.1437 | [-0.1466, -0.1407] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.4942 |
| Thompson sampling | over_persistence_weight | 10 | 10 | -0.2394 | [-0.2434, -0.2354] | 0.000 | 0.001953 | 0.02344 | -1.000 | 0.3528 |


## Limitations

- Seeds reuse one dataset split; they are not independent participant resamples.
- Ten seeds provide limited resolution for exact non-parametric p-values.
- Reward components are proxies, and data sensitivity/interruption/long-term persistence harm are not observed outcomes.
- Raw reward values from different weight configurations are not compared as if they shared one scale.
- Persistence is conditioned on observed access for branch isolation; end-to-end compounding errors require a separate experiment.
