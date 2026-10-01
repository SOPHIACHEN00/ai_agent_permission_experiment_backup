# Agent Architecture Gap Audit：当前项目与 Wu et al. 的完整 Agent 对照

审计日期：2026-09-27

## 结论先行

**你的直觉是对的：当前已完成的实验还没有一个完整的 task-performing agent architecture。**

但需要同时纠正另一个印象：**Wu et al. (IEEE S&P 2026) 也没有真正实现端到端 agent。** 他们有清楚的 agent 概念背景、MIRA 沉浸式 vignette 网站和 IC/CF/hybrid permission predictor；planner、真实工具执行、runtime enforcement、observation/replanning 和最终回答并未在论文系统中闭合，而且 implementation/deployment 被作者明确列为 scope 外。

两项工作的差异不是“Wu 有 agent、我们没有”，而是：

- **Wu et al.**：真人 user study 与 permission inference 做得完整，但 agent runtime 主要是概念宿主；
- **当前项目**：permission learning、sequential controller、ledger/reference monitor 和受控执行路径更深入，但前后的 task-agent shell 尚未实现。

最准确的当前名称是：

> **RL-based sequential permission controller and authorization substrate for tool-using agents**

而不是：

> **an end-to-end RL-based personal-assistant agent**

## 1. 什么才算这里所说的“完整 Agent”

判断标准不是代码中是否有 `Agent` 类，也不是是否调用过 LLM，而是下面这条因果链是否在同一个运行实例中闭合：

```text
自然语言用户目标
  -> 任务理解与动态计划
  -> 工具/参数/数据 scope 提议
  -> permission prediction 与询问策略
  -> authoritative grant + reference monitor
  -> 真实或状态化 sandbox tool effect
  -> tool observation
  -> denial/failure/新信息驱动的 replanning
  -> 基于实际 effect 的最终用户答复
```

当前系统真正闭合的是中间一段：

```text
预定义 task step + ledger/history
  -> RL/MAB/rule 选择 permission-control action
  -> synthetic permission answer 或 monitored MockTool effect
  -> 新的 structured state/reward
  -> 下一 controller action
```

这是一个真实的 sequential-control loop，但不是完整的 task-agent loop。

## 2. 当前项目缺什么、已经有什么

| Agent 能力 | 当前状态 | 证据性判断 |
|---|---|---|
| 自然语言 task understanding | 缺失/fixture 代替 | `ScenarioManifest` 已经给定任务、步骤与精确 scope；RL encoder 不理解 request 文本 |
| Task-plan synthesis | 缺失 | `TaskEngine` 顺序执行预定义 steps；controller 只规划权限生命周期动作 |
| 动态 tool selection/arguments | 缺失 | 工具与参数来自 manifest，不是 planner 运行时生成 |
| Permission learning | 已实现 | 四标签 prediction、WP-FTS、DDQN/MAB/rule 比较均有真实代码和结果 |
| Sequential permission controller | 已实现、范围受限 | request/refresh/disable/execute/deny/escalate 会真实改变后续状态 |
| Authorization ledger/reference monitor | 已实现、受控域内真实 | effect 前检查授权、scope、expiry、reservation 与 candidate binding |
| Tool execution | 模拟 | 下游为 plan-driven `MockTool`；结果从冻结 outcome plan 读取 |
| Observation | 结构化、受限真实 | 能观察 ledger/task/event 状态，但没有真实工具内容或开放环境反馈 |
| Replanning | 只有 reactive control | 每步重新选择 permission action，但不会诊断失败、改任务计划或换工具 |
| Final user response | 缺失 | 只有 metrics/summary JSON，没有 grounded natural-language answer |
| Agent memory | 缺失/位置不对 | cache 和 S-QSTN memory 服务于 synthetic respondent/replay，不是 task-agent memory |
| LLM planner | 缺失 | o4-mini 当前扮演四选一 synthetic respondent，不是主 agent |

