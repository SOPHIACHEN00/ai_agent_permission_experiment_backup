# Notes: QSTN Dynamic User-Simulator Assessment

## Project-grounded evidence

- The proposal is explicitly staged: completed work is participant-held-out stated-policy prediction and sequential replay MAB; live interaction, CMDP/RL, security sub-agent, and Constitutional AI remain future work.
- Current survey data observe one four-way stated permission choice. They do not observe explanation requests, overrides, revocations, trust/burden dynamics, task outcomes, or longitudinal re-consent.
- Existing QSTN prompt cards and four-label empirical policy failed their participant-held-out gate; prior project review reports an over-sharing regression.
- PrivacySIM's AI-agent-permissions subset is reorganized from the same upstream `llm-platform-security/ai-agent-permissions` study used by this project. It cannot be an independent human evaluation pool.

## Primary-source verification

- QSTN: questionnaire inference for in-silico surveys/annotation, with presentation, perturbation, and generation experiments; not a state-transition model or RL environment.
- PrivacySIM: privacy-persona evaluation suite over 1,000 users. The highest reported individual accuracy is 40.4%. Its public code is batch simulation, static alignment evaluation, and plotting.
- AlignSurvey: SurveyLM models and four survey-pipeline tasks, including survey response modeling; no permission-specific longitudinal transition component.
- UserLM-8b: MIT-licensed runnable multi-turn user language model (opening turn, follow-ups, end token). It is WildChat-trained and requires domain-specific testing/adaptation.
- HumanLM: state-alignment user-simulation method with a real-time human study; no verified AI-permission trajectory data for this project.
- tau2-bench: reusable tool-agent-user, custom-domain, Gymnasium environment engineering; its published domains are not privacy-permission behavior.
- Two 2026 validation papers find (a) behavior-grounded simulators transfer RL assistants to people better than role-playing LLMs, and (b) LLM simulators are often over-cooperative/overly positive relative to real users.

## Sources

- QSTN: https://aclanthology.org/2026.eacl-demo.37/
- PrivacySIM: https://arxiv.org/abs/2605.12147 and https://github.com/james-flemings/PrivacySIM
- AlignSurvey: https://arxiv.org/abs/2511.07871 and https://github.com/PiLab-ZJU/AlignSurvey
- UserLM: https://arxiv.org/abs/2510.06552 and https://huggingface.co/microsoft/UserLM-8b
- HumanLM: https://arxiv.org/abs/2603.03303
- Simulator downstream utility: https://arxiv.org/abs/2605.09808
- Sim2Real user-simulation gap: https://arxiv.org/abs/2603.11245
- tau2-bench: https://github.com/sierra-research/tau2-bench
