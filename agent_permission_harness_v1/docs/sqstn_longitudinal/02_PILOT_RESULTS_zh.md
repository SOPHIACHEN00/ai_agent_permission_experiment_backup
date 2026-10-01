# S-QSTN—每用户独立 DDQN 小测试：结果记录

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation / remote test / bounded live probe
- Origin Date: 2026-09-29
- Verification Status: MECHANICS VERIFIED；LIVE ABORTED AT NETWORK PROBE
- Version Label: sqstn-longitudinal-results-v1

## 本次执行状态

**服务器实现、133项机械测试和独立复核已完成；真实请求在第一笔任务模型网络探测时中止，训练/评估均未开始。** 不能把假HTTP测试当作LLM实验或偏好学习收益。

| 项目 | 本次状态 |
|---|---|
| 新代码实现 | 已在指定HyperAI项目完成，独立复核完成，唯一发现已修复 |
| 远端接口/安全测试 | 最终133/133通过；含原103项回归、真实CUDA优化和CPU→CUDA恢复 |
| 有状态 S-QSTN 付费往返 | 未运行 |
| 每用户连续 DDQN 训练 | 未运行 |
| 冻结前后对照 | 未运行 |
| 新 DDQN + live task LLM + S-QSTN | 未运行 |
| 本次 OpenAI 请求尝试及费用 | task 1次、human 0次；已知usage上界0美元，未知费用预留0.60美元，不能称实耗0或已花0.60 |
| 内部文档上传 | 无；全部本地保存 |

已批准规模为3名独立用户各12个连续训练任务、之后6个冻结评估任务。任务模型OpenAI/gpt-6-luna、人类端OpenAI/o4-mini，角色硬预算分别5/4美元。该规模尚无live样本；密钥仅经加密非回显进程输入传至服务器，未写入文件或提示。网络失败发生在验证账户/模型能力之前，不能据此判断模型不支持或余额不足。

## 真实探测的停止原因

- run目录：`agent_permission_harness_v1/results/sqstn_longitudinal_20260929_001`；启动为独立服务器进程，30分钟硬超时，无自动重试。
- UTC 2026-09-30 03:26:53开始探测，03:28:23中止（本地Toronto仍为9月29日）。
- 首个`gpt-6-luna`请求发生`URLError`，stage=request，没有模型回复/usage。全局费用闸门停止；human端未调用，train=0、eval=0、D=0。
- 不带密钥的`curl -I --connect-timeout 8 --max-time 15 https://api.openai.com/`同样失败：443连接超时（exit28，约8002毫秒）。检查时服务器未设置HTTP/HTTPS/ALL_PROXY变量。只能确定该时点出网不可达，不据此断言具体DNS/地域/供应商原因。
- 下一步需要可用的服务器出网方案或用户批准的代理，然后另行确认恢复；保留原账本，未知0.60美元仍占任务端限额，不得新建账本抹掉。
- 证据：[summary.json](../../results/sqstn_longitudinal_20260929_001/summary.json)、[预算流水](../../results/sqstn_longitudinal_20260929_001/budget/attempts.jsonl)、[无密钥连接诊断](../../results/sqstn_longitudinal_20260929_001/network_head.txt)、[源码及产物清单](../../results/sqstn_longitudinal_20260929_001/artifacts.sha256)。

当前可支持的结论是“系统接线、跨任务训练机制和权限边界已通过机械验证”；**尚不能说明S-QSTN在线交互学得好不好、偏好适应有效，或效率—隐私权衡有改善。**

## 本次机械验证证据

- 远端：`/hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001`（解析为`/output/agenticAI/ddqn_agent_bridge_20260929_001`），4×RTX3090。
- 命令：`env PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m unittest discover -s agent_permission_harness_v1/tests -v`。
- [最终完整测试日志](../../results/sqstn_impl_checks_20260929_001/full_suite_final.log)：133项、17.237秒、OK。所有测试均在服务器运行。
- [最终代码SHA256清单](../../results/sqstn_impl_checks_20260929_001/final_source.sha256)：18个生产/测试文件，已只读验证与本地备份全部匹配。
- S-QSTN桥接真实v2规则与StateStore，正确等待pending请求；人类回答经内核消费后才写记忆。跨任务保留人类记忆/learner，但不保留grant；跨用户隔离。
- 强制权限动作的两任务fixture产生8条真实transition、replay=8和1次optimizer update；这是接线证据，不是DDQN自然学出的策略。
- 完整三用户fixture覆盖36训练+6冻结评估；冻结前后训练状态hash不变。持续澄清的另一fixture用尽129个人类调用时，独立D阶段正确中止，36+6记录仍保留，未伪造奖励。
- GPU RNG隔离发现并修复；续训格式保留online/target/optimizer/replay/RNG/去重/人类记忆，预算账本变化或未知费用阻止旧快照重跑。
- 七类scope攻击（无、过期、耗尽、禁用、工具/字段/接收者不匹配）均被阻止且mock无变化；六动作生命周期继续通过。
- **内容边界诊断为缺口：** 合法send.body包含已合法读取的合成敏感canary，实际进入本地outbox。`content_flow_gap_observed=true`。当前系统不能宣称通用语义防泄漏。

完整实施过程和过程决定见[实施ledger](04_IMPLEMENTATION_LEDGER_zh.md)。内部文档从未同步到服务器；服务器仅收到必需代码/测试及合成运行资产。

## 静态核对结果（不是运行测试）

- 有 HumanWait/resume 接口，但现有 drive_episode 遇到等待即返回。
- 旧 SqstnAdapter 的 reset 清空用户记忆，与本次跨任务要求不符。
- S-QSTN v2 memory view 不暴露具体 answer，需要新增受限问答记忆视图。
- 现有 DDQN 默认 warmup=256，小样本需单独配置并验证真实 optimizer updates。
- 现有 checkpoint 为 frozen inference 格式，不含 optimizer/replay/RNG，不能直接称为续训快照。
- 当前 authority/monitor 针对实际授权和 scope，不构成任意内容的语义防泄漏保证。

## 后续实际执行必须回填的证据

1. 远端目录、实际命令、源码/规则/模型/配置哈希、设备与运行时间。
2. 各测试通过/失败分子分母与日志路径；所有失败单独保留。
3. 每用户逐任务：实际人类回复、动作、训练更新、任务成功、打扰、授权暴露、多余读取/发送。
4. 冻结前后逐条配对结果；网络/replay/optimizer 不变证据。
5. 缩权/扩权生命周期和 monitor 拒绝后的无副作用证据。
6. 完整费用账、失败/未知费用预留、实际调用次数；预算中止与任务失败分开。
7. 结论分级：机制接通 / 确有训练 / 初步行为改善 / 尚无改善证据。不得用更低一级替代更高一级。

## 旧实验不是本次结果

上一轮 `pilot_300x3_cuda_001` 使用固定人类回复及 offline planner，不是 S-QSTN 长期交互。其报告保留在 [06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md](../06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md)，不将其计入本次样本。
