# Notes: Permission Experiment Gap Positioning

Working evidence log. Final conclusions will be written to `experiment_audit.md`.

## Root synthesis evidence

### Experiment corpus

- The original benchmark predicts four permission policies: deny+persist, deny+ask-next-time, allow+ask-next-time, and allow+persist. It separates current access from future persistence.
- The frozen paper scope is survey-derived stated-policy fidelity: offline population-level prediction plus randomized sequential online-feedback replay. It explicitly disallows claims about real privacy leakage, live deployment, or task success.
- WP-FTS improves joint exact match versus the canonical offline baseline by 7.173 percentage points and versus a matched frozen control by 8.872 points; the gain is mainly persistence accuracy, while false-allow remains 98.538%.
- The latest multi-step S-QSTN/RL pilot uses 8 fixed scenarios, 26 synthetic responses, four scenario families, at most two permission questions per route, and two seeds. DDQN, MAB, and the fixed rule each complete 3/4 dev scenarios per seed. No DDQN advantage is observed.
- The current controller exposes structured state, a permission lifecycle, an authorization ledger, an external reference monitor, action masks, audit chains, and protected tool reads. Invalid actions, unauthorized effects, and adapter faults were zero in the pilot, but these guarantees are shared infrastructure rather than learned DDQN behavior.
- Critical boundary: `CLARIFY` and `PROPOSE_NARROW_SCOPE` are explicitly excluded from S-QSTN v0. Free-form ambiguous/malicious user input, scope negotiation, and human interaction are therefore not tested.

### Survey taxonomy

- Deng et al. (2025), pp. 2-3, defines Gap 1 as unpredictability of multi-step user inputs: initial guidance plus multi-turn feedback, with inadequate specification and malicious instructions as the two highlighted threat sources.
- The survey maps Gap 2 to Brain and Action. Its Action section explicitly discusses tool calls, excessive permissions, commands executed without user permission, and ToolEmu.
- Gap 3 concerns behavior inconsistency across development/deployment/execution environments; merely running training on a remote GPU is not an evaluation of Gap 3.
- Gap 4 concerns interaction with untrusted external entities. The survey's detailed taxonomy also places Agent-to-Tool action threats under Gap 2, so tool-mediated permission control spans the Gap 2/Gap 4 boundary rather than fitting cleanly into only one box.

### Candidate related work

- Direct predecessor: Wu et al., *Towards Automating Data Access Permissions in AI Agents*, IEEE S&P 2026, DOI 10.1109/SP63933.2026.00018.
- Survey-cited close works: ToolEmu (Ruan et al., ICLR 2024), TrustAgent (Hua et al., Findings EMNLP 2024, DOI 10.18653/v1/2024.findings-emnlp.585), PrivacyAsst (Zhang et al., IEEE TDSC 2024, DOI 10.1109/TDSC.2024.3372777), Formal-LLM, and InjecAgent.
- Post-survey authorization work that must be considered for a 2026 paper: Progent (arXiv:2504.11703), Conseca / Contextual Agent Security (HotOS 2025), MiniScope (arXiv:2512.11147), AgentGuardian (arXiv:2601.10440), SEAgent (arXiv:2601.11893), and AuthBench (arXiv:2605.14859).

### Provisional synthesis

- The project addresses a narrow, operational slice of Gap 1: evolving permission feedback across sequential requests. It does not yet address Gap 1's ambiguity, underspecification, adversarial user input, or free-form multi-turn language.
- Its strongest current contribution is cross-gap: convert user feedback uncertainty (Gap 1) into explicit, auditable authorization state (Gap 2) and mediate protected tool actions at the trust boundary (Gap 2/4).
- Recommended headline is not “solving Gap 1,” but “auditable sequential permission control under evolving user feedback.”
- Current evidence supports infrastructure feasibility and one stated-policy adaptation result. It does not support real privacy-harm reduction, DDQN superiority, broad human generalization, or cross-environment robustness.
