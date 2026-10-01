# Research Notes: Human-Simulating Questionnaire Agents

## Scope

Target use case: synthetic humans answer data-permission questionnaires so an RL agent can train against heterogeneous, reproducible user responses. Current baseline: QSTN, whose personas require substantial manual construction.

## Local Context to Inspect

- `ai_agent_permission_experiment/qstn_simulator/README.md`
- `ai_agent_permission_experiment/qstn_simulator/PERSONA_DESIGN_zh.md`
- `ai_agent_permission_experiment/qstn_simulator/persona_rebuild_notes.md`

## Local Findings

- The QSTN simulator already separates stable `profile-grounded persona` from mutable RL `memory_state`; this is the right abstraction for a sequential permission environment.
- It has 201 anonymized calibration personas and three discovery-only behavioural prototypes: Persistent Granters, Re-consent Seekers, and Broad Restrictors.
- The current prototypes are evidence-constrained prompt cards over response clusters, but their natural-language wording is manually authored. Held-out labels are intentionally excluded from prompts.
- The practical question is therefore not merely how to create text personas; it is how to obtain a defensible target population and map it to reproducible policy/response behaviour without target-label leakage.

## Evidence Log

### QSTN — survey execution layer, not persona generator

- Paper: https://arxiv.org/abs/2512.08646
- Source: https://github.com/dess-mannheim/QSTN
- Verified finding: QSTN accepts externally prepared persona rows and questionnaire rows; it is a modular questionnaire-inference framework rather than a library that learns or supplies a target population.

### StanfordHCI/genagents — strongest drop-in alternative for ready-made demographic agents

- Source: https://github.com/StanfordHCI/genagents
- Persona availability: repository includes a demographic bank of 3,000+ GSS-based agents plus one richer interview-grounded example. It exposes categorical, numerical, and open-ended response functions; agent memory/reflection can hold sequential RL state.
- License: MIT. Limitation: the real-interview agent bank is restricted for privacy; the open bank is demographic-only and therefore not consent-behaviour calibrated.

### SocioVerse — ready population/data but incomplete runtime release

- Paper: https://arxiv.org/abs/2504.10157
- Source: https://github.com/FudanDISC/SocioVerse
- User pool: https://huggingface.co/datasets/Lishi0905/SocioVerse
- Persona availability: project releases a gated research-use pool with sample task pools and an X user pool; labels include several demographic fields. The paper describes 10M social-media users and sampling to target distributions.
- Limitation: the official repository explicitly says the World Model code is "coming soon"; repository currently ships questionnaires/evaluation/data rather than a complete drop-in simulator. User pool is social-media-derived and privacy/representativeness constraints are material.

### PersonaHub — massive pre-generated prompt personas, but not survey-valid people

- Paper: https://arxiv.org/abs/2406.20094
- Source: https://github.com/tencent-ailab/persona-hub
- Persona availability: official release reports 200k preview personas and a 370M elite-persona release, with demonstration code for OpenAI/vLLM.
- Limitation: personas are automatically curated from web data and the project validates synthetic data generation, not individual permission choices or population representativeness. Use only as a stress-test/diversity source, not as ground-truth human proxies.

### SubPOP — distributional response model rather than a persona bank

- Paper: https://arxiv.org/abs/2502.16761
- Source: https://github.com/JosephJeesungSuh/subpop
- Verified finding: provides preprocessing, LoRA checkpoints, batched inference, and subpopulation response-distribution prediction from Pew American Trends Panel / GSS-style data. Paper reports up to 46% reduction in human–LLM distributional gap.
- License: BSD-3-Clause. Limitation: answer distributions over 22 predefined subpopulations, not persistent individual agents; US public-opinion domain needs re-training/calibration for permission decisions.

### SocioBench — evaluation/calibration dataset, not a simulator

- Paper: https://aclanthology.org/2025.emnlp-main.1335/
- Source: https://github.com/JiaWANG-TJ/SocioBench
- Verified finding: 480k real respondent records, 30+ countries, 10 sociological domains, and 40+ demographic attributes; its reported 30–40% individual-survey accuracy is a strong warning against claiming human equivalence.
- Use: add as an external robustness benchmark for a chosen model/prompt pipeline where licensing permits; do not use it to assert consent-domain validity.

### Sample-free LLM population generator — automatic demographic persona construction

- Paper and code links: https://doi.org/10.1371/journal.pone.0341704
- Persona availability: generate individual/household records from aggregate demographic descriptors, schema, and feasibility rules; no manual prose biographies or model fine-tuning.
- Limitation: validated for demographic/household alignment, not attitudes or data-permission choices. Best used to construct a target population before attaching an empirically calibrated permission-response policy.

