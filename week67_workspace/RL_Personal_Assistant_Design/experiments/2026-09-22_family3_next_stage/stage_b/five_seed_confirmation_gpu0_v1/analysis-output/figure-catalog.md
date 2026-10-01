# Figure catalog — descriptive experiment figures

Generated from verified local results by ../summarize_evidence.py. Both SVGs pass XML parsing; no visual/publication QA claimed. No smoothing, selective seed omission or error bars: all five seed observations are shown. Error bars are not silently used as confidence intervals. Zero-based axes and exact source CSVs retained.

## Figure1: paired new-seed outcomes

- File: figures/figure-01-paired-seeds.svg.
- Purpose: show whether mean improvement is consistent across paired seeds, rather than hide variability behind two means.
- Data:5 paired seed means, each across4 fixed validation cells;10 models. Vertical axis exact validation success probability0–.8. Horizontal positions A/B; lines show pairing, not temporal training curves. Mean diamonds and DPmean.7075 reference.
- Notice: four rises and one tie; biggest is7010→.425, with three smaller rises. Mean .4335→.5450.
- Supported interpretation/implication: observed direction is more consistent in this batch, but residual DP gap remains; stop seed search and inspect failures rather than claim the task solved.
- Caption: “Final exact validation values for five additional paired training seeds under baseline A(lr.001) and fixed B(lr.0003), both gamma1/every4. Each point averages four reused validation conditions. Dashed connecting segments link the same seed, not training time. Black diamonds denote configuration means; horizontal reference is DPmean.7075. All seed values shown, no error bars or smoothing; not held-out test evidence.”
- Limit/checklist: n5 pairs, not40 observations; do not infer significance from connecting lines. Verify701 recovery,1103 tie and all5 labels, plus nonzero gap to DP.

## Figure2: B cell-level residual failures

- File: figures/figure-02-fixed-candidate-cells.svg.
- Purpose: identify remaining deficient conditions after mean improvement.
- Data:5 B policies ×4 fixed cells=20 exact values, repeatedly measured policies, not20 independent fits. Vertical axis0–1; dashed cell DP references [.50,.60,.93,.80].
- Notice: B/701 br05/original remains0; B/1103 there is.10. Several br06 values remain below DP; both original and toggle conditions show gaps.
- Supported interpretation/implication: no zero seed-mean is not equivalent to no failing cell. Prioritize branch diagnosis in br05/original for701/1103 and remaining br06 deficits; the plot alone does not reveal causal actions.
- Caption: “Exact validation probabilities for the five fixed-candidate B policies by br05/br06 × original/prompt_toggle condition. Dashed segments are cell-specific DP optima. Small horizontal offsets distinguish seeds and have no numerical meaning. Five points per cell, no error bars or smoothing; reused validation graphs, test unopened.”
- Limit/checklist: ensure cell-specific DP values, include zero for701, retain all20 values; no claim that condition comparisons are independent seed replications.
