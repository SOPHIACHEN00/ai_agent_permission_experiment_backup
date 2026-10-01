# Notes: Dynamic User Simulator Research Design

## Purpose

Evidence, design decisions, open questions, and limitations for a dynamic user simulator supporting privacy-permission agent research. This is a design record, not an implementation log.

## Known Project Constraints

- Existing data contain static four-label stated permission choices, not observed multi-turn transitions.
- The simulator must support the future human-interaction, security-sub-agent, and Constitutional-RL stages, while retaining the MAB work as a baseline.
- Safety-critical automatic disclosure must be controlled by external security rules rather than inferred solely from simulated user preference.

## Evidence Log

### Project and methodological boundary

- The existing project has a strong Step-1/Step-2 four-label stated-policy and MAB baseline, but it has no measured transitions for explanation, override, revocation, trust, burden, or termination. Those later outcomes cannot honestly be learned from the present survey.
- The appropriate methodological stance is pragmatic mixed methods: controlled longitudinal human interaction is needed for causal/transition evidence; qualitative pilot work is useful to identify state variables and user feedback categories that fixed labels miss.

### Closest permission-management environment: Janus

- Janus (Brigham et al., arXiv 2026) is a newly released playground for user-involved agentic permission management: agent, tool, permission manager, pluggable assistant, user follow-up, scenarios and evaluation harness.
- Its default-deny ABAC interception and actions `approve_once`, `create_policy`, and `reject` are highly reusable conceptual building blocks. It also supplies attack and out-of-alignment scenarios.
- Its synthetic responder modes are only `always_yes`, `always_no`, and `alignment_aware`; the latter uses scenario-known desirable/attack labels. It is therefore an excellent environment/baseline source, not empirical evidence of human behavior.
- The public repository did not visibly expose a license in the inspected repository root. Re-check license before any code reuse.
- Sources: https://arxiv.org/abs/2607.01510 ; https://github.com/GraceBrigham/Janus ; https://raw.githubusercontent.com/GraceBrigham/Janus/main/architecture.md

### Dynamic user-simulation methods

- UserLM-8b is an MIT research model trained on WildChat to generate first turns, follow-up turns, and an end-conversation token from intent and conversation state. It is a language-layer warm start only, not a permission simulator. https://arxiv.org/abs/2510.06552 ; https://huggingface.co/microsoft/UserLM-8b
- HumanLM explicitly aligns latent belief, goal, value, stance, emotion and communication state; it provides an open method/code base but has no permission-scope or revocation ground truth. https://arxiv.org/abs/2603.03303 ; https://github.com/zou-group/humanlm
- UserLM-R1 separates static and dynamic profiles (memory, goal/strategy, trust, emotion, patience, participation) and is a useful architecture blueprint, but its permission validity is unproven. https://arxiv.org/abs/2601.09215
- UGST is useful for modular profile/policy/objective/requirement/preference state updates, while warning that user simulators can drift from stated goals. https://arxiv.org/abs/2507.20152
- OdysSim/OSim is a broad behavioral foundation model/training recipe, not permission calibration. https://arxiv.org/abs/2606.14199 ; https://github.com/sunnweiwei/OdysSim

### Validation precedents

- Sim2Real evaluates 31 simulators against 451 real users in a tool-agent setting and documents over-cooperation, overly positive feedback, premature information sharing, and poor resistance to errors. This justifies a human replay/policy-ranking gate. https://arxiv.org/abs/2603.11245
- ConvApparel uses randomized helpful versus frustrating AI behavior and turn-level satisfaction/frustration outcomes. Its counterfactual validation pattern can be adapted to correct, under-specified, misleading, and high-risk permission-agent behaviors. https://aclanthology.org/2026.eacl-long.244/ ; https://huggingface.co/datasets/google/ConvApparel
- PrivacySIM is the closest privacy-specific static calibration benchmark; reported individual-level fidelity remains limited and it lacks multi-turn state transitions. https://arxiv.org/abs/2605.12147
- Dynamic permission research provides a longitudinal, contextual-history precedent but not an LLM agent user simulator. https://arxiv.org/abs/1703.02090

### Environment frameworks

