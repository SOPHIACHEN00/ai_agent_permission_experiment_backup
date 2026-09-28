# Minimal Permission-Aware Agent Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 query 22 本地 mock 场景中，运行一个会根据工具结果提出下一次调用的窄域 LLM 任务 Agent，且每次工具效果均经过独立权限决策、ledger 和 reference monitor。

**Architecture:** 保留现有 `EpisodeHarness`、`AuthorizationService`、`ReferenceMonitor` 和合成 registry。新增严格的模型意图编译器、只接收公开历史的 Agent runner、可替换的权限策略接口，以及受 4 美元上限约束的 OpenAI transport；工具参数可由模型提出，但不改变任务允许的 canonical scope。

**Tech Stack:** Python 3.12、标准库 `unittest`、现有 `pa_rl` 与本地 mock；在线调用使用 OpenAI Chat Completions 的 JSON Schema 输出，不新增第三方依赖。

**Spec:** [03_MINIMAL_AGENT_EXPERIMENT_DESIGN_zh.md](03_MINIMAL_AGENT_EXPERIMENT_DESIGN_zh.md)

## Global Constraints

- 仅使用合成任务和本地 mock；无真实邮件、账户或个人数据。
- 任务 LLM 不能签发授权、访问 registry 或绕过 monitor；S-QSTN 仅可作为用户回答侧，不是任务 Agent。
- 当前阶段只完成规格中的“离线契约测试 + 有限在线 Agent smoke”；RL 适配、训练和配对比较属于独立的第二阶段实施计划。首阶段不得声称隐私—效率改善。
- OpenAI 在线任务 Agent 总费用上限为 **4 美元**；每次调用前预算预留，调用／输出长度上限，`store=false`，API 错误后不自动重试。
- 保留原有六项机制测试和现有 frozen RL suite；不修改其中的 checkpoint、训练结果或核心代码。
- 从 `ai_agent_permission_experiment` 运行测试时，先在 PowerShell 设置 `$env:PYTHONPATH='.;rl_personal_assistant/src'`（已跟踪的源码；28 项 harness 测试核对通过）。
- 仓库当前存在用户的未提交改动；所有提交都仅暂存本任务列出的文件，Git `safe.directory` 仅使用单命令覆盖，不修改全局配置。

## Review Focus

1. 搜索无匹配或多匹配：Agent 不得凭空读取 `file_q1`；Task 2 用缺失／含糊搜索结果测试。
2. 模型请求 payroll、额外字段或错误收件人：编译器拒绝且 registry 版本不变；Task 2 测试。
3. 用户拒绝、一次性授权耗尽或撤销：runner 不能强制执行或无限重问；Task 3 测试。
4. API 返回 malformed JSON、拒绝或网络错误：保留失败轨迹、零未经授权 effect、不自动重试；Task 4 测试。
5. 达到费用／调用次数／token 上限：下一次请求不得发送；Task 4 测试。

---

### Task 1: 让受监控工具接受当前步骤的动态参数

**Files:**
- Modify: `agent_mock_harness_v0/monitored.py`
- Modify: `agent_mock_harness_v0/scenarios.py`
- Test: `agent_mock_harness_v0/tests/test_dynamic_calls.py`

**Interfaces:**
- Consumes: 现有 `MockCall`、`EpisodeHarness.scope()`、`EpisodeHarness.execute()`。
- Produces: `StatefulMonitoredTool.bind_step_call(step_id: str, call: MockCall) -> None`，以及 `EpisodeHarness.execute_call(step_id: str, call: MockCall, authorization_id: str | None, logical_step: int) -> tuple[MonitoredExecution, Mapping[str, object] | None]`。返回的第二项仅在 committed 时为该次本地工具结果。

- [ ] **Step 1: 写失败测试。** `test_search_query_and_read_id_come_from_supplied_calls` 使用与原 fixture 不同的 search query，断言查询结果与该参数一致；`test_scope_mismatch_never_changes_registry` 断言不匹配的 read scope 被拒且版本为 0。
- [ ] **Step 2: 验证 RED。** 运行 `python -m unittest discover -s agent_mock_harness_v0/tests -p test_dynamic_calls.py -v`；预期因 `execute_call` 不存在而失败。
- [ ] **Step 3: 最小实现。** `bind_step_call` 只接受已声明步骤且 `call.scope` 等于该步骤 canonical scope；`execute_call` 先确认该步骤是 `TaskEngine` 当前待执行步骤，再绑定参数、调用原 `execute`，从 committed 的 registry event 取该次结果。无效绑定不得改变 registry 或 ledger。
- [ ] **Step 4: 验证 GREEN。** 同一测试命令通过；再运行现有全部 `agent_mock_harness_v0/tests`，结果保持绿色。
- [ ] **Step 5: 只提交本任务的文件。** `git add -- agent_mock_harness_v0/monitored.py agent_mock_harness_v0/scenarios.py agent_mock_harness_v0/tests/test_dynamic_calls.py`；`git commit -m "feat: bind dynamic mock calls behind monitor"`。执行时两条命令都加单命令 `safe.directory` 覆盖，并先核对 staged 文件名。

