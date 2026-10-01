# Family-3 v2 held-out test-once — terminal report

> Interpretation correction, 2026-09-22: RULE_PARITY_SIGNAL takes precedence over CREDIT_SIGNAL; all three seeds satisfy both. Identical first actions and success outcomes do not imply identical full trajectories. See classification_interpretation.md and RL_Personal_Assistant_Design/experiments/2026-09-22_family3_next_stage/RESULTS_ARCHIVE_zh.md. Original run data and classification are unchanged.

日期：2026-09-22 UTC  
实验：`increment8_family3_v2_learner_pilot_v0`  
运行：一次 CUDA `test-once`，退出码 0，597.944 秒

## 运行完整性

本轮严格使用已批准的 validation permit 和最终 checkpoint。没有重新训练、调参、改 seed、修改 source/config、自动重试或重复打开 test。测试写入 6,300/6,300 条记录；formal validation 保持 4,200 条，12 个 checkpoint 保持完整。解锁 ledger 只有一条记录，测试进程只有一个 writer。

安全与审计 hard counts 全部为 0：包括 invalid action、unauthorized committed effect、test-before-unlock、duplicate rows、source/config/checkpoint hash mismatch、split leakage 等。

## 科学结果

最终分类是 `RULE_PARITY_SIGNAL`，不是 `CREDIT_SIGNAL`：

| method | test terminal success |
|---|---:|
| `masked_ddqn_gamma1` | 737 / 900 (81.9%) |
| `forecast_rule` | 737 / 900 (81.9%) |
| `forecast_ablated_rule` | 453 / 900 (50.3%) |
| `masked_ddqn_gamma0` | 0 / 900 |
| `tabular_q_gamma0` | 0 / 900 |
| `tabular_q_gamma1` | 0 / 900 |
| `random_valid` | 0 / 900 |

γ=1 DDQN 在三个 seed 上与 forecast rule 完全同分，并达到 900/900 的 first-request 与 forecast-rule match；因此当前证据支持“DDQN 学到了与规则基线相同的行为/长期信用路径”，不支持“DDQN 已经超过规则基线”。

## 证据位置

本地归档：`server-test/formal_test_evidence/formal_test_once_evidence.zip`  
SHA256：`78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0`  
23 entries，780,834 bytes；归档已做本地完整性检查。

后续不应在这份 sealed test 上继续调参或重跑；若要证明超越规则，应另立、预注册并重新授权的训练/评估实验。
