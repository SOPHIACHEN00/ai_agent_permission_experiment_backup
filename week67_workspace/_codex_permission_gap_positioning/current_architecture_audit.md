# 当前架构审计：现有实验是否已经包含“完整 Agent”

日期：2026-09-27  
审计范围：`ai_agent_permission_experiment/rl_sqstn_integration_v0`、其调用的 `rl_personal_assistant/src/pa_rl` runtime，以及 `RL_Personal_Assistant_Design` 中与当前实验状态直接相关的说明。  
方法：只读静态代码与已有实验产物审计；未运行训练、未修改项目代码。

## 1. 结论先行

**是的：如果“完整 Agent”指一个能从用户自然语言目标出发，理解任务、制定/修改计划、选择真实工具、受权限约束地执行、读取工具结果、继续规划并生成最终自然语言回复的 tool-using assistant，那么当前实验确实还没有这套完整架构。**

但也不能说“目前完全没有 agent”。更准确的分层结论是：

1. **按强化学习/MDP 的最小定义，已有真正的 agent policy。** DDQN/MAB/规则策略反复接收结构化 observation、选择 controller action、取得 reward/next observation，并在 DDQN 路径中更新网络。因此它不是纯 classifier，也不是把答案静态查表。
2. **按现代 LLM tool-agent 的定义，目前只是其中一个中间子系统。** 已实现的是一个 `permission lifecycle controller + authorization ledger + reference monitor + synthetic environment`，不是端到端 personal assistant。
3. **现有安全执行内核不是摆设。** authorization service 和 reference monitor 在模拟 runtime 中处于因果执行路径上，会在执行前检查授权、scope、expiry、reservation 和 candidate binding；这部分是真实现，不是只在结果后打分。
4. **任务、计划、工具和世界效果仍主要由 fixture/manifest/oracle 预先给定。** “理解任务”“生成计划”“挑工具”“使用真实工具”“根据真实工具输出修正计划”“生成最终答复”均未由当前 learned agent 完成。
5. **S-QSTN 的 LLM 调用位于 synthetic user/respondent 一侧。** live smoke 中 o4-mini 只输出四选一 permission answer；执行侧 controller 仍是固定 `rule_action`。多步 RL 训练则读取提前枚举并缓存的 response graph，训练期间 API 调用为 0。

项目自己的设计文档其实已经准确承认了这一边界：当前研究单元是“结构化 permission controller，而不是整个通用 LLM agent”，后续 LLM/真人路线未完成。证据：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:24-30`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:68-76`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\README.md:3`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\README.md:23-33`

所以核心问题不是“现有实验假的”，而是**命名和 claim 层级容易比实际实现高一层**：目前可以叫 RL-based permission controller / permission-management agent，不宜直接叫完整 RL personal assistant agent。

## 2. 当前真正运行的 runtime loop

### 2.1 fixture pilot 的在线环境闭环

实际调用链可以重建为：

```text
人工编写的 Case / ScenarioManifest
  ├─ public_request_context（展示性任务文本）
  ├─ 有序 task_steps + 每步 scope
  └─ 固定 permission replies
          ↓
Episode.reset(seed)
          ↓
PermissionEnvironment.reset()
  ├─ TaskEngine(manifest.task_steps)
  ├─ AuthorizationService
  ├─ ReferenceMonitor
  ├─ MockTool(precomputed outcome plan)
  └─ SqstnAdapter(fixture/cache/live respondent)
          ↓
structured public observation + candidate catalog + action mask
          ↓
DDQN / MAB / fixed rule 选择一个 candidate slot
          ↓
PermissionEnvironment.step(index)
  ├─ REQUEST/REFRESH → adapter 给四选一回答 → ledger 更新
  ├─ EXECUTE → reference monitor 检查 → MockTool
  └─ DENY/ESCALATE/DISABLE → 结构化 public event
          ↓
reward + next structured observation + done
          ↓
policy update / 再选一步
          ↓
episode summary、checkpoint、metrics JSON（无自然语言 final answer）
```

