# Notes: QSTN and Permission-RL Environment Review

## Local Evidence

- The current proposal treats participant-held-out stated-policy prediction and sequential replay as preliminary baselines, not evidence of live privacy safety.
- QSTN prompt-card V1/V2 failed their held-out calibration gate and are frozen.
- The current four-label empirical policy also failed its participant-held-out quality gate, including an over-sharing regression.
- Existing raw data contain four permission labels and static survey responses, but no observed sequences of trust change, overrides, revocations, task outcomes, or burden.

## Working Distinction

- **Static stated-policy fidelity**: can be evaluated with the existing survey data.
- **Sequential behavioral fidelity**: requires observed interaction trajectories or explicitly labelled, unvalidated transition assumptions.
- **Policy-ranking fidelity**: requires a common policy benchmark and human replay with observed outcomes, or a new live/small-scale human study.

## Verified External Sources

- QSTN (Kreutner et al., EACL 2026) is a modular framework for questionnaire-style prompt presentation, perturbation, and response generation. Its published scope is in-silico surveys and annotation, not a calibrated sequential user environment.
- PrivacySIM (Flemings and Annavaram, 2026) evaluates privacy-decision simulation with persona facets from five privacy studies. Its strongest reported individual-level accuracy is 40.4%, so it is useful as an evaluation/baseline framework but not as a validated human replacement.
- Suh et al. (2026), *Quantifying the Utility of User Simulators for Building Collaborative LLM Assistants*, finds that RL assistants trained against role-playing simulators fail to generalize reliably, whereas grounding simulators in human behavior improves downstream utility. This supports policy-ranking/downstream validation as an end criterion.
- AlignSurvey / SurveyLM provides an open, structured social-survey response benchmark and model family, but lacks permission-domain and longitudinal interaction ground truth.
- Twin-2K-500 provides a broad, repeated-wave individual survey corpus and simulation tooling, but no AI-agent permission labels or validated revoke/override trajectories.

## Tool Implication

No verified off-the-shelf tool simultaneously provides: four-way AI-agent permission labels, profile-calibrated behavior, observed multi-turn override/revoke transitions, and validation of the ranking of safety policies. Tools must therefore be assigned narrower roles rather than presented as direct replacements for human interaction.
