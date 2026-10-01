# Agent Completeness Rubric：面向论文审稿的分层判据与当前项目定位

审计日期：2026-09-27  
用途：判断一项工作究竟实现了 permission learner、sequential controller、effect-enforcement substrate，还是完整的 end-to-end agent；据此约束论文 claim、Gap 1/2 定位、外部有效性和下一篇论文贡献。  
方法边界：本文件依据当前仓库的设计、实现和冻结实验记录做静态审计；未运行任何实验。

## 结论先行

**是的，当前完成实验仍缺少一个完整的 end-to-end agent loop。** 但更准确的判断不是“项目还没有 agent，所以前面的实验都无效”，而是：

- 已经有可执行的 **permission learning**；
- 已经有可执行的、闭环的 **structured permission controller**；
- 已经有相当完整、但只在受控 mock/synthetic 环境中验证的 **effect enforcement**；
- 尚没有从自然语言用户目标出发，经动态任务规划、工具/参数选择、权限中介、真实状态化工具执行、观察驱动重规划，到最终回答的 **end-to-end agent**。

按本文下面的四层、四级 rubric，当前最合适的证据向量是：

> **Permission learning P2 / Controller C2 / Effect enforcement E2 / End-to-end agent A1**

其中 `2` 表示“已在受控实验环境中因果接通并执行”，`1` 表示“只有 scripted/pre-authored shell，尚不足以支持该层的系统 claim”。四项不能取平均；论文能使用的最高层 claim 由对应层的证据门槛决定。

因此：

1. 缺少完整 agent loop **不推翻**现有 stated-policy adaptation、structured controller、ledger/reference monitor 和 bounded execution-audit 结果。
2. 它会直接阻止将当前系统写成“一个完整 RL-based agent”或把结果外推为“真实 agent task safety/privacy”。
3. Gap 1 仍只能定位为 history-dependent categorical permission feedback 的窄子问题；Gap 2 可主张 Agent-to-Tool action control，但不能主张已经覆盖 planning、tool selection、observation 和 replanning 的完整内部执行链。
4. 下一篇若补 end-to-end prototype，真正可发表的贡献不能只是“接了一个 LLM”；应是证明 permission learner、authority controller 和 reference monitor 如何在模型生成的、会变化的 agent trajectory 中组合，并通过消融分离各层作用。

还有一个需要校正的比较前提：**Wu et al. 并没有在该论文中完成一个安全部署的端到端 agent。** 论文介绍了标准 agent 语境，并实现 permission-assistant prediction proof of concept；但明确只处理 preference understanding/prediction，而把 reliable enforcement 以及 permission assistant 的安全部署列为 scope 外。因此，当前项目不是在所有架构层面都落后于 Wu et al.；它在 controller/enforcement 层反而更深入，但同样缺少完整 agent front-to-back loop。

## 1. 审稿时先区分的四个对象

一个 LLM、一个名为 `Agent` 的类、一个 Gym environment，或一条多步轨迹，都不能单独证明“完整 agent”。应按功能和因果路径判断：

```text
用户目标
  -> 任务解释 / 规划 / 工具与参数提议
  -> permission learner 给出偏好估计
  -> controller 决定询问、澄清、缩小范围、执行、拒绝或升级
  -> authority service + reference monitor 决定 effect 是否可以发生
  -> 工具产生 observation / state change
  -> agent 根据 observation、拒绝或失败重规划
  -> 基于实际结果生成最终回答
```

四层的边界如下。

### P — Permission learning

研究“用户可能希望允许什么”。输入可以包含任务上下文、用户画像、历史 permission feedback 和不确定性；输出是偏好预测、posterior 或 action recommendation。

**它不产生 authority。** 即使预测为 allow，也不能据此直接 mint grant 或执行工具。

### C — Permission controller

研究“当前状态下下一步采取哪个结构化控制动作”。它维护多步状态，接收反馈，在 `request / refresh / clarify / narrow / execute / deny / escalate` 等动作之间选择，并处理终止条件。

