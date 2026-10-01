# Six-action single-Agent permission harness v1

这是可运行、模块化的最小 **任务 Agent + 权限 harness**。任务 planner 可用真实 OpenAI LLM；工具与用户端是本地有状态模拟。原六动作 enum、授权 ledger 和 reference monitor 被实际调用，没有用日志标签替代执行强制。默认策略仍是规则基线；现已新增真实 DDQN 学习闭环和 CPU／CUDA 支持，使用独立的新环境 schema，不加载旧 Family3 权重。最新执行证据见 [DDQN 接入记录](docs/06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md)。

## 架构

```text
用户任务 → LLM 下一调用 → compiler → 参数化六动作 policy
                              ↙                 ↘
                    local human inbox        ledger
                              ↘                 ↓
                         matched reply       monitor/permit
                                                ↓
                                           local mock
                                                ↓
                                 public result/拒绝 → LLM
终局 → 隐藏必要性与业务事实 oracle
```

每个模块独立：contracts / compiler / candidates / policy / rl_policy / ledger_dispatch / human_channel / monitor_adapter / tools / planner / llm / runner / oracle / scenarios / dataset_catalog / run_agent。

## 六动作的真实效果

| 类型 | 实际行为 |
|---|---|
| REQUEST_AUTHORIZATION | 为所选窄/宽 request_scope 写本地询问；匹配回复后才能生成 grant，不自动执行 |
| REQUEST_REFRESH | 重新询问所选 scope；获准后 supersede 指定旧 grant，可扩或缩 |
| DISABLE_LOCAL_AUTHORIZATION | 使 active grant 变 revoked；不可直接复活 |
| EXECUTE_WITH_AUTHORIZATION | 对所选 actual operation_scope 校验覆盖/有效性；monitor 发一次 permit，工具才提交 |
| DENY_WITH_REASON | 零工具效果；公开拒绝原因反馈给 planner，可改计划或 incomplete |
| ESCALATE | 写 local human inbox；无回复 awaiting_human；澄清后继续，不自动授予权限 |

六个是**动作类型**，不是六个固定候选。不同 request/operation scopes、grant IDs 会生成不同候选，并由 valid mask 限制。窄执行不会偷偷改写宽 grant；真正替换授权需要 refresh + 模拟用户同意，或 disable 后重新申请。

## 运行

以下为原离线入口说明；按用户本轮要求，测试和训练只在指定 SSH 服务器的 `agenticAI` 下执行。本地仅编辑代码。规则运行不需要 torch，DDQN 需要 PyTorch。

```powershell
$env:PYTHONPATH = '.;rl_personal_assistant/src'
python -m unittest discover -s agent_permission_harness_v1/tests -q
python -m agent_permission_harness_v1.run_agent --scenario q22 --output agent_permission_harness_v1/results/my_q22_offline --export-catalog
python -m agent_permission_harness_v1.run_agent --scenario adaptive --policy lifecycle-fixture --output agent_permission_harness_v1/results/my_six_action_probe
```

每次 output 必须是新目录。写 summary.json / result.json；真实 LLM 另写 attempts.jsonl / budget.json。离线 planner 只用于确定性接线验证，不能描述为 LLM 结果。

真实 LLM：先在当前进程安全配置 `OPENAI_API_KEY`，再加 `--planner openai`。仅将任务、当步公开工具接口和公开历史交给 LLM，不传完整工具数据库、oracle、参与者回答。单 session 最多8次，保守预约0.4美元/次，预留旧 smoke 的预算；失败不自动重试。重复运行会产生额外费用，须另算总预算。

## 暂停和次数

`AgentSession(task, planner, policy, LocalHumanChannel())` 不自动回答。`run()` 返回 awaiting_message_id 后，可 `channel.submit(HumanReply(...))`，再在**同一个内存 session** 调用 run()。等待不会重复发消息、调用 LLM 或重做已提交工具效果。不支持退出进程后持久恢复。

- planner_turns：LLM/离线 planner 提议次数，默认上限8；不是授权使用次数。
- controller_steps：实际六动作 micro-step，默认上限30；请求和执行各算1步。
- prompts_used：普通权限询问＋刷新询问；escalations_used 单列，两者都应计入用户打扰。
- remaining_uses：ALLOW_ONCE 是1，实际提交后变0/consumed；ALLOW_REUSE 为None，仍受 scope、撤销和逻辑 expiry 限制，不是永久无限权限。
- expiry：逻辑 episode 步数，不是现实秒数。

