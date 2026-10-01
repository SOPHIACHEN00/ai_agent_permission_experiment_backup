# RL 动作、S-QSTN query 来源与完整覆盖边界核查

日期：2026-09-29。本文解决六动作与三选择的层级混淆，并记录原始数据来源；不是新的 RL 训练或 Agent 效果报告。

## Material Passport

- Origin Skill: `academic-research-suite` / `experiment-agent`
- Origin Mode: `plan`（本地源码与数据关联核查）
- Origin Date: `2026-09-29`
- Verification Status: `ANALYZED`（源码、逐项数据关联和计数已核对；新 adapter、完整任务 oracle 与效果比较尚未实现）
- Version Label: `rl_actions_query_provenance_audit_v1`
- 数据边界：本地读取公开问卷与已有合成产物，没有新增 API 调用，没有改动冻结的 RL 实验。

## 1. 六动作没有被改成三动作

原 RL 的 [ControllerAction](../../rl_personal_assistant/src/pa_rl/contracts.py) 仍包含六种动作。最小 Agent 的 [ControllerChoice](../agent_runner.py) 是另一层临时 smoke 接口，只有 `reuse / request_exact / stop`。

| 原 RL 动作类型 | 原有含义 | 当前 Agent runner 的缺口 |
|---|---|---|
| `REQUEST_AUTHORIZATION` | 为指定 scope 请求新授权 | `request_exact` 只支持该步固定精确 scope；不能选择窄/宽候选。 |
| `REQUEST_REFRESH` | 为已有授权请求新 scope / 新授权；获准后替代旧授权 | 未暴露给策略。 |
| `DISABLE_LOCAL_AUTHORIZATION` | 停用已有本地授权 | 脚本机制 probe 可以调用 ledger.disable，但 Agent 策略不能选择。 |
| `EXECUTE_WITH_AUTHORIZATION` | 使用有效授权执行一个受保护操作 | `reuse` 或新授权之后 runner 自动执行，请求与执行没有分成两次控制决策。 |
| `DENY_WITH_REASON` | 拒绝并记录理由 | `stop` 没有提供完整的拒绝理由语义。 |
| `ESCALATE` | 转交人类处理 | 没有独立的升级动作或目标。 |

因此，三选择是新增集成层尚未接齐原接口，不是把 RL 重新设计为三个动作。原 six-action 核心与旧训练结果无需因为这个 smoke 的限制而推倒重做。

## 2. 窄/宽范围已经存在，但不是所有 suite 都具备同一种能力

### Family-3 v2

[CandidateRoleV2](../../rl_personal_assistant/src/pa_rl/family3_v2_contracts.py) 有七个候选：

`request_narrow, request_broader, execute_covering, refresh_closed, disable_active, deny, escalate`。

其中前两个都映射为 `REQUEST_AUTHORIZATION`，只是 scope 参数不同。因此是六种动作类型、七个参数化候选；候选数也不等于每个状态下合法动作数。

[model](../../rl_personal_assistant/src/pa_rl/family3_v2_model.py) 与 [environment](../../rl_personal_assistant/src/pa_rl/family3_v2_environment.py) 确实将选中的窄/宽 scope 派发给回答器并记录入 ledger。该 suite 在请求后关闭 offer；refresh 没有合法的可刷新授权。它研究的是初始授权范围及后续任务的权衡，不是执行中自动修改已有 grant 的 scope，也不是读取字段的真实裁剪实验。

### 通用 RL / RL–S-QSTN fixture

[PermissionEnvironment](../../rl_personal_assistant/src/pa_rl/environment.py) 的请求/刷新候选使用当前固定 `TaskStep.scope`。[multistep_v1](../../rl_sqstn_integration_v0/multistep_v1.py) 的 `scope_denial` 将第二步从 title 预定扩展到 title + private_notes，用来检查范围变化后的授权行为；这不是 RL 自主选择窄/宽读取。

### 最小 Agent query 22

[编译器](../agent_protocol.py) 与 [scenarios](../scenarios.py) 将 search/read/send 字段固定；[TaskEngine.authoritative_step](../../rl_personal_assistant/src/pa_rl/execution.py) 要求执行 scope 与预定 step 完全相等。这是集成测试过小和接口未接齐的共同限制。

必须区分：选择较窄的请求授权、在宽授权内实际只访问较小字段集合、缩减已存在的授权记录。旧代码不能被笼统宣称已经完成这三件事。ledger 的 refresh/disable 可以支持授权替换与停用；自动无提示缩减原 grant 没有现成专用 API。

## 3. 修复方向：复用六动作语义，另建 Agent adapter 版本

1. Agent 策略接口使用既有六种 `ControllerAction`，并显式携带 `request_scope`、`operation_scope`、`authorization_id` 和 `prior_authorization_id`。范围大小作为动作参数，不必仅因需要 narrow/broader 就另造动作类型。
2. 将权限控制 micro-step 与 LLM tool-step 分开。一次工具意图可以先经历请求、回答、刷新或停用，再由控制器选择执行；不要在授权返回后自动绕过后续策略决策。
3. 每步生成有限、类型化、可掩码的 scope 候选。mask 判断机械合法性，不把隐藏的任务必要性标签作为选择答案。
4. 请求范围与执行范围分开：较宽 grant 可以覆盖较窄的实际操作；扩大权限需要新的实际用户模拟回答。预测的四类回答不能自行伪装成用户授权。
5. 若要比较真实数据获取/传递范围，新的任务 manifest 必须允许明确的替代执行投影，mock 返回与发送须真正裁剪字段。旧 TaskEngine 的精确 scope 检查不能被简单绕开。
6. 旧 Family-3 checkpoint 的固定七候选和编码，与 RL–S-QSTN encoder 以及 Agent 的四字段 ControllerView 不同。新 adapter 必须验证语义与 shape；改变训练环境后产物标为新版本。

