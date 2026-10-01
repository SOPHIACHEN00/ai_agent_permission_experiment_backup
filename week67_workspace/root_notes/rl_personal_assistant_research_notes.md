# Notes: RL Personal Assistant 与循环验证风险

## Project evidence

- `personal_assistant_rl_plan_zh.md` 已给出 authority-aware structured controller、authorization service、reference monitor、typed environment、CMDP costs、UserSim release gates 和 matched-myopic comparison 的完整方向。
- S-QSTN v2.0 的 `state_schema.json` 将内部状态限定为由 externally verified events 触发的 bounded categorical state，并明确 ordinary denial 不能更新 violation/trust。
- S-QSTN v2.0 的 `security_behavior_rules.json` 标记为 `stateful_directional_only`，没有 calibrated probabilities 或 numeric behavior weights；`pa_rl_observation`、`pa_rl_reward` 和 `pa_tool_policy` 均在 forbidden targets 中。
- 因此，S-QSTN v2.0 当前可用于 deterministic engineering diagnostic 和 qualitative stress testing；在 longitudinal human calibration、sealed fidelity 与 policy-ranking gates 通过前，不应作为 human-faithful RL environment。
- 已完成的 classification/MAB 数据可继续作为 stated-preference baselines、population priors 与 comparator，不构成 action→feedback→state transition 的纵向真值。

## Verified literature evidence

1. Shi et al. (EMNLP-IJCNLP 2019)指出 simulator 质量直接影响其训练出的 RL policy，并同时使用 automatic、human direct 和 human indirect/downstream evaluation：
   https://aclanthology.org/D19-1206/
2. Kreyssig et al. (SIGDIAL 2018)采用 cross-model evaluation，并最终让 simulator-trained policies 与真人交互：
   https://aclanthology.org/W18-5007/
3. SimulatorArena (EMNLP 2025)把 message-level behavioral similarity 与 simulator 对 assistant ranking 是否符合 human judgment 分开评估；其最好结果并非完美一致，因此 simulator ranking 不能被视为真人真值：
   https://aclanthology.org/2025.emnlp-main.1786/
4. Liu et al. (ACL 2023)显示单一 simulator 会带来过拟合风险，多 simulator 训练有助于鲁棒性，但仍需 human evaluation：
   https://aclanthology.org/2023.acl-long.1/
5. Suh et al. (2026 preprint)控制其他变量、只改变 training simulator，并以 283 人真人 study 测量 downstream utility；role-play simulator 的训练收益未迁移，而 human-grounded simulator 更好，支持 cross-simulator + real-human downstream evaluation：
   https://arxiv.org/abs/2605.09808
6. Zhou et al. (2026 preprint)在 agentic tasks 上以 451 名真人比较 31 个 simulator，发现 simulator 往往过度合作、反馈过度正面并形成 easy mode，支持 human validation 与 OOD/robustness gate：
   https://arxiv.org/abs/2603.11245
7. Alshiekh et al. (AAAI 2018)用独立 shield 检查并修正会违反 specification 的 action，支持将 hard authorization invariants 放在不可训练 reference monitor 中：
   https://ojs.aaai.org/index.php/AAAI/article/view/11797
8. Achiam et al. (ICML 2017)支持把 reward 与 safety-related costs/constraints 分开，而不是用一个 scalar reward 让任务收益补偿安全代价：
   https://proceedings.mlr.press/v70/achiam17a.html
9. Gao et al. (ICML 2023)实证展示过度优化 imperfect reward proxy 会降低 ground-truth performance，直接对应“优化 S-QSTN 回答而非真实用户结果”的 Goodhart 风险：
   https://proceedings.mlr.press/v202/gao23h.html
10. Janner et al. (NeurIPS 2019)说明 model-generated data 的收益与 model bias 有权衡，并以从真实数据分支的短 rollout 限制误差累积；在本项目中只作 user-model rollout 设计的类比证据：
    https://proceedings.neurips.cc/paper/2019/hash/5faf461eff3099671ad63c6f3f094f7f-Abstract.html

## Synthesis

### The key distinction

`PA action -> user becomes more cautious -> future answer changes` is ordinary endogenous environment dynamics, not circular validation by itself.

It becomes circular when one or more of the following hold:

1. PA or S-QSTN itself decides whether the PA made a mistake;
2. S-QSTN feedback is both the training reward and the safety/correctness ground truth;
3. PA and S-QSTN parameters update simultaneously and co-adapt;
4. the same S-QSTN version/data is used for policy selection and final evaluation;
5. the researcher claims human improvement from simulator-only gains.

### Proposed separation

- **Safety/authority truth:** versioned scenario manifest, authorization ledger, reference monitor, and independent postcondition evaluator.
- **User-response model:** frozen, versioned S-QSTN that receives only verified public events and generates public structured feedback; it is a stochastic transition model, not a safety oracle.
- **Training objective:** task outcome and measurable burden/exposure costs from the environment; S-QSTN feedback is one noisy soft-preference channel, not the sole reward.
- **Evaluation truth:** sealed human cohort plus disjoint held-out simulator(s); the training S-QSTN never judges its own trained policy.

### Formal anti-coadaptation condition

Within experimental generation `k`, freeze simulator parameters `phi_k` while optimizing policy `theta`:

`d phi_k / d theta = 0`.

State transitions may still depend on PA actions, which is the intended MDP. If new human data are collected, update only between versioned rounds:

`freeze S_k -> train pi_k -> freeze pi_k -> collect new human calibration data -> build S_{k+1}`.

The sealed human evaluation set is never used in this update loop.

### Reviewer-facing falsification rule

If simulator gains fail cross-simulator tests, policy-ranking agreement, or final human evaluation, the result must be reported as simulator exploitation / simulation-only engineering evidence, not human privacy-preference improvement.

