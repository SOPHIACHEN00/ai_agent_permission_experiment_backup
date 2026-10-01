# Four-label in-context learning baseline

This experiment adapts the IC-only method in Wu et al., [Towards Automating Data Access Permissions in AI Agents](https://techpolicylab.uw.edu/wp-content/uploads/2026/02/2511.17959v1.pdf) (IEEE S&P 2026, Sections 5.1.1 and 5.2), using the authors' [released code](https://github.com/llm-platform-security/ai-agent-permissions). It predicts all four original survey responses for each permission request:

| ID | Exact survey response |
|---:|---|
| 0 | No, never share |
| 1 | No, but ask me next time |
| 2 | Yes, but ask me next time |
| 3 | Yes, always share |

The prompt contains the user's demographic and AI/privacy survey profile, all four kinds of their own historical answers, and unseen query/tool/data-type requests with null answers. The model must return one exact four-class label and a 0–1 confidence score for every request. This is **IC-only**: no collaborative-filtering scores or training on other users' answers are inserted into the prompt.

## Completed experiment records

| Record | Scope | Results |
|---|---|---|
| [S-QSTN 20-persona pilot, 2026-09-26](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/EXPERIMENT_LOG_2026-09-26_zh.md) | o4-mini synthetic labels; Gemini 0/4-shot, fold 0; 274 test rows | Accuracy 55.47% / 74.09%; macro-F1 0.4568 / 0.5845 |
| [S&P full 201-person run](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/multi_model_screening/full_201_gemini_4shot_fold0_results.md) | Human labels; Gemini 4-shot, fold 0; 3,123 test rows | Accuracy 62.82%; macro-F1 0.5451 |
| [Matched real/synthetic comparison](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/COMPARISON_zh.md) | Same 20 participants and 274 test contexts; different target labels | Human 4-shot accuracy 66.79%; synthetic 4-shot accuracy 74.09%; not a same-target method comparison |

These completed pilots use four history queries and only fold 0. The general
runner protocol below describes the broader five-fold setup, including its
original full-history configuration; it is not the configuration of these pilots.

## Relation to the paper and its source code

The paper's IC model uses a participant's earlier query, tool, data type, and decision as natural-language examples, then asks an LLM for a label plus confidence. Its reported evaluation retains only the two endpoint decisions and describes 5-fold question-level cross-validation. The published `permission_ic_only.py` reads the endpoint-only `processed_dataset.json` (181 people, 7,563 answers), prompts for only those two labels, and runs the one pre-split training/testing set present in that file. Thus this four-label run requires the raw answers and a new split.

The paper names **o3-mini**; the published script currently defaults to **o4-mini**. This runner defaults to o3-mini and allows `--model` to change it. It sends the prompt in a user-role message rather than the published script's assistant-role message. It also rejects missing/invalid predictions instead of silently dropping them from accuracy. These deviations are intentional and recorded in each run's configuration and outputs.

## Evaluation protocol

- Input: the existing `../data/processed/four_label_dataset.csv` built from `../external/ai-agent-permissions/data/user_study.json`. The CSV SHA-256 in the current workspace is `4A6F61191318EAA79BA2FAC1AB80E6FB850E099F1F0178EEF2F53B3B527FE463`: 16,361 decisions, 201 valid people, 65 distinct scenarios.
- Five shuffled folds **within each participant**, seed 42. The raw survey presents 20 scenarios per valid participant; 192 participants have 20 nonempty permission queries in the CSV, seven have 19, and two have 18. Per fold, 14–16 other nonempty queries (all their four-label answers) are history and 3–4 unseen queries are predicted. A query and all its data-type rows stay together. Every row is tested once.
- No test answers, other participants' answers, `necessity_status`, or other query ground-truth metadata enter the prompt. The raw profile provides age range, gender, education, AI familiarity/use, trust, privacy importance, concerns, and privacy-sensitive domains.
- Report complete-coverage accuracy, macro-F1, quadratic weighted kappa, over-sharing, persistent over-allow, per-class precision/recall/F1, the confusion matrix, and 2,000-resample participant-cluster bootstrap 95% intervals. The two safety rates use the definitions in `../../classification_experiments/01_评估协议与防泄漏约定_zh.md`.
- This is a **personalized warm-history** task. The classification experiments' main `participant_heldout` test is a **new-user** task with no personal history available. Their scores should be shown in separate protocol sections, not ranked in the same table. A direct model comparison requires rerunning classifiers on this exact fold manifest with the same per-fold training restrictions.

## Run

From `ai_agent_permission_experiment`:

```powershell
# Use the existing experiment environment; install the API client only for live inference.
& .venv/Scripts/python.exe in_context_learning/run_ic_four_label.py `
  --out in_context_learning/artifacts/my_prepare_run

# Before live inference, install the API client and read the existing dotenv file.
& .venv/Scripts/python.exe -m pip install -r in_context_learning/requirements.txt
& .venv/Scripts/python.exe in_context_learning/run_ic_four_label.py `
  --out in_context_learning/artifacts/my_prepare_run `
  --env-file qstn_simulator/.env --execute --max-jobs 1 --max-cost-usd 4

# Inspect the one-job pilot and resume; omit --max-jobs for all 1,005 jobs.
& .venv/Scripts/python.exe in_context_learning/run_ic_four_label.py `
  --out in_context_learning/artifacts/my_prepare_run `
  --env-file qstn_simulator/.env --execute --max-cost-usd 4
```

Without `--execute`, the runner makes **no API calls** and writes `run_config.json`, `fold_manifest.json`, `preview_prompt.txt`, and `status.json`. A full run needs 201 × 5 = **1,005 model calls**. The runner enforces a maximum of USD 4 for its own output directory: before each call it reserves the cost of the prompt's conservative UTF-8 token bound plus the maximum 3,000 completion tokens; after each call it records actual usage and charges all input at the full rate, even if caching reduces the bill. Failed calls without usage are reserved at the maximum. The runner stops before a call that could cross the cap. This is an upper-bound account for standard text-token charges, not a substitute for the provider's invoice. When switching output directories or models, subtract earlier spend from the new directory's cap. The same output directory can be resumed only with matching model, seed, and input hashes. Each successful job gets a checkpoint. Invalid or incomplete model JSON stops the run and writes an error checkpoint for inspection; it does not disappear from the denominator. Once all jobs finish, the runner writes `predictions.csv`, `metrics.json`, `classification_report.json`, `confusion_matrix.csv`, and `participant_bootstrap_ci.json`.

The prepared offline smoke artifact at `artifacts/prepare_smoke_20260923/` confirms 1,005 jobs and full input coverage. A one-call live pilot has completed; full five-fold model metrics have not yet been produced. The API key is read from the existing ignored `qstn_simulator/.env` file and is not written to experiment artifacts.




## Budgeted pilot

The first o3-mini pilot used the anonymized study profile and a single user's 16-query history to predict four held-out queries (17 permission rows). It returned a complete valid JSON prediction with 2,463 prompt tokens and 2,227 completion tokens, costing an upper-bound USD 0.0125081 at the published USD 1.10 / 4.40 per million input/output token rates. The pilot artifact is `artifacts/o3mini_budget4_v1/`. Extrapolating one pilot to 1,005 calls gives about USD 12.6, which is too expensive under the user's USD 4 cap; this is a rough estimate, not a full-run result. Official model prices: https://developers.openai.com/api/docs/models/o3-mini and https://developers.openai.com/api/docs/models/gpt-4o-mini.
