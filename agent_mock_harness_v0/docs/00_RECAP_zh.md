# 本地 mock harness：下次从这里回顾

更新：2026-09-28。本文记录当前代码状态，不把下一步计划写成已完成结果。

## 一句话定位

当前版本是「现有权限 ledger + reference monitor → 有状态的本地 mock 工具 → 本地任务结果检查」的机制验证夹具。它**不是**完整 Agent，也尚未连接 LLM planner 或学习后的 RL 权限策略。

## 已完成

- 从 [Wu 发布的 queries.json](../../external/ai-agent-permissions/queries.json) 读取 65 条 query；按原始 `tool1/tool2` 字符串统计为 28 个工具标签。论文概括的 21 类工具与 JSON 原始标签不是同一计数口径。
- 28 个标签都有合成记录；通过统一的 `search/read/create/update/send/book/control` 引擎，声明了 69 个「工具 × 操作」组合，并逐组合做了本地 smoke test。
- 接入原有 `AuthorizationService` 和 `ReferenceMonitor`，没有修改冻结的 RL suite 核心代码。
- 做了两组多轮机制 probe：query ID 22 的云盘→邮件任务，以及三轮重复读取测试一次性授权、复用和撤销。
- 截至本记录，`unittest` 的 6 项测试通过；测试包含授权缺失、范围扩大、无效 permit、授权消耗/撤销、审计链与 ledger replay。

## 尚未完成，不能误写成贡献

- 尚无 LLM 自主规划/动态选择工具及参数；`MockCall` 在场景代码中预先指定。
- 尚未把真实 RL policy 接到这个 harness，因而没有效率—隐私权衡的对照实验结论。
- 尚未为 65 条 query 分别做任务状态、转移和成功 oracle；现在只有 2 条专门设计的多轮 probe。
- 28 个 mock 是浅层统一操作，不是 28 个真实服务 API 的语义复刻。
- 没有真实外部通信、真实私人数据、分布式执行或崩溃恢复保证。

## 阅读入口

1. [01_MOCK_TOOLS_DESIGN_zh.md](01_MOCK_TOOLS_DESIGN_zh.md)：数据结构、七种操作、授权边界、一次调用的生命周期。
2. [02_MECHANISM_TESTS_AND_NEXT_EXPERIMENT_zh.md](02_MECHANISM_TESTS_AND_NEXT_EXPERIMENT_zh.md)：已跑的多轮检查、可记录的指标、待做的策略对照与消融。
3. [现有 README](../README.md)：最短运行命令与英文概述。

核心实现：[catalog.py](../catalog.py)、[monitored.py](../monitored.py)、[scenarios.py](../scenarios.py)。验证：[test_mock_tools.py](../tests/test_mock_tools.py)、[test_mechanisms.py](../tests/test_mechanisms.py)。

## 复现命令

在 `ai_agent_permission_experiment` 目录用 Python 3.12 运行：

```powershell
$env:PYTHONPATH='.;rl_personal_assistant_cuda_v1/src'
python -m unittest discover -s agent_mock_harness_v0/tests -v
```

## 下次最短决策

如果目标是尽快得到一条可信的研究证据链，不应先声称全 65 任务完成。先固定少数任务的 planner trace，接入实际 RL 策略，在同一 mock 初始状态下与静态授权策略比较任务成功、用户提示次数和不必要的数据访问；ledger/monitor 的移除测试只在纯合成环境进行。
