# Integration Guide: Twin-2K-500 × QSTN

## Decision

**Yes, Twin-2K-500 is technically a good fit for QSTN, but as a separate
persona-generation lane rather than a replacement for the present held-out
permission calibration.** QSTN supplies the permission-question interface,
four-option constraint, API batching, audit trail and response parsing. Twin
supplies a large, non-hand-written pool of stable persona context.

The two should meet at the prompt, not by merging their labels:

```text
Twin persona_summary P + QSTN permission item E
             -> frozen LLM prompt -> four-option response y
             -> cached Twin response bank

existing permission-study P/R + same QSTN item E
             -> held-out human-label calibration
             -> main evidence for the permission simulator
```

## Do not make this combination

Do not attach the existing `Persistent Granter`, `Re-consent Seeker`, or
`Broad Restrictor` empirical cards to a Twin persona. Those are discovery-only
behavioural summaries learned from *different* permission-study participants.
Doing so would manufacture a permission preference for an unrelated Twin person
and make the source of an answer impossible to interpret.

## Minimal technical design

### 1. Build a Twin persona adapter

Add a **new** read-only preparation script, for example
`qstn_simulator/scripts/build_twin2k_personas.py`. It should load the released
dataset and write `outputs/twin2k_personas_summary.csv` with this contract:

| Output field | Value |
|---|---|
| `persona_id` | `twin2k_<pid>` |
| `participant_id` | same stable internal key, used only for QSTN lookup |
| `questionnaire_name` | `permission_survey` |
| `persona_text` | Twin `persona_summary` |
| `system_prompt` | generic survey-simulation instruction |
| `questionnaire_instruction` | fixed instruction below, including `{{QUESTION_PLACEHOLDER}}` |
| `persona_source`, `persona_variant` | `Twin-2K-500`, `summary` |
| `source_revision`, `persona_sha256` | dataset/reproducibility provenance |

Use the summary variant first. It is lighter and avoids sending the complete
survey history, some of which is sensitive, to the inference API. Full text and
JSON belong only in a small, declared sensitivity test.

Suggested stable instruction:

```text
Answer the following AI-agent data-sharing permission question as the person
described by the supplied survey profile. Use the profile only as evidence of
stable tendencies. Do not claim that the person previously made a privacy or
permission decision unless it appears in the profile. Do not invent facts,
experiences, or motivations. Choose exactly one listed option.

Survey profile:
{persona_summary}

Permission scenario:
{{QUESTION_PLACEHOLDER}}
```

### 2. Add a separate Twin runner; preserve the calibration runner

Do **not** alter `run_heldout_calibration.py`: it is the protected main-study
path and correctly assumes a target participant has a held-out human label.

Instead add `run_twin2k_permission_simulation.py`, reusing the QSTN pieces that
already work (`LLMPrompt`, `QuestionnairePresentation.SINGLE_ITEM`, and
`conduct_survey_single_item`). Its plan is a Cartesian product of:

`selected Twin persona IDs × selected rows in questionnaire_items.csv`.

It must have no `label_id`, `label_text`, accuracy, or F1 code path. Write:

- `twin_inference_plan.csv` — persona/question pairs, no human targets;
- `twin_preflight_manifest.json` — rendered-prompt samples, prompt hash, data
  version, model/provider/temperature/seed;
- `twin_response_bank.csv` — persona ID, item ID, four-option answer, raw output,
  replicate ID, and run fingerprint;
- `TWIN_SIMULATION_REPORT.md` — only structural and robustness diagnostics.

### 3. Make provider choice explicit

The current calibration runner uses `AsyncOpenAI` directly. For the new Twin
runner, expose a provider configuration rather than changing the frozen
calibration config:

```json
{
  "provider": "openai | openrouter | gemini",
  "model": "pinned provider model identifier",
  "base_url": "only for OpenAI-compatible providers",
  "temperature": 0,
  "seed": 20260722,
  "api_concurrency": 3
}
```

OpenAI works with the current client. OpenRouter can use the same OpenAI SDK
with its documented base URL; Gemini needs a small client adapter. Pin the exact
model name and provider routing in the manifest: a moving `latest` alias is not
acceptable for a reproducible paper experiment.

### 4. Start with a bounded pilot

Do not run all `2,058 × 373 = 767,634` persona-question pairs. Start with a
fixed seed sample of 100 Twin personae and a balanced request set, for example
8 domains × 2 necessity states × 2 data-type/request contexts = up to 32 items.
That is at most 3,200 calls for one deterministic draw.

Pilot checks:

1. Every response parses into exactly one of the four QSTN options.
2. Same persona is stable under a repeated identical prompt; prompt order does
   not materially change its response.
3. The Twin population is not collapsed into one response option.
4. Necessary versus explicitly unnecessary requests produce distinguishable
   aggregate distributions.
5. Prompt/model/dataset hashes and all provider parameters are recorded.

Only after this passes should a larger cached response bank be created for RL.
For a stochastic environment, collect a pre-specified number of independent
draws per pair and sample from their empirical option distribution. For a fully
reproducible baseline, cache one frozen answer per pair.

## How it enters the RL study

Use two lanes, not one blended claim:

| Lane | Role | Reportable outcome |
|---|---|---|
| Target-domain QSTN calibration | Main simulator quality gate; labels available | accuracy, macro-F1, TV distance, over/under-sharing against held-out humans |
| Twin-QSTN response bank | Out-of-domain persona-heterogeneity environment | agent safety/utility/stability under an unseen, rich persona pool; no human-fidelity score |

The RL `memory_state` remains your own explicit transition model (e.g., recent
overreach, trust, re-consent, fatigue). Twin provides a stable starting profile,
not longitudinal permission behaviour. Freeze this transition rule across both
lanes so a performance difference is attributable to the persona environment,
not to different RL dynamics.

Initially, train and tune the core policy in the target-domain calibrated lane.
Run the frozen policy in the Twin lane as a robustness experiment. If Twin is
later used for domain randomization during training, present it as an additional
ablation and retain a target-domain-only result as the primary claim.

## Paper wording

> Twin-2K-500 is used as an external source of fixed, richly observed persona
> context. QSTN renders the same constrained data-permission questions for these
> personas. Because Twin-2K-500 does not contain matched answers to our permission
> requests, this arm evaluates robustness to persona heterogeneity rather than
> individual-level fidelity to human privacy decisions.

## Required limitations and provenance

- The Twin paper validates related behavioural tasks, not data-permission choices.
- The population is a U.S. panel, so it is not a substitute for a Canada/global
  user study.
- The public persona record can contain sensitive survey content. Prefer summary
  input, document the API data-handling choice, and do not send any unpublished or
  locally private participant content to a provider.
- Preserve Twin-2K-500 attribution/licence information and record the exact
  dataset snapshot used.
