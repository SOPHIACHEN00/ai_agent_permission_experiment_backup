# Family-3 v2 CUDA v1：服务器最小试跑报告

日期：2026-09-21（America/Toronto；服务器回执 UTC 为 2026-09-22）。
状态：**CUDA_BOUNDED_SMOKE_POSTFLIGHT_PASS**。

## 结论与范围

已完成独立 CUDA 执行版本，并在服务器物理 GPU 1 完成唯一一次非证据小试跑。GPU 2 未使用。该结果证明 DDQN 的 GPU 更新、checkpoint 保存/重载和评估链路连通，不证明 DDQN 优于基线，也不代表正式验证门槛通过。

- 本地版本：`ai_agent_permission_experiment/rl_personal_assistant_cuda_v1`。
- 服务器版本：`/output/agenticAI/family3_v2_cuda_v1/rl_personal_assistant`。
- 原服务器基线仍位于 `/output/agenticAI/family3_v2_pilot_task8_d7064176/rl_personal_assistant`，99/99 文件无改动。
- 仅 3 个生产模块有变化：`family3_v2_learning.py`、`family3_v2_learner_pilot.py`、`family3_v2_pilot_checkpoints.py`。新增设备测试、变体说明、manifest 和验证器。
- 科研配置、划分、seed、预算、门槛、认证环境、exact DP 和冻结 `ddqn.py` 保持不变；CUDA manifest 的 103 个文件全部通过校验。
- 使用 daily-coding / planning-with-files 等技能的最小流程，保留 RED、GREEN、独立窄复核与恢复断点；遵循用户要求，没有扩展到完整回归或崩溃矩阵。

## 实际证据

| 检查 | 已验证结果 |
| --- | --- |
| 两项 CUDA 测试 | 2/2 通过，unittest 2.137 秒；整个子进程 4.271 秒 |
| 冻结检查 / 试跑后 inspect | 均 exit 0 |
| 唯一一次 smoke | exit 0，28.512 秒（子进程墙钟时间） |
| 训练量 | seed 17，4 个方法各 320 transitions，共 1,280 |
| 保存模型 | 4 个 final checkpoint；重载指纹全部一致 |
| DDQN 更新 | gamma0 / gamma1 各 17 次；online/target 与 Adam 动量重载后均为 CUDA |
| 评估 | 28 条 validation 记录，0 条 test 记录 |
| 安全与完整性 | 逐行汇总和验证阶段的 26 项 hard counts 全为 0 |
| 设备 | 仅一个 CUDA 可见设备；UUID 与物理 GPU 1 比对一致（不保存原始 UUID） |
| 正式实验与 test | 正式根目录不存在；test 目录、许可、开启标记均不存在 |
| 科学分类 | null；run_status 为 NON_EVIDENCE_SMOKE_COMPLETE |

DDQN 的模型前向、反向、批张量与优化器在 GPU 执行；环境仿真、特征编码、经验回放存储及 Tabular-Q 仍是常规 CPU 端操作。这不是启动一个单独的 CPU 对照实验，也不宣称整条流程都运行于 GPU。本轮未运行本地 RL 测试或训练，未安装依赖，未调用 OpenAI API。不能把此前本地 smoke 时间与本轮时间作严格加速比比较。

## 复核与两处收尾工具错误

独立静态窄复核没有 Critical / Important 问题。一个 Minor 保留：运行中修改 CUDA_VISIBLE_DEVICES 时，某个 runtime helper 没有独立比较旧设备身份；本次进程环境固定，没有设备热切换，边界重开仍检查身份。此版本只声明固定设备环境下的验证，不声明运行中切卡支持。

1. RED 包装器把测试方法数 2 当作失败计数；实际 1 个主断言及 3 个子测试共 4 个预期失败、0 errors。原 STOP_UNEXPECTED_RED 回执和原日志保留，另存解释；未重跑 RED 或放宽测试。
2. 初次只读 postflight 错把 hard_counts 当作 final_verdict 顶层字段，产生 KeyError。此时设备、checkpoint、28 行及行安全计数已核验。查明真实结构后，从已验证的 validation gate 读取计数，并完成余下校验；不修改产品、不可变 smoke 结果或重跑训练。原错误回执保留，另存 completion receipt。

权威完成证据为 `evidence/cuda_postflight_completion_receipt.json`。早期 `cuda_execution_receipt.json` 的 POSTFLIGHT_PENDING 和初次 postflight 错误是历史快照，不能覆盖最新补充完成回执。

## 证据归档与断点

- 本地 `evidence/cuda_smoke_evidence.zip`：54 entries，557620 bytes。
- ZIP SHA-256：`fcefecf467dd8226d1244f7726676fa8724fa7b35b7ec040c4bd1f27f3181d2d`。
- CUDA source manifest SHA-256：`320cbf4175ddfb815d0517a08e8ab8d5952c8f99cc46b6a999a4cb9fb0e86d84`。
- ZIP 包含原始检查日志、历史及补充回执、变体 manifest、完整 smoke 产物；本地已安全解包并通过 ZIP CRC 检查。
- 服务器证据位于 CUDA 项目父目录；认证信息未写入项目文件。连接已关闭，本轮未留下后台训练任务。
- 恢复先读本报告、task_plan.md 和 completion receipt。**不得重跑或覆盖已完成 smoke。**
- 下一阶段是同一冻结配置下的服务器正式 train-validate；本轮没有启动。正式 test 继续保持关闭，之后依据 validation 结果及显式授权处理。