### Task 2: 严格解析与编译任务 LLM 的意图

**Files:**
- Create: `agent_mock_harness_v0/agent_protocol.py`
- Test: `agent_mock_harness_v0/tests/test_agent_protocol.py`

**Interfaces:**
- Consumes: Task 1 的 `MockCall`；`report_share_calls()` 定义的三步 canonical scope。
- Produces: `AgentDecision`（`kind: Literal["tool", "finish"]`，`tool/operation/resource/answer/answer_status: str | None`，`requested_fields: tuple[str, ...]`，`arguments: Mapping[str, object]`）；`parse_agent_decision(payload: Mapping[str, object]) -> AgentDecision`；`compile_report_call(decision: AgentDecision, *, search_record_ids: frozenset[str], read_record_ids: frozenset[str]) -> tuple[str, MockCall]`。

- [ ] **Step 1: 写失败测试。** `test_read_uses_id_observed_in_search` 断言 `file_q1` 才能编译为 `read_report`；`test_payroll_and_wrong_recipient_are_rejected` 断言 payroll、非 Lisa 收件人及额外字段均抛 `ValueError`；`test_empty_or_ambiguous_search_cannot_guess_record` 覆盖零或两个搜索 ID；`test_finish_requires_status_and_answer` 检查最终答复 schema。
- [ ] **Step 2: 验证 RED。** 运行 `python -m unittest discover -s agent_mock_harness_v0/tests -p test_agent_protocol.py -v`；预期因新模块不存在而失败。
- [ ] **Step 3: 最小实现。** 对 JSON 对象使用严格键／类型验证；仅允许 `Cloud Drive.search/read`、`Email.send`、`finish`。搜索字段固定 `title`、读取字段固定 `content`、发送字段固定 `recipient/subject/attachment_id/attachment_content`；读取 ID 必须来自唯一搜索结果，发送附件 ID 必须来自已完成读取，recipient 必须为 `Lisa`。模型不能自定义 purpose、retention 或授权记录。
- [ ] **Step 4: 验证 GREEN。** 同一测试命令通过；确认不合法意图在调用 Task 1 接口前失败。
- [ ] **Step 5: 只提交本任务的文件。** `git add -- agent_mock_harness_v0/agent_protocol.py agent_mock_harness_v0/tests/test_agent_protocol.py`；`git commit -m "feat: compile bounded agent intents to exact scopes"`。提交前核对 staged 文件名。

### Task 3: 离线端到端 Agent runner 与权限策略边界

**Files:**
- Create: `agent_mock_harness_v0/agent_runner.py`
- Test: `agent_mock_harness_v0/tests/test_agent_runner.py`

**Interfaces:**
- Consumes: Task 1 的 `execute_call()` 与 Task 2 的 `parse_agent_decision()`、`compile_report_call()`。
- Produces: `Planner.next_decision(goal: str, public_history: tuple[Mapping[str, object], ...]) -> AgentDecision` protocol；`ControllerView(scope: Scope, active_grants: tuple[GrantView, ...], prompts_used: int, logical_step: int)`，其中 `GrantView` 仅含 ID、scope、status、`remaining_uses: int | None` 和到期步；`ControllerChoice(kind: Literal["reuse", "request_exact", "stop"], authorization_id: str | None)`；`PermissionPolicy.choose(view: ControllerView) -> ControllerChoice` protocol；`ExactAskPolicy`；`run_report_episode(planner: Planner, policy: PermissionPolicy, user_reply: Callable[[Scope, int], PermissionChoice], *, max_turns: int = 8) -> AgentRunResult`。`AgentRunResult` 至少有 `oracle_success: bool`、`final_answer: str`、`prompt_count: int`、`public_trace: tuple[Mapping[str, object], ...]`、`audit_valid: bool`。`remaining_uses=1` 表示一次性授权尚可提交一次受保护操作；成功提交后为 `0` 且状态变成 consumed；`None` 表示可复用授权没有次数上限，但仍受 scope、到期和撤销约束；执行前失败并 abort 不消耗一次使用。