runner 中这条闭环是实在存在的：创建 `Episode`、`reset`、编码 observation、策略选 action、`step`、learner `observe/feedback`、再把 `result.frame` 作为下一状态。证据：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_pilot.py:116-173`
- evaluation 也逐步调用 policy 和 environment，而非一次性分类：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_pilot.py:213-243`
- `Episode` 把 adapter 注入 `PermissionEnvironment` 并把 action index 交给环境：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\environment.py:35-43`, `:46-88`

### 2.2 multistep r2 的实际训练闭环

multistep r2 并不是在训练时动态调用 LLM/world，而是：

```text
事先用 LLM respondent 枚举所有允许分支
        ↓
保存 dataset.json（node → valid edge → successor）
        ↓
训练时加载整张图和每个 node 的 frozen PolicyFrame
        ↓
policy 选 action index
        ↓
直接查 node.edges[index] 得 successor、reward、answer
        ↓
更新 policy
```

代码直接加载 `dataset.json`、构造 `frames`，并通过 `node['edges'][str(index)]` 前进；配置明确写着 learning 时 API 为 0、结果仅是 cached-environment descriptive pilot：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_multistep_r2.py:20-28`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_multistep_r2.py:52-68`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_multistep_r2.py:83-121`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_multistep_r2.py:150-178`

response graph 的生成本身也是“对每个合法 action prefix 重建 episode并枚举边”，而不是 task agent 自己规划：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\multistep_r2.py:14-58`

## 3. Agent 能力逐项判定

判定标签：

- **真实**：该模块真实参与当前因果 runtime，并非只写在设计文档里。
- **受限真实**：存在真实闭环，但功能范围远窄于完整 agent 中同名能力。
- **脚本/预定义**：由 fixture、manifest、确定性规则或预生成 graph 提供。
- **模拟**：接口和状态转移真实，但世界对象/用户/工具效果是 synthetic/mock。
- **缺失**：当前执行路径没有该层。

| 能力 | 当前判定 | 实际发生了什么 | 为什么还不是完整 Agent |
|---|---|---|---|
| Task understanding | **脚本/缺失** | fixture 作者把任务拆成 `ScenarioManifest.task_steps` 和精确 `Scope`；policy 只看结构化摘要 | 没有把开放式用户自然语言解析为目标、约束、子任务或可执行意图；policy encoder 甚至不使用 request 文本 |
| Planning | **任务计划脚本化；controller 决策受限真实** | `TaskEngine` 顺序取下一个 manifest step；RL 只规划 ask/refresh/execute/deny/escalate 等 permission lifecycle 动作 | 没有生成工具计划、子目标、依赖图或替代路线，也不能重写任务步骤 |
| Tool selection | **脚本/缺失** | fixture 固定为 `calendar_api` 和固定 data scope；candidate catalog 只围绕当前 scope 建 permission/execution 动作 | 没有多个工具的 discovery、ranking、argument construction 或 tool routing |
| Permission-management decision | **真实但窄** | DDQN/MAB/规则真实选择是否请求、刷新、执行、拒绝、升级；DDQN 是真正 value-based learner | 这是完整 agent 的一个 controller 子策略，不是全部 cognition/action policy |
| User authorization answer | **模拟** | fixture 固定四标签，或由 o4-mini 作为 synthetic respondent 输出四选一 | LLM 扮演用户，不是主 agent；也不是真人授权 |
| Authorization enforcement | **真实（模拟域内）** | ledger 和 reference monitor 在 tool invocation 之前检查 authorization、scope、expiry、CAS reservation、candidate/task binding | 保护的是 `MockTool`，尚未绑定真实 OS/API capability、真实 credential 或外部副作用边界 |
| Tool execution | **模拟** | `MockTool` 按预置 `(scenario, step, attempt)` outcome plan 返回 committed/absent/unknown，并合成 effect id | 没有 calendar/file/email/web 等真实或 sandboxed tool adapter，也没有真实 tool result 内容 |
| Observation | **真实但结构化且窄** | policy 得到 public task progress、ledger summary、event counts、candidate rows、mask | 没有感知自然语言对话、真实工具输出、网页/文件内容或未结构化环境反馈 |
| Replanning | **受限反应式** | 每个 transition 后重新编码 next frame 并再次选择 action | 这是 closed-loop reactive control；没有显式 plan object、failure diagnosis、plan repair 或新工具选择。r2 更是在 frozen graph 上查 successor |
| Final response | **缺失** | episode 结束后 runner 写 summary、metrics、checkpoint；DENY/ESCALATE 只是结构化 event | 没有面向用户的答案合成、证据汇总、自然语言解释或交付物 |
| Memory | **部分且位置不同** | synthetic respondent 有 episode 内 bounded event memory；policy 能看到公开 history aggregates；learner 参数跨 episode 更新；cache 保存 exact responses | 没有主 agent 的 working plan、task memory、semantic/episodic retrieval 或跨任务 personalization；cache 不是 agent reasoning memory |
| LLM participation | **RL 主循环缺失；respondent 侧有限真实** | fixture pilot 0 API；live smoke/collection 用 o4-mini 生成 synthetic permission label | LLM 不做 task understanding、planning、tool call generation、replanning、security review或 final answer |

