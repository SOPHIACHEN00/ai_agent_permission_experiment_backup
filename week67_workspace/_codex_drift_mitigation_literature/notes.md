# Notes: PA–S-QSTN 闭环漂移缓解

## Search protocol

- 日期：2026-08-08
- 类型：目标导向、多来源原始文献检索；不是 PRISMA 式系统综述或 meta-analysis。
- 来源优先级：PMLR、NeurIPS proceedings、ACL Anthology、JMLR、AAAI/IJCAI/RSS、PubMed/期刊官方页、arXiv 原始预印本。
- 排除：博客、新闻、厂商解释文、仅重复已有原始论文主张的综述。
- 去重：标题规范化 + DOI/arXiv ID + 作者/年份；正式版本优先于预印本。

## Query families

1. `multi-agent reinforcement learning non-stationarity replay fingerprint two timescale`
2. `model-based reinforcement learning compounding error short rollout model uncertainty conservative offline RL`
3. `user simulator assistant reinforcement learning human evaluation policy ranking simulator utility`
4. `performative prediction preference drift non-stationary bandit change point active preference learning`
5. `micro-randomized trial propensity off-policy evaluation doubly robust sequential`
6. `safe reinforcement learning shielding runtime assurance constrained policy optimization`

## Core evidence retained

### Coupled learning and endogenous distribution

- Borkar (1997), *Stochastic Approximation with Two Time Scales*, DOI 10.1016/S0167-6911(97)90015-3: theoretical basis for fast/slow update separation.
- Foerster et al. (2017), *Stabilising Experience Replay for Deep Multi-Agent Reinforcement Learning*: version fingerprints and importance weighting for obsolete replay.
- Perdomo et al. (2020), *Performative Prediction*: deployed policy changes the future data distribution; performative stability is not external validity.
- Nekoei et al. (2023), *Multi-Timescale Learning*: sequential/multi-timescale updates reduce decentralized MARL non-stationarity under stated assumptions.
- Fudenberg & Levine (1993), *Self-Confirming Equilibrium*: an on-path stable system can remain wrong on unvisited actions/states.

### Learned environment and simulator exploitation

- Ross et al. (2011), DAgger: collect expert labels on learner-induced states; synthetic self-labeling is not a substitute.
- Janner et al. (2019), MBPO: short model rollouts branched from real states reduce model-bias accumulation.
- Chua et al. (2018), PETS: probabilistic ensemble plus trajectory sampling propagates model uncertainty.
- Yu et al. (2020), MOPO: penalized model MDP/pessimism under distribution shift; needs meaningful uncertainty bounds.
- Yu et al. (2021), COMBO: conservative value regularization for out-of-support model rollouts without relying solely on explicit uncertainty.
- Talvitie (2017), self-correcting models: one-step error alone is insufficient for judging long rollout quality.
- Eysenbach et al. (2022), joint model-policy optimization: policy actively discovers small model errors; low prediction MSE need not imply good control.
- Rajeswaran et al. (2017), EPOpt; Rigter et al. (2022), RAMBO-RL: worst-tail/adversarial model robustness, but not human-validity proof.

### Preference drift and causal evaluation

- Sadigh et al. (2017): active pairwise trajectory comparisons for preference learning.
- Shao et al. (2023): comparative feedback for multi-objective user preferences; privacy authorization must remain non-compensable.
- Klasnja et al. (2015): micro-randomization estimates proximal and time-varying effects at eligible decisions.
- Besson et al. (2022): change-point detection plus forced exploration/restart for piecewise stationary bandits.
- Li et al. (2011), Wang et al. (2017), Jiang & Li (2016): randomized logs, IPS/DR/SWITCH/sequential DR require known propensities and overlap.
- Kallus & Zhou (2022): stateful offline policy evaluation; confounding error may persist rather than attenuate with horizon.

### Independent safety and human validation

- Alshiekh et al. (2018): runtime shield enforces formal safety constraints independently of learned reward.
- Achiam et al. (2017): explicitly separate reward and constraints in constrained policy optimization.
- Dou et al. (2025), *SimulatorArena*: user simulator validity should include alignment with human assistant judgments/rankings.
- Suh et al. (2026), arXiv preprint: simulator quality should be measured by downstream assistant performance with real humans; role-playing simulators did not yield the same gains as human-grounded simulators.

## Synthesized design principle

令闭环偏差近似满足 `d_(t+1) <= kappa*d_t + epsilon_t`：

- 冻结/双时间尺度/阻尼降低 `kappa`；
- 真人校准、DAgger-like 真人标注、版本化 replay 降低 `epsilon_t`；
- 短 rollout 与周期 re-anchor 限制误差传播时间；
- OOD/保守价值/worst-tail 训练降低 simulator exploitation；
- reference monitor/shield 限制即使漂移发生也不能转化为越权执行；
- 新真人 cohort 验证负责判断外部效度，不能由稳定性指标替代。

## Project-specific blockers found by direct inspection

1. 当前 S-QSTN v2 仍为 `stateful_directional_only` / `human_calibration=not_claimed`，只能支持 synthetic engineering diagnostics。
2. `StateStoreV2` 对需要 verified source 的事件只拒绝 `source=unknown`；若集成层把 PA 派生事件写成 `runner_derived + verified`，会污染 trust/consent 状态。
3. fixture builder 先摄取全部事件再构造较早 turn 的 view，可导致 future-state leakage。
4. persistent verified events 无 visible-event 数量上限；部分负态缺少明确恢复到 neutral/active 的闭环，可能形成滞后或吸收态。
5. 当前 WP-FTS 日志 `propensity_draws=0`，不满足 IPS/DR OPE 的行为概率要求。

## Final synthesis

- 主实验：冻结 S-QSTN 参数，只允许预注册 state transitions；PA 在独立 shield 下学习。
- rollout：从真人校准状态分叉 1–3 步作为起点，按 horizon sweep 决定上限，不做无限 free-run。
- 数据：安全动作集内 micro-randomized human calibration，逐 turn 记录 propensity、available actions、版本和 provenance。
- 鲁棒性：跨模型/规则/数据 split 的 simulator ensemble；高分歧/OOD 时 ASK/DENY/escalate；对低支持动作使用保守价值。
- 偏好：时间衰减/滑窗/变点重置 + 周期性 pairwise re-elicitation；授权 ledger 不从隐式偏好推断。
- 验证：冻结 simulator 和 PA 后，用独立真人 cohort 做 counterbalanced pairwise policy ranking；失败只能降级为 simulation claim。
