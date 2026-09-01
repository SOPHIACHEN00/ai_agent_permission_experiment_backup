# QSTN Permission Simulator

This isolated project prepares QSTN as the questionnaire-response layer for the AI-agent permission study. It intentionally leaves the parent four-label benchmark unchanged.

## Design document

The current design for adding privacy/security behavior rules and longitudinal hidden state is maintained in [SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md](SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md). Update its Change Log when the QSTN/rules architecture changes.

The implemented static RulePack v1.0 is documented in the bilingual [RULEPACK_V1.0_README.md](RULEPACK_V1.0_README.md). Its version-pinned assets are grouped under [config/v1.0/](config/v1.0/), including the complete English evidence-derived rule catalog. The current-turn audit extension is documented in [RULEPACK_V1.1_README.md](RULEPACK_V1.1_README.md) and grouped under [config/v1.1/](config/v1.1/). The project-level roadmap and file inventory are maintained in [versioning.md](versioning.md).

## RulePack v1.1 audit extension

Build the label-free current-turn context sidecar first, then compile the v1.1 templates:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1_1.build_context_v1_1
.\.venv\Scripts\python.exe -m scripts.v1_1.compile_s_qstn_v1_1
.\.venv\Scripts\python.exe -m scripts.runtime.run_heldout_calibration `
  --config config\v1.1\heldout_calibration_s_qstn.json `
  --dry-run
```

The default v1.1 mode is `audit_compatible`: it records information-completeness and current-turn burden buckets without changing v1.0 permission directions. `qualitative_exploratory` is reserved for synthetic fixtures or prompt ablations. Neither mode adds unsupported numeric weights or longitudinal state.

## RulePack v2.0 bounded-memory layer

The bilingual [RULEPACK_V2.0_README.md](RULEPACK_V2.0_README.md) documents the
implemented v2.0 memory/state substrate. It is grouped under
[config/v2.0/](config/v2.0/) and keeps the full English evidence-rule skill
catalog. The v2 compiler uses explicit label-free memory fixtures; it does not
claim human-calibrated forgetting or human likeness.

```powershell
.\.venv\Scripts\python.exe -m scripts.v2.build_memory_fixtures_v2
.\.venv\Scripts\python.exe -m scripts.v2.compile_s_qstn_v2
.\.venv\Scripts\python.exe -m scripts.v2.smoke_test_openai_qstn_v2 --dry-run
```

The default mode is `stateful_audit_compatible`. The optional
`synthetic_exploratory` mode is for offline transition diagnostics only. The
v2 smoke test validates the exact QSTN prompt path and can send one request
only when `--dry-run` is omitted.

## Why it is separate

The parent project predicts answers observed in a static user study. This project will generate simulated questionnaire responses, then calibrate them against that study before any reinforcement-learning experiment uses them.

## Setup

From this directory:

```powershell
uv sync
Copy-Item .env.example .env
# Add OPENAI_API_KEY to .env locally.
uv run python scripts/check_environment.py
```

The offline environment check and dry-run smoke tests do not call an LLM or transmit data. They verify QSTN, the local environment, prompt rendering, and read-only access to the four-label dataset.

## Build QSTN Inputs

```powershell
.\.venv\Scripts\python.exe scripts\build_qstn_inputs.py
```

This creates `outputs/questionnaire_items.csv`, `outputs/personas.csv`, and `outputs/calibration_assignments.csv` locally. The questionnaire has one closed-ended permission item per observed request/tool/data context. Personas use only structured, anonymized profile fields; the observed Task 3 answers are excluded to prevent label leakage.

`calibration_assignments.csv` is the evaluation index: it contains only persona-question pairs with an observed human Task 3 label. Do not treat unobserved combinations in the full 201-by-373 simulation space as human ground truth.

Read `PERSONA_DESIGN_zh.md` before making any external LLM call with the generated personas.

## One-Question API Smoke Test

After setting `OPENAI_API_KEY` in `.env`, first render and inspect the default
empirical-profile prompt without a remote call:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1.smoke_test_openai_qstn --dry-run
```

