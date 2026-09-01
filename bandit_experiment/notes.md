# Notes: Factored contextual bandit experiment

## Data audit

- Primary input: `data/processed/four_label_dataset.csv`, rebuilt from valid participants' `task3` responses in raw `user_study.json`.
- Shape: 16,361 rows, 201 participants, 65 queries.
- Four-label mapping:
  - 0 = deny + persist (`No, never share`)
  - 1 = deny + ask next time
  - 2 = allow + ask next time
  - 3 = allow + persist (`Yes, always share`)
- Access counts: deny 4,081; allow 12,280.
- Persistence counts: ask next time 8,776; persist 7,585.
- Necessity status: 14,133 necessary; 2,148 explicitly incorrect/unnecessary; 80 unknown.
- Available context includes profile fields, query/domain/tool, raw/generic data type, necessity status, and query text.
- Not available as observed ground truth: intrinsic data sensitivity, interruption cost, over-persistence consequence, temporal state transitions.

## Protocol decisions

- This is an offline interaction simulation over fully labeled survey rows, not logged-bandit IPS evaluation and not an online human study.
- Split by participant into train/validation/test to reduce identity leakage.
- For each row, the environment can calculate both actions' rewards from the label, but the learner receives only the chosen action's reward.
- Access reward proxy follows the proposed decomposition using observed necessity and preference mismatch. Sensitivity cost is zero by default because sensitivity is unobserved.
- Persistence reward proxy uses interruption, over-persistence, and preference-mismatch costs.
- Sparse contextual features are learned with diagonal ridge estimates. UCB and Thompson uncertainty therefore use a diagonal covariance approximation.
- Exploration hyperparameters are selected on validation reward and frozen before test.

## Experiment findings

- Participant split: 120/40/41 train/validation/test participants and 9,826/3,212/3,323 rows, with no participant overlap.
- Selected exploration parameters: epsilon-greedy 0.01, UCB 2.0, Thompson 0.5.
- Five-stream test mean total rewards: epsilon-greedy -0.6950; UCB -0.6746; Thompson -0.6794.
- Fixed train-majority policy (`allow + ask_next_time`) total reward: -0.6797.
- UCB only narrowly beats the fixed majority policy on reward. Its access accuracy is 0.7461, but over-sharing is 0.9561 and unnecessary-access rate is 0.8448.
- The result is a baseline failure/safety finding: the policies largely collapse toward the majority `allow` action rather than learning a privacy-safe access policy.
- Reward sanity check over all 16,361 rows found zero cases where the reward oracle disagreed with the observed factored target. The collapse is not caused by an inverted label/action mapping.
- Likely drivers: access class imbalance (75.1% allow), positive utility attached to necessary allows, partial-feedback exploration, and the limited diagonal-linear context estimator.
- A next experiment should not simply tune weights on test reward. It should predefine a privacy selection rule (for example, minimize reward regret subject to an over-sharing ceiling) and run reward-weight sensitivity analysis on validation data only.