上述是定位后的解决方案；本次没有声称六动作已全部接入 Agent runner。

## 4. 静态 S-QSTN 问卷的 query 来自 Wu 原问卷

实际数据链：

`external/ai-agent-permissions/queries.json + data/user_study.json`
`→ src/build_dataset.py → data/processed/four_label_dataset.csv`
`→ qstn_simulator/scripts/build_qstn_inputs.py → questionnaire_items.csv`
`→ in_context_learning/sqstn_pilot/sqstn_backend.py → 合成授权回答`。

- [build_dataset](../../src/build_dataset.py) 用原始 task3 的 query ID 查原 `queries.json`，直接取原 query 文本；tool/data item 来自原回答 key。
- [build_qstn_inputs](../../qstn_simulator/scripts/build_qstn_inputs.py) 从上述数据去重构造一个 query × tool × raw_data_type 对应的问卷 item，提示拼接原用户请求、工具、数据项。只规范显示空白。
- [sqstn_backend](../../in_context_learning/sqstn_pilot/sqstn_backend.py) 按完整 context 与 query 文本匹配问卷 item；找不到即拒绝，不能任意替换 query。

### 本次逐项关联检查

| 数据层 | 已核对计数与来源 |
|---|---|
| Wu 原 `queries.json` | 65 queries，ID 0–64，8 个领域，28 个非空原始 tool1/tool2 标签。 |
| 四标签处理数据 | 16,361 回答记录，201 用户，65 queries，373 个唯一 query × tool × data item 上下文。 |
| S-QSTN `questionnaire_items.csv` | 373 items，65 queries；与处理数据 context 集合没有新增、没有缺失。 |
| 文本匹配 | 处理数据原 query 及问卷中拼接的原 query，在规范空白后均为 0 mismatch。 |
| 最近静态 S-QSTN pilot | 20 用户，624 回答（350 history + 274 test），250 唯一 contexts，56 个原 query；624 项均能对应原来源记录。 |

373 是权限问题组合数，不是 373 个新任务；模拟的是回答，不是重新创作用户任务。

pilot 未覆盖的原 query IDs：`5, 7, 9, 15, 20, 22, 36, 39, 47`。因此当前 Agent 的 query 22 **不在这批 624 个已冻结模拟回答中**，不能假定有现成回答可直接复用。

## 5. 另有新造的工程任务，不能混同为原问卷

[rl_sqstn_integration_v0/fixtures.py](../../rl_sqstn_integration_v0/fixtures.py) 明确构造新的合成 Calendar 场景；[multistep_v1.py](../../rl_sqstn_integration_v0/multistep_v1.py) 构造 continuous、once、scope_denial、disable_refresh 多轮任务家族。

[S-QSTN v2 memory fixture](../../qstn_simulator/scripts/v2/build_memory_fixtures_v2.py) 也新建了六组无标签事件诊断。它们用于生命周期或记忆机制测试，没有 Wu 原 query 的人类回答真值。

结论要分数据路线：静态问卷与最近 ICL synthetic pilot 沿用原 query；RL–S-QSTN 的小型工程环境确实有新任务。

## 6. 完整覆盖目标：全部原 query、原工具标签及内部数据访问

用户本轮要求后续纳入全部 query 和 tools。正式目标是原 65 queries 全部进入版本化任务 manifest，28 个外部原始工具标签全部保留；query 22 仅作为调试入口，不能代替这个目标。

还须覆盖原问卷的 `mira` 内部 Agent 数据访问通道：

- 原外部 tool1/tool2 有 28 标签，当前 mock catalog 全部存在。
- 原处理数据/问卷有 24 个实际回答 tool 标签：23 外部标签 + `mira`。
- 当前 mock catalog 未包含 `mira`。应为信息进入任务 Agent/LLM 的过程设置受 monitor 管理的本地合成数据入口，保留原标签和映射；它不是第 29 个外部厂商工具。
- 原 catalog 中 Energy Management、Health Records、Investment、Security Camera、Smart Lock 没有单独的外部工具回答 context，不能因此从全 query/tool 覆盖删除。

每个 query 的 manifest 至少记录原 ID/文本、领域、外部工具和内部数据入口、原始 data item 与合成字段映射、步骤与候选 scope、初始 mock 状态、成功 oracle、可允许的拒绝/升级终局及实现/验证状态。自然语言任务题干保持原始；多轮变体明确记录 `parent_query_id` 和变体版本。

覆盖应分别报告：任务 manifest 收录、字段/数据项可执行、六动作及 scope 变体验证、真实/缓存 LLM 闭环、任务 oracle 通过。已有 28 工具/69 操作 smoke 并不意味着 65 完整任务已经完成。

完整问卷包含 373 个静态权限 contexts；已冻结 pilot 只覆盖其中 250 个，不能把它当作全范围动态回答缓存。动态 request/operation/recipient/retention 变体也需要明确的 scope-aware 回答协议与缓存，不从原静态标签默默推导新真值。