Then run the one-item OpenAI wiring check:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1.smoke_test_openai_qstn
```

By default, this uses the canonical `prototype_persistent_granters` profile and
the first permission item. It sends exactly one request to the configured model,
validates the constrained four-option JSON answer, and writes:

- `outputs/openai_qstn_empirical_profile_smoke_test_preflight.json`: the exact
  system/user prompt before inference, with `api_called: false`.
- `outputs/openai_qstn_empirical_profile_smoke_test.json`: the response and
  parsed answer after inference.

This is a wiring check, not a human-calibration result. To inspect a different
prototype, pass `--persona-id prototype_reconsent_seekers` or
`--persona-id prototype_broad_restrictors`.

## One-Question v1.1 RulePack API Smoke Test

The v1.1 diagnostic uses the version-pinned RulePack, context sidecar, English
respondent contract, and skill catalog. First inspect the rendered v1.1 prompt
without a remote call:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1_1.smoke_test_openai_qstn_v1_1 --dry-run
```

Then send exactly one single-item request through the configured model:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1_1.smoke_test_openai_qstn_v1_1
```

The default is `audit_compatible` with `active_excerpt` skill exposure. The
diagnostic validates that the prompt contains the v1.1 contract, active
RulePack context, and audit boundary, then checks the constrained four-option
JSON answer. It is an API wiring check, not a calibration run or a
human-likeness result. It writes:

- `outputs/openai_qstn_rulepack_v1_1_smoke_test_preflight.json`: exact v1.1
  request messages and context audit before inference.
- `outputs/openai_qstn_rulepack_v1_1_smoke_test.json`: one API response and
  parsed permission answer.

## Empirical Permission-Response Profiles

Build descriptive profiles directly from the 201 participants' observed permission behavior:

```powershell
.\.venv\Scripts\python.exe scripts\discover_empirical_profiles.py
```

The script splits each participant's responses into discovery and held-out subsets, clusters only six directly observable response features, and compares `k=2..6`. The selected solution is `k=3`, using a one-standard-error-style parsimony rule after enforcing minimum-size and split-stability constraints.

It writes:

- `outputs/candidate_cluster_metrics.csv`
- `outputs/empirical_profile_assignments.csv`
- `outputs/empirical_profile_centers.csv`
- `outputs/EMPIRICAL_PROFILE_DISCOVERY_REPORT_zh.md`

The resulting labels (`Persistent Granters`, `Re-consent Seekers`, and `Broad Restrictors`) are post hoc descriptions of observed permission behavior. They are not validated psychological constructs, independent traits, or population prevalence estimates.

## Compile QSTN Personas

Turn the selected K=3 profiles into auditable QSTN prompt inputs without an LLM call:

```powershell
.\.venv\Scripts\python.exe scripts\compile_empirical_personas.py
.\.venv\Scripts\python.exe scripts\validate_empirical_personas.py
```

The compiler produces two different inputs:

- `outputs/personas_with_empirical_profiles.csv`: the 201 anonymized calibration personas, each retaining its raw profile fields and receiving only its discovery-derived empirical profile card.
- `outputs/qstn_empirical_profile_prototypes.csv`: three canonical profile personas for later simulator and RL work, without real participant background fields.

QSTN persona conditioning is implemented through each row's `system_prompt` and `questionnaire_instruction`; the instruction must include `{{QUESTION_PLACEHOLDER}}` so QSTN renders the actual permission scenario and its four options. `validate_empirical_personas.py` verifies this locally for all 204 generated prompts and confirms that target-answer columns are absent.

The learned cluster assignments and centers are distinct from the English prompt-card wording. The latter is manually authored, evidence-constrained wording recorded in `config/empirical_profile_prompt_cards.json`, not language learned from participant text.

## Qualitative Profile-Card Pilot

Before held-out calibration, inspect the three canonical prototypes on three
metadata-selected scenarios: a routine aligned request, a sensitive aligned
request, and a sensitive mismatched request. The configuration contains the
selection rationale and explicitly forbids the use of participant response
labels:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1.run_qualitative_profile_pilot --dry-run
.\.venv\Scripts\python.exe -m scripts.v1.run_qualitative_profile_pilot --api-concurrency 1
```

