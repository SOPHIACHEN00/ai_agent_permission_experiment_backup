# Notes: RL Personal Assistant and S-QSTN Validation

## Local Project Evidence

- `classification_experiments/analysis-output/analysis-report.md`: participant-held-out classification is modest (best tuned point-estimate Accuracy 0.4364, Macro-F1 0.3776) and shows accuracy--over-sharing trade-offs. It is a context/prior baseline, not a safety oracle.
- `ai_agent_permission_experiment/online_bandit_experiment/RESULTS_COMPARISON_zh.md`: WP-FTS achieves 51.083% JEM and gains over matched frozen/canonical baselines, largely through persistence; false-allow remains 98.538%. Existing logs have no estimated action propensities and cannot directly support IPS/DR OPE.
- `QSTN_Longitudinal_UserSim_HCI_Rules/HCI_RULE_REGISTRY_FOR_S_QSTN_zh.md`: verified assistant errors reduce trust and increase caution/control need; ordinary denial is not necessarily a trust violation. `incorrect_explicit`, necessity, and scope correctness must be supplied by an independent task/security oracle.
- `ai_agent_permission_experiment/qstn_simulator/config/v2.0/{VERSION.md,state_schema.json,event_schema.json}`: S-QSTN v2 is a categorical bounded-memory substrate, not a calibrated probability/human-memory model. Only externally verified/synthetic-oracle events may update trust/violation state.
- `Dynamic_UserSim_Research_Design/DYNAMIC_USERSIM_DESIGN_BLUEPRINT_zh.md`: already defines the decisive separation among human preference truth, authorization truth, and security truth; recommends a POMDP, an external ledger/oracles, separate feedback and transition models, sealed fidelity tests, and a human policy-ranking gate.
- `Dynamic_UserSim_Research_Design/CMDP_REWARD_POLICY_QSTN_FEASIBILITY_zh.md`: proposes a preference-conditioned shielded CMDP with hard costs for unnecessary disclosure, scope violations, and unsafe reuse; static survey data alone are a no-go for dynamic RL claims.
- `personal_assistant_rl_plan_zh.md`: a strong, unimplemented proposal already defines an authority FSM, eight scoped high-level actions, four isolated data channels, typed Gym-style interface, reference monitor, deterministic engineering phases, matched myopic comparator, and final human policy-ranking gate. The present research task should audit/consolidate it rather than replace it.
- Code-level inventory found no implemented Gym environment, authorization service, reference monitor, scenario manifest, or public-feedback adapter. S-QSTN runtime still returns a four-choice `answer_id`; the expanded sequential feedback schema is design-only.
- S-QSTN profile-card held-out accuracy is v1 0.4889 and v2 0.3222. RulePack v2 adds state/audit infrastructure but cannot turn those values into a validated feedback oracle.

## Literature Sources

- Shao et al. (NeurIPS 2023), personalized multi-objective decision making via comparative feedback: https://proceedings.neurips.cc/paper_files/paper/2023/hash/286e7ab0ce6a68282394c92361c27b57-Abstract-Conference.html
- Achiam et al. (ICML 2017), CPO separates reward and constraints: https://proceedings.mlr.press/v70/achiam17a.html
- Alshiekh et al. (AAAI 2018), shielding blocks formally unsafe actions independently of the learned reward: https://ojs.aaai.org/index.php/AAAI/article/view/11797
- Gao et al. (ICML 2023), optimizing an imperfect proxy reward can reduce gold-standard performance: https://proceedings.mlr.press/v202/gao23h.html
- Shi et al. (EMNLP-IJCNLP 2019), user-simulator quality affects learned RL policies and should be tested directly/indirectly with humans: https://aclanthology.org/D19-1206/
- Kreyssig et al. (SIGDIAL 2018), train-one-simulator/test-another cross-model evaluation plus real-user evaluation: https://aclanthology.org/W18-5007/
- Dwork et al. (Science/STOC 2015), adaptive reuse of a holdout can overfit the holdout: https://pubmed.ncbi.nlm.nih.gov/26250683/
- Jiang & Li (ICML 2016), doubly robust OPE for sequential RL: https://proceedings.mlr.press/v48/jiang16.html
- Wang, Agarwal & Dudik (ICML 2017), IPS/DR/SWITCH OPE in contextual bandits: https://proceedings.mlr.press/v70/wang17a.html
- Malkin et al. (SOUPS 2022), Wizard-of-Oz study of runtime permissions for proactive assistants: https://www.usenix.org/conference/soups2022/presentation/malkin
- Huang et al. (AAAI 2026), simulator-generated feedback can induce strategy preference bias: https://doi.org/10.1609/aaai.v40i26.39348
- Suh et al. (2026 preprint), simulator utility is assessed by downstream performance with real humans; role-play simulator gains may not transfer: https://arxiv.org/abs/2605.09808
- Perdomo et al. (ICML 2020), a deployed model can alter its future data distribution; this helps distinguish endogenous dynamics from invalid circular evaluation: https://proceedings.mlr.press/v119/perdomo20a.html
- Gretton et al. (JMLR 2012), MMD two-sample testing: https://www.jmlr.org/papers/v13/gretton12a.html
- Rabanser et al. (NeurIPS 2019), empirical dataset-shift detection: https://proceedings.neurips.cc/paper/2019/hash/846c260d715e5b854ffad5f70a516c88-Abstract.html
- Bifet & Gavaldà (SDM 2007), ADWIN adaptive-window drift detection: https://epubs.siam.org/doi/10.1137/1.9781611972771.42

## Synthesized Findings

- A causal feedback loop (assistant action changes user caution, which changes later feedback) is the phenomenon the dynamic environment must model; it is not by itself circular validation.
- Circular validation occurs when the same fitted S-QSTN instance supplies preference feedback/reward, is optimized against, and then serves as the final evaluator or safety truth.
- Required firewalls: independent truth/oracles, frozen train-time simulator(s), untouched human evaluation, and versioned one-way data lineage.
- S-QSTN feedback may define only soft preference/control/burden reward components. It must never determine objective correctness, authorization validity, or whether disclosure is safe.
- Final claims should be based on independent oracle constraint metrics plus sealed human policy ranking; simulator scores are mechanism/stress-test evidence.

## Open Risks and Assumptions

- No human-calibrated multi-turn transition data currently exist; S-QSTN v2 cannot support a claim of calibrated trust/fatigue dynamics.
- Existing static labels identify stated policy, not task utility, real disclosure harm, or longitudinal burden.
- Existing WP-FTS logging does not estimate propensities, so future OPE requires a new randomized sequential protocol and exact propensity/action-set logging.
- `qstn_simulator/scripts/v2/compile_s_qstn_v2.py` joins list-valued audit fields, but the current compiled CSV contains character-wise semicolonation, indicating those values arrived as strings. Normalize/validate these fields before the RL logger consumes `rule_context_audit.csv`.