**它不等于通用 task planner。** 如果任务步骤、工具和 scope 已由 manifest 预先指定，那么 controller 只是在预编译 workflow 中做权限控制。

### E — Effect enforcement

研究“未经有效 authority，受保护 effect 是否在架构上不可能发生”。典型组件包括 authoritative ledger、独立 reference monitor、capability/permit、scope matching、one-time consume、revocation/expiry、fail-closed path 和不可由 policy 改写的 audit trail。

**action mask 不是完整 enforcement。** mask 可以减少 policy 选择非法动作，但只有位于工具 effect 前、不可被 planner/policy 绕过的 monitor 才能支持 complete-mediation claim。

### A — End-to-end agent

研究“系统是否把开放用户目标转化为工具行动，并根据实际观察持续调整直至回答”。最低闭环包含 task interpretation、plan/tool/argument generation、permission mediation、tool execution、observation、replanning/recovery 和 final response。

**LLM 也不自动等于 agent。** 一个只做 permission classification 的 LLM 属于 P 层；反过来，一个非 LLM policy 若真实闭合 perception–action loop，也可以是窄域 agent。

## 2. 四级成熟度评分

所有层统一使用以下成熟度，但每层分别打分：

| 等级 | 含义 | 审稿证据要求 |
|---|---|---|
| `0 — absent` | 没有该功能，或只在 future work 中出现 | 无可执行路径 |
| `1 — illustrative/scripted` | 有概念图、接口、预编排脚本或 mock shell；关键选择由 manifest/oracle 预先决定 | 能展示接口，但不能证明该层承担了实际决策或反馈闭环 |
| `2 — operational/controlled` | 组件在受控 testbed 中真实运行，输入会因果改变下游状态或 effect；有匹配基线和审计 | 可复现轨迹、negative tests、component-specific metrics；仍可使用 synthetic user/sandbox tool |
| `3 — externally challenged` | 在 held-out、自然变化、攻击、跨工具/跨环境或真人条件下仍成立 | distribution shift、failure recovery、adversarial/cross-domain/human validation，且报告置信区间与失效模式 |

### 2.1 各层的通过门槛

| 层 | 达到 `2` 至少必须满足 | 常见但不充分的“伪证据” |
|---|---|---|
| P | 可执行 learner；训练/更新协议清楚；held-out 或 matched frozen comparison；预测与 authority 分离 | 有 survey labels；prompt 中写“permission assistant”；单次 LLM 分类演示 |
| C | 显式 state/action/transition；至少一次反馈影响后续动作；有 deny/failure/terminal branch；policy 的选择真实改变执行路径 | horizon 大于 1；预写 legal trace；把一次四分类称为 RL agent |
| E | 每次 protected effect 前 complete mediation；ledger/monitor 独立于 learned policy；可观察 committed effect；篡改、过期、scope mismatch 等会 fail closed | action mask；reward 中惩罚违规；日志声称“blocked”但工具仍可绕过 |
| A | 从用户 goal 到 final response 的同一运行实例；plan/tool/arguments 不是全部预写；工具 observation 至少一次改变后续 plan/action；permission denial 或 tool failure 有 recovery；最终回答对应真实 tool outcome | Chat UI 包装；LLM 复述预定 plan；工具返回固定字符串；只有 permission question–answer loop |

### 2.2 不允许用平均分掩盖缺层

审稿结论应写成向量，例如 `P2/C2/E2/A1`，而不是总分 `7/12`。原因是：

- P3 不能补偿 E0：偏好预测再准也不是授权；
- E3 不能补偿 A0：安全 kernel 再强也未证明真实 agent 会正确调用它；
- A2 不能补偿 E0：能完成任务的 agent 仍可能越权；
- C2 不能自动升级为 A2：权限控制闭环不是完整任务闭环。

## 3. 当前项目的逐层判定