The full run makes nine OpenAI requests. It writes a preflight prompt audit,
a nine-row response table, and a descriptive report under `outputs/`:

- `qualitative_profile_pilot_preflight.json`
- `qualitative_profile_pilot_results.csv`
- `qualitative_profile_pilot_result.json`
- `QUALITATIVE_PROFILE_PILOT_REPORT.md`

This is a qualitative prompt diagnostic only. It must not be scored against
human labels or reported as accuracy, F1, statistical evidence, or human-likeness.

## Minimal Held-Out Calibration Before RL

Run the fixed pre-RL quality gate before treating the QSTN personas as a feedback source. It samples 10 participants from each learned profile and three held-out contexts per person: one `necessary`, one `incorrect_explicit`, and one deterministic random remaining context.

```powershell
.\.venv\Scripts\python.exe -m scripts.runtime.run_heldout_calibration --dry-run
.\.venv\Scripts\python.exe -m scripts.runtime.run_heldout_calibration --execute
```

The dry run makes no remote request. It validates all 90 rendered QSTN prompts and writes an inference plan with no `label_id` or `label_text` fields. The execute command makes exactly 90 calls to the frozen `OPENAI_MODEL` (currently `o4-mini`), one at a time, and can be resumed after an interruption with `--execute --resume`.

The protocol is fixed in `config/heldout_calibration_v1.json`. It evaluates only the deployed `raw_participant_profile_plus_empirical_card` condition; the larger paired raw-profile versus card ablation is deliberately deferred because it would double the call budget. Outputs are written under `outputs/minimal_heldout_calibration_v1/`:

- `preflight_manifest.json`: prompt audit, sampling record, and no-label guardrail.
- `inference_plan.csv` and `sampled_heldout_contexts.csv`: the 90 model inputs without human targets.
- After execution: `predictions.csv`, overall/profile/context metrics, participant-bootstrap intervals, and `HELDOUT_CALIBRATION_REPORT.md`.

This is a small, strict held-out entry check for RL, not a population estimate, a causal ablation of the prompt card, or proof of general human-likeness. Human-study labels are used only after model inference to calculate the reported metrics.

## Discovery-Only Prompt Card V2

`empirical_profile_cards_v1` and its completed 90-row diagnostic are frozen. The revised `empirical_profile_cards_v2` wording is separately versioned and is constrained only by the discovery-derived cluster centers. It introduces a shared privacy decision rule and clearer profile-specific defaults; it does not place held-out labels, predictions, metrics, or numeric response rates inside prompts.

Compile and inspect v2 without calling an LLM:

```powershell
.\.venv\Scripts\python.exe scripts\compile_empirical_personas.py `
  --config config\empirical_profile_prompt_cards_v2.json `
  --out outputs\empirical_personas_v2 `
  --base-personas outputs\personas.csv `
  --assignments outputs\empirical_profile_assignments.csv `
  --centers outputs\empirical_profile_centers.csv

.\.venv\Scripts\python.exe scripts\validate_empirical_personas.py `
  --out outputs\empirical_personas_v2 `
  --questionnaire outputs\questionnaire_items.csv
```

The v2 calibration configuration excludes both every v1 participant and every v1 response row before sampling. Its dry run verifies the disjoint 90-row plan locally:

```powershell
.\.venv\Scripts\python.exe -m scripts.runtime.run_heldout_calibration `
  --config config\heldout_calibration_v2.json `
  --out outputs\minimal_heldout_calibration_v2 `
  --dry-run
```

Only after wording review should `--dry-run` be changed to `--execute`. That command will make exactly 90 additional `o4-mini` requests. Do not modify v2 using its evaluation labels and then re-evaluate it on the same 90 rows.
