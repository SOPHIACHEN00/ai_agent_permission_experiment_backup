# RL Personal Assistant Design

本目录保存从 classification/MAB 进入 sequential RL、security LLM 与 Constitutional AI 的研究设计和实施记录。RL 基础实现与 Family-3 v2 learner pilot 已完成；后续 LLM/真人路线仍不能视为已完成。

## 最新入口（2026-09-22）

- [当前：GPU1正式训练与验证完成，科研门槛未通过](experiments/2026-09-22_family3_next_stage/stage_b/formal_gpu01_v1/report.md)：72000步/6模型/3600validation全部完成、安全计数0；gamma1三个seed精确值0.5125/0.6375/0，均未近最优。完整证据已下载核验，test关闭；不自动补训/调参。最新仅允许GPU0/1。

- [历史：两处修复及GPU2最小试跑](experiments/2026-09-22_family3_next_stage/stage_b/B2_SMOKE_RESULTS_zh.md)：320步接入证据原样保留；后续正式GPU1运行见上方当前报告。先前失败与[B1随机数修复](experiments/2026-09-22_family3_next_stage/stage_b/RNG_FIX_zh.md)记录保留。

- [历史：Stage A 6/6检查、20/20结构核验及独立复核](experiments/2026-09-22_family3_next_stage/stage_a/RESULTS_zh.md)：强规则在全部test条件已最优，随后已获批改为近最优学习目标；旧证据与原失败保留。

- [下一轮中英文实验设计与候选配置](experiments/2026-09-22_family3_next_stage/EXPERIMENT_DESIGN_zh.md)：共享预算与明确追加授权；原设计归档，目标修订见stage_b/GOAL_AMENDMENT_zh_en.md，当前实现状态以上方Stage B断点为准。
- [已完成实验结果、规则持平机制与解释更正](experiments/2026-09-22_family3_next_stage/RESULTS_ARCHIVE_zh.md)：包括原始ZIP索引、逐seed CSV和校验信息。
- [主进展记录](RL_IMPLEMENTATION_PROGRESS_LOG.md)与[主决策记录](RL_IMPLEMENTATION_DECISION_LOG.md)：连续历史与当前断点。

## 建议阅读顺序

1. [`RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md`](RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md)：主设计、实验协议、实施步骤、阶段 gates 与待讨论决策。
2. [`notes.md`](notes.md)：项目证据、外部方法依据、框架比较和开放决策记录。
3. [`task_plan.md`](task_plan.md)：本次设计任务的进度与审计记录。

## 当前推荐主线

```text
基础 authorization/privacy rules + ledger + RL environment
→ masked Double DQN / masked PPO + 0/1 reward
→ validated reward components / CMDP constraints
→ fine-tuned independent security LLM
→ Constitutional SFT / reward model / final LLM RL
```

其中 authorization ledger 与 reference monitor 始终保留；S-QSTN 只通过 public adapter 提供训练/压力测试反馈，不能同时作为唯一安全真值和唯一最终 evaluator。

## 当前 v0 action 边界

S-QSTN 阶段只启用两组 actions：

- **Authorization**：`REQUEST_AUTHORIZATION`、`REQUEST_REFRESH`、`DISABLE_LOCAL_AUTHORIZATION`；
- **Execution & Safety**：`EXECUTE_WITH_AUTHORIZATION`、`DENY_WITH_REASON`、`ESCALATE`。

**Interaction & Scope** 组的 `CLARIFY` 与 `PROPOSE_NARROW_SCOPE` 不在 S-QSTN v0 中实现、训练或保留 candidate slot。它们延后到获得 ethics/IRB approval 的真人实验阶段，并使用独立于 permission 四选一的 clarification/scope-negotiation 回答合同。详见主设计的 `ADR-ACTION-V0` 修订 A1。

## 最早设计阶段的待办（历史，非当前断点）

开始写代码前，请先审阅主设计第 25–26 节，冻结 episode boundary、reusable scope、hard-violation transition、safe fallback、primary observation 和 RL framework spike。
