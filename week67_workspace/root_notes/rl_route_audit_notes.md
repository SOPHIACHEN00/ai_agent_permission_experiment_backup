# Notes: RL Personal Assistant 后续路线审计

## Project Evidence

- `ai_agent_permission_experiment/proposal/proposal_zh.md:7-24`：MAB 已完成；CMDP/RL、security sub-agent、Constitutional AI 是后续阶段。当前 0/1 reward 是 stated-policy exact match，不表示 privacy、task utility 或 prompt cost。
- `ai_agent_permission_experiment/proposal/proposal_zh.md:132-138`：后续核心问题是带历史与风险/提示预算的 sequential policy，以及 security sub-agent/constitutional feedback 是否减少 high-risk errors。
- `ai_agent_permission_experiment/proposal/proposal_zh.md:209-244`：标书要求 reward 与 privacy/prompt constraints 分离，security sub-agent 是额外 risk assessor，不替代 controller。
- `ai_agent_permission_experiment/proposal/proposal_zh.md:359-380`：CMDP/RL 达成标准包括状态、动作、转移、task reward、privacy/prompt costs、budgets、无约束/penalty/constrained/rule-gate baselines。
- `personal_assistant_rl_plan_zh.md:324-345`：现有计划已经把高维 structured state 的候选算法写成 masked DQN/PPO；只有存在非零 residual cost 时才转 primal-dual/CPO-style。
- `personal_assistant_rl_plan_zh.md:279-322`：主 deep RL 前应先有 deterministic environment、scripted user、exact DP/tabular Q、matched myopic、reference monitor 与 UserSim release gate。
- `proposal_review.md:53-134`：必须区分高层 permission controller、低层 support LLM、security critic 与 reward model，不能把不同模型和不同 action space 混成一个“RL agent”。
- 文档一致性风险：`reward_function_design_zh.md:23-33` 仍描述旧的多项手写 scalar reward；当前 proposal 则冻结 `r=1[a=y]`。进入 RL 前需标记前者为 archive/alternative，并显式 version `reward_v0_binary`，否则 reviewer 会看到两套互相冲突的“current reward”。

## Literature Evidence

### ER-20260815-dqn-01
- Source: Mnih et al., *Human-level control through deep reinforcement learning*, Nature 2015. https://www.nature.com/articles/nature14236
- Type: peer-reviewed primary paper.
- Supports: DQN 是以深度网络近似 action value 的经典离散动作 deep RL baseline。
- Limitation: Atari 视觉控制与本项目的 structured permission state 不同；不能据此证明 DQN 必然优于 simpler baselines。

### ER-20260815-ddqn-02
- Source: van Hasselt et al., *Deep Reinforcement Learning with Double Q-Learning*, AAAI 2016. https://ojs.aaai.org/index.php/AAAI/article/view/10295
- Type: peer-reviewed primary paper.
- Supports: vanilla DQN 可能有 action-value overestimation；Double DQN 是更稳妥的 DQN-family implementation candidate。

### ER-20260815-actorcritic-03
- Source: Mnih et al., *Asynchronous Methods for Deep Reinforcement Learning*, ICML 2016. https://proceedings.mlr.press/v48/mniha16.html
- Type: peer-reviewed primary paper.
- Supports: Actor–Critic 是算法家族；A3C 是其中一个具体经典实例，不能把“actor-critic”当成完整可复现实验名称。

### ER-20260815-ppo-04
- Source: Schulman et al., *Proximal Policy Optimization Algorithms*, arXiv 2017. https://arxiv.org/abs/1707.06347
- Type: canonical preprint.
- Supports: PPO 是较易实现和调试的 actor–critic/policy-gradient representative，适合作为与 DQN 不同算法家族的 baseline。
- Limitation: on-policy、通常比 replay-based DQN 消耗更多 environment interactions；比较需匹配 interaction budget 并单独报告 wall-clock。

### ER-20260815-repro-05
- Source: Henderson et al., *Deep Reinforcement Learning That Matters*, AAAI 2018. https://ojs.aaai.org/index.php/AAAI/article/view/11694
- Type: peer-reviewed primary paper.
- Supports: deep RL 结果对实现、超参数、环境随机性和 seed 敏感；必须用多 seed、标准化预算和不确定性报告。

### ER-20260815-shield-06
- Source: Alshiekh et al., *Safe Reinforcement Learning via Shielding*, AAAI 2018. https://ojs.aaai.org/index.php/AAAI/article/view/11797
- Type: peer-reviewed primary paper.
- Supports: hard safety specifications 应由 action-execution 前的 shield/reference monitor 保证，不能只靠负 reward 或事后 critic。

