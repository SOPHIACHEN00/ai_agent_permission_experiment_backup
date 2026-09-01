# Notes: WP-FTS Implementation

## Reusable offline components

- `bandit_experiment/run_stated_policy_bandit.py` provides the action mapping, governed feature schema, sparse context transformation, `DiagonalLinearBandit`, `FactoredJointPolicy`, selected-action joint reward, and diagnostics.
- The online runner must reuse those components rather than redefine action labels or features.

## Planned evaluation

- Participant-held-out split stays at 120 train / 40 validation / 41 test.
- Fit a global Factored Thompson policy on train; create a tempered independent copy for every validation/test participant.
- Replay test users by fixed random `query_id` bundles. Choose all actions in a bundle before any feedback update.
- Compare online selected-action decisions with a frozen global Factored Thompson policy on the identical bundle order and action randomness.

## Existing offline reference

- The existing factored Thompson report is a static frozen test result; its 43.78% joint exact match and 100% false allow motivate, but do not tune, the online evaluation.
- The online comparison will be recomputed from a single runner/configuration so its aggregation and policy initialization are identical.
