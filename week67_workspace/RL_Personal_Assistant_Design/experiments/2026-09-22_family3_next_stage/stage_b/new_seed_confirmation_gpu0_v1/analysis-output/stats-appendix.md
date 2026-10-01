# Statistical appendix — new-seed fixed-candidate replication

## Units, estimands and provenance

- Independent replication coordinate: training seed pair; n=3 (401,503,607). Seeds are disjoint from old tuning seeds 101,211,307. Numeric distinctness alone does not verify statistical independence or representativeness.
- A and B share each seed and pretraining network fingerprint. Each policy is evaluated exactly on the same four fixed validation conditions. These 24 rows are repeated conditions of six fitted policies, not 24 independent replications.
- Primary frozen estimand: descriptive mean of paired final-policy value differences B−A over the three specified seeds. No checkpoint selection after observing outcomes, no current-data hyperparameter selection, no held-out test opening.
- Each value is the uniform mean over four simulator-exact success probabilities; DP references are [.50,.60,.93,.80], mean 283/400=.7075. Exact evaluation eliminates rollout Monte Carlo error for these policies/conditions, not training-seed or task-distribution uncertainty.
- Source: ../postflight_verification.json, ../per_seed_results.csv, ../exact_values.csv. Derived offline by ../summarize_evidence.py; no local model execution.

## Descriptive results

| Statistic | A | B |
|---|---:|---:|
| n seeds | 3 | 3 |
| Mean exact value | 89/240=.3708333333 | 67/120=.5583333333 |
| Sample SD, ddof=1 | .3260400027 | .0520416500 |
| Minimum | 0 | .5 |
| Mean exact regret | 101/300=.3366666667 | 179/1200=.1491666667 |
| Seeds with mean regret ≤ .05 | 0/3 | 0/3 |

Paired differences in seed order: [−1/80,0,23/40]=[−.0125,0,.575]. Their arithmetic mean is 3/16=.1875 (18.75 percentage points), not an 18.75% relative increase. One win, one tie, one loss. Report every pair; do not remove seed607 as an outlier, and do not hide the seed401 decrease.

## Exploratory direction-only inference

The following diagnostic was not the primary frozen success criterion and introduces no new gate:

- Exact two-sided sign test of equal probabilities of positive and negative non-zero paired differences. Tie discarded; effective n=2, wins=1, losses=1, raw p=1.0.
- Only one A/B contrast, so there is no multi-comparison family to correct here; the generator's Holm-adjusted value is also 1.0. It does not retrospectively correct the prior tuning search.
- Marginal exact Clopper–Pearson 95% interval for the probability of B winning **conditional on a non-tied pair**: [.0125791171,.9874208829], based on 1/2 wins.
- This is **not** a confidence interval for mean value, mean paired gain, near-optimal success frequency, or graph/test generalization. It excludes ties and assumes independent representative seed pairs with a common conditional win probability; those population assumptions are not demonstrated by these three chosen seeds.
- n=3 is insufficient to establish normality. No paired t-test, mean-gain confidence interval, power claim or statistical equivalence claim is made. A large p-value does not show no effect; this test largely ignores the size of the +.575 gain and −.0125 decrease.

## Missingness, selection and sensitivity

All six planned groups and all 24 cells are present. No failed seed discarded, no extra training/retry, no post-hoc checkpoint selection. B was selected in the previous tuning experiment and its receipt hash pinned before this run. Old tuning results are not pooled into the current replication sample. The numerical mean is strongly driven by seed607; this is reported explicitly rather than hidden behind the lower sample SD.

No reward, mask, graph definition, threshold or exploration schedule changed. Lower learning rate can change later online behavior and therefore replay contents. The experiment identifies the observed total A/B difference at fixed budgets, not a unique internal mechanism. Same validation graphs and three seeds cannot support deployment reliability, broad long-horizon superiority or unseen-task claims.

## Integrity checks and research criterion

Offline postflight PASS: six checkpoints, 30 record chains, 72000 transitions, 17622 optimizer updates, matched paired initialization, stable evaluation fingerprints, all five hard counters zero, test_opened=false. Near-optimal criterion is unchanged (per-seed four-cell mean regret ≤ .05), and neither A nor B passes it for any of the three seeds. Safety zeros are separate from learning effectiveness.