设计文档自己也承认这一边界：当前里程碑是一个 public-observation-only、ledger-backed、reference-monitored sequential environment；最终系统图中的 `LLM planner / support model`、真实 tool layer、output review 和 user-visible result 仍属于目标形态，见 [主设计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/RL_Personal_Assistant_Design/RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:187) 与 [最终设计决策](D:/Study/Graduate_Study_UofG/Research/paper/Week67/RL_Personal_Assistant_Design/RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:3229)。

最直接的实现证据包括：

- [`TaskEngine`](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/execution.py:60) 把 manifest steps 当作 authoritative；
- [`MockTool`](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/effects.py:168) 明确是 plan-driven synthetic tool；
- [S-QSTN adapter](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/rl_sqstn_integration_v0/adapter.py:168) 明确要求 LLM 扮演 synthetic respondent；
- [r2 runner](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/rl_sqstn_integration_v0/run_multistep_r2.py:83) 在训练时遍历预生成 response graph，API 调用为 0；
- live smoke 也明确没有访问真实日历或真人数据，见 [implementation log](D:/Study/Graduate_Study_UofG/Research/paper/Week67/RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md:586)。

## 3. 为什么 Wu 那篇看起来像有 Agent，但其实没有闭合

Wu et al. 的论文中有三种容易混在一起的“系统”：

1. **Generic host-agent background**：LLM、system prompt、memory、tools、planning 和 autonomous execution。这是研究语境，不是他们实现的系统。
2. **Envisioned permission-assistant insertion point**：设想把 permission assistant 放在可信 scaffolding 中，LLM 不直接访问它。这是合理的概念接口。
3. **Actually implemented prototype**：MIRA vignette/survey shell，以及离线 IC、CF、IC+CF permission predictors。

论文明确把可靠执行预测结果留给互补工作，并将 permission assistant 的 implementation/deployment、sandbox/TEE、恶意 data-flow detection 和 LLM instruction control 列为 scope 外。Discussion 又把 UI、override、revoke、feedback 与完整 hybrid system 作为 future work。

