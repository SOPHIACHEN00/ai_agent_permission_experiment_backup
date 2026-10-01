# AI Agent Permission Four-Label Benchmark

For the complete Week67 RL experiment backup and source map, see
[WEEK67_RL_BACKUP_INDEX.md](WEEK67_RL_BACKUP_INDEX.md).

This folder contains the first-stage supervised benchmark for four-label AI-agent data-access permission prediction.

The benchmark uses the original raw `user_study.json` from [`llm-platform-security/ai-agent-permissions`](https://github.com/llm-platform-security/ai-agent-permissions), not the released `processed_dataset.json`, because the processed file filters the two intermediate permission responses.

## Goal

Test whether the four permission responses are learnable and whether they are better modeled as:

1. flat four-class labels;
2. ordered sharing-willingness levels;
3. two factored permission decisions: current access and future persistence.

## Directory Layout

```text
ai_agent_permission_experiment/
  external/ai-agent-permissions/   # cloned source repo and raw data
  data/processed/                  # generated four-label dataset and summaries
  src/                             # dataset builder and benchmark runner
  in_context_learning/             # four-label, within-user IC-only baseline
  bandit_experiment/               # isolated no-weight stated-policy contextual-bandit benchmark
  qstn_simulator/                  # isolated simulator work for later stages
  results/                         # benchmark outputs
  requirements.txt
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Build Dataset

```powershell
python src/build_dataset.py --repo external/ai-agent-permissions --out data/processed/four_label_dataset.csv
```

## Run Benchmarks

```powershell
python src/run_four_label_benchmark.py --data data/processed/four_label_dataset.csv --split row_stratified
python src/run_four_label_benchmark.py --data data/processed/four_label_dataset.csv --split participant_heldout
```

## Four-label in-context learning

See [in_context_learning/README.md](in_context_learning/README.md) for the paper-style personalized five-fold IC-only baseline. It uses all four survey responses as user history and predicts all four labels. Its within-user protocol differs from the classifier participant-heldout results.

## Models

- `flat_four_class_lr`: multinomial logistic regression over four labels.
- `ordinal_lr`: three cumulative binary logistic regressions for `y > 0`, `y > 1`, and `y > 2`.
- `factored_lr`: two binary logistic regressions for access (`deny`/`allow`) and persistence (`ask_again`/`persist`), then recombined into four labels.

## Main Metrics

- `accuracy`
- `macro_f1`
- `quadratic_weighted_kappa`
- `over_sharing_rate`: true label is deny-like (`0` or `1`) while prediction is allow-like (`2` or `3`).
- `persistent_over_allow_rate`: prediction is `Yes, always share` (`3`) while true label is not `3`.

## Notes

The supervised benchmark remains the data/model foundation. The isolated `bandit_experiment/` folder contains the Step 2 no-weight stated-policy contextual-bandit simulation; it does not depend on QSTN and is not sequential RL. Its canonical runner is `bandit_experiment/run_stated_policy_bandit.py`; the older manually weighted runner is retained only as legacy exploratory work.

