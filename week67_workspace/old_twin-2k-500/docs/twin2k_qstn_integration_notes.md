# Notes: Twin-2K-500 × QSTN Integration

## Scope

Document verified release facts, the local QSTN/project interface, and a
methodologically bounded integration design for the permission-agent study.

## Verified Twin-2K-500 contract

- The release contains 2,058 U.S. four-wave completers with about 500 survey
  questions/tasks each. Its input variants are `persona_text` (all past survey
  responses in free-form text), `persona_json` (the structured form), and a
  `persona_summary` (a concise, but still substantial, synthesis).
- The official pipeline is exactly: persona profile + a newly authored survey
  question + formatting instruction -> LLM response. The demo loads persona
  summaries from Hugging Face and simulates a batch of new questions with an API
  model.
- The paper's strongest individual result (71.72%) is for its own held-out
  behavioural-economics/pricing tasks using full text + GPT-4.1 mini. Summary
  input reported 68.02%. Neither number validates data-permission responses.
- The official helper supports direct OpenAI and Gemini calls. Its OpenAI-client
  path can be adapted to an OpenAI-compatible endpoint such as OpenRouter, but
  that adapter is not included in the upstream project.

## Verified local QSTN interface

- `qstn_simulator/scripts/build_qstn_inputs.py` creates 373 fixed permission
  questionnaire items. Each has the four options: never share; do not share but
  ask next time; share but ask next time; always share.
- A QSTN persona is not a separately trained model. It is a row containing
  `persona_id`, `participant_id`, `questionnaire_name`, `system_prompt`,
  `questionnaire_instruction`, and `persona_text`. QSTN inserts the request into
  `{{QUESTION_PLACEHOLDER}}`, enforces the closed option set, and invokes an LLM.
- `run_heldout_calibration.py` is correctly restricted to the 201 released
  permission-study participants. It joins `participant_id` to real held-out
  labels, explicitly removes target labels from inference prompts, and computes
  accuracy, macro-F1, distribution TV distance, over-sharing, and under-sharing.
- Its current provider binding is `AsyncOpenAI(api_key=OPENAI_API_KEY)`. OpenAI is
  usable as-is; Gemini or OpenRouter requires a small provider-client/config
  adapter, not a redesign of the persona/QSTN layer.

## Crucial integration boundary

Twin personae have no matched ground-truth answers to the 373 permission items.
They must therefore **not** be passed to the held-out calibration runner, and
their outputs must not be called accuracy or human fidelity. The integration
needs a separate generation runner with a stable ID such as `twin2k_<pid>` and
no target-label join.

## Correct component mapping

| Component | Target-domain QSTN lane | Twin-2K lane |
|---|---|---|
| Stable persona P | anonymized participant background | Twin `persona_summary`, or a documented filtered version |
| Permission policy R | discovery-only empirical response card, calibrated on held-out labels | LLM extrapolation conditioned on P; no permission ground truth |
| Question/action E | same 373 QSTN permission items | same items, four-option JSON output |
| Memory M | an explicit RL-state transition, designed separately | same explicit transition; Twin supplies no such state |
| Valid use | fidelity calibration and main simulator evidence | OOD persona-heterogeneity / stress-test environment |

## Design consequences

- Do **not** append a QSTN `Persistent Granter` / `Re-consent Seeker` / `Broad
  Restrictor` card to a Twin persona. Those cards are learned from different
  people’s permission responses; attaching one would invent a behavioural label
  for the Twin and confound the experiment.
- Use `persona_summary` for the main Twin lane. Use full text only in a small
  sensitivity analysis, because it is much larger and the paper's reported
  accuracy advantage is outside the target domain.
- Keep target-domain calibration as a gate before RL. Then freeze the simulator
  prompt/model/version, pre-generate Twin responses into a response bank, and
  use that bank for reproducible offline RL.
