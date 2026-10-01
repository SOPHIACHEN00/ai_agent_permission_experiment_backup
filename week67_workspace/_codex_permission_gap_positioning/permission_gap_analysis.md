# Automating Permission 与 Agent Privacy/Security Gaps：实验定位与写作建议

审计日期：2026-09-27

## 结论先行

**你们的工作与 Gap 1 有实质联系，但不应写成“我们正在解决 Gap 1”。** 更准确的两层判断是：

1. **偏好学习层**：online WP-FTS 与 multi-step permission feedback 实验，解决了 Gap 1 的一个窄子问题——用户特定的权限偏好会随着历史反馈逐步显露，agent 如何据此调整后续授权决策。
2. **系统执行层**：authorization ledger、reference monitor、action mask 和 audit chain 所解决的核心问题，按 Deng et al. survey 的正式章节分类，首先属于 **Gap 2 / Threats on Action / Agent2Tool**：如何避免 agent 在未经用户许可时执行高风险工具动作，并使执行过程可审计。

因此，最稳妥的整体定位是：

> **Gap 2-centered auditable sequential authorization, with a bounded Gap 1 component for evolving user permission feedback.**

中文可写成：

> 本工作以可审计的 Agent-to-Tool 运行时授权为核心，并研究其中一个受限的输入不确定性问题：agent 如何根据多步任务中逐步出现的用户权限反馈，更新个体化授权策略。

这比“解决 Gap 1”更准确，也比仅称作 permission prediction 更能概括当前的系统设计。

## 1. 为什么它既涉及 Gap 1，又更应以 Gap 2 为主

Survey 的 Introduction 将 Gap 1 定义为多步用户输入不可预测，包括初始指令、执行中反馈、描述不足及恶意指令；但其正式 taxonomy 将 `Brain + Action` 映射到 Gap 2，并在 `Agent2Tool Threats` 中直接讨论 excessive tool permissions 和未获用户许可的高风险命令。因此需要区分“权限信息从哪里来”和“权限在哪里被执行”：

| 研究问题 | 对应 gap | 你们当前覆盖程度 |
|---|---|---|
| 用户的权限偏好未知，并在多轮历史中逐步显露 | Gap 1 | **部分覆盖**：四类、结构化、历史依赖的 permission feedback |
| agent 如何把权限状态转成可检查的工具动作 | Gap 2 | **当前主贡献**：ledger、reference monitor、action mask、审计链 |
| 同一策略在本地、远端、浏览器、沙箱等环境中是否一致 | Gap 3 | **未作为实验变量研究** |
| 不可信工具、其他 agent 或外部 memory 是否突破授权边界 | Gap 4；工具部分与 Gap 2 有重叠 | **只覆盖受控工具边界，尚未做一般不可信实体实验** |

所以，如果论文主对象是完整的 permission controller，应把 **Gap 2 放在主位，Gap 1 放在第二研究轴**。如果某一篇短文只写 WP-FTS sequential personalization，那么可以将它定位为 Gap 1 的窄子问题，但仍不能泛化到完整 Gap 1。

## 2. 当前实验究竟覆盖了 Gap 1 的哪一部分

已经覆盖的是：

- 同一用户过去的 permission feedback 会影响未来决策；
- `allow_once`、`allow_reuse`、扩大 scope 后拒绝、disable 后 refresh 等状态具有跨步后果；
- online replay 能比较“更新个人 posterior”和“保持 frozen”之间的差异；
- multi-step controller 把历史回答、当前授权状态和合法动作集合纳入决策。

尚未覆盖的是：

- 含糊、不完整或相互冲突的开放式自然语言指令；
- 用户在任务中途自由修改目标、recipient、purpose、retention 或 scope；
- 恶意用户输入、prompt injection 或诱导危险代码执行；
- noisy、missing、delayed 或自相矛盾的真人反馈；
- clarification 与 scope negotiation。当前 v0 明确排除了 `CLARIFY` 和 `PROPOSE_NARROW_SCOPE`，见 [RL 设计 README](D:/Study/Graduate_Study_UofG/Research/paper/Week67/RL_Personal_Assistant_Design/README.md:35)；
- live human sequential validation。当前反馈是 synthetic、预采集并在训练时 cache-only replay。

