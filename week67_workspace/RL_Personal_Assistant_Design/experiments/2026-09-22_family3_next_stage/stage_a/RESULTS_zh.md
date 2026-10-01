# Stage A：最小修复后的结构核验结果

日期：2026-09-22。运行结束：UTC 13:37:11。

状态：**STAGE_A_BOUNDED_PASS_STAGE_B_ON_HOLD：固定候选结构核验及一次独立复核完成；Stage B 未启动，强规则优势研究目标需要讨论。** 这是 Increment 8 后续独立 budget/recourse 原型，不是旧 Family-3 v2 的重训或结果替换。

## 1. 本次只修了什么

用户批准“最小修复继续”后，只为新适配器的 MockTool 补齐当前 task step、第一次调用的确定性成功计划。没有改 monitor、纯状态转移、规则、费用、奖励、阈值或原六项测试。

同一组六项检查重跑一次：**6/6 通过，0.147 秒**。随后新增一个最小核验入口，固定十图 × original/prompt-toggle 共二十条件只运行一次。原先 5/6 的失败输出与 source receipt 完整保留，见 [首次失败报告](REPORT_zh.md)；新输出见 [修复检查](evidence/fix1_focused_check.json)。

## 2. 完成了哪些核验

- 二十条件全部具有正值成功路径；全部使用精确分数计算，没有 Monte Carlo 误差。
- 费用路径分别为 narrow/exact：3 exposure、1 prompt；broader-first：6、1；narrow 后明确追加 broader 授权：6、2（n=1）。真实 ledger 在阶段切换时清除上一阶段的有效授权。
- 手算 witness 匹配：P=2 时首次 narrow/broader Q 值为 1/5、1/2；P=3 时为 3/5、1/2，最优动作确实翻转。
- 同一已公开 exact 分支下，阶段一的授权选择可令阶段二剩余 exposure 为 6 或 3；在 p2=1/5、P_left=1 时，后续最优价值相应为 1 或 1/5。
- train/validation 有 **5 个条件**存在 Current-task rule 的严格 regret；全二十条件共 7 个。没有删除规则最优的条件，也没有参数搜索。
- 三个确定性规则及一个 DP 最优策略，各在每条件的全部 8 种私有未来 tape 上通过真实授权/monitor 回放；加权成功概率与纯模型 exact value 完全一致。

这次回放计数：**640 个策略 episode、3,823 个合法步骤、1,415 次明确同意、2,124 个受保护 effect**。另外执行了 3 条费用 witness 路径，未混入这些策略回放计数。

已检查策略的非法动作与未授权 effect 均为 **0**。额外主动输入的 **11,793 次非法候选**均被拒绝且 snapshot 不变；这些是预期负例，不是策略安全失败。

计算规模：1,276 个 full-DP 非终局状态；包含局部规则的虚拟预留预算状态后，共记录 1,556 个非终局状态。总结构运行约 **4.328 秒**，峰值 RSS **261.375 MiB**，低于预设 100,000 状态 / 60 秒 / 512 MiB；未触限、未扩限、未重跑。

## 3. 结果说明什么

以下是所有二十条件等权的**精确期望成功率**，不是 DDQN 训练成绩，也不是二十次独立训练。

| 方法 | 精确期望成功率 |
|---|---:|
| Exact DP 公开信息最优规划 | 66.15% |
| Reservation rule 预留资源规则 | 63.90% |
| Current-task rule 只顾当前任务 | 57.30% |
| Forecast-transfer rule | 54.10% |
| Random-valid | 约 0.0311% |

因此，“共享资源会产生跨任务规划价值”在这个固定机制中获得支持；不能据此说 DDQN 已经学会、优于规则或必须使用 RL。当前精确规划本身成本很低，也是有效备选。

### 重要限制一：强规则仍然很强

Reservation rule 在 **18/20 条件**达到 V*。仅两处有差距：