| 层 | 当前已有的实质证据 | 关键缺口 | 判定 |
|---|---|---|---:|
| P | 四类 access × persistence prediction；participant-held-out baseline；online WP-FTS matched frozen replay；历史反馈更新 posterior；S-QSTN multi-step 中有 history-conditioned categorical responses | 反馈主要为 survey/synthetic/cache replay；没有 live human、自由文本 clarification、noisy/contradictory feedback；false-allow 仍很高 | `P2` |
| C | 六个结构化动作；公开 state、ledger summary、history、candidate catalog 和 action mask；`reset/step` 闭环；DDQN/MAB/rule 共享环境；request/grant/disable/refresh/execute/deny/escalate 会改变后续状态 | task steps、scope、tool route 和场景分支大多由 manifest 固定；没有 `CLARIFY`/`PROPOSE_NARROW_SCOPE`；不是通用 planner | `C2` |
| E | 独立 authorization service/ledger、reference monitor、scope check、effect permit/receipt、one-time consumption、audit chain；protected mock effects 在 monitor 后提交；tested traces 中 unauthorized committed effect 为 0 | 仅受控 fixtures 和 `MockTool`；没有真实 tool backend、untrusted output、prompt injection、tool-schema drift、跨环境 bypass 测试 | `E2` |
| A | `PermissionEnvironment` 将 controller、scripted/S-QSTN user、TaskEngine、MockTool 和 evaluator 串接为多步 test harness | 不接收开放自然语言 goal；不生成任务 plan；不动态发现/选择工具；不从 observation 重规划；没有面向用户的 grounded final answer；关键 route 来自预写 manifest | `A1` |

### 3.1 为什么可以说“有闭环 controller”，却不能说“有完整 agent”

当前真正运行的闭环大致是：

```text
预定义 task step + 当前 ledger/history
  -> permission controller action
  -> scripted/S-QSTN permission answer 或 monitored mock effect
  -> 新的 ledger/task snapshot
  -> 下一 controller step
```

完整 agent 还需要的前后两端是：

```text
自然语言 goal
  -> 动态 plan/tool/arguments
  -> [当前已有的 permission controller + enforcement]
  -> tool observation
  -> 根据 observation/denial/failure 重规划
  -> grounded final response
```

所以缺的不是“再加一个 `Agent` 类名”，而是目前由 scenario manifest 替代的 **task cognition and orchestration plane**，以及由 evaluator 替代的 **observation-to-replanning-to-response plane**。

### 3.2 当前判定的仓库证据

- 主设计明确写明当前研究单元是 structured permission controller，而不是整个通用 LLM agent，并把端到端 LLM autonomous-agent deployment safety 排除在当前范围外：[`RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md`](../RL_Personal_Assistant_Design/RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md)。
- 当前 v0 只有 authorization、execution 和 terminal 六类动作；`CLARIFY` 与 `PROPOSE_NARROW_SCOPE` 被延期：[`README.md`](../RL_Personal_Assistant_Design/README.md)。
- 实际环境组合的是 `ScenarioManifest -> TaskEngine -> MockTool -> ReferenceMonitor -> evaluator`，且 default tool outcomes 由 deterministic plan 构造：[`environment.py`](../ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/environment.py)、[`effects.py`](../ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/effects.py)。
- user side 是类型化 `PermissionChoice` 的 scripted adapter；它不是开放任务对话 agent：[`scripted_user.py`](../ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/scripted_user.py)。
- 已完成实验的对象和限制已有逐项证据审计：[`experiment_audit.md`](experiment_audit.md)。

## 4. 与 Wu et al. 的正确比较

Wu et al., *Towards Automating Data Access Permissions in AI Agents* 对标准 agent 的描述包括 LLM、system prompt、memory、tools、planning 和 autonomous execution；但这是研究语境，不等于论文实现了整套 agent。

该论文自己的 scope 边界很清楚：

