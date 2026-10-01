# Research Notes: RL Personal Assistant Detailed Design

## 1. Scope

- Current completed work: classic/semantic classification, offline MAB, online WP-FTS replay.
- New primary object: structured personal-assistant permission controller trained in an authority-aware sequential environment.
- Later objects: independent security-check LLM and final Constitutional support LLM.
- Human-side simulator: S-QSTN v2, used only within its documented auxiliary, bounded-memory, non-human-calibrated scope.
- This task produces design/protocol files only; it does not claim RL code or human-subject validation is complete.

## 2. Project Evidence Records

### E-P01 — Current data are static stated-policy vignettes

- Evidence: `ai_agent_permission_experiment/proposal/proposal_zh.md`; `ai_agent_permission_experiment/data_format_explanation_zh.md`; dataset build scripts.
- Facts: 16,361 rows, 201 participants, 65 query templates/families, four joint permission labels.
- Inference: rows can seed contexts and preference profiles, but they do not contain observed sequential transitions, revocations, expiry events, downstream task results, or real interaction order.
- Design consequence: create a versioned scenario manifest and a separate sequential environment; never call the original survey a trajectory dataset.

### E-P02 — Four survey labels encode two decisions

- Labels: deny+persist, deny+ask, allow+ask, allow+persist.
- Design mapping: denial state plus re-ask policy, or authorization grant plus one-time/reusable scope.
- Caution: “always” is stated preference, not perpetual/unbounded authorization. In ledger v0 it becomes reuse only inside a matching, explicit scope and expiry window.

### E-P03 — MAB is a preference-fidelity baseline, not a safety controller

- Evidence: completed offline ε-greedy/UCB/Thompson and online WP-FTS artifacts.
- Online WP-FTS joint exact match is about 51.08%; false-allow among relevant errors is about 98.54% in the current report.
- Consequence: preserve MAB comparison, but do not interpret exact-match reward as privacy safety or deployment readiness.

### E-P04 — S-QSTN v2 is structured but not human-calibrated

- Evidence: QSTN v2 rules/readiness documents and task plans.
- Facts: bounded event ledger, categorical private state, frozen rulepack-style behavior, fixtures/audits/tests completed.
- Limitation: no claim of calibrated transition probabilities or human-equivalent response distribution.
- Consequence: S-QSTN may support training stress tests and mechanism development; it may not be the sole reward source and sole evaluator of the same PA policy.

### E-P05 — Hidden QSTN state must not leak to PA

- Private: trust dimensions, caution, burden, internal memories/rules, unobserved profile variables, future responses/labels.
- Public: the current user utterance/event, explicit grant/edit/deny/revoke/defer/explanation request/end/timeout, and externally verified task outcome.
- Consequence: public adapter emits only observable events; leakage tests intentionally perturb private state while holding public history fixed.

### E-P06 — Existing RL documents contain two generations of design

- Newer documents specify a structured controller, typed environment, authorization service, reference monitor, public-only S-QSTN adapter and later LLM stages.
- Older `sequential_rl_cmdp_versions_zh.md` includes hidden user trust/fatigue/profile features and an old hand-weighted scalar reward.
- Consequence: the older scalar-state design is archived as an alternative, not the current contract. Hidden-state access is prohibited in the new design.

### E-P07 — Current software stack has no implemented RL environment/trainer

- Existing requirements cover numerical ML, QSTN and transformer classification; no established Gymnasium/RL trainer dependency is part of the current root project.
- Consequence: framework choice remains an implementation spike, and the project must not state that Step 3 RL has already been implemented.

## 3. External Method Evidence Records

### E-M01 — Deep value baseline

- Mnih et al. (2015) established DQN with replay and a target network for value learning from high-dimensional observations.
- van Hasselt et al. (2016) showed DQN can overestimate action values and proposed Double DQN to decouple selection from target evaluation.
- Design consequence: Double DQN is a defensible classic off-policy candidate for the fixed discrete controller action space.

### E-M02 — Policy-gradient baseline

- Schulman et al. (2017) introduced PPO with a clipped surrogate objective and multiple minibatch epochs over on-policy data.
- Design consequence: PPO provides a classic actor–critic comparison with a stochastic policy, but must receive the same valid-action mask and environment budget as Double DQN.

### E-M03 — Action masking and shielding are different

- Gymnasium documents masks for invalid actions; Tianshou documents masked observations for DQN and an `is_double` setting; RLlib documents Double-Q and action-mask support.
- Huang & Ontañón (2020) analyze invalid-action masking for policy gradients.
- Alshiekh et al. (2018) describe a shield that monitors/corrects actions to enforce a safety specification.
- Design consequence: masks remove phase/syntax-invalid choices before sampling; the independent reference monitor rechecks semantic authorization at execution time. Neither safety decision is learned from reward.

### E-M04 — Constrained RL is a later evidence-gated stage

