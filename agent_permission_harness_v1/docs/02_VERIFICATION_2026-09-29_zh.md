# 六动作完整 Agent：实现与验证记录

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation + run / functional verification（不是统计效能验证）
- Origin Date: 2026-09-29
- Verification Status: VERIFIED for the scoped functional tests and synthetic episodes below
- Version Label: agent_permission_harness_v1
- User-approved scope: 完整 Agent＋六动作控制器＋RL 接口与接入测试；正式训练和策略比较另做。

## 结论

以下实际执行链已经连接：LLM → intent compiler → permission policy → local human/ledger → reference monitor/permit → stateful mock → public feedback → LLM → task oracle。
所有模块分独立 Python 文件，复用原 pa_rl 六动作、ledger、scope matcher 和 monitor，未修改原内核。
这证明模块接线、授权生命周期与执行强制在测试范围内有效，**不证明训练后的 RL 改善 privacy–efficiency trade-off**。

## 验证命令和结果

在 ai_agent_permission_experiment 根目录，PYTHONPATH=`.;rl_personal_assistant/src`。

| 命令 | 结果 |
|---|---|
| python -m unittest discover -s agent_permission_harness_v1/tests -q | 72 tests，OK |
| python -m unittest discover -s agent_mock_harness_v0/tests -q | 29 tests，OK |
| python -m unittest discover -s rl_personal_assistant/tests -p test_authorization.py -q | 27 tests，OK |
| python -m unittest discover -s rl_personal_assistant/tests -p test_execution.py -q | 25 tests，OK |

共153个范围内测试通过；不声称整个仓库所有 ML/长训练 suite 都通过。未运行正式训练。v0 测试输出中的费用来自注入的假 requester，不是本次额外 API 消费。
全工作树 `git diff --check` 另报已有根 README.md 末尾空行及行尾转换提示；没有修改这项无关用户改动，亦不把该检查记为全仓库通过。

新增测试包含：六动作候选/参数/mask；真实窄读取与窄写入；宽 grant 不被静默改写；窄 grant 无法扩权；一次性消耗；撤销；显式刷新 supersede；DENY 反馈；ESCALATE 暂停/同 session 恢复；消息重放拒绝；未观察 ID；非法 scope/参数/候选；无效 permit；stale/foreign/forged prepared effect；附件实际读取及变更后需重读；oracle 拒绝错误主题、虚假完成和额外工资读取。

RL 接入同时验证了 CandidateScorerPolicy 完整 episode，以及原 TabularQLearner 手填 Q 表后通过 TabularQPolicy 驱动真实 ledger/monitor/tool，Q 表未发生更新。新 schema 明确拒绝旧 fixed-seven checkpoint；不把手填 Q 值说成学习结果。

## 离线六动作 episode

目录：`results/six_action_offline_2026-09-29_001/`。

动作顺序：请求宽授权 → 刷新为窄授权 → 窄读取 → 撤销窄授权 → ESCALATE（本地澄清）→ DENY（让 planner 重提）→ 请求宽授权 → 宽读取 → finish。

- 所有6种动作均实际走 dispatcher；不是只检查 enum。
- 5 planner turns、8 controller steps、3 permission prompts、1 escalation。
- 两个实际 read effects；第一步只 title，第二步 title/private_notes。
- 旧宽 grant superseded；窄 grant revoked；新宽 grant active。
- task oracle、ledger replay、monitor audit chain 全部通过。
- hand-authored lifecycle-fixture policy + scripted planner：接线证据，不是 RL/LLM 表现。

## 原 query22 离线与真实 LLM episode

原 query 文本保留；仅 world records/业务步骤是合成。所有工具效果在本地。

| episode | planner turns | controller steps | prompts | 结果 |
|---|---:|---:|---:|---|
| results/q22_offline_2026-09-29_001 | 4 | 6 | 3 | oracle/audit success |
| results/q22_openai_2026-09-29_001 | 7 | 6 | 3 | oracle/audit success |

