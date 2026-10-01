# Statistical appendix: exploratory, not confirmatory

Source: postflight-verified tables. Reproduce with ../summarize_evidence.py; machine values are descriptive_statistics.json. No extra model execution. All seeds and all four cells are retained; neither48 cells nor144,000 transitions are independent training replicates.

| Config | n | Mean | Sample SD (ddof1) | Paired mean change vs A | Individual changes |
|---|---:|---:|---:|---:|---|
| A | 3 | .383333 | .337809 | 0 | 0,0,0 |
| B | 3 | .590000 | .025372 | +.206667 | +.0825,-.075,+.6125 |
| C | 3 | .575000 | .037500 | +.191667 | +.10,-.10,+.575 |
| D | 3 | .578333 | .035030 | +.195000 | +.10,-.095,+.58 |

No Gaussian assumption is established from three pairs, so no t-test/ANOVA or parametric mean-value CI is reported. As a limited post-hoc descriptive inferential check, use the exact two-sided paired sign test for each of B/C/D versus A. Each has2 positive and1 negative non-tied differences: p=1.0; Holm correction over the three contrasts also yields1.0. This checks direction, discards magnitude, and has very low power. It does not show equivalence or absence of useful effects. The sign test was not the preregistered selection criterion.

Under independent, representative seed-pair sampling, each2/3 win count has marginal exact Clopper-Pearson95%CI[.094299,.991596] for the probability of beating A on a seed. This is NOT a confidence interval for mean policy value, mean gain, generalization across graphs, or the selected configuration's unbiased future performance. These intervals are marginal, not simultaneous; the p-values alone receive Holm correction. The seed-representativeness assumption is not verified, and hyperparameter selection uses the same validation data. No broad inferential claim follows.

Primary selection remains mean exact regret with fixed tie-breakers, not a p-value. The selected B remains0/3 near-optimal at the original regret<=.05 threshold. Improvement is largely driven by avoiding the previous seed307 collapse, while seed211 declines. All reported precision comes from exact evaluation under the simulator, not from increased numbers of independent runs.