### AgentSociety 2 / SOTOPIA / OASIS — strong environments, not answers to persona sourcing

- AgentSociety: https://github.com/tsinghua-fib-lab/AgentSociety
- SOTOPIA: https://github.com/sotopia-lab/sotopia
- OASIS: https://github.com/camel-ai/oasis
- Verified finding: all support configurable agents and multi-step environments; AgentSociety supports scalable/replayable execution, SOTOPIA gives typed agent actions and profile schema, and OASIS has explicit profile-file formats and social-media simulations.
- Limitation: their documentation still asks the user to supply/create a profile. They are appropriate only after the persona/population problem has been solved upstream.

### Methodological evidence for the recommendation

- Self-report grounded agents: https://arxiv.org/abs/2411.10109. Survey/interview-grounded agents beat demographics-only agents on held-out measures in that study, supporting the existing local strategy of grounding profiles in observed data rather than inventing free-form backstories.
- Persona caution: https://arxiv.org/abs/2602.18462. The authors find no clear aggregate benefit from multi-attribute persona prompting and report subgroup distortions.
- Distributional caution: https://arxiv.org/abs/2606.09013. Report mean, condition-pattern, and distributional alignment; mean fit alone can mislead.

### PrivacySIM — strongest domain match for data-permission simulation

- Paper: https://arxiv.org/abs/2605.12147
- Source: https://github.com/james-flemings/PrivacySIM
- Data: https://huggingface.co/datasets/jamesflemings/PrivacySIM
- Verified finding: combines five published privacy user studies; its processed sample contains 1,000 users (200 per domain), including an LLM-based AI-agent-permissions domain. Records expose demographics where available, previous experiences, privacy attitudes, questionnaire, observed responses, and preferences.
- Execution: vLLM plus OpenAI, Claude, and Gemini batch backends; configuration and `run.json` preserve sampling parameters and run metadata.
- License: code MIT; combined data CC BY 4.0, while per-row material retains source-study attribution requirements.
- Validation boundary: the paper's strongest model reached 40.4% individual decision accuracy. It is a highly relevant simulator/training data source, not evidence that a synthetic respondent replaces a person.

### Twin-2K-500 — most practical ready-made individual persona pool

- Paper: https://arxiv.org/abs/2505.17479
- Source: https://github.com/tianyipeng-lab/Digital-Twin-Simulation
- Data: https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500
- Verified finding: 2,058 US participants completed four waves and more than 500 questions. The released data includes `persona_text`, `persona_summary`, and `persona_json`; the official notebook loads these and batch-simulates responses to custom survey questions.
- License: code Apache-2.0; dataset CC BY 4.0.
- Fit: a direct no-authoring persona source for English/US experiments, but it has no privacy-permission ground truth and should be an external baseline/stress-test rather than the primary consent behavior model.

### AlignSurvey / SurveyLM — structured profile to answer model

- Paper: https://arxiv.org/abs/2511.07871
- Source: https://github.com/PiLab-ZJU/AlignSurvey
- Verified finding: provides SurveyLM checkpoints trained on a Social Foundation Corpus with 44K+ interview dialogues and 400K+ structured survey records. Its input example embeds demographic fields, question, and options directly; no natural-language biography is required.
- Limitation: it is a survey-response model and evaluation suite, not a persistent person bank or a permission-decision model. Repository terms limit use to academic, non-commercial work and require compliance with the source datasets.

### Other verified implementation options

- SynthPanel: https://github.com/DataViking-Tech/SynthPanel. MIT, 14 bundled persona packs / 232 personas, branching instruments, schema-constrained responses, saved results and provenance. Its own documentation warns that outputs are AI generated and not human research data. Good for smoke tests/OOD stress tests, not the main behavior simulator.
- Stanford GenAgents: https://github.com/StanfordHCI/genagents. MIT, 3,000+ GSS demographic agents and categorical/numerical/open-ended response APIs with memory. The richer 1,000 interview-grounded bank is not publicly downloadable; it is a generic benchmark baseline rather than a privacy population.
- German General Personas: https://github.com/germanpersonas/German-General-Personas. 5,246 ALLBUS-derived German personas in JSON/full-text formats, CC BY-NC-SA. Useful only when the target population is Germany and non-commercial licensing is acceptable.
- AgenticSociety: https://github.com/baiyuqi/agentic-society. GPL-3.0 research prototype that samples census skeletons and lets an LLM enrich personas, define question groups, and execute experiments. Useful as a persona compiler/UI idea, not a validated consent simulator.
