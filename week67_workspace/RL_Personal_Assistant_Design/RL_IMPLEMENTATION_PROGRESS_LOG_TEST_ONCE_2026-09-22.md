# Increment 8 Family-3 v2 held-out test-once progress record

> 2026-09-22 解释更正：下文原历史措辞中关于 credit signal 的限制过强。三个seeds实际同时满足credit signal与rule parity，分类器优先报告parity；只是不能声称超过规则。首动作/成功相同不代表所有轨迹相同。以主进展日志最新条目及 experiments/2026-09-22_family3_next_stage/RESULTS_ARCHIVE_zh.md 为当前解释；原始数据不变。

日期：2026-09-22 UTC

## 已完成

- Formal train-validation 的 `READY_FOR_TEST` permit 被只读核验；validation 仍为 4,200 rows，12/12 checkpoint 完整，qualifying seeds 为 17、29、43。
- 按原封存配置只启动一次 CUDA `test-once`：3 个 held-out graphs × 7 methods × 3 seeds × 2 conditions × 50 episodes = 6,300 rows。
- 进程正常退出（exit code 0，597.944 s），未重训、未调参、未更换 seed、未修改 source/config、未自动重试。
- test 完成 6,300/6,300 rows；一个 unlock ledger entry、一个 writer、无 duplicate rows。
- 所有安全与完整性 hard counts 为 0，包括 invalid action、unauthorized committed effect、test-before-unlock、split leakage 和 source/config/checkpoint hash mismatch。

## 科学结论

最终分类为 `RULE_PARITY_SIGNAL`。`masked_ddqn_gamma1` 与 `forecast_rule` 都是 737/900（81.9%），且两个方法在 900/900 的 first-request/forecast-rule match 上一致。故本轮只能说明 γ=1 DDQN 达到规则基线的同等行为，不足以支持“DDQN 超越规则”或独立的 credit signal。

## 证据

本地 test 归档位于：
`.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/server-test/formal_test_evidence/formal_test_once_evidence.zip`

SHA256：`78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0`；23 entries，780,834 bytes。CUDA overlay 103/103；本地未修改 baseline 99/99。

本文件是对既有 `RL_IMPLEMENTATION_PROGRESS_LOG.md` 的 test-once 终态补充记录；未覆盖早期历史条目。