因此，推荐使用下面的限定语：

> We operationalize one bounded class of multi-step input uncertainty: history-dependent categorical authorization feedback during tool-mediated execution.

不要写：

> We solve unpredictable multi-step user input for AI agents.

## 3. 现有结果能够支持什么

### 3.1 Online WP-FTS：支持“个体化历史反馈有用”，不支持“系统更安全”

相对 matched frozen control，WP-FTS 的 joint exact match 提高 **8.872 percentage points**，macro-F1 提高 **9.252 points**，persistence accuracy 提高 **10.339 points**。改善主要来自“未来能否复用授权”的预测，而不是当前 access 判断，见 [online MAB 结果](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/online_mab/01_RESULT_SUMMARY_zh.md:37)。

但 false-allow 仍为 **98.538%**；该结果不能解释为 privacy leakage 减少、真实授权安全性提升或可部署性。这一阶段最合适的结论是：

> Sequential personal feedback improves stated-policy fidelity, especially persistence prediction, under controlled replay.

### 3.2 Multi-step cache r2：支持集成与执行约束，不支持 DDQN 优越性

最新 r2 包含 8 个固定 graph、26 个经过验证的 synthetic responses、4 个 dev scenarios 和两个 learner seeds。DDQN、WP-FTS 与 fixed rule 在两个 seeds 上都完成 **3/4** 场景；`scope_denial` 在冻结回答下没有成功路线，因此当前没有 DDQN 相对 MAB/rule 的优势，见 [matched comparison](D:/Study/Graduate_Study_UofG/Research/paper/Week67/RL_Personal_Assistant_Design/experiments/2026-09-23_sqstn_rl_integration_v0/multistep_cache_pilot_r2/2026-09-23--sqstn-multistep-cache--r2--matched-comparison.md:53)。

测试轨迹中 invalid action、unauthorized effect 和 adapter fault 均为 0。这支持“共享的 ledger/reference-monitor 执行路径在这些 fixtures 中正常工作”，但**安全性主要来自共同的 enforcement kernel，不是 DDQN 学会了安全策略**。

### 3.3 建议把三类指标分开

| 维度 | 当前是否有证据 | 推荐指标/表述 |
|---|---|---|
| Preference fidelity | 有 | JEM、macro-F1、access/persistence accuracy；只代表 stated-policy match |
| Authorization correctness | 有限、受控场景 | scope/lifecycle validity、blocked unauthorized effects、audit completeness |
| Privacy outcome | 尚无 | 实际数据暴露、purpose/recipient violation、harm、data minimization |

这三者不能互相替代。特别是 prediction 更准，不等于真实 privacy harm 更低。

## 4. 如果现在开始写论文，建议怎样讲故事

### 推荐问题定义

> Can an AI agent adapt to sequential, user-specific permission feedback while an independent authorization layer ensures that protected tool effects occur only under valid, scoped, and auditable authority?

### 推荐贡献结构

1. **Problem formulation**：分离 preference、authority 和 effect。用户“可能愿意”不等于系统“已经获得有效授权”。
2. **Sequential personalization**：从 population prior 到 per-user posterior，学习 access × persistence 的四类策略。
3. **Auditable enforcement**：结构化 action space、authorization ledger、complete-mediation reference monitor、public/private/oracle separation。
4. **Controlled evaluation and negative findings**：报告 WP-FTS 的 persistence gain，同时诚实呈现 false-allow、DDQN tie、rule ceiling 与 synthetic/cache-only 边界。

### 推荐标题方向

- *From Permission Prediction to Auditable Sequential Authorization for AI Agents*
- *Learning When Authorization Persists: Sequential Permission Control for Tool-Using Agents*
- *Auditable Permission Lifecycles under Evolving User Feedback*

### 一段可以直接发展成 Introduction 的定位

> Existing work either predicts user permission preferences or constrains risky agent actions. We connect these layers. We study how an unseen user's access-and-persistence policy can be adapted from sequentially revealed feedback, while treating predicted preference as evidence rather than authority. Every protected tool effect is mediated by an explicit authorization ledger and an independent reference monitor. Our current evaluation establishes stated-policy adaptation and controlled execution auditability, not general natural-language robustness or real-world privacy-harm reduction.

