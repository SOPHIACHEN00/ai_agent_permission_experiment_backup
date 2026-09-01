# Notes: Offline Full-Information Benchmark

## Findings

- The existing `run_factored_bandit.py` is a legacy weighted-proxy experiment. It uses manual task/sensitivity/interruption/persistence coefficients, broad features, and prequential test updates; it is not the requested no-weight stated-policy benchmark.
- The processed data contain 16,361 rows, 201 participants, 65 query templates, and four labels. Label IDs map exactly to the four action pairs: 0=(deny,persist), 1=(deny,ask-next-time), 2=(allow,ask-next-time), 3=(allow,persist).
- The canonical reward is `r_joint = 1[action_id == label_id]`. Its mean must equal four-class exact-match accuracy. Access and persistence bit accuracy are diagnostics, not a summed reward.
- The primary context excludes `query_id`, `necessity_status`, demographics, target fields, participant IDs, and pseudo-history. It uses domain, tool, raw/generic data type, and opt-in privacy-profile fields; query text and oracle availability are explicit ablations.
- Primary static evaluation is frozen after train/validation fitting. Participant-held-out, leave-query-out, leave-tool-out, and leave-data-type-out are selectable grouped splits.

## Implementation

- Added `run_stated_policy_bandit.py` as the canonical runner. It includes factored-joint and flat four-arm policies, epsilon-greedy/UCB/Thompson variants, grouped splits, frozen test evaluation, exact-match tuning, full-information reward-vector audit output, and fixed four-policy baselines.
- Added `test_stated_policy_bandit.py` for mapping, reward-vector, feature-governance, split-isolation, and frozen-evaluation invariants.
- Rewrote `bandit_experiment/README.md` so the previous weighted runner and sensitivity scripts are explicitly legacy rather than the default workflow.

## Verification

- `python -m py_compile` passed for the new runner and its unit test module.
- All five unit checks passed: action mapping, exact-one reward vector, primary feature exclusions, grouped split isolation, and frozen prediction state.
- Smoke runs completed for all three algorithms, all four grouped split modes, and the query-text/necessity-oracle/profile feature flags. Repeated identical-seed smoke runs produced identical metrics and predictions.
- A full participant-held-out run completed at `bandit_experiment/stated_policy_results/participant_heldout/` for both policies, all three algorithms, three validation tuning seeds, and five frozen-test training seeds.
- The held-out reward-vector audit contains 3,323 rows; each row's four action rewards sum to exactly 1. The runner asserts that frozen test prediction cannot modify policy state and that mean joint reward equals joint exact-match accuracy.
- Temporary smoke outputs and execution logs were removed after verification; the canonical full participant-held-out result remains.
