# 模块化六动作单 Agent 设计

依据：已批准的最小 Agent 设计、本轮六动作/模块独立/本地 ESCALATE 要求，以及用户选择的“RL 接口和接入测试；正式训练另做”。

## 执行链
LLM → 编译器 → 六动作候选与策略 → 人类模拟端/ledger → monitor → 本地工具 → 公开反馈 → LLM → oracle。

## 模块
- contracts.py：TaskStepSpec、TaskDefinition、CompiledCall、GrantView、ControlCandidate、ControlView、AgentResult。
- compiler.py：把 AgentDecision 编译为当步允许的工具意图；模型不能改写授权或隐藏 oracle。
- candidates.py：六动作与参数化范围/授权身份；生成合法性 mask。
- ledger_dispatch.py：请求、刷新、停用、拒绝、升级及执行的调度；请求不自动执行。
- human_channel.py：本地 permission/escalation inbox、匹配回复、一次消费与暂停恢复。
- tools.py：七类本地有状态操作；28 外部标签与 mira；字段裁剪及读取/发送记录。
- monitor_adapter.py：预声明投影 TaskEngine 与 monitor-issued permit 工具适配器；旧 monitor 不变。
- policy.py：确定性规则基线，使用同一候选接口。
- rl_policy.py：公开特征编码、合法候选打分适配与真实 TabularQLearner 接口；旧 checkpoint schema 不自动兼容。
- runner.py：独立 planner turn 与 controller micro-step，暂停/恢复、反馈、失败和预算步数。
- planner.py / llm.py：任务 planner 协议与结构化 OpenAI 提议，不接触 registry。
- oracle.py / scenarios.py：合成任务定义、必要性与终局事实校验。
- dataset_catalog.py：完整原65 query/28工具及 mira 的来源、context 与覆盖清单。
- run_agent.py：离线/可选真实 LLM 入口与可审计输出。

## 共用接口
TaskStepSpec(step_id, operation_scopes, request_scopes, arguments, require_observed_record=False)；scope 均为已有 pa_rl.contracts.Scope。
TaskDefinition(scenario_id, goal, steps, records, oracle)；oracle 是受信任评估器，不能进入 planner/policy observation。
CompiledCall(step_id, scope, arguments)。
GrantView(authorization_id, scope, status, remaining_uses, expires_at_step)。
ControlCandidate(candidate_id, action, request_scope=None, operation_scope=None, authorization_id=None, prior_authorization_id=None, reason_code=None, escalation_target=None, valid=True, invalid_reason=None)。
ControlView(pending, grants, candidates, public_history, logical_step, prompts_used)。
PermissionPolicy.choose(view) 返回候选 ID；runner 重新核对是否属于当前目录和 mask。

人类接口：HumanMessage(message_id, kind, task_goal, step_id, requested_scope, logical_step, reason)；HumanReply(message_id, kind, permission=None, text='')。LocalHumanChannel.send(...)、submit(reply)、take_reply(message_id)、snapshot()。reply kind 为 permission/clarification/deny/stop；仅 permission 携带 PermissionChoice。

工具接口：LocalToolStore(records)、prepare(CompiledCall)→PreparedEffect、commit(PreparedEffect)→Mapping、snapshot()。scope 决定真实返回/写入字段；结果不增加未批准字段。ExecutionAdapter(task, store, ledger).execute(call, authorization_id, logical_step)→(MonitoredExecution, tool_result)。

## 权限语义
请求和刷新是独立 micro-step；只有匹配 scope 的真实模拟回复使 ledger grant 生效。execute 只使用覆盖实际 operation_scope 的有效 grant。停用不可自动恢复。拒绝或澄清反馈给 LLM 允许重新计划；ESCALATE 写本地 human inbox，没有回复时返回 awaiting_human，同一 session 可继续。

窄执行投影必须是 task manifest 预声明的合法选项，monitor 按实际投影校验；宽 grant 本身不会被偷偷改窄。将宽 grant 换成窄 grant 可显式 refresh 并获准或 disable 后请求。任务必要性标签只用于 oracle/指标，不用于候选 mask 给出答案。

## 验收
真实 ledger/monitor/tool 状态下分别验证六动作；窄/宽请求、部分字段实际读取、扩权重问、刷新 supersede、一次性消耗、撤销、拒绝反馈、升级暂停/恢复、消息重放拒绝、非法候选零效果、scope 越界零效果、oracle 事实最终答复。RL 接入测试验证公开特征、mask 与调度一致，不声称策略已训练或优于 baseline。

原65 query 和所有工具进入来源清单；完整业务 oracle 的覆盖单独标记，不能以工具列表或通用 CRUD 成功替代原任务成功。
