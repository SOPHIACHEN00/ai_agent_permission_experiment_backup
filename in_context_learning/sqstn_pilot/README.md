# S-QSTN 20-persona ICL pilot

This isolated experiment evaluates synthetic permission-answer predictability.
It reuses 20 participants and their exact four history / four fold-0 test queries
from the existing 40-person pilot. The selected persona quota is 3 broad
restrictors, 7 persistent granters, and 10 reconsent seekers.

## Models and information

- Generator: configured `o4-mini` through OpenAI; QSTN 0.5.1 single-item prompts,
  empirical profile cards v2, RulePack v2, fresh empty state per item, native
  four-option JSON schema, low reasoning, 4,096 maximum completion tokens.
- Predictor: `google/gemini-3.8-flash` through OpenRouter; original ICL prompt,
  low reasoning, 8,000 maximum output tokens. Compare empty history with the
  same user's four complete synthetic answered queries.
- Generate all 624 labels (350 history, 274 test), then freeze them before
  either predictor condition. Private profile cards, rules, state and test
  answers are absent from predictor inputs. No model weights are updated.

## Run from the Week67 workspace

Offline preparation (no API calls):

```powershell
& 'ai_agent_permission_experiment\qstn_simulator\.venv\Scripts\python.exe' -u 'ai_agent_permission_experiment\in_context_learning\sqstn_pilot\run_pilot.py'
```

Authorized execution or resume:

```powershell
& 'ai_agent_permission_experiment\qstn_simulator\.venv\Scripts\python.exe' -u 'ai_agent_permission_experiment\in_context_learning\sqstn_pilot\run_pilot.py' --execute --concurrency 4
```

Default output is `artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1`.
Successful calls are reused. Failures stop dispatch; `--retry-errors` is an
explicit recovery option after inspecting the error ledger. No automatic retry
or fallback model is used. Every request reserves its conservative cost before
dispatch; actual token costs replace that reserve afterward. The run cap is
USD 8, including retained failure costs. In-flight reserves can make live
`run tracked` console totals temporarily exceed the final batch cost.

## Artifacts

- `run_config.json`, `participants.csv`, `job_manifest.json`: fixed configuration,
  source hashes, sampled personas and exact query lists.
- `generator_preflight.json`, `predictor_preflight.json`: exact messages and
  prompt hashes. They contain public anonymous data or synthetic outputs.
- `calls/`: raw responses, parsed results, requested/returned model IDs, token
  usage, failure records and costs. API keys are never saved.
- `synthetic_answers.csv`, `synthetic_freeze.json`: frozen simulated labels and
  content hashes.
- `predictions_0shot.csv`, `predictions_4shot.csv`: matched per-permission results.
- `metrics_*.json`, `classification_report_*.json`, `confusion_matrix_*.csv`,
  `metrics_by_profile.csv`, `paired_bootstrap.json`: descriptive analysis with
  fixed four-class macro-F1 and 1,000 paired participant bootstrap draws.
- `format_fix_provenance.json`: the initial failed format request was retained
  for accounting; its answer was not reused. The corrected run uses native
  QSTN schema throughout successful generation.

## Scope

This is a static synthetic pilot with 20 personas and one fixed split/sample.
Persona discovery and ICL fold assignment are different splits, so this is not
an independent held-out human reconstruction experiment. Intervals condition
on frozen labels and model outputs; they do not incorporate fresh generator
samples, new folds, or different demonstration selection. The three persona
types are descriptive response tendencies, not validated psychological traits.

## Experiment record

- [2026-09-26 experiment log](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/EXPERIMENT_LOG_2026-09-26_zh.md): fixed protocol, results, matched human comparison, cost, limitations and artifact links.
- [Full results report](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/REPORT_zh.md).
- [S-QSTN / S&P comparison](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/COMPARISON_zh.md).

The same 20 source participants have 1,628 human answers in total. Both matched
experiments use the same 624 selected permission records: 350 history and 274
test. S-QSTN generates replacement labels only for these selected records.