- automated permission management 被拆成 preference understanding、preference prediction 和 reliable enforcement；论文聚焦前两项，把 enforcement 交给互补工作；
- permission assistant 被设想部署在 agent scaffolding 中；
- permission assistant 的实现与安全部署、sandbox/TEE、恶意 data-flow detection 和 LLM instruction control被明确列为 scope 外；
- 第 5 节把模型称为 proof of concept / initial exploration，而不是 definitive solution。

本地全文证据见 [`paper_text_2511_17959.txt`](../paper_text_2511_17959.txt)，尤其是 AI-agent 定义段、Research Goals、Permission Assistant Design Assumptions/Out of Scope 和模型设计开头。

用同一 rubric 比较：

| 系统 | P | C | E | A | 审稿式解释 |
|---|---:|---:|---:|---:|---|
| Wu et al. 论文原型 | `P2` | `C0–1` | `E0` | `A1` | 有 LLM+CF permission predictor 和 agent conceptual setting；没有可靠 enforcement 或完整部署 loop |
| 当前项目 | `P2` | `C2` | `E2` | `A1` | preference learner 之外，新增 sequential control 与 bounded reference-monitor path；仍无完整 task-agent front/back end |

因此更准确的比较不是“Wu 有 agent、我们没有”，而是：

> **两项工作都还不能宣称完成 end-to-end agent；Wu 更集中于用户研究和 permission inference，当前项目向 sequential control 与 enforceable authority 前进了两层，但尚未把这些层接入一个动态 task-performing agent。**

## 5. 缺少完整 agent loop 对论文的四类影响

### 5.1 对当前 claim：不致命，但必须降到 component-level

| 当前可能的 claim | 缺少 A2 的影响 | 可接受写法 |
|---|---|---|
| 历史 permission feedback 改善 stated-policy fidelity | 基本不受影响；这是 P 层 claim | “under controlled replay / synthetic categorical feedback” |
| structured controller 能处理授权生命周期 | 不致命；这是 C 层 claim | “a sequential permission controller for tool-using agents” |
| ledger/reference monitor 在 tested traces 中阻止 unauthorized committed effects | 不致命，但只限 E2 fixtures | “zero committed unauthorized effects in the evaluated bounded traces” |
| DDQN 是更好的 agent | 不能支持；既无完整 agent，现有结果也未显示 DDQN 优于 MAB/rule | 删除或改成 matched controller comparison/negative result |
| 系统让 AI agent 更安全、更隐私、可部署 | 不能支持；缺真实 task loop、真实工具、攻击和 privacy-harm outcome | 改成 architecture feasibility / controlled execution auditability |
| 本文提出完整 RL-based personal-assistant architecture | 构念效度严重不足 | 改称 layered authorization subsystem / permission-control testbed |

最关键的命名建议：

> 当前可以叫 **RL-based/sequential permission controller for tool-using agents**，不宜简称 **RL-based agent**。

### 5.2 对 Gap 1 / Gap 2 定位

**Gap 1：影响较大。** 当前有多步、历史依赖 permission feedback，但没有开放式 goal interpretation、含糊 task specification、自由修改意图、clarification、自然语言冲突或 malicious input。没有 agent front end 会使 Gap 1 证据停留在：

> bounded uncertainty in sequentially revealed categorical authorization feedback

而不能升级为：

> robustness to unpredictable multi-step user input in AI agents

**Gap 2：部分影响，但不会抹掉主定位。** 当前 ledger、reference monitor、action mask 与审计链确实处理 `action input -> action execution` 的 Agent-to-Tool authorization；这仍是 Gap 2 的直接组成部分。但由于 planning、动态 tool selection、argument generation、tool observation 和 replanning 尚未进入同一系统，不能声称覆盖 Gap 2 所说的整个复杂内部执行过程。

最稳妥定位仍是：

> **Gap 2-centered Agent-to-Tool authorization and effect mediation, with a bounded Gap 1 component for sequential permission feedback.**

端到端 prototype 的主要价值，是把 Gap 1 的输入不确定性和 Gap 2 的内部执行复杂性在一条真实 trajectory 上连接起来，而不是把项目从“非 agent”神奇地变成“完整解决两个 gap”。