真实 LLM：o4-mini，7次结构化响应，3个 proposed intents 被 compiler 拒绝后重新规划（其中2次在发送前、1次在发送后），另有3次成功工具调用及终局答复。失败提议没有工具效果。没有 API transport 自动重试；planner 根据公开反馈重新提议属于 Agent 自我修正，不等于重试失败 API。
当前日志保留拒绝事件与响应 hash，但不保存被拒绝提议的完整参数，故这3次意图错误的具体参数原因尚不能仅靠保存结果重建；后续 benchmark 应增加 proposal-level trace。

实际 outbox：Email / Lisa / Q1 Financial Update / file_q1 / Synthetic Q1 revenue report。
实际 reads：file_q1.title 与 file_q1.content；未暴露工资记录。
privacy_proxy：6 field instances（2返回字段＋4发出字段），0阶段性多余字段；元数据 IDs/工具内部搜索扫描不计作 Agent 获得的数据。
CLI 人类端是固定 ALLOW_REUSE 合成回复，不是 Wu 真实用户、S-QSTN预测标签或实际发送的人类消息。默认策略是 rule，真实 LLM smoke 只走 request/execute 两种；六动作覆盖由上面的独立生命周期 episode 支撑。

## API 成本与授权

- 本次估算费用：USD **0.0134926**；usage/attempts/budget 保存在真实 LLM 目录。
- 加旧 v0 smoke USD0.0013156，已记录这两次 Agent smoke 合计 **0.0148082**。
- 每次请求前预约USD0.4，本次7次＋旧1次保守占用上界USD3.2；若本次用满8次也为USD3.6，小于用户原4美元预算。
- 仅上传当前公开任务、公开接口和合成公开历史；未上传完整工具记录、oracle、参与者问卷回答或密钥。
- 没有重跑旧失败实验，也没有失败后的自动 API retry；本次是新实现的一次新验证 session。
- 估算不是账户账单。价格参数核对依据：[OpenAI o4-mini 官方页面](https://developers.openai.com/api/docs/models/o4-mini)；结构化接口依据：[官方 Structured Outputs 指南](https://developers.openai.com/api/docs/guides/structured-outputs)。

## 发现与修复

先写核心行为测试，RED显示缺失模块，然后实现 GREEN。独立只读 review 发现搜索缺失具体资源会被当全库集合；增加失败复现后改为明确的 collection/drive.files 名称，复验零暴露且 grant 未消耗，reviewer 已确认修复并通过最后模块/CLI复查。
另修复：相同 need 的持久拒绝不能靠请求宽 scope 绕过；跨 human channel 的消息 ID 碰撞；prepared effect 内部映射可变性。原 ledger records() 是按ID排序，测试按 request_created 顺序读生命周期，未为测试修改内核。

## 尚未证明/尚未完成

1. **尚未训练新 Agent 环境的 RL 策略，也未比较 ICL/classification**；reward、状态泛化、train/test划分和统一 policy arms 另做。
2. **65来源 query 已全收录，64个尚未各自编写 task world / field mapping / business oracle。** 28外部工具＋mira 的工具层操作路径存在，不等于65任务全可完成。
3. 当前只有原query22完整业务任务，以及另写的adaptive多轮机制任务；不是通用 Agent。步骤顺序/可执行投影由可信 manifest 约束。
4. privacy_proxy 为阶段性字段计数；合成测试中窄→宽为3次读字段/0多余，始终宽为4次/1多余且均完成，但这是受控 fixture，不是 RL 性能或真实隐私损失结论。
5. 没有专门 LLM-security model、语义泄漏识别或全套 prompt-injection/red-team 评估；compiler/monitor 只强制结构性边界。
6. 可信、单线程本地 harness；不提供 OS隔离、进程级崩溃原子性或持久重启恢复。ESCALATE resume 是同一内存 session。

下一步应先把更多原 query 的必要字段、可变 scopes 和真实成功条件映射进同一执行环境，再做冻结 planner/相同用户端下的策略与组件消融。不能将旧静态分类准确率直接当这里的任务成功/隐私/打扰指标。