## 4. 逐项代码证据

### 4.1 Task understanding：自然语言任务没有被 agent 理解

fixture 直接声明唯一工具、data attributes、operation、purpose、recipient、retention，并把任务拆成 `read_first/read_second`：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\fixtures.py:18-27`
- manifest 连同 hidden postcondition、legal/prohibited trace 都由 fixture 作者给定：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\fixtures.py:45-58`

`TaskEngine` 明确把 manifest steps 当作 authoritative，并只允许预定顺序与精确 scope：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\execution.py:60-80`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\execution.py:99-111`

虽然 observation 内保留 `request_context`，RL encoder 实际只读取 horizon、task/ledger/history/candidate 等结构字段；没有读取 `o.request_context`，schema 还明确声明不编码 raw identifiers：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\features.py:38-79`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\features.py:89-95`

因此当前 policy 学的是**与任务语义脱钩的结构化权限状态控制**，不是对用户目标的语言理解。

### 4.2 Planning：有 sequential control，没有 task-plan synthesis

环境根据当前预定 `TaskStep` 构造候选：REQUEST、EXECUTE、DENY、ESCALATE，以及条件性的 REFRESH/DISABLE；agent 只能在这张 catalog 中选 slot：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:427-489`
- observation 和 mask 随当前 task/ledger 状态重新构造：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:497-532`

固定规则策略清楚显示当前 controller 的全部“思考”：有可执行授权就 execute；已拒绝就 fallback；否则 request/refresh：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\policies.py:14-43`

DDQN 的确用 Q-network 在合法候选间选择，并非假 RL：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\learner.py:64-108`
- loss、Double-DQN target 和 optimizer update：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\learner.py:110-137`

所以应称为**learned sequential controller**，而不是 planner。它能学习“下一步权限动作”，不能提出“为了完成用户目标，先查日历、再查地图、失败后改用另一工具”这样的计划。

### 4.3 Tool selection 与 execution：工具和结果都由实验预置

当前 fixture 始终将工具固定为 `calendar_api`：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\fixtures.py:20-23`

环境默认 tool plan 为每个 manifest step 的第一次调用预置 `committed/completed` 结果：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:96-111`

`MockTool` 的 docstring 和实现都明确说明它是 plan-driven synthetic tool；结果从 `_plan[(scenario_id, task_step_id, attempt_index)]` 读取：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\effects.py:168-176`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\effects.py:198-230`

这意味着 tool interface、effect receipt 与失败语义可以被严肃测试，但实验没有证明真实工具使用能力。

### 4.4 Permission decision：必须区分三种不同决定

当前系统有三类容易被混称为 permission decision 的操作：

1. **controller decision**：是否 ask/refresh/execute/deny/escalate。DDQN/MAB/规则策略负责；这是当前真正的 learned-agent 部分。
2. **user choice**：`allow_once / allow_reuse / deny_reask / deny_persist`。由 fixture 或 S-QSTN respondent adapter 给出。
3. **authorization verdict**：这个 choice 是否创建 active grant、是否覆盖本次 scope、能否执行。由 deterministic ledger/reference monitor 决定，LLM 和 RL 都不能自行授权。

adapter 在 fixture mode 中按固定 reply schedule 返回；live mode 才调用 transport：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:76-93`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:183-213`

环境只在 controller 选择 REQUEST/REFRESH 后调用 adapter，并把返回的 `PermissionChoice` 交给 ledger：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:690-749`

