# Evidence-first tuning analysis

Question: at12,000environment transitions per run, do learning rate and optimizer frequency improve current Budget-Recourse DDQN validation value? Unit: training seed, paired across four configurations; n=3 (101,211,307). Each run's response is its equal-weight mean over four fixed validation cells. Higher value/lower regret is better.

| Configuration | Seed101 | Seed211 | Seed307 | Mean | Mean regret |
|---|---:|---:|---:|---:|---:|
| A .001/every4 | .5125 | .6375 | 0 | .383333 | .324167 |
| B .0003/every4 | .595 | .5625 | .6125 | .590000 | .117500 |
| C .001/every2 | .6125 | .5375 | .575 | .575000 | .132500 |
| D .0003/every2 | .6125 | .5425 | .58 | .578333 | .129167 |

## Claim candidates

- Claim: B improved the observed three-seed mean by0.206667 and removed the observed zero-valued seed307 outcome.
  - Evidence: verified per_seed_results.csv; paired changes+.0825,-.075,+.6125.
  - Allowed: descriptive improvement in this fixed pilot.
  - Forbidden: significant population improvement, all-seed improvement, held-out superiority, unique causal diagnosis, or guaranteed code correctness.
  - Uncertainty: three seeds and reused validation for configuration selection; independent confirmation absent.
  - Next check: freeze B and, if authorized, paired confirmation on new seeds; preserve all results.
  - Decision: keep with limited scope.
- Claim: B has not solved the task near-optimally.
  - Evidence: all three mean regrets exceed.05; seed307 prompt_toggle values.50/.52 versus DP.60/.80.
  - Allowed: no evaluated seed passes the fixed near-optimal criterion; investigate those existing traces.
  - Forbidden: DDQN is universally ineffective or prompt_toggle is proven the sole failure cause.
  - Uncertainty: other seeds have additional losses; no new trace intervention performed.
  - Decision: keep.

Figure1 makes the seed trade-off visible; figure2 locates remaining condition-level loss. See figure-catalog.md for captions and limits. postflight_verification.json establishes provenance/coverage, not scientific near-optimality. The two frequency settings have unequal optimizer budgets and different target-sync rates per environment step.