## RL 接口

`rl_policy.PublicFeatureEncoder` 只编码权限结构、scope、生命周期、计数、事件类型，不读取工具结果内容、参数值或必要性 oracle。
`CandidateScorerPolicy` 接任意输出当前候选分数的模型；检查 shape/finite/mask。
`TabularQPolicy` 调用原 `pa_rl.baselines.TabularQLearner`，epsilon=0。测试使用手填 Q 值验证完整执行链，不是训练结果。
上述是旧 mapping/tabular 接口，schema 为 `agent_permission_harness_v1.public_structure.v1`，保留兼容。

本轮研究策略是 `ddqn_policy.DDQNPermissionPolicy`，调用原 `MaskedDoubleDQN.select_candidate/observe`，不使用手填 Q。新数值 schema 为 `agent_permission_harness_v1.ddqn_public_v1`（38 state／35 candidate／最多64个参数化候选）。`learning_environment` 提供逐决策边界；`learning_outcome` 只在业务 oracle、语义审计和打扰／授权暴露预算均满足时给终局1，其余0。`device_ddqn` 让网络、梯度和 Adam 可在 CUDA，replay 保留 CPU；这不是多卡训练或加速效果声明。

冻结 checkpoint 接入现有 Agent（远端根目录）：

```bash
export PYTHONPATH=.:rl_personal_assistant/src
python -m agent_permission_harness_v1.run_agent --scenario adaptive --policy ddqn --checkpoint results/pilot_300x3_cuda_001/final-17.pt --device cuda:0 --output results/ddqn_agent_eval_new
```

`--planner openai` 接入相同的 DDQN／ledger／monitor 路径，仍保留原 API 预算限制。本轮没有调用付费 API；因此离线 pilot 不能冒称真实 LLM 实验。ICL／classification 尚未在这个动态 Agent 环境中重新对齐比较。

## 覆盖与证据边界

完整来源目录：原65 queries / 8领域 / 28外部工具，以及 mira 内部读通道；373问卷 contexts 保留。工具层实现所有已有声明的7类操作路径，但仅是统一合成状态机，不是真实商家/支付/门锁连接。
显式搜索集合只有各工具的 `collection` 和 Cloud Drive 的 `drive.files`；其他不存在的具体资源会失败，不能自动变成全库搜索。

业务 oracle 已写：query22 的共享报告；另有独立人工设计的 adaptive_read 生命周期 probe。**其余64个原 query 还没有各自可执行任务世界/业务 oracle**，清单收录不等于任务完成覆盖。
privacy_proxy 统计阶段性实际字段暴露及多余字段次数，是合成实验代理，不是差分隐私、内容语义泄漏或全面安全保证。自由文本发送、提示注入、恶意工具输出需后续独立安全评估；本版没有声称完成 LLM-security 模型。
mock 数据、reference monitor、任务 manifests 与解释器属于可信 harness；这不是 OS sandbox，不能防御任意 Python 代码读取内部对象。
S-QSTN 不是本任务 Agent 的 RL 输入、状态或训练数据。本次 CLI 只用固定合成回复并明确记录来源。

设计：[docs/00_DESIGN_zh.md](docs/00_DESIGN_zh.md)；来源覆盖：[docs/01_DATASET_COVERAGE_zh.md](docs/01_DATASET_COVERAGE_zh.md)；测试记录：[docs/02_VERIFICATION_2026-09-29_zh.md](docs/02_VERIFICATION_2026-09-29_zh.md)。

## 2026-09-29：后续设计与 recap

- [已批准的 DDQN 接入 recap](docs/03_APPROVED_DDQN_RECAP_zh.md)：新 38/35 编码、六动作、transition/reward 边界，以及当前尚未实现的部分。
- [安全检查器接入设计](docs/04_SECURITY_CHECKER_DESIGN_zh.md)：pre-action / release 两处检查、结构化输出与 DDQN / ledger / monitor 的分工。
- [安全模型微调与消融方案](docs/05_SECURITY_CHECKER_FINETUNING_AND_ABLATIONS_zh.md)：数据分组、LoRA SFT、独立评价与 2×3 对照。

上述文件保留设计时的历史状态；新 DDQN 已实现，实际测试／训练证据以 [最新记录](docs/06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md) 为准。fine-tuned security checker 仍只是设计，未实现或训练。