- tau2-bench/τ³-bench provides an active MIT-licensed half-duplex tool-agent-user framework and Gymnasium interface; it can inform a future custom domain but does not provide privacy-user calibration. https://github.com/sierra-research/tau2-bench
- Janus is more directly task-aligned than tau2-bench, while τ-bench is more mature as a generic environment/Gym engineering reference.

### Additional environment and validation references

- SimulatorArena provides a useful *validation* precedent: it compares user simulators by human replay and by whether simulator-based policy rankings agree with people. Its current task domains are mathematics tutoring and document writing, so it informs methodology rather than permission semantics. https://github.com/mitchellgiles/SimulatorArena
- Verifiers and Gymnasium are future environment-interface references, not user models. They can later supply a typed multi-turn step/reset contract and automated checks, but neither provides human preference or privacy safety truth. https://github.com/willccbb/verifiers ; https://gymnasium.farama.org/
- UserBench/TravelGym offers a small preference-revealing Gym-loop reference with an Apache-2.0 repository license; its travel domain must not be treated as evidence for privacy decisions. https://github.com/RUCAIBox/UserBench
- Name disambiguation: the permission-management Janus above is the Brigham et al. 2026 project. Other papers or repositories called Janus (for example preference-assistant or information-distortion work) are unrelated and must not be cited as this environment.

### Sequential privacy-study protocol evidence

- Treat feedback policy and state transition as two different estimands: `P(user_feedback_t | state_t, agent_action_t, outcome_t)` and `P(state_{t+1} | state_t, agent_action_t, feedback_t, outcome_t)`. This prevents a language model from silently inventing causal dynamics.
- Contextual Integrity supports representing subject, sender, recipient, information type, and transmission principle explicitly, with purpose, necessity, retention, processing, scope, lifetime, and task stage added for operational permission requests. https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/
- The 2017 longitudinal mobile-permissions study supports contextual history and uncertainty-triggered re-prompting, but its effect sizes and transition probabilities cannot be imported into AI-agent permissions. https://arxiv.org/abs/1703.02090
- Repeated request timing/expectation and explanations are plausible state/intervention variables, supported by field evidence, not optional prompt wording. https://www.usenix.org/conference/usenixsecurity21/presentation/cao-weicheng ; https://www.usenix.org/conference/usenixsecurity21/presentation/elbitar
- A controlled, sandboxed micro-randomized sequential study is the appropriate way to identify immediate consequences of competing agent actions while never actually disclosing participant data. https://pmc.ncbi.nlm.nih.gov/articles/PMC4732571/
- Dynamic consent literature supports scope, modification, revocation, and traceability in an authorization ledger, but comes from another domain and should not be used as behavior-effect evidence. https://pmc.ncbi.nlm.nih.gov/articles/PMC4130658/
- Canadian human-subjects planning must treat consent as ongoing and make collection, access, confidentiality, withdrawal, and retention transparent. This is a protocol requirement to take to the REB, not an ethics approval. https://ethics.gc.ca/eng/tcps2-eptc2_2022_chapter3-chapitre3.html?wbdisable=true ; https://ethics.gc.ca/eng/tcps2-eptc2_2022_chapter5-chapitre5.html

### Design safeguards justified by the protocol

- Model `allow_once`, `allow_same_scope_until_expiry`, `deny_now_reprompt_if_same_scope`, and `deny_scope_and_remember` separately; never encode `persist` as indefinite permission.
- Add `ask_explanation`, scope narrowing, edit authorization, directional override, revoke, defer, and end task as structured actions. Natural language is an optional rendering, not the label source.
- Separate simulator false allow (prediction error relative to a human) from controller/shield execution failure (violation of independently defined policy). Both must be safety gates.
- Collect logging propensity and action availability at every eligible decision point. Off-policy methods cannot recover counterfactual effects without exploration support. https://www.microsoft.com/en-us/research/publication/unbiased-offline-evaluation-of-contextual-bandit-based-news-article-recommendation-algorithms/ ; https://mlanthology.org/icml/2016/jiang2016icml-doubly/

## Provisional Synthesis

No verified off-the-shelf artifact jointly supplies individual heterogeneity, longitudinal permission scope/duration, revocation/override, safety-calibrated refusal, and human policy-ranking validation. The defensible design therefore composes an explicit permission-state engine, a calibrated structured user-feedback/transition model, an optional language renderer, and an independent safety oracle/shield.