### 5.3 对外部有效性：这是最大影响

当前 testbed 有意冻结 task graph、scope、tool outcome plan 和 feedback contract，因此内部归因清楚，却没有回答部署时最容易出错的接口问题：

- planner 是否会提出 manifest 中没有的新工具、数据类型、recipient、purpose 或 retention；
- 自然语言 goal 如何稳定映射为 canonical permission scope；
- tool schema/argument 漂移是否造成 under-scoping 或 scope inflation；
- tool output、失败、部分提交或间接 prompt injection 是否改变后续计划；
- permission denial/revocation 后 agent 是否绕行、重复询问、改写参数或选择不安全替代工具；
- final answer 是否忠实反映实际 effect，而不是模型想象中的 effect；
- monitor 是否位于所有真实调用路径上，第三方 SDK、parallel call 或 retry 是否可绕过。

所以当前结果最合理的外推对象是“结构化 authorization subsystem”，不是“真实 LLM agent ecosystem”。这是一项明确的 external-validity limitation，而不是对当前内部效度的否定。

### 5.4 对下一篇论文贡献：补 loop 是必要条件，但不是充分 novelty

仅把现有 controller 包进 ReAct/LangChain/任一 LLM shell，通常只算 engineering integration。更有说服力的下一篇贡献组合应包括：

1. **Planner-to-authority interface**：把模型生成的 tool intent 编译成可审计、可比较的 canonical scope，并保证模型输出永远不能自行产生 grant。
2. **Permission-aware agent loop**：denial、scope narrowing、revocation 和 tool failure 能触发 task-preserving replanning，而不是简单终止或绕过。
3. **Effect-grounded evaluation**：区分 proposed/attempted action、authorized action、committed effect 和 final response；不再用 task-success 或 prediction accuracy代替安全结果。
4. **Causal component decomposition**：用必要消融证明增益来自 sequential learning、agent replanning 或 external enforcement，而不是预写 graph、oracle 信息或共同 kernel。
5. **New empirical finding**：例如动态 planning 如何放大 scope error、何时 sequential personalization 减少 prompt burden 但增加 false allow、external monitor 如何改变 planner recovery。没有这种新问题/发现，完整 loop 本身很难成为主要科研贡献。

## 6. 最小可信 end-to-end prototype

目标不是立即做通用个人助理，而是让当前 P/C/E 层在一个真实、可审计、可复现的 task loop 中承担因果作用。

### 6.1 最小组件

1. **Natural-language task interface**  
   接收未写成 manifest action trace 的用户目标。任务集可以很小，但 goal 必须先于 plan 存在。

2. **Frozen task planner/orchestrator**  
   使用固定版本 LLM 和固定 prompt，根据 goal 与 tool schemas 生成结构化 `tool_intent`。本阶段不需要 fine-tune LLM；冻结 planner 更利于归因。

3. **Intent-to-scope compiler**  
   将 `tool, operation, resource/data, purpose, recipient, retention` 转成 canonical scope。不能让 planner 自报“已授权”；解析失败、缺字段或冲突必须触发 clarify/narrow/escalate，而不是补默认宽权限。

4. **现有 permission learner + controller**  
   learner 提供 user-preference evidence；controller 选择 request、refresh、clarify、propose-narrow-scope、execute、deny 或 escalate。prediction 和 authority 必须继续分离。

5. **Authoritative ledger + reference monitor**  
   保留现有 complete-mediation 设计。所有 tool invocation——包括 retry、parallel branch 和 fallback——只能持 monitor 签发的单次 permit 进入 backend。

6. **两个状态化 sandbox tools**  
   至少一个读取型工具和一个具有可观察状态变化的写入/发送型工具。例如 sandbox calendar + local message outbox。不能只返回 manifest 预写字符串；effect 后应能独立查询 backend state/receipt。不要接真实个人账户或敏感数据。

