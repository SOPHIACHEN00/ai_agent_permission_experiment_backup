# Task Plan: WP-FTS Online MAB Implementation

## Goal

Implement the approved warm-started personalized Factored Thompson Sampling replay baseline, run its frozen participant-held-out evaluation, and compare it fairly against the matched frozen offline Factored Thompson policy.

## Phases

- [x] Phase 1: Read the approved design and reusable offline implementation.
- [x] Phase 2: Specify data flow, leakage guards, tuning, and output contracts.
- [x] Phase 3: Implement the online replay runner and unit tests.
- [x] Phase 4: Run the initial validation tuning and frozen test evaluation (archived as `participant_heldout_wp_fts_v1`).
- [x] Phase 5: Repair the offline-comparison protocol, rerun the locked evaluation, and write the final comparison report.

## Non-negotiable constraints

- Four factored actions, existing governed context features, and selected-action unweighted joint reward only.
- Test participants receive independent tempered personal posterior copies; their feedback never updates the global policy or another participant.
- `(participant_id, query_id)` is an atomic feedback bundle; no action in a bundle can use another row's feedback from that bundle.
- Full labels may be used by the evaluator to generate selected-action binary feedback and metrics, but never by `update()`.
- The output must be named a randomized sequential online-feedback replay simulation, not a real online deployment or CMDP experiment.

## Key questions

1. Can the personal posterior adapt fast enough without overwhelming it with the global posterior?
2. Does the online method improve post-adaptation stated-policy agreement and reduce false allow relative to the frozen comparator?
3. Are all selection, replay, and confidence-interval calculations participant-level and leakage-free?

## Decisions made

- Use one online method only: WP-FTS, with a tempered Factored Thompson posterior.
- Tune only Thompson exploration and tempering strength on validation participants using the pre-registered lexicographic rule.
- Use original human survey labels as replay feedback; QSTN is not used in this primary evaluation.
- The primary causal comparator is a frozen *tempered* Thompson control with the identical initialization and action-sampling mechanism but no test-user updates. A separate frozen global greedy reference reproduces the existing offline evaluation style and is descriptive only.
- One replay run is one paired global-training/order/action seed; test default is 20 paired runs, not a 20x20 Cartesian product.
- A one-seed smoke evaluation completed successfully after all 12 online+offline unit tests passed. It wrote valid trajectory, bootstrap, static-reference, and leakage artifacts.

## Errors encountered

- Initial unit test incorrectly assumed `Q1` always precedes `Q2`; randomized replay may order either query first. Resolution: make the test identify the actual later bundle before altering its labels.
- One plan-file read used a path relative to the project root incorrectly; implementation tests themselves still executed. Resolution: use `online_bandit_experiment/...` paths when the working directory is `ai_agent_permission_experiment/`.

## Status

**Complete.** The final result is `participant_heldout_wp_fts_v2`.

The repaired protocol holds the canonical offline global-training setting
(Factored Thompson exploration \(=2.0\)) fixed, tunes only personal online
sampling and \(\kappa\), and records both (a) a matched within-simulation
adaptation control and (b) a canonical offline-greedy baseline comparison.
The v1 output remains retained as an audit artifact and is not used for the
final result table.