| 条件 | V* | Reservation | 可提升上限 |
|---|---:|---:|---:|
| br00 / original（train） | 4/5 | 1/2 | 3/10 |
| br06 / prompt-toggle（validation） | 4/5 | 13/20 | 3/20 |

**全部 6 个 test 条件上 Reservation rule 均已最优。** test 等权均值两者均为 19/30，约 63.33%。因此，在当前相同公开信息、同奖励定义下，任何策略相对它的 test 期望优势上限都是 0，原拟议的“每 seed ≥0.05 强规则优势”不可能作为真实期望性能达成。抽样偶然高于规则不构成突破该上限的证据。

这不是 DDQN 失败，而是 **目前候选 test 与强规则优势目标不匹配**。不应训练后再改阈值、增加预算或选择性更换图。完整保留原设计与证书，先讨论研究目标。

### 重要限制二：后续信息的作用有限

存在可到达的后续分支 witness：初次 narrow 后，若揭示 exact，应 execute；若揭示 broader，应重新明确请求 broader。它满足设计中“后续决策使用新公开信息”的最低要求，但其变化与 coverage/action mask 改变有关，不是对同一 mask 下复杂 forecast 推理的证明。

对阶段二入口的 **132 对**匹配公开状态，p2 从 1/5 变成 4/5 导致的最优动作集合变化为 **0**。p2 会改变部分路径的成功概率，却未在这些状态中改变最优动作。不能把此结果包装为丰富的后续预测决策能力。

## 4. 证据边界

- 真实适配一致性覆盖固定规则和一个 DP 最优策略的全部八种 tape；不是所有合法动作历史的穷尽真实回放。Random 的值只由纯模型精确评价。
- observation 检查针对 Stage A public-state 适配；尚未实现 learner encoder/replay，因此没有宣称训练管线的信息隔离已通过。
- 这是合成的确定性同意、确定性工具成功原型，不是用户拒绝、故障恢复、真人或生产系统验收。
- 十图是同一机制的参数组合，original/toggle 成组；没有 training seeds，不能做训练方差、置信区间或显著性结论。640 个回放也不是 640 次独立训练。
- 本次允许 auditor 为新 test 参数生成解析证书；**没有新 learner test、模型评估或训练**。旧 v2 test 没有重开。
- 26 个旧冻结 CUDA 源文件、两份旧结果 ZIP、已批准设计/候选配置，以及原六项测试的哈希均保持不变。
- 没有服务器连接、GPU 训练、OpenAI API、依赖安装或参数修改。拟议 72,000 transitions / 6 checkpoints 没有开始。

## 5. 归档与下一步边界

- [逐图逐条件完整值表](evidence/preflight_v0/values.csv)
- [精确证书与资源/安全汇总](evidence/preflight_v0/certificate.json)
- [原始条件结果](evidence/preflight_v0/conditions.jsonl)
- [含私有 tape 的 auditor-only 回放](evidence/preflight_v0/auditor_episodes.jsonl)：不得作为 learner observation/replay 输入。
- [手算/真实费用 witness](evidence/preflight_v0/witnesses.json)
- [冻结输入与源码清单](evidence/preflight_v0/source_manifest.json)
- [运行终态](evidence/preflight_v0/status.json)与[原始执行回执](evidence/preflight_execution.json)

一次独立只读复核已完成：[复核及裁定](REVIEW_zh.md)。没有发现需要继续修复的实质实现问题；确认上述科研限制。运行时原始证书中的REVIEW_PENDING不回写，最终状态另存completion_receipt.json。最小验证/故障定位技能使本轮只修配置、保留测试与首次失败；独立复核技能提供了范围内的一次复核；结果分析按精确结构证据而非学习统计解释，不生成无依据显著性结论。

当前不修改候选、门槛或冻结输出，不启动训练。建议优先讨论：是否接受下一轮仅验证“DDQN 学会跨步规划并接近最优”，明确放弃在本候选 test 上证明超越 Reservation rule；若研究必须证明强规则优势，应另立版本重新设计，而不是对本次结果调参。
