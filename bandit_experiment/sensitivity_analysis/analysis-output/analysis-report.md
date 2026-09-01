# Reward-weight sensitivity: strict analysis report

## Analysis questions

1. Does increasing task utility increase necessary-data access?
2. Does increasing the unnecessary-access penalty reduce unnecessary access?
3. Does increasing interruption cost reduce asking again?
4. Does increasing over-persistence cost reduce erroneous persistence?

## Evidence boundary

The unit of repeated analysis is the randomized stream seed (`n=10`) on one fixed participant-held-out split (120/40/41 train/validation/test participants). Confidence intervals and tests quantify algorithmic/order variability on this split; they do not estimate population-level uncertainty across new participant samples.

## Main findings

- Access policies remain strongly allow-oriented throughout the requested grid. The grid changes boundary behavior, but it does not remove the majority-allow collapse.
- Raising the unnecessary-access penalty generally moves policies toward less unnecessary access, with a corresponding reduction in necessary-data access for some algorithm/configuration pairs.
- Persistence weights produce a direct interruption-versus-over-persistence tradeoff: reducing ask actions tends to increase erroneous persistence, so there is no single dominant configuration without an external preference or safety constraint.
- 12 of 12 pre-specified paired contrasts remain significant after global Holm correction. Interpret effect sizes together with absolute rate changes and the fixed-split limitation.

## Exact contrast table

| Algorithm | Factor | Metric | Low mean | High mean | Paired change | Raw p | Holm p | Rank-biserial |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Epsilon-greedy | task_utility_weight | necessary_data_allow_rate | 0.9802 | 0.9950 | +0.0148 | 0.001953 | 0.02344 | +1.000 |
| Epsilon-greedy | unnecessary_access_weight | unnecessary_access_rate | 0.7175 | 0.3615 | -0.3559 | 0.001953 | 0.02344 | -1.000 |
| Epsilon-greedy | interruption_weight | ask_action_rate | 0.8830 | 0.7315 | -0.1515 | 0.001953 | 0.02344 | -1.000 |
| Epsilon-greedy | over_persistence_weight | persistent_over_allow_rate | 0.2668 | 0.0328 | -0.2341 | 0.001953 | 0.02344 | -1.000 |
| UCB | task_utility_weight | necessary_data_allow_rate | 0.9740 | 1.0000 | +0.0260 | 0.001953 | 0.02344 | +1.000 |
| UCB | unnecessary_access_weight | unnecessary_access_rate | 0.6533 | 0.3177 | -0.3355 | 0.001953 | 0.02344 | -1.000 |
| UCB | interruption_weight | ask_action_rate | 0.8831 | 0.7303 | -0.1528 | 0.001953 | 0.02344 | -1.000 |
| UCB | over_persistence_weight | persistent_over_allow_rate | 0.2657 | 0.0322 | -0.2334 | 0.001953 | 0.02344 | -1.000 |
| Thompson sampling | task_utility_weight | necessary_data_allow_rate | 0.9795 | 1.0000 | +0.0205 | 0.001953 | 0.02344 | +1.000 |
| Thompson sampling | unnecessary_access_weight | unnecessary_access_rate | 0.6765 | 0.3464 | -0.3301 | 0.001953 | 0.02344 | -1.000 |
| Thompson sampling | interruption_weight | ask_action_rate | 0.8857 | 0.7420 | -0.1437 | 0.001953 | 0.02344 | -1.000 |
| Thompson sampling | over_persistence_weight | persistent_over_allow_rate | 0.2697 | 0.0303 | -0.2394 | 0.001953 | 0.02344 | -1.000 |

## Claim Candidates

- Claim: Reward weights measurably change the learned policy on the fixed held-out participant split.
  - Source evidence: `contrast_tests.csv`, both per-seed tables, Figures 1-2.
  - Allowed wording: The requested weights induce stable changes across randomized stream orders on this fixed split.
  - Forbidden stronger wording: These weights are universally optimal or validated for deployed users.
  - Uncertainty: Only one participant split and proxy rewards are available.
  - Next check: Repeat across participant split seeds or nested group cross-validation.
  - Decision: keep

- Claim: The tested Access grid solves over-sharing.
  - Source evidence: Access summaries show persistently high over-sharing/allow behavior.
  - Allowed wording: The grid exposes a tradeoff but does not eliminate majority-allow collapse.
  - Forbidden stronger wording: Reward tuning produced a privacy-safe access controller.
  - Uncertainty: The estimator is a diagonal-linear baseline and intrinsic sensitivity is unobserved.
  - Next check: Add a validation-only privacy constraint or cost-sensitive/constrained policy selection.
  - Decision: discard

- Claim: Persistence has a single best weight pair.
  - Source evidence: Figure 2 and `persistence_pareto.csv` show interruption and persistent-over-allow move in opposite directions.
  - Allowed wording: The preferred operating point depends on an externally chosen interruption-versus-persistence tradeoff.
  - Forbidden stronger wording: The data identify one objectively optimal persistence configuration.
  - Uncertainty: Interruption and long-term persistence costs are simulated, not measured.
  - Next check: Elicit costs from users or define a safety constraint before selecting a point.
  - Decision: discard