7. **Observation-driven replanning**  
   至少一个任务的下一动作必须依赖真实 tool observation；至少一个 denial/scope-narrowing 或 tool-failure 分支必须促使 planner 生成替代安全路径。若所有下一步在 episode 开始前已知，仍只是 scripted workflow。

8. **Grounded final response and unified trace**  
   final answer 必须依据实际 observation/effect receipt生成。统一 trace 应能串起 `goal -> plan revision -> permission event -> authority -> tool call -> effect -> observation -> final answer`，同时维持 public/private/oracle 分离。

### 6.2 最小场景包

为了通过 A2 门槛，场景不必多，但必须包含不同因果分支：

- 一个无需敏感数据即可完成的任务，用于检测不必要 permission request；
- 一个需要 protected read 且授权后成功的任务；
- 一个 scope/recipient 含糊、必须 clarification 或 narrow-scope 的任务；
- 一个用户拒绝/撤销后仍可通过较弱替代路径部分完成的任务；
- 一个 tool 返回失败或新 observation、要求 replanning 的任务；
- 一个 sandbox attack case，例如 tool output 诱导请求额外数据，用于确认 planner 可以被诱导但 monitor 仍不放行未授权 effect。

### 6.3 A2 的验收门槛

只有同时满足下列条件，论文才适合写“end-to-end agent prototype”：

- tool/argument 至少部分由 planner 在运行时产生，而不是从 legal trace 读取；
- permission controller 的选择会改变 planner 可见 observation 和后续 plan；
- backend 产生可独立核验的 state change 或 read receipt；
- denial、revocation或失败后至少存在一条真实 replan path；
- final response 与 effect receipt 一致；
- 没有从 evaluator/oracle 泄露 correct action、minimal scope 或 future response 给 planner/policy。

以上足以证明受控环境中的 A2 agent loop。若论文还要声称 external enforcement 带来独立安全收益，则另需在无真实风险的 sandbox 中完成 monitor on/off 诊断，证明阻断来自 enforcement kernel，而不是 planner 恰好没有提出违规动作。

### 6.4 仍不需要做的事情

最小原型不需要浏览器自动化、几十种工具、真实邮箱/银行卡、训练新的 foundation model、长期真人在线学习或宣称 production security。过早扩大这些部分只会降低归因质量。

以下做法也不能单独把 A1 升为 A2：

- 给现有 environment 加聊天界面；
- 让 LLM 用自然语言复述 manifest 中的固定 route；
- 把 `MockTool` 改名为 tool API，但 outcome 仍完全预写；
- 在 episode 结束后让 LLM写一段 summary；
- 把 permission controller 封装成 `Agent` 类。

## 7. 必要 baselines 与 ablations

消融应围绕“每一层是否产生独立因果价值”，而不是堆更多 RL 算法。所有比较应共享相同 task split、planner version、tool backend、prompt/token budget、user responses 和 reference-monitor rules。

| 编号 | 比较 | 隔离的问题 | 必报结果 |
|---|---|---|---|
| B1 | **Full dynamic planner** vs **oracle/manifest plan** | 从 controller testbed 到真实 agent planning 带来多少错误与方差 | plan validity、scope error、task completion、unsafe attempts、recovery |
| B2 | **Sequential learner** vs **matched frozen/no-history learner** | 个体历史更新是否在 agent trajectory 中仍有增益 | preference fidelity、prompt count、false allow/deny、task completion |
| B3 | **Learned automation** vs **always ask + same monitor** | 自动 permission 的收益是否超过最安全的人机基线 | task completion、user burden、unsafe committed effects、latency/cost |
| B4 | **External reference monitor** vs **LLM/controller self-enforcement only**，仅在无真实风险 sandbox 中 | 零 unauthorized effect 来自 learned policy 还是 enforcement kernel | unsafe attempted/committed effects、scope mismatch、bypass rate |
| B5 | **Replanning enabled** vs **one-shot/no-replan** | “agent loop”本身是否改善 denial/failure 后的任务保持 | recovery success、repeat prompts、looping、final-answer correctness |
| B6 | **Structured explicit goals** vs **ambiguous + mid-execution revision** | 是否真的推进 Gap 1，而非只接上一个 planner | clarification success、scope inflation、revision compliance、unsafe effect |
| B7 | **Full P/C/E separation** vs **LLM directly predicts-and-executes** | 分层架构是否优于把 preference 当 authority | false authority creation、committed violations、audit completeness |
| B8 | **Stateful sandbox tools** vs **现有 precomputed mock-outcome harness** | 既有结论中有多少依赖预写 effect/observation | effect consistency、retry/partial-failure handling、trace divergence |