## 5. Survey 里的文章能不能作为 related work

**可以，而且应该引用；但 survey 应主要作为 taxonomy 和研究动机，具体技术判断应回到原始论文。** 另外，该 survey 的检索截止到 2024 年 4 月，2026 年投稿不能只依赖其 reference list。

### A. Survey 中最直接的 Agent2Tool / action-control 锚点

- [ToolEmu (ICLR 2024)](https://openreview.net/forum?id=GEcwtMk1uA)：说明 excessive tool permission 与未经许可的高风险动作；它评估/模拟风险，不学习个体权限偏好。
- [R-Judge (Findings of EMNLP 2024)](https://aclanthology.org/2024.findings-emnlp.79/)：从 agent interaction trajectory 判断风险。注意 survey 将 venue 写错，正式出处是 Findings of EMNLP 2024。
- [TrustAgent (Findings of EMNLP 2024)](https://aclanthology.org/2024.findings-emnlp.585/)：用 policy/constitution 约束 agent planning；适合作为 plan-level safety baseline，而非 user-specific authorization learning。
- [Formal-LLM](https://arxiv.org/abs/2402.00798)：用形式语言限制合法动作空间；与 action mask 有方法层联系，但其约束不是从动态用户偏好中学习。
- [PrivacyAsst (IEEE TDSC 2024)](https://doi.org/10.1109/TDSC.2024.3372777)：保护 tool-using agent 的数据内容与通信；与授权生命周期不同。

### B. 与 Gap 1 攻击/不确定输入有关，但不是当前 completed experiment 的 baseline

- [PDoctor](https://arxiv.org/abs/2404.17833)：从用户约束测试错误 planning，适合作为“输入约束到执行合规”的桥梁。
- [Formalizing and Benchmarking Prompt Injection (USENIX Security 2024)](https://www.usenix.org/conference/usenixsecurity24/presentation/liu-yupei)、[Greshake et al. (AISec 2023)](https://doi.org/10.1145/3605764.3623985) 与 [WIPI](https://arxiv.org/abs/2402.16965)：适合定义恶意输入/外部数据 threat model。只有在新增攻击实验后，才能成为直接比较对象。

### C. 比 survey 更直接的 permission / consent 前作

- [Wu et al., *Towards Automating Data Access Permissions in AI Agents* (IEEE S&P 2026)](https://doi.org/10.1109/SP63933.2026.00018)：数据和问题的直接前作，必须引用。
- [Michael & Roesner, *How Agents Ask for Permission*](https://arxiv.org/abs/2607.13718)：2026 年 agent-permission landscape，适合用 `specification → derivation → enforcement` 划分层次；目前应标为 preprint。
- [Malkin et al., Runtime Permissions for Proactive Intelligent Assistants (SOUPS 2022)](https://www.usenix.org/conference/soups2022/presentation/malkin)：runtime prompt 与 interruption burden。
- [Wijesekera et al., Dynamically Granted Permissions (IEEE S&P 2017)](https://doi.org/10.1109/SP.2017.51)：根据 context 自动 grant/deny，并在不确定时询问；特别适合启发 `ask-now/defer` baseline。
- [Zhan et al., Dialogue and Case Similarity (ECAI 2023)](https://doi.org/10.3233/FAIA230614)：对话、online feedback 与个体化 privacy preference。
- [Filipczuk et al., Automated Privacy Negotiations with Preference Uncertainty (2022)](https://doi.org/10.1007/s10458-022-09579-1)：用户 override 与增量偏好学习。

### D. Preference learning 之外的 enforcement 层

- [AirGapAgent (CCS 2024)](https://doi.org/10.1145/3658644.3690350)、[IsolateGPT (NDSS 2025)](https://www.ndss-symposium.org/ndss-paper/isolategpt-an-execution-isolation-architecture-for-llm-based-agentic-systems/)、[AgentDojo (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html) 与 [CaMeL](https://arxiv.org/abs/2503.18813) 说明为什么 preference predictor 之后仍需要 least privilege、isolation、data-flow control 和 adversarial evaluation。
- 这些工作不能用来证明你们的偏好预测更准；它们是系统层互补工作。

### E. 2025–2026 投稿前必须纳入的 concurrent runtime-authorization 工作

至少需要定向比较 [Progent](https://arxiv.org/abs/2504.11703)、[Contextual Agent Security / Conseca](https://research.google/pubs/context-is-key-for-agent-security/)、[MiniScope](https://arxiv.org/abs/2512.11147)、[AgentGuardian](https://arxiv.org/abs/2601.10440)、[SEAgent](https://arxiv.org/abs/2601.11893) 与 [AuthBench](https://arxiv.org/abs/2605.14859)。这些工作的共同问题是 runtime policy、least privilege、authorization inference 或 privilege escalation；你们可能的区别是：

> **user-specific sequential permission lifecycle (reuse / refresh / revoke) + explicit ledger/reference monitor + matched learner comparison**。

这个差异目前是可检验的 positioning hypothesis，正式 novelty claim 仍应在精读全文后逐项确认。

## 6. 建议的 Related Work 四段结构

1. **Automated agent permissions and privacy assistants**：Wu、Michael & Roesner、Malkin、Wijesekera、Zhan、Filipczuk。
2. **Sequential personalization and deferral**：Thompson sampling、partial-feedback learning、calibration、learning to defer；明确 `ask next time` 是 persistence label，不是本轮 abstention。
3. **Agent action safety and constrained execution**：ToolEmu、R-Judge、TrustAgent、Formal-LLM、Progent/Conseca 等。
4. **Isolation and adversarial tool environments**：PrivacyAsst、AirGapAgent、IsolateGPT、AgentDojo、CaMeL；说明 enforcement 与 preference inference 是互补层。

写作时不要把 related work 组织成“Gap 1 论文列表”。按 **policy specification/derivation → sequential adaptation/deferral → enforcement/audit → adversarial evaluation** 会更清楚，也更容易显示你们的接口位置。

## 7. 为了真正把 Gap 1 做强，下一轮最小实验应是什么

建议不要立刻扩大 RL 规模，而是先补上当前 taxonomy claim 缺失的 treatment：

1. 加入 `CLARIFY` 与 `PROPOSE_NARROW_SCOPE`；构造 missing scope、ambiguous recipient、conflicting purpose 和 incomplete retention 四类输入。
2. 加入真正的 mid-execution revision：用户自主追加约束、撤销授权、改变 recipient/purpose；不要只用 protocol-forced disable。
3. 加入 malicious-user 与 untrusted-tool-output 两个独立攻击 arm，分别对应输入侧 Gap 1 与执行/外部边界问题。
4. 报告 unsafe effect、unnecessary prompt、clarification success、scope inflation、task-preserving recovery 与 risk–coverage curve，而不仅是 JEM/task success。
5. 最后再做小规模 repeated-measures human study，验证 synthetic simulator 是否保留 policy ranking、revoke/override 行为和 prompt burden。

若完成前两项，就可以把论文从“Gap-1-adjacent”推进到“直接研究 Gap 1”；若再完成攻击与真人验证，才有资格讨论更一般的 Gap 1 robustness。

## 8. 最终建议

当前最有说服力的论文不是“RL solves agent privacy”，也不是“we solve Gap 1”，而是：

> **把逐步显露的个人权限偏好与可执行授权分离：学习层处理受限的 Gap 1 不确定性，独立的授权层处理 Gap 2 的工具执行与审计，并为以后测试 Gap 4 的不可信工具环境留下清楚接口。**

这条主线既忠实于已有结果，也能自然解释负结果：WP-FTS 的提升主要在 persistence、false-allow 仍高、DDQN 未胜过 MAB/rule、硬安全来自 reference monitor。它们不是论文的尴尬点，反而共同支持一个重要结论：**个体化 permission learning 和安全 authorization enforcement 必须被当作两个不同、但可组合的研究问题。**

## 附：详细审计文件

- [实验逐项审计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/experiment_audit.md)
- [Survey taxonomy 与原始引用审计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/survey_audit.md)
- [28 篇 related-work map](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/related_work_map.md)
