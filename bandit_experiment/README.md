# Offline Stated-Policy Contextual-Bandit Benchmark

This folder's canonical baseline is `run_stated_policy_bandit.py`. It is a no-weight, offline simulation over the four stated permission responses in `data/processed/four_label_dataset.csv`.

## What it learns

Each survey row supplies one target policy:

| Action ID | Current access | Future policy | Survey response |
|---:|---|---|---|
| 0 | deny | persist current deny | No, never share |
| 1 | deny | ask next time | No, but ask me next time |
| 2 | allow | ask next time | Yes, but ask me next time |
| 3 | allow | persist current allow | Yes, always share |

The only learning reward is:

```text
r_joint = 1[predicted action ID == stated action ID]
```

There are no task-utility, sensitivity, interruption, unnecessary-access, or persistence weights. Access and persistence bit accuracy are diagnostic metrics only; they are never summed into a primary reward.

The evaluator can reconstruct all four 0/1 rewards from each label, but the training simulator updates only the action selected by the learner. The output reward-vector CSV makes this distinction auditable.

## Policies and algorithms

- `factored_joint`: selects access, then `persist_current_decision` conditional on that selected access action; both components receive the same joint exact-match reward.
- `flat_four_arm`: selects one of the four full policies directly; this is the required action-space comparator.
- Algorithms: contextual epsilon-greedy, UCB, and Thompson Sampling with a documented diagonal-linear reward estimator.

The primary test is frozen greedy/posterior-mean evaluation: validation and test labels never update model state. This is a static stated-policy benchmark, not a temporal online-adaptation or sequential-RL result.

## Run

From `ai_agent_permission_experiment/`:

```powershell
.\.venv\Scripts\python.exe bandit_experiment\run_stated_policy_bandit.py `
  --data data\processed\four_label_dataset.csv `
  --split participant_heldout `
  --out bandit_experiment\stated_policy_results\participant_heldout
```

Repeat with `--split leave_query_out`, `leave_tool_out`, and `leave_data_type_out` for scenario/context generalization stress tests.

For a fast smoke run:

```powershell
.\.venv\Scripts\python.exe bandit_experiment\run_stated_policy_bandit.py `
  --data data\processed\four_label_dataset.csv `
  --out bandit_experiment\stated_policy_smoke `
  --algorithms epsilon_greedy `
  --tuning-seeds 11 `
  --test-seeds 101 `
  --exploration-grid 0.1
```

## Context governance

The default primary context contains domain, tool/recipient proxy, raw and generic data type, and explicitly opt-in privacy-profile fields (`concern_domain`, `privacy_importance`). It excludes participant IDs, query IDs, target labels, scenario-curated `necessity_status`, demographics, and pseudo-history.

- `--include-query-text-ablation`: adds query TF-IDF as a representation ablation.
- `--include-necessity-oracle-ablation`: adds the curated scenario label as an oracle-availability ablation.
- `--without-opt-in-profile`: removes the opt-in profile fields.

## Outputs

- `test_metrics_summary.csv`: primary joint exact-match and secondary diagnostics.
- `test_predictions.csv`: frozen row-level predictions.
- `full_information_test_reward_vectors.csv`: the complete four-action 0/1 reward vector for every held-out row.
- `fixed_policy_baselines.csv`: four constant policies plus training four-action majority.
- `validation_tuning.csv`, `confusion_matrices/`, and `run_config.json`: reproducibility/audit artefacts.

Run the independent full-information supervised comparators from `src/run_four_label_benchmark.py` alongside this baseline; the source table contains complete labels, so MAB results alone are not sufficient.

## Legacy weighted experiment

`run_factored_bandit.py`, `reward_config.json`, and the reward-sensitivity scripts are retained only to preserve previous exploratory work. They use manually weighted proxy objectives and prequential test updates, so they are **not** the canonical no-weight stated-policy baseline.
