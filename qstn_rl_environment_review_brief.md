# QSTN and Permission-RL Environment Review

## Verdict

The five requested properties are methodologically appropriate as requirements
for a **QSTN-backed, safety-sensitive permission-RL environment**. They are not,
however, requirements that QSTN itself can satisfy alone. QSTN is a modular
questionnaire inference framework: it renders prompts, varies questionnaire
presentation, obtains constrained responses, and parses outputs. It is not a
data-calibrated, stateful user-transition model or a simulator-validation
framework for RL policy ranking.

The project should therefore retain QSTN only as a static questionnaire and
prompt-robustness layer. It should not use prompt-only QSTN as the primary
human feedback environment for RL.

## Assessment of the Five Requirements

### 1. Behavioral fidelity: correct, with a probabilistic target

The target should be a held-out conditional distribution over the four observed
permission labels, rather than an expectation that every individual item is
predicted exactly. The currently observed data support this only for one-step
choices conditional on available request features and, in a warm-start setting,
some prior responses from the same participant.

The data do not support observed transitions for requests for explanation,
override, revoke, task termination, agent mistakes, trust, or burden. These may
be included in a future environment only as explicit state-transition hypotheses
until a sequential human study measures them.

### 2. Profile-specific fidelity: correct and mandatory

Aggregate accuracy can conceal dangerous subgroup errors. Evaluation must report
each profile x context stratum's four-label distribution, current-access error,
persistence error, false-allow rate, and uncertainty interval. A simulator whose
overall distribution is accurate by cancelling a restrictive-profile false allow
against a permissive-profile false deny is not acceptable.

### 3. Safety fidelity: correct, but formalize the gate

False allow / over-sharing should be a pre-registered hard constraint, evaluated
especially on `incorrect_explicit` contexts and a separately defined high-risk
slice such as sensitive-data x inappropriate-purpose/recipient. It remains a
proxy for disagreement with a human stated-deny label, not a measured privacy
harm.

The gate must include an under-sharing or utility diagnostic as well. Otherwise
an always-deny simulator can appear safe merely by refusing everything. Thresholds
should be set before the final evaluation and reported with one-sided confidence
bounds, not selected after observing a candidate's result.

### 4. Sequential fidelity: correct as the eventual RL requirement, unavailable now

The intended state machine is reasonable:

`agent request/action -> user feedback -> update history/burden/trust -> next state`.

For the current survey, only the initial four-way response is observed. A first
multi-turn wrapper can be useful for stress testing, but it must be described as
a designed MDP/CMDP transition model, not as a learned human simulator. The
transition probabilities for trust decay, fatigue, explanation requests,
overrides, and revocations require a new sequential user study or prospective
logged deployment.

### 5. Policy-ranking fidelity: correct as the final acceptance test

A simulator should be judged by whether policies trained or selected with it
retain their ordering on an independent human benchmark. This is stronger than
next-response accuracy and is the right protection against simulator reward
hacking.

The present full-information survey can rank only one-step stated-policy
agreement under a fixed context distribution. It cannot validate the long-run
ranking of always-allow, MAB, CMDP, or RL policies because it has no observed
trajectory outcomes under their actions. That test needs either randomized human
replay with relevant outcome logging or a small prospective multi-turn study.

## Implication for the Current Project

- QSTN prompt cards V1/V2 are frozen and failed their static held-out gate.
- The four-label empirical response policy also failed its participant-held-out
  primary gate and increased over-sharing relative to its profile-majority
  baseline.
- The current online replay MAB is a useful stated-policy adaptation baseline,
  but its false-allow rate remains near 100%; it cannot be called a safety
  controller.

This is consistent with the professor-aligned project plan: the completed MAB
work is the high-level permission-controller baseline. A future Step 3 needs a
separate interaction environment; Steps 4--5 need a security critic and a
Constitution/SFT/preference/RL pipeline. A questionnaire simulator is a component
of Step 3, not a substitute for the whole pipeline.

## Tool Recommendation

No verified open-source tool is a drop-in replacement for humans under all five
requirements. The practical allocation is:

| Tool | Appropriate role | Not sufficient for |
| --- | --- | --- |
| QSTN | Questionnaire rendering, constrained four-option inference, prompt robustness ablations | calibrated personas, state transitions, policy-ranking validation |
| PrivacySIM | Strongest privacy-specific simulation evaluation baseline and persona schema | independent AAP test data, longitudinal revoke/override behavior, human replacement |
| AlignSurvey / SurveyLM | General structured-survey-response baseline; possible domain-adaptation starting point | permission-specific or multi-turn simulation |
| Twin-2K-500 | External persona-heterogeneity and robustness arm | permission ground truth or safety validation |
| Generative-agent / survey-agent frameworks | Engineering a stateful interaction shell | empirically calibrated permission feedback |

PrivacySIM is the first tool worth using next, but only as a benchmark and
persona-schema baseline. Its AI-agent-permissions subset overlaps the project's
source study, so it is not an independent human pool. Its authors report a best
individual-level accuracy of 40.4%, which is evidence against treating it as a
human substitute.

## Recommended Staged Path

1. Preserve the current paper's claim: participant-held-out stated-policy and
   online-replay MAB baselines only.
2. Use QSTN and PrivacySIM as static baselines in a frozen, profile-stratified
   calibration comparison. Do not train RL from either unless a pre-registered
   static safety gate is passed.
3. Build a transparent finite-state permission environment for simulation-only
   stress tests. Separate static persona parameters from unvalidated dynamic
   transition assumptions.
4. Run a small sequential human study with repeated permission requests and
   varied agent explanations/actions. Record confirmation, denial, re-consent,
   override, revoke, task abandonment, perceived burden, and task outcome.
5. Fit and evaluate the transition model on held-out participants/trajectories.
   Select or train MAB/CMDP/RL policies only after an independent policy-ranking
   test; retain a final human evaluation for the safety claim.

## Sources

- Kreutner et al. (2026), QSTN: https://aclanthology.org/2026.eacl-demo.37/
- Flemings and Annavaram (2026), PrivacySIM: https://arxiv.org/abs/2605.12147
- Suh et al. (2026), Quantifying the Utility of User Simulators for Building
  Collaborative LLM Assistants: https://arxiv.org/abs/2605.09808
- Lin et al. (2025), AlignSurvey: https://arxiv.org/abs/2511.07871
- Toubia et al. (2025), Twin-2K-500: https://arxiv.org/abs/2505.17479