### ER-20260815-cpo-07
- Source: Achiam et al., *Constrained Policy Optimization*, ICML 2017. https://proceedings.mlr.press/v70/achiam17a.html
- Type: peer-reviewed primary paper.
- Supports: reward 与 safety costs/constraints 分离比把全部目标压成一个 scalar reward 更适合安全任务。

### ER-20260815-privacybench-08
- Sources: PrivacyLens (NeurIPS 2024) https://proceedings.neurips.cc/paper_files/paper/2024/file/a2a7e58309d5190082390ff10ff3b2b8-Paper-Datasets_and_Benchmarks_Track.pdf ; AgentDAM (NeurIPS 2025) https://proceedings.neurips.cc/paper_files/paper/2025/hash/c9826b9ea5e1b49b256329934a578d83-Abstract-Datasets_and_Benchmarks_Track.html ; AgentDojo (NeurIPS 2024) https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
- Type: peer-reviewed benchmarks.
- Supports: privacy norm awareness、data minimization、tool-agent prompt injection 应进入 scenario/rule taxonomy、held-out tests 和 runtime enforcement，而非只作为训练后 prompt。
- Limitation: 三个 benchmark 的 domain/threat model 不等于本项目；可借用 ontology/evaluation pattern，不能直接复制为 ground truth。

### ER-20260815-cai-09
- Source: Bai et al., *Constitutional AI: Harmlessness from AI Feedback*, 2022. https://arxiv.org/abs/2212.08073
- Type: primary preprint.
- Supports: Constitution/rules 在 supervised critique-revision 和后续 preference/RL 阶段之前确定；“先 fine-tune，之后再找 rules”与该 recipe 顺序相反。

### ER-20260815-rmoveropt-10
- Source: Gao et al., *Scaling Laws for Reward Model Overoptimization*, ICML 2023. https://proceedings.mlr.press/v202/gao23h.html
- Type: peer-reviewed primary paper.
- Supports: learned/proxy reward 被过度优化时，ground-truth performance 可能下降；reward tuning 必须只用 train/validation，并保留独立 safety/human evaluation。

## Synthesis

### Conditional verdict

- “先做一到两个经典 deep RL 算法”合理，但它是 Step 3A 的 engineering/method baseline，不是研究贡献本身。
- “暂时用 0/1 reward”仅在两个条件下合理：明确标为 `reward_v0`；episode 中存在真正的 delayed dependency。若每一步仍独立做 `1[action==survey label]`，则只是 neural contextual bandit 包在 episode 外壳中，不能证明 RL 的长期价值。
- 最合适的双算法不是“DQN + 泛称 actor-critic”，而是 `masked Double DQN + masked PPO`；前者代表 off-policy value-based，后者代表 actor–critic。A3C/A2C 可作为术语确认后的替代，但不建议同时实现三种。
- LLM fine-tuning 放在 structured controller 验证之后合理；但 privacy/security rule pack 必须在 SFT 数据生成、动作合法性、测试集构建之前冻结第一版。
- rich reward/reward model 可以后做；reward semantics、primary metrics、cost channels、日志和 sealed test 必须现在定义。否则“最后调 reward”会变成看到结果后移动目标。

### Three route options

1. **Algorithm-first linear route**: DQN/PPO + 0/1 → LLM FT → rules → reward tuning. Fastest, but methodology risk high: rules/reward define the environment too late, early results不可比较。
2. **Recommended two-track route**: minimal rule/authority scaffold + binary-reward deep-RL pilot in parallel; then calibrated costs/reward and LLM layers. Preserves speed and research validity.
3. **LLM-first constitutional route**: immediately fine-tune/RL the LLM. Highest compute/data confounding, weakest causal attribution; not recommended now.

### Falsification criterion for the first deep-RL study

If DQN/PPO do not outperform a matched myopic `gamma=0` policy or a no-history ablation on delayed-outcome scenarios under the same observation/action/monitor and interaction budget, the evidence does not justify deep sequential RL for that formulation. Report the negative result and revise the state/transition design rather than tuning until positive.

## Devil's-Advocate Audit

### Strongest counterclaim

The permission problem may remain a contextual classification/bandit problem. If the next user response and terminal outcome are conditionally independent of earlier assistant actions once the current context is known, deep RL adds variance and tuning burden without adding a valid sequential estimand.

