# Five-seed fixed-candidate confirmation — verified analysis

## Question and comparison unit

Does fixed candidate B (lr .0003) improve over baseline A (lr .001) on five additional seeds, with every4 updates, gamma1 and 12000 transitions per group? Seeds701/809/907/1009/1103 and budgets were fixed before outcomes. Primary metric is the mean paired difference in final-policy exact validation value. Each value averages four fixed br05/br06 × original/prompt_toggle cells; n=5 seed pairs, not40 independent replications. All ten planned groups and40 cells are present.

## All paired outcomes

| Seed | A | B | B−A | A regret | B regret |
|---|---:|---:|---:|---:|---:|
|701|0|.4250|+.4250|.7075|.2825|
|809|.5425|.6125|+.0700|.1650|.0950|
|907|.5375|.5750|+.0375|.1700|.1325|
|1009|.5500|.5750|+.0250|.1575|.1325|
|1103|.5375|.5375|0|.1700|.1700|
|Mean|.4335|.5450|+.1115|.2740|.1625|

Four improvements, one tie, no decreases in this batch. A/B sample SD .242387861/.072132690, median .5375/.5750, minimum0/.4250. Zero-valued four-cell mean policies:1/5 versus0/5. Both configurations remain0/5 near-optimal under unchanged mean regret≤.05. Mean DP optimum is .7075.

The largest gain is seed701's0→.425, but seeds809/907/1009 also improve. The observation is more directionally consistent than the previous three-seed batch (one win/one tie/one loss), which remains separate and is not overwritten or pooled into this primary comparison. This is not a guarantee that every future seed improves.

## Residual failures of B

| B policy | br05 original | br05 toggle | br06 original | br06 toggle |
|---|---:|---:|---:|---:|
|DP|.50|.60|.93|.80|
|701|0|.50|.60|.60|
|809|.50|.50|.93|.52|
|907|.50|.50|.65|.65|
|1009|.50|.50|.65|.65|
|1103|.10|.60|.93|.52|

No all-cell-mean zero does not mean no zero cell: B/701 still fails br05/original exactly. B/1103 also has a large br05/original deficit. Original conditions and prompt toggles both require diagnosis. These values identify cells, not the causal decision branch.

Mean gains do not imply all cells improve: for seed907, br06/original drops from A=.93 to B=.65 despite the positive four-cell mean difference. Preserve this cell-level tradeoff, not only aggregate wins.

## Statistics and limits

Unstandardized paired mean effect is223/2000=.1115, or11.15 percentage points. An exploratory exact two-sided sign test excludes the tie:4 wins/0 losses, n4, p=.125. Its95% Clopper–Pearson interval [.3976353644,1] concerns conditional win probability among non-tied seed pairs, NOT mean gain. The test has low power and does not establish statistical significance or equivalence. Assumed independence/representativeness of seed pairs is not proven. No parametric normality claim or paired t-test; see stats-appendix.md.

All conditions reuse validation graphs; there is no new-graph/test generalization evidence. Changing learning rate also changes online behavior and replay collection. B/701's first training success was later than A's (7310 vs6806), despite higher final value: earlier success alone is not a sufficient account. This does not isolate credit assignment, replay coverage or optimization dynamics.

## Claim candidates

- Claim: fixed B improved the observed five-seed mean.
  - Source evidence: ../postflight_verification.json and ../per_seed_results.csv.
  - Allowed wording: observed mean gain11.15 percentage points, four improved seed pairs and one tie on reused validation cells.
  - Forbidden stronger wording: statistically established universal improvement or held-out generalization.
  - Uncertainty: n5, fixed validation graphs, largest gain from seed701.
  - Next check: diagnose the saved policies' residual failure branches; no more seed search.
  - Decision: keep as an observed batch result.
- Claim: B has lower observed variability and no zero-valued four-cell mean in this batch.
  - Source evidence: descriptive_statistics.json and all40 exact rows.
  - Allowed wording: SD .07213 versus .24239; zero-mean seeds0/5 versus1/5.
  - Forbidden stronger wording: B cannot collapse, or all conditions are solved.
  - Uncertainty: B/701 br05/original still0; small sample and earlier negative seed-pair result remain.
  - Next check: inspect B/701 br05/original and B/1103 residual cells.
  - Decision: keep descriptive, weaken any general stability claim.
- Claim: the near-optimal objective remains unmet.
  - Source evidence: all ten per-seed regrets exceed .05.
  - Allowed wording: A0/5 and B0/5 pass the unchanged criterion; B mean gap .1625 to DP.
  - Forbidden stronger wording: no improvement occurred, or DDQN is intrinsically ineffective.
  - Uncertainty: specific budgets/settings/validation graph family only.
  - Next check: branch-level diagnosis before any further training authorization.
  - Decision: keep.

## Integrity and disposition

Single run on physical GPU0, UTC2026-09-23 03:45:38—04:08:53, exit0.120000 transitions/29370 updates/10 final models/40 exact cells. Offline postflight PASS:50 record chains, ten checkpoint byte hashes, paired initializations, unchanged evaluation fingerprints, prior B selection provenance. Five hard counters zero; test closed. Full archive downloaded, processes/helper exited, GPU0 released. No retraining/retry, seed removal, default promotion or additional experiment. Two descriptive SVGs and statistics generated locally without model execution; SVG XML checks pass, visual/publication QA not claimed.
