# CMDP reward、policy 与 QSTN 动态 UserSim：研究计划

## 研究目标

在冻结现有 MAB baseline 的前提下，为 permission-automation 的下一阶段设计一个可审计的、安全优先的 CMDP：

1. 重构 reward、cost/constraint 与 policy/action space，并以一手研究、标准和法规为依据；
2. 明确哪些 trade-off 可通过用户反馈自适应学习，哪些安全阈值不能由学习到的权重抵消；
3. 审计 `Dynamic_UserSim_Research_Design` 中的 QSTN 改造是否足以支撑该 CMDP，给出一个单一、可验证的最终 UserSim 设计，而非模型族。

## 阶段

| 阶段 | 工作 | 状态 |
|---|---|---|
| 1 | 读取现有 UserSim、CMDP 与 MAB 文档，确定数据与设计边界 | 已完成 |
| 2 | 用原始论文/权威标准核验 reward、constraint、preference learning、safe RL 的证据 | 已完成 |
| 3 | 给出风险条件化、偏好自适应、带 shield 的 CMDP 形式化设计 | 已完成 |
| 4 | 评估 QSTN 动态模拟器可行性，定义一次到位的 v1、数据与 release gates | 已完成 |
| 5 | 写入中文研究设计，交叉检查引用与旧文档的一致性 | 已完成 |

## 决策边界

- 当前 MAB 只保留为 stated-policy baseline，不再扩展为新的研究主线。
- 不能把“用户愿意允许”当成“安全”；安全事实来自 scenario threat model / security oracle。
- 高风险、越权或失效授权不能用 task reward 或用户偏好权重补偿。
- QSTN 是一个最终 hybrid UserSim 的语言/人格接口；不能独自充当安全真值来源。