因此可以说“RL agent 学 permission-management strategy”，但不能说“RL/LLM 自己决定并授予用户权限”。

### 4.5 Authorization enforcement：当前最完整、最真实的一层

`AuthorizationService` 实现了 append-only authorization state、request/refresh、四类 permission choice、disable/expiry、reservation 和 commit/abort：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\authorization.py:163-227`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\authorization.py:260-325`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\authorization.py:327-381`

`ReferenceMonitor` 是唯一 execution entrypoint；它检查 action/version/candidate binding、authoritative task step、active/unexpired/scope-covering authorization，并在 tool call 前取得 CAS-style reservation：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\execution.py:167-185`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\execution.py:273-318`
- 执行结果再驱动 ledger commit/abort/reconciliation 和 task receipt：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\execution.py:319-350`

这一层值得保留为未来完整 agent 的 runtime shield。限制只是其下游目前是 MockTool，而非真实 capability boundary。

### 4.6 Observation 与 reactive loop：是真的，但语义很窄

public observation 包含 task progress、authorization summaries、interaction-history aggregates、candidate catalog 和 mask。policy feature encoder 只投影这些结构字段：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\features.py:38-79`

每次 environment step 后会重新 evaluation、递增 logical step、构造新的 catalog/mask/observation，再记录 transition：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:840-944`

这满足“observe → act → observe again”的最小 agent loop，也形成一定的长期 credit assignment；但它看不到真实 tool payload，也没有 plan repair object，所以只能称 reactive permission control，而非一般 replanning。

### 4.7 Final response：没有 user-facing completion layer

环境的 DENY/ESCALATE 只追加结构化 public event；execute 也只产生结构化 execution result：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\environment.py:751-804`

runner 最终写的是 experiment completion JSON 和 aggregate metrics：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_pilot.py:259-269`

没有 response composer/support LLM/template renderer 来向用户说明做了什么、返回查询结果或给出安全替代方案。设计文档也把“support LLM verbalizes approved structured act”放在后续层：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:187-198`

### 4.8 Memory：有 simulator memory，不是完整 agent memory

`SqstnAdapter.reset()` 每个 episode 都新建 `StateStoreV2`，只保留 16 个 event 的 bounded memory；该 memory 用来构造 synthetic respondent prompt：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:95-113`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:159-181`

policy 只看到公开回答与统计投影；private memory 明确留在 auditor artifacts 外侧：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\features.py:44-61`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:219-222`

shared cache 保存的是 prompt context → exact raw response，用于可复现 replay，不是 agent 自己检索并用于任务推理的 memory：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:182-210`

DDQN weights/MAB posterior 是学习状态，也不能自动等同于 episodic/semantic/task memory。

### 4.9 LLM participation：存在，但角色不是主 Agent

fixture pilot 的 frozen config 明确写 `synthetic_fixture_not_live_sqstn`、`api_calls: 0`，最终 scientific status 也是 engineering fixture comparison only：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_pilot.py:63-78`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_pilot.py:265-268`

live adapter 的 prompt 明确要求模型扮演“synthetic respondent”，且只能输出四个 permission labels：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:168-181`

live smoke 配置明确写 controller 是 `existing_rule_action`，循环中也确实调用固定规则，而非 LLM/RL planner：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_live_smoke.py:46-55`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\run_live_smoke.py:68-87`

o4-mini transport 只接受 prompt并返回 schema 限定的 `answer`：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\live_api.py:16-25`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\live_api.py:96-143`

多步数据收集阶段用 live respondent 枚举 response graph，然后验证 cache-only replay；学习阶段不联网：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\collect_multistep_r2.py:124-177`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_v1\SPEC_zh.md:8-16`, `:60-77`

所以“用过真实 LLM API”不等于“完整 agent 使用 LLM”。目前真实 LLM 的实验角色是**用户模拟器/数据生成器**。

## 5. 最新 Family-3 v2 并没有越过这个边界

当前设计入口称 RL 基础实现和 Family-3 v2 learner pilot 已完成，但同时明确说后续 LLM/真人路线未完成：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\README.md:3-15`

