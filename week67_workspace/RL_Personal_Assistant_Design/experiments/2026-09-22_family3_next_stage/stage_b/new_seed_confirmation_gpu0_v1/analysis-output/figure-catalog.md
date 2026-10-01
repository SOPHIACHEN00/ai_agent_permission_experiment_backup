# Figure catalog — descriptive drafts

Generated from verified local results by ../summarize_evidence.py. Both SVG files passed XML parsing; no visual/publication QA is claimed. No smoothing, selective seed omission or fitted trend. Display rounding does not replace exact CSV values. No error bars: all individual seed observations are shown instead; apparent point overlap is not additional replication.

## Figure 1 — all paired new seeds

- File: figures/figure-01-paired-seeds.svg.
- Purpose: distinguish average improvement from consistency of improvement across seeds.
- Data: three paired seed values for A and preselected B, each the mean of four fixed exact validation cells; n=3 pairs, six policies. Mean references and DP mean .7075 shown. Vertical value axis starts at zero and ends at .8.
- Notice: seed607 rises 0→.575, seed503 ties at .5, seed401 decreases .6125→.6. Mean rises .370833→.558333.
- Implication: mean gain is dominated by avoiding the zero-valued seed607 final policy, not an improvement for every seed.
- Caption: “Final exact validation values for three new paired training seeds under baseline A (lr .001) and fixed candidate B (lr .0003), both optimize_every=4 and gamma=1. Each point averages four reused validation conditions. Connecting lines identify paired seeds, not time trajectories. Mean gain is .1875; neither configuration reaches the per-seed near-optimal criterion. No error bars; individual seed values are shown.”
- Limit: fixed validation graphs and n=3; no confidence/held-out generalization claim. Connecting lines do not denote training curves.

## Figure 2 — fixed candidate residual gaps

- File: figures/figure-02-fixed-candidate-cells.svg.
- Purpose: locate which fixed validation conditions remain below their DP-optimal value.
- Data: B's three seed values in each of four cells (12 exact values); three policies repeatedly evaluated, not 12 independent training replications. DP references are .50,.60,.93,.80. Axis spans 0–1.
- Notice: prompt_toggle gaps remain, but br06 original is also deficient for seed503 (.60) and seed607 (.65) versus DP .93.
- Implication: subsequent diagnosis should include original conditions, not assume the earlier seed307 original-cell result generalizes.
- Caption: “Exact success probabilities of the three fixed-candidate B policies by validation cell. Dashed references indicate cell-specific exact DP optima. Slight point offsets make seeds visible and have no numerical meaning. No error bars; three seed values are shown per cell. Conditions reuse br05/br06 and are not held-out test data.”
- Limit: no branch-level causal diagnosis follows from cell values alone. Best performance on one cell/seed is not representative evidence for all policies.