- Achiam et al. (2017) frame policy optimization with explicit expected-cost constraints.
- Design consequence: do not call a weighted scalar penalty “CMDP.” First log cost signals, validate them, then compare scalarization with a genuine constrained optimizer such as Lagrangian PPO/CPO-style training.

### E-M05 — Simulated-user feedback is policy-dependent and simulator-bound

- MacGlashan et al. (2017) show human feedback can depend on the learner’s policy.
- Simulated-user evaluation literature treats simulator results as indicative under specified constraints, not automatically human-valid.
- Cross-simulator testing is a useful robustness check.
- Design consequence: freeze S-QSTN per run, hold it outside the policy, compare against scripted users and future human holdout, and report simulator-specific performance.

### E-M06 — Security should not rely on a learned model alone

- Saltzer & Schroeder motivate fail-safe defaults, complete mediation and least privilege.
- CaMeL demonstrates a system-layer separation of control/data flow and capability-based authorization around potentially fallible LLMs.
- Design consequence: ledger/reference monitor remains authoritative even after the security LLM exists; the security LLM may veto/rewrite/escalate but may not mint authorization.

### E-M07 — Privacy context needs more than data sensitivity

- Contextual Integrity frames information flows through actors, attributes and transmission principles.
- PrivacyLens and AgentDAM operationalize trajectory-level privacy and data-minimization failures for agents; AgentDojo/ASB add adversarial tool-use evaluation.
- Design consequence: later scenario manifests and security rules must include subject, sender/requester, recipient, data type, purpose/operation and retention/expiry—not only a “sensitive” bit.

### E-M08 — Constitutional/RM stages require independent evaluation

- Bai et al. (2022) use constitutional principles for critique/revision followed by AI-feedback preference learning.
- Gao et al. (2023) show optimizing an imperfect proxy reward can reduce ground-truth performance.
- Everitt et al. (2019) analyze incentives to tamper with reward processes.
- Design consequence: constitution, grader, reward model and final policy need version separation, KL/early-stopping controls and an independent held-out evaluator; no component may write its own reward or ledger truth.

### E-M09 — RL results need uncertainty, not a best seed

- Henderson et al. (2018), Agarwal et al. (2021), and Patterson et al. (2024) document sensitivity to seeds, hyperparameters and reporting choices.
- Design consequence: predeclare tuning budget, use identical scenario budgets/common random numbers, report all seeds, learning curves, interval estimates and robust aggregates.

## 4. Framework Evidence and Provisional Choice

| Candidate | Double DQN | masked PPO | action mask | Cost/complexity | Provisional decision |
|---|---:|---:|---:|---|---|
| Tianshou | documented `is_double=True` | available | documented observation mask for DQN; PPO adapter must be API-tested | relatively light | preferred first API spike |
| RLlib | documented `double_q` | available | documented action-mask key/example | heavy distributed stack | fallback if scaling/masking integration is cleaner |
| Stable-Baselines3 + contrib | core DQN documented as vanilla only | MaskablePPO available | PPO path convenient | would require custom Double DQN or two stacks | not the matched two-algorithm default |
| custom PyTorch | yes | yes | fully controllable | highest correctness/maintenance burden | use only for minimal reference implementation or if library behavior fails tests |

No package/version is frozen until an API spike passes: mask correctness on selection and bootstrap targets, deterministic seeds, checkpoint resume, dict observation, vectorized env, and audit callback tests.

## 5. Decision Registers

### 5.1 Resolved Decision Record

#### ADR-ACTION-V0 — Align the v0 controller with the four-choice S-QSTN interface

- Date: 2026-08-17.
- Status: amended by project-owner decision A1 and accepted for the first DDQN/PPO prototype; collaborator review still required before schema freeze.
- Decision: during the S-QSTN stage, enable only the Authorization group (`REQUEST_AUTHORIZATION`, `REQUEST_REFRESH`, `DISABLE_LOCAL_AUTHORIZATION`) and the Execution & Safety group (`EXECUTE_WITH_AUTHORIZATION`, `DENY_WITH_REASON`, `ESCALATE`).
- Amendment A1 supersedes the interim idea of folding `PROPOSE_NARROW_SCOPE` into an authorization candidate. S-QSTN v0 does not generate alternative scopes or perform scope negotiation.
- The entire Interaction & Scope group—`CLARIFY` and `PROPOSE_NARROW_SCOPE`—is deferred to a separately approved human-interaction study after ethics/IRB approval.
- Only `REQUEST_AUTHORIZATION` and `REQUEST_REFRESH` trigger the S-QSTN four-choice permission response. Other actions are environment transitions or terminal/safety actions and do not require a permission answer.
- The future human study must use separate clarification and scope-negotiation response contracts, interface-comprehension pilots, fixed candidate policies, and a new experiment ID. It must not reuse the S-QSTN four permission labels for those interactions.

### 5.2 Open Decisions Register