Family-3 v2 runtime 仍然从预建 graph suite 选择 `graph_id`，使用 `DeterministicAllowReuseUserV2`，为各 ordinal 预建 MockTool committed plan，再接 authorization service/reference monitor：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_environment.py:76-120`

这说明后续实验增强了 sequential credit assignment、stochastic branch、recourse、ledger binding 和安全审计，但**没有补上自然语言 task agent、planner、real tool layer 或 final response layer**。

## 6. 实验自己已经给出的 claim boundary

已有报告将 v0 定义为工程链路验证，而不是 general agent 结果：

- “证明工程链路跑通，不证明 DDQN 更优或收敛”：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\REPORT_zh.md:18-22`
- 四个真实 API prompt 内容相同，只验证接通，不是多步/拒绝泛化：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\REPORT_zh.md:29-30`
- analysis report 明确禁止把结果表述为 live S-QSTN、general agent safety 或 RL superiority：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\analysis-output\analysis-report.md:45-47`

因此这次“缺完整 agent”的判断不是推翻原实验，而是把现有实验放回它本来就声明的层级。

## 7. 当前可以与不可以声称什么

### 可以声称

- 已实现一个多步、public-observation-only 的 permission-controller MDP。
- DDQN 是真实训练的 masked value-based policy，而不是伪装成 RL 的静态分类器。
- policy、authorization ledger、reference monitor、evaluator 和 replay/evidence pipeline 已被连成闭环。
- 在 synthetic task/user/tool 环境内，reference monitor 对每个 protected effect 做执行前授权检查。
- S-QSTN prompt/memory/respondent adapter 已经接入，并做过有限 live API/cached-tree 工程验证。

### 不可以声称

- 已实现端到端 RL personal assistant / autonomous tool agent。
- agent 能理解开放式用户任务并自主分解计划。
- agent 能在多个真实工具间选择、构造参数并处理真实结果。
- agent 会根据真实 tool observation 进行语义 replanning。
- agent 有跨任务长期 memory/personalization。
- LLM 是主 planner、主 actor、security critic 或 final response generator。
- mock-domain 的零 unauthorized-effect 计数已经证明真实部署安全。

## 8. 缺失的完整 Agent 外壳，以及现有模块应放在哪里

当前代码最合理的定位不是丢弃，而是嵌入下面的完整架构：

```text
User message
    ↓
[缺失] Task interpreter / intent & constraint extractor
    ↓
[缺失] Planner：产生可修订的 task/tool plan
    ↓
[缺失] Tool registry + candidate tool-call builder
    ↓
[已有] RL permission controller
    ↓
[未来/缺失] semantic security critic（不能授予权限）
    ↓
[已有且应保留] AuthorizationService + ReferenceMonitor
    ↓
[缺失] real or sandboxed tool adapters
    ↓
[部分已有] structured observation/event normalization
    ↓
[缺失] planner diagnosis + replanning
    ↓
[缺失] user-facing final response composer
    ↓
[缺失] agent working/episodic/semantic memory
```

最小可辩护的下一阶段不必立刻做“端到端 LLM RL”。更稳妥的是先加一个**薄但完整的 agent shell**：冻结 LLM planner（不训练）+ 2–3 个 sandbox tools + 当前 permission controller + 当前 reference monitor + deterministic observation adapter + frozen response generator。这样可把研究问题保持为“RL 是否改善 permission lifecycle control”，同时实验对象终于是一个真正执行任务的 agent，而不只是独立 controller simulator。

## 9. 最终判断

一句话版本：

> **当前项目已经有一个真实的 RL permission-control agent kernel，也有相当扎实的 authorization/reference-monitor runtime；但还没有完整的 task-performing agent architecture。任务理解、计划生成、工具选择、真实工具执行、语义 replanning、最终回复和主 agent memory 仍然缺失或由 fixture 代替，LLM 目前主要扮演 synthetic user。**

因此用户的直觉是对的：若论文或项目标题要突出 “RL-based agent”，下一轮至少需要把现有 controller 接入一个端到端、可观察、可执行、可回复的 agent loop；否则最稳妥的定位应继续写成 **RL-based permission controller for agentic systems**，而不是 **RL-based personal assistant agent**。