官方仓库的发布结构也只有 survey data、65 个 scenarios、`website.pdf`、三个 predictor 脚本与 evaluation utilities，没有 planner、tool adapter、runtime authorization gate 或 observation/replanning loop。[官方仓库](https://github.com/llm-platform-security/ai-agent-permissions) 的 README 对此列得很清楚。

因此，MIRA 的准确名称是：

> **agent-themed interactive vignette / survey interface**

而不是：

> **implemented task-performing AI agent**

## 4. 用统一成熟度向量比较

为了避免“用了 agent 这个词”造成混淆，可以用四层评分：

- `P`：permission learning；
- `C`：sequential controller；
- `E`：effect enforcement；
- `A`：end-to-end task agent。

其中 `0`=缺失，`1`=概念/脚本，`2`=受控环境中真实运行，`3`=经过真人、攻击或跨环境挑战。

| 系统 | P | C | E | A | 最准确解释 |
|---|---:|---:|---:|---:|---|
| Wu et al. | 2 | 0–1 | 0 | 1 | permission predictor + agent conceptual setting |
| 当前项目 | 2 | 2 | 2 | 1 | operational permission/control/enforcement testbed，但 task-agent shell 仍脚本化 |

这个表不能取平均。`E2` 不能补偿 `A1`；同样，Wu 的 `P2` 也不能证明其已经实现 agent runtime。

## 5. 这个缺口会不会推翻现有实验

**不会推翻 component-level 结果，但会阻止 agent-level overclaim。**

仍然成立的结果：

- sequential feedback 对 stated-policy fidelity 的影响；
- RL/MAB/rule 在同一结构化 controller 环境中的比较；
- authorization lifecycle、action mask、ledger 和 reference monitor 的工程可行性；
- tested mock traces 中的 scope/authorization audit 结果。

当前不能声称：

- 完整 RL personal assistant 已经实现；
- agent 能理解开放式任务、自己规划并安全使用工具；
- 零 unauthorized effect 已在真实 agent/tool ecosystem 中成立；
- DDQN 让完整 agent 更安全或更有效；
- 当前实验解决了完整 Gap 1 或整个 Gap 2 internal execution chain。

因此，论文当前若以 subsystem paper 写作并非不可行；但如果标题、摘要和 evaluation unit 都强调“RL-based agent”，审稿人很可能会追问：**agent 在哪里？planner 在哪里？真实 tool observation 在哪里？final answer 在哪里？**

## 6. 最小可信的下一阶段 Agent 架构

不需要立即训练端到端 LLM-RL，也不需要接真实邮箱或银行卡。最小且可发表的 A2 prototype 可以是：

1. **冻结 LLM planner**：从自然语言 goal 生成结构化 `tool_intent`，planner 本身不训练，便于隔离 permission-controller 贡献。
2. **Intent-to-scope compiler**：把 tool、operation、resource/data、purpose、recipient、retention 编译为 canonical scope；缺字段或冲突时进入 clarify/narrow/escalate，不能自动补宽权限。
3. **现有 permission learner/controller**：保留 request、refresh、disable、execute、deny、escalate，并加入 `CLARIFY` 与 `PROPOSE_NARROW_SCOPE`。
4. **现有 ledger/reference monitor**：所有调用、retry、fallback 和 parallel branch 都必须持 monitor 签发的 permit 才能进入 backend。
5. **两个状态化 sandbox tools**：至少一个 protected read，例如 sandbox calendar；一个可核验写入，例如 local message outbox。effect 不能再只是 manifest 预写字符串。
6. **Observation-driven replanning**：至少一个任务因 tool observation 改变后续计划；至少一个 denial/revocation/failure 触发安全替代路线。
7. **Grounded final response**：最终回复必须与 backend state/effect receipt 一致。
8. **统一审计链**：串起 `goal → plan → permission → authority → tool effect → observation → replan → final response`，继续维持 public/private/oracle separation。

这套架构的关键不是“把 LangChain 接上去”，而是让 planner 生成的动态 tool intent 真正经过你们已有的授权内核，并让授权拒绝或工具结果对后续计划产生因果影响。

## 7. 下一阶段最关键的实验，而不是继续扩大 RL 训练

建议优先做以下五个比较：

| 对照 | 回答的问题 |
|---|---|
| Dynamic LLM planner vs manifest/oracle plan | 真实 planning 会引入多少 scope/tool/argument 错误？ |
| Sequential learner vs matched frozen/no-history | 个体历史更新在真实 agent trajectory 中是否仍有价值？ |
| Learned automation vs always ask | 自动化收益是否足以抵消 false allow 与 prompt burden？ |
| Reference monitor on vs self-enforcement only | 零 unauthorized effect 是否确实来自外部 enforcement？仅在无真实风险 sandbox 做 |
| Replanning on vs one-shot plan | 拒绝、撤销或 tool failure 后，agent 能否安全地保留任务效用？ |

至少分别报告：

- task completion under valid authority；
- unauthorized **attempted** 与 **committed** effects；
- false allow/deny 与 risk–coverage；
- permission/clarification burden；
- scope inflation；
- denial/failure recovery；
- final-answer faithfulness；
- latency 与调用成本。

## 8. 最终判断

一句话总结：

> **当前项目已经有一个真实的 RL permission-control kernel 和比 Wu et al. 更深入的 authorization/reference-monitor testbed，但尚未有完整 task-performing agent；Wu et al. 也没有，只是其 agent framing 和用户界面使它看起来更像完整系统。**

因此现在最优先的工作不是继续堆更多 DDQN 训练，而是做一个薄但真实的 agent shell，把现有模块放进动态的 planner–tool–observation–replanning 闭环中。完成这一步以后，你们才可以严谨地把研究对象从“permission controller for agents”升级为“permission-aware agent prototype”。

## 详细证据

- [当前代码架构逐项审计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/current_architecture_audit.md)
- [Wu et al. 架构与代码审计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/wu_agent_architecture_audit.md)
- [Agent completeness rubric 与必要消融](D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_permission_gap_positioning/agent_completeness_rubric.md)