### Major validity threats in the unmodified route

1. Per-turn `1[action == label]` can make an episodic implementation a neural contextual bandit rather than a sequential-control experiment.
2. Adding privacy rules only after LLM fine-tuning changes the action legality, labels and evaluation target after training, preventing clean comparison.
3. Tuning reward after examining final results risks post-hoc objective selection; the schema, primary metrics and sealed test must be fixed before training.
4. Using S-QSTN as the training transition model, reward source and only evaluator creates simulator exploitation/circular validation.
5. Treating the structured permission controller and the token-generating LLM as one RL policy obscures which action space, feedback and safety boundary produced an effect.
6. A more complex neural policy may appear better only because it receives more history, a different action catalog, more environment interactions or a larger tuning budget.

### Residual risks after revision

- S-QSTN human fidelity remains unproven until an independent release gate is passed.
- A binary terminal success signal may be sparse and may require curriculum/reward diagnostics, but shaping must remain versioned and cannot leak oracle truth into policy observations.
- Double DQN/PPO conclusions may remain implementation-sensitive; multi-seed uncertainty and matched budgets are mandatory.
- External privacy rules/benchmarks supply ontology and scenarios, not ground truth for this authority model.

### Audit verdict

**REVISE / Conditional Go.** No fatal conceptual flaw remains if the minimal rule/authority scaffold is frozen first, 0/1 is limited to a versioned pilot, delayed dependence is explicitly tested, and S-QSTN is separated from final evaluation.

## Round 2: General Project Description and Five-Slide Audit

### What the new material clarifies

- The high-level five-step programme is coherent: stated-policy baseline → sequential permission control → learned security critic → Constitutional response alignment.
- The slides describe two different targets:
  - Figures 1–2: safe support-response generation (requesting full SSN vs proposing an alternative).
  - Figures 3–5: response-level Constitutional SFT/RLAIF/RM/RL.
- None of the five figures defines the Step-3 permission MDP, authority ledger, tool transition, or structured action space. Therefore they cannot by themselves justify applying PPO directly to the LLM at Step 3.

### Four distinct learnable/non-learnable objects

1. Step-3 structured permission controller: public state/history/ledger → ask, clarify, narrow, deny, execute-with-auth, escalate; candidate deep-RL algorithms are Double DQN/PPO.
2. Step-4 security sub-agent: request + candidate action/output → risk/critique/rewrite/escalation; trained from independent security labels/taxonomy.
3. Step-5 support LLM: conversation + approved structured action → natural-language response; Constitutional SFT/RM/RL is token/response-level.
4. Reference monitor/authorization service: deterministic enforcement; never learned and never replaced by a grader.

### Empirical bridge from current results

- Online WP-FTS JEM is 51.083% vs canonical offline 43.911% (+7.173 pp), mostly from persistence; stated-preference false-allow remains 98.538%.
- Therefore MAB is evidence that same-user feedback can improve personalization, but also direct evidence that preference matching is not a sufficient safety controller.
- The MAB four actions (`deny+persist`, `deny+ask`, `allow+ask`, `allow+persist`) do not equal the planned PA structured actions. A direct `r=1[action==survey label]` is undefined unless a frozen mapping is supplied.

### S-QSTN-specific finding

- S-QSTN v2 is a rule-informed bounded-state auxiliary respondent, not a human-calibrated oracle.
- Verified PA errors/scope violations can produce categorical caution; that endogenous transition is scientifically usable.
- Its private trust/caution/burden state must not enter PA observation or reward. Only public responses/events may enter the controller.
- S-QSTN may provide training transitions but cannot be the sole final judge. Sealed task/security truth and human/expert holdouts are required.

### Slide-level validity warnings

- Calling the alternative “order number + last two phone digits” safe is context-dependent; without a service-specific necessity/authorization policy it is only a candidate safer alternative, not objective ground truth.
- A constitution-following LLM grader and a reward model trained on that grader have correlated failure modes. The same judge cannot be the only safety evaluator.
- Constitutional AI's original recipe contains supervised critique/revision followed by AI-feedback preference modelling and RL. This supports Step 5, not Step 3 permission control.

### Updated verdict

The overall five-step research programme is stronger than the collaborator's abbreviated implementation sequence. Begin Step 3A now, but train a structured permission controller rather than the final LLM. Establish rule/authority semantics before this training; reserve Constitutional LLM RL for Step 5. The correct architecture is layered, not one monolithic RL agent.