最小可发表实验不必做完整笛卡尔积。可采用 full system 为中心的一次一层消融，并保留两个关键交互：

- `dynamic vs oracle plan × monitor on/off`，判断 planner error 是否被 enforcement 隔离；
- `sequential vs frozen learner × explicit vs ambiguous/revision input`，判断 personalization 是否在 Gap 1 条件下仍成立。

### 7.1 指标必须按层报告

| 层 | 核心指标 |
|---|---|
| P | access/persistence fidelity、calibration、false allow/deny、risk–coverage |
| C | action validity、prompt/clarification burden、authorization lifecycle correctness、loop/termination rate |
| E | unauthorized attempted vs committed effects、scope/recipient/purpose violation、revocation latency、audit completeness |
| A | valid-authority task completion、plan/tool/argument validity、denial/failure recovery、final-answer faithfulness、cost/latency |

`task success` 不能覆盖 unauthorized effect；`zero committed violation` 也不能说明 preference learner 准确；`prediction accuracy` 更不能说明完整 agent 安全。

## 8. 建议的论文边界与表述

### 当前论文/当前证据

建议把对象写成：

> We develop and evaluate a structured sequential permission controller and an independently enforced authorization substrate for tool-using agents. The current evaluation uses pre-specified task graphs, categorical synthetic/replayed feedback, and sandboxed mock effects; it does not instantiate a general end-to-end LLM agent.

中文：

> 我们研究面向工具型 agent 的结构化顺序权限控制器与独立授权执行层。当前实验采用预定义任务图、离散的合成/回放反馈和受控 mock effects，不构成通用端到端 LLM agent。

不建议继续使用没有限定语的：

- “our RL agent”；
- “end-to-end personal assistant”；
- “the agent learns to use tools safely”；
- “we solve unpredictable multi-step input/internal execution”。

### 下一篇论文/加入 A2 后

只有完成最小闭环和关键消融后，才建议把贡献升级为：

> We integrate sequential permission adaptation and complete-mediation enforcement into an end-to-end tool-using agent, and quantify how dynamic planning, user revision, and tool feedback change authorization correctness, task recovery, and prompt burden.

即使达到 A2，也应称为 **end-to-end prototype in a controlled sandbox**，而不是 production-ready autonomous agent；后者至少还需要 A3/E3 的跨模型、跨工具、攻击、人类和部署环境证据。

## 9. 最终审稿判断

若按典型审稿问题回答：

- **“目前有没有完整 agent architecture？”** 没有；有 P2/C2/E2 的 authorization subsystem 和 A1 scripted harness。
- **“这会不会让现有实验失效？”** 不会让 component-level 结果失效，但会让 agent-level、安全性和部署性 overclaim 失效。
- **“它主要影响哪个 gap？”** 最大幅度削弱广义 Gap 1 与完整 Gap 2 claim；不影响把工作定位为 Gap 2 的 Agent-to-Tool action-control 子问题。
- **“与 Wu et al. 相比是否明显落后？”** 不是。Wu 的 agent architecture 主要是 conceptual context，论文实证核心仍是 permission prediction；当前项目已增加 controller/enforcement，但双方都未达到 A2。
- **“下一步最值得补什么？”** 不是先扩大 RL 训练，而是把当前 authorization stack 接入一个最小但真实因果闭环的 planner–tool–observation–replanner，并用 layer-isolating ablations 证明每个组件的贡献。
