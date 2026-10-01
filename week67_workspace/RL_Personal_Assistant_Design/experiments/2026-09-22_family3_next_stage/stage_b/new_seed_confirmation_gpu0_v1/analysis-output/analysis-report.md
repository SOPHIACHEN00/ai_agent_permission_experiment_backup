# Fixed-candidate new-seed confirmation — analysis report

## Question and design

Does previously selected B (learning rate 0.0003, optimize every 4 environment steps) improve over A (0.001, every 4) on three new seeds? B and seeds 401/503/607 were fixed before outcomes. Gamma=1 and all other scientific settings, 12000 transitions per group, and final-checkpoint evaluation are unchanged. This is seed replication on reused validation graphs, not a fresh graph or held-out test experiment.

Primary outcome: mean of three paired B−A differences in exact validation value. Each seed value averages four fixed cells (br05/br06 × original/prompt_toggle). Exact DP reference mean is 0.7075. With the specified terminal binary reward and gamma=1, these values are exact success probabilities under the simulator, not Monte Carlo estimates.

## All observed results

| Seed | A | Fixed B | B−A | A regret | B regret |
|---|---:|---:|---:|---:|---:|
| 401 | .6125 | .6000 | −.0125 | .0950 | .1075 |
| 503 | .5000 | .5000 | .0000 | .2075 | .2075 |
| 607 | .0000 | .5750 | +.5750 | .7075 | .1325 |
| Mean | .370833 | .558333 | +.1875 | .336667 | .149167 |

Paired mean improvement is 18.75 percentage points; one improvement, one tie, one decrease. Observed sample SD across seeds is .326040 for A and .052042 for B. Worst seed improves from 0 to .5. Neither configuration has a seed meeting mean regret ≤ .05 (0/3 each).

The mean gain is dominated by seed607. Thus the evidence supports an observed average gain and one avoided zero-valued final policy, not universal seed improvement or assured stability. A/607 still experienced 107 successful training episodes; its zero refers to final validation policy value, not absence of successful training transitions.

## Remaining deficiencies

B values by [br05 original, br05 prompt_toggle, br06 original, br06 prompt_toggle]:

- 401: [.40, .40, .92, .68].
- 503: [.40, .40, .60, .60].
- 607: [.50, .50, .65, .65].
- DP: [.50, .60, .93, .80].

The gap is not limited to prompt_toggle: br06 original remains below DP for B/503 and B/607. Old tuning seed307's original-cell optimality must not be generalized to these new seeds. Learning rate can change online actions and replay collection as well as parameter updates; these outcomes do not isolate reward propagation, optimization dynamics or implementation correctness.

## Inference boundary

The replication unit is the paired seed (n=3), not 24 independent evaluation rows. The four cells are fixed reused validation conditions. The exploratory exact two-sided sign test excludes the tie, leaving one win and one loss (p=1.0). It has very low power and is not a test of the magnitude of the mean gain; it proves neither equivalence nor no effect. No broad significance/generalization claim is justified. See stats-appendix.md for the conditional win-probability interval and assumptions.

## Integrity and disposition

All six groups completed on physical GPU0 only, exit 0; 72000 transitions, 17622 optimizer updates, six checkpoints, 24 exact rows. Offline postflight PASS: 30 record chains, checkpoint hashes, paired initialization, frozen candidate provenance and unchanged evaluation fingerprints. All five hard counters zero; test closed. Full models/logs downloaded, server processes exited, GPU0 released. Runtime success does not mean the near-optimal research gate passed.

Keep B as the preselected working candidate without changing production defaults or thresholds. Do not expand search or start another experiment. Suggested next investigation: inspect saved policies/logs for the specific lost-value branches on br06, including original conditions and seed503. This recommendation is not an executed follow-up.

## Sources and figures

- ../config.json and ../task_plan.md: frozen protocol.
- ../server_evidence/unpacked/completion.json and exit_receipt.json: run receipts.
- ../postflight_verification.json: checked provenance, counts and exact summaries.
- ../per_seed_results.csv and ../exact_values.csv: all six groups and 24 cells.
- descriptive_statistics.json: machine-readable descriptive and exploratory statistics.
- figures/figure-01-paired-seeds.svg: all paired seed values and mean/DP references.
- figures/figure-02-fixed-candidate-cells.svg: residual B gaps in each fixed cell.

Plots are descriptive drafts. SVG XML validity checked; visual/publication QA not performed. This package is an experiment analysis record, not manuscript-ready Results prose.