| ID | Decision | Recommended default | Alternatives | Latest safe decision point |
|---|---|---|---|---|
| D1 | v0 episode boundary | one bounded task/session, 3–8 decisions; ledger expires at episode end | multi-task longitudinal user session | before scenario schema freeze |
| D2 | reusable grant scope | exact context key + explicit purpose/recipient/operation, episode expiry | query-family-only; long-lived cross-session grant | before ledger fixtures |
| D3 | text encoder | structured public features only; frozen text embedding as ablation | fine-tuned encoder | before neural architecture freeze |
| D4 | RL framework | Tianshou API spike first | RLlib; custom PyTorch | before implementation sprint 2 |
| D5 | binary sequential reward | terminal 1 only for valid-authority task/fallback success; otherwise 0 | per-step exact-match parity only | before trainer tests |
| D6 | blocked hard violation | terminate episode with 0 in v0 and log violation | block then continue | before transition contract freeze |
| D7 | S-QSTN role | training robustness source only until human calibration | primary simulator | before S-QSTN integration |
| D8 | first constrained method | scalar penalty diagnostic, then Lagrangian PPO; CPO only if justified | CPO directly | after cost-signal validation |

## 6. Source URLs Retained for Final Document

- Gymnasium custom environments and action masking: https://gymnasium.farama.org/main/tutorials/environment_creation/ ; https://gymnasium.farama.org/tutorials/training_agents/action_masking_taxi/
- Tianshou DQN parameters: https://tianshou.org/en/stable/03_api/highlevel/params/algorithm_params.html
- RLlib algorithms/action masking: https://docs.ray.io/en/master/rllib/rllib-algorithms.html
- Stable-Baselines3 DQN: https://stable-baselines3.readthedocs.io/en/v2.7.0/modules/dqn.html
- DQN: https://www.nature.com/articles/nature14236
- Double DQN: https://doi.org/10.1609/aaai.v30i1.10295
- PPO: https://arxiv.org/abs/1707.06347
- Invalid action masking: https://arxiv.org/abs/2006.14171
- CPO: https://arxiv.org/abs/1705.10528
- Shielding: https://doi.org/10.1609/aaai.v32i1.11797
- Constitutional AI: https://arxiv.org/abs/2212.08073
- Reward overoptimization: https://proceedings.mlr.press/v202/gao23h.html
- Policy-dependent feedback: https://arxiv.org/abs/1701.06049
- Reward tampering: https://arxiv.org/abs/1908.04734
- PrivacyLens: https://arxiv.org/abs/2409.00138
- AgentDAM: https://arxiv.org/abs/2503.09780
- AgentDojo: https://arxiv.org/abs/2406.13352
- CaMeL: https://arxiv.org/abs/2503.18813
- NIST Privacy Framework: https://www.nist.gov/privacy-framework/privacy-framework
- RL evaluation: https://doi.org/10.1609/aaai.v32i1.11694 ; https://arxiv.org/abs/2108.13264 ; https://jmlr.org/papers/v25/23-0183.html

## 7. Fresh-Reader Self-Test

因本次学术研究工作流不自动委派给 sub-agent，本轮采用“关闭前文后按 reviewer 问题定位”的人工 fresh-reader 检查。

| Reader question | Expected location | Result |
|---|---|---|
| 现在究竟训练什么，不训练什么？ | §0, §3 | PASS：structured controller 与 later LLM RL 已分开 |
| survey 四标签如何连接 ledger？ | §6.6, §7.2.1 | PASS：grant 与 re-ask preference 分型；预测不 mint authority |
| 为什么 0/1 reward 不是旧 MAB reward？ | §10.1–10.2 | PASS：P0 parity 与 S0 sequential 分开 |
| RL 是否真的必要？ | §1.3, §13.1–13.3, Gate G2 | PASS：`γ=0` 与 history/ledger ablation 可否证 |
| S-QSTN 会不会自我训练、自我评价？ | §9 | PASS：truth/learning/evaluation/governance 四道 firewall |
| privacy rules 是现在还是以后用？ | §5 | PASS：hard authorization policy 与 later constitution 分开 |
| DDQN/PPO 如何公平比较？ | §11.2, §14 | PASS：相同 interaction/search/eval budget 与所有 seeds |
| 什么情况下不能继续下一阶段？ | §20 | PASS：每阶段有 go/no-go gate |
| 还有哪些决定没有冻结？ | §25–26 | PASS：12 项 open decisions，6 项 immediate decisions |
| reviewer 可以接受哪些 claim？ | §24 | PASS：simulation/human/security claims 分层 |

## 8. Structural Validation

- Main design: approximately 3,206 lines / 96k+ UTF-8 characters after adding the concrete observation example.
- Code fences: even count; four Mermaid blocks.
- Encoding: no replacement characters.
- Local evidence map: 10/10 referenced project files exist.
- `TBD` tokens appear only in the explicitly labeled future results template, not as hidden design gaps.
- Known unresolved items are centralized in §25 instead of silently defaulted.