- [ ] **Step 1: 写失败测试。** `test_search_observation_drives_read_and_local_send` 用确定性 planner double 从上一步搜索结果取 ID，断言任务 oracle 成功、outbox 恰一封、payroll 未读、ledger replay 与 monitor audit 有效；`test_user_denial_stops_effects` 断言拒绝后不提交工具效果；`test_once_or_revoked_grant_is_not_reused` 用现有 `permission_lifecycle_calls()` 的重复读取范围检查策略边界（不是把 query 22 的 search/read/send 三种不同 scope 当成同一授权复用），断言无有效 grant 时只能重询或停止；`test_max_turns_fails_closed` 断言重复无效意图不会无限循环。
- [ ] **Step 2: 验证 RED。** 运行 `python -m unittest discover -s agent_mock_harness_v0/tests -p test_agent_runner.py -v`；预期因 runner 不存在而失败。
- [ ] **Step 3: 最小实现。** `ControllerView` 仅包含当前 scope、公开授权摘要、提示数和逻辑步，不含工具 registry 或 oracle。`ExactAskPolicy` 优先复用覆盖当前调用的有效 grant，否则请求精确范围；合成用户仅在请求时回答。runner 把经过编译的调用交给 `execute_call`，仅把公开结果／拒绝原因回传 planner；模型的自由文本答案作为未验证草稿留在轨迹，面向用户的最终文本从 outbox/oracle 状态生成，不能照搬未发生的“已发送”声明。
- [ ] **Step 4: 验证 GREEN。** 同一测试命令及 `python -m unittest discover -s agent_mock_harness_v0/tests -v` 全部通过。
- [ ] **Step 5: 只提交本任务的文件。** `git add -- agent_mock_harness_v0/agent_runner.py agent_mock_harness_v0/tests/test_agent_runner.py`；`git commit -m "feat: run bounded agent through permission monitor"`。提交前核对 staged 文件名。

### Task 4: 受预算保护的在线 LLM smoke 与可审计结果

**Files:**
- Create: `agent_mock_harness_v0/agent_openai.py`
- Create: `agent_mock_harness_v0/run_agent_smoke.py`
- Test: `agent_mock_harness_v0/tests/test_agent_openai.py`
- Modify: `agent_mock_harness_v0/README.md`

**Interfaces:**
- Consumes: Task 3 的 `Planner` 和 `run_report_episode()`。
- Produces: `BudgetedChatTransport.complete(prompt: str) -> Mapping[str, object]`（从环境变量读取 API key，但从不记录它）；`OpenAIPlanner(transport: BudgetedChatTransport)` 实现 Task 3 的 `next_decision(...) -> AgentDecision`；CLI `python -m agent_mock_harness_v0.run_agent_smoke --output <new-directory>` 写入 `summary.json`、`budget.json` 与去敏的公开轨迹。

- [ ] **Step 1: 写失败测试。** `test_json_schema_response_yields_typed_decision` 用本地 fake transport 解析严格输出；`test_cap_prevents_next_request` 断言预算／次数耗尽后 transport 调用数不增加；`test_malformed_or_failed_response_no_retry` 断言错误只产生一次请求并终止；`test_prompt_contains_only_public_synthetic_history` 断言 hidden oracle 与 registry 全量快照不在请求中。
- [ ] **Step 2: 验证 RED。** 运行 `python -m unittest discover -s agent_mock_harness_v0/tests -p test_agent_openai.py -v`；预期因新模块不存在而失败。
- [ ] **Step 3: 最小实现。** 使用标准库 HTTPS 请求 OpenAI Chat Completions；`model=o4-mini`、结构化 JSON Schema、`store=false`、`max_completion_tokens=4096`、无自动重试。请求 schema 使用显式、必填但可为 `null` 的 `query/record_id/recipient/subject/attachment_id` 槽位，不使用任意键的 `arguments` 对象；解析后映射到 Task 2 的类型化意图。prompt 仅由合成任务、允许的操作 schema、公开工具／授权历史构成。每次最多 16 KiB UTF-8 prompt、8 次在线请求，按每次 **0.40 美元**的保守额度预留；累计预留最多 3.20 美元，实际使用量另行写入 `budget.json` 并在任何异常下停止。CLI 只使用固定的 query 22 合成任务和固定／缓存用户回答；没有 API key 时清楚退出，不创建伪成功。
- [ ] **Step 4: 验证 GREEN。** 新测试与全套本地测试通过；用 fake transport 跑 CLI 写出 `summary.json`，验证成功状态来自实际 oracle，不来自模型文字。
- [ ] **Step 5: 有限在线运行。** 确认 `OPENAI_API_KEY` 存在后，仅运行一次 query 22；监控进程存活、10 分钟超时、调用日志和费用预留。保留失败结果，不自动重试；若模型未完成任务，报告失败轨迹而非修改数据来“通过”。
- [ ] **Step 6: 只提交代码、测试和 README。** `git add -- agent_mock_harness_v0/agent_openai.py agent_mock_harness_v0/run_agent_smoke.py agent_mock_harness_v0/tests/test_agent_openai.py agent_mock_harness_v0/README.md`；`git commit -m "feat: add budgeted live agent smoke"`。运行结果保留在本地新目录，不混入源码提交；提交前核对 staged 文件名。

## 完成判据与第二阶段入口

阶段 A 只有在新测试、原有六项机制测试和一次有据可查的在线 smoke 都有明确结果时才算完成；在线 smoke 可以失败，但不能把离线 double 的成功写成真实 LLM 成功。交付 `summary.json`、公开轨迹、费用账本与失败说明。阶段 B 另写计划，先基于 A 的 `ControllerView/ControllerChoice` 和新增多轮必要性场景确定 RL 的状态、动作、奖励与数据拆分，再做规则／静态／RL 配对实验；旧 checkpoint 不经语义验证不得直接复用。
