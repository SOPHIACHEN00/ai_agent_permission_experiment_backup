# WP-FTS Online MAB：最终 v2 测试结果与 offline 比较

## 结论

最终的 v2 WP-FTS 在线 MAB **比 canonical offline MAB 更好**，但这里的“更好”必须准确限定为：在这份问卷 stated-policy label 的顺序 replay 模拟中，它更贴近用户的四类 permission policy；相对 canonical baseline，它也有更低的观察到的 *stated-preference false allow*。后者不是与 online update 机制严格匹配的比较，不能单独归因于个人更新。

它**不是**“已经安全的自动权限收缩 agent”。即使 false-allow 从 100.000% 降到 98.538%，仍然高得不可接受；而且该指标来自问卷 label，不是现实中的 privacy leakage / disclosure harm。

## 为什么 v2 才是最终结果

初始 v1 只能严格比较 WP-FTS 与 matched frozen stochastic control，不能公平比较原有 offline MAB，因为 global training exploration 与测试动作机制混在了一起。

v2 做了三个修正：

1. global Factored-TS prior 固定使用原 offline baseline 的训练设置：Thompson exploration \(=2.0\)；个人 online 的 Thompson sampling scale 单独在 validation 上调参。
2. 每个 candidate 都和同一个 canonical global-greedy reference 比较 false allow，而不是和自己的 candidate-specific frozen control 比较。
3. canonical global-greedy prediction 被附加到与 online 完全相同的 participant、query bundle、row、round 的审计事件上。

额外 regression check：v2 在 shared seed 101 下与原 offline Factored Thompson 的 frozen greedy prediction **逐项一致**。

## 最终设置

| 项目 | 设置 |
|---|---|
| 方法 | WP-FTS：warm-started personalized factored Thompson sampling |
| 动作 | `deny+persist`, `deny+ask-next-time`, `allow+ask-next-time`, `allow+persist` |
| 学习 reward | \(r_t=\mathbb{1}[a_t=y_t]\)：仅已选择动作的 0/1 joint exact-match reward |
| Runtime context | `domain`, `tool`, `raw_data_type`, `generic_data_type`, `concern_domain`, `privacy_importance` |
| 排除的 feature | participant/query ID、label/target、necessity oracle、人口统计变量、historical rate 等 |
| Canonical global prior | Factored Thompson，training exploration \(=2.0\) |
| Validation-selected personal state | \(\kappa=0.01\)，personal Thompson exploration \(=0.5\) |
| Feedback timing | 同一 `(participant_id, query_id)` 的所有 row 均先选择动作；之后才揭示 label、再更新 online posterior |
| Test | 41 个 held-out participants、3,323 row/stream、20 个 paired replay streams、5,000 participant-cluster bootstrap replicates |

这里的完整实验应称为：

> randomized sequential online-feedback replay simulation using human stated-policy labels

不是 live deployment、QSTN validity test、OPE，或 CMDP 评估。

## 三个比较对象分别回答什么问题

| 比较对象 | 回答的问题 | 可以怎样解释 |
|---|---|---|
| `frozen_tempered_fts_control` | 单独“吸收个人 feedback”是否有用？ | **主要机制比较**。与 WP-FTS 有相同 global prior、\(\kappa\)、personal TS scale、bundle order 和 random stream；唯一差别是是否更新。 |
| `canonical_offline_global_greedy_reference` | 最终 online 方法相对原 canonical offline MAB 表现如何？ | **offline baseline 比较**。它使用原 offline 的 global prior 训练配置和 frozen greedy action；但与 WP-FTS 同时不同于 personalization 和 action-selection mechanism，因此不是纯粹的 update 因果比较。 |
| 历史 offline summary | 旧报告中的数值是否一致？ | v2 seed-101 regression 完全复现旧 baseline；v2 的 20 个 global training seeds 形成更稳定的同配置 canonical reference。 |

## All-round 主结果

数值为 20 个 replay stream 的 pooled row-level metric；95% CI 是对 **41 位 participant cluster** 进行重抽样。它不是“20 个 seeds 等于 20 个独立人”的分析。

| 指标 | Canonical offline greedy | Matched frozen control | WP-FTS online | Online − canonical（95% CI，百分点） |
|---|---:|---:|---:|---:|
| Joint exact match (JEM) | 43.911% | 42.212% | **51.083%** | **+7.173** [ +2.789, +12.162 ] |
| Four-class macro-F1 | 20.473% | 18.806% | **28.058%** | **+7.585** [ +3.377, +11.006 ] |
| Access accuracy | 74.481% | 74.272% | 74.634% | +0.153 [ -0.145, +0.645 ] |
| Persistence accuracy | 54.684% | 53.255% | **63.593%** | **+8.909** [ +3.450, +15.219 ] |
| False-allow rate | 100.000% | 99.304% | **98.538%** | **-1.462** [ -2.980, -0.281 ] |
| False-deny rate | 0.000% | 0.519% | 0.295% | +0.295 [ +0.204, +0.415 ] |
| Under-persistence rate | 87.362% | 90.083% | **69.443%** | **-17.919** [ -28.229, -6.387 ] |

相对 **matched frozen control**（唯一的机制比较），WP-FTS 的 JEM 提升为 **+8.872 pp**（CI [ +4.595, +13.830 ]），persistence accuracy 提升 **+10.339 pp**（CI [ +5.066, +16.472 ]）。这说明用户自身前序反馈的确产生了可测的学习收益。

## 后期 round 10--18：是否随着反馈而变好？

所有 41 位用户都有这 9 个 round，因此它是完整 cohort 的 post-adaptation 视角。

| 指标 | Canonical offline greedy | WP-FTS online | Online − canonical（95% CI，百分点） |
|---|---:|---:|---:|
| JEM | 43.598% | **53.863%** | **+10.265** [ +4.025, +17.250 ] |
| Macro-F1 | 20.359% | **30.778%** | **+10.418** [ +4.989, +14.600 ] |
| Persistence accuracy | 54.216% | **66.572%** | **+12.356** [ +4.770, +20.911 ] |
| False-allow rate | 100.000% | **98.205%** | **-1.795** [ -3.866, -0.209 ] |
| False-deny rate | 0.000% | 0.195% | +0.195 [ +0.107, +0.311 ] |

JEM 的 all-round 和后期 CI 都明确大于零；主要增益来自 persistence，而 access accuracy 的提升不显著。

## 安全上该怎么说

可以说：

- 相对 canonical offline stated-policy baseline，WP-FTS 在本 replay 中有较低的 false allow 观察频率；
- 该 baseline difference 有 participant-cluster CI 支持，但它不能隔离 personal update、tempering 与 action-selection mechanism 的作用；
- 它仍产生大量错误 allow，因此只能视为初步 alignment diagnostic 改善。

不能说：

- “真实 privacy leakage 已被降低”；
- “agent 已经能安全地自动收缩权限”；
- “false allow 的降低可以补偿任何 task 或 interruption 后果”。

尤其重要的是，online false-allow 仍为 **98.538%**；观测到的 improvement 不能掩盖 baseline 的 access/deny 学习仍然很弱。后续 CMDP 的安全约束、随机 audit、真实 override/revoke 和 prompt-burden feedback 仍然是必要的研究步骤。

## 统计口径的透明说明

- 当前 bootstrap 是 **participant-cluster resampling 下的 pooled row-level metric**；它不是 equal-participant mean 的 CI。
- Equal-participant sensitivity check 的 JEM 结论相同：相对 canonical offline，all-round \(+6.941\) pp，95% CI [ +2.519, +11.924 ]；相对 matched frozen，\(+8.671\) pp，CI [ +4.704, +13.596 ]。
- Thompson action propensity 没有被估计（`propensity_draws=0`），因此这些日志不能直接用于 IPS/DR off-policy evaluation。

## 验证状态

- 14/14 单元测试通过。
- Canonical seed-101 回归测试通过：v2 static greedy prediction 与旧 offline Factored Thompson 完全一致。
- 41 人 participant-held-out split（120 train / 40 validation / 41 test）完全不重叠。
- `participant_id`、`query_id`、label、target、necessity oracle 和人口统计变量均未进入 feature。
- 同 bundle 先行动、后反馈；online 仅更新自己；frozen/canonical 从不更新；global posterior 不被 test feedback 改变。
- 所有 199,380 event（\(3{,}323\times20\times3\)）均通过 leakage / alignment checks。

## 可复现文件

- `results/participant_heldout_wp_fts_v2/run_config.json`：冻结配置与限制。
- `results/participant_heldout_wp_fts_v2/test_metrics_summary.csv`：三类策略的完整指标。
- `results/participant_heldout_wp_fts_v2/participant_bootstrap_summary.csv`：WP-FTS − matched frozen 的主要机制比较。
- `results/participant_heldout_wp_fts_v2/online_vs_canonical_greedy_bootstrap_summary.csv`：WP-FTS − canonical offline greedy 的 baseline 比较。
- `results/participant_heldout_wp_fts_v2/offline_greedy_reference_summary.csv`：canonical static reference。
- `results/participant_heldout_wp_fts_v2/leakage_checks.json`：数据切分、feature、feedback timing 和 state-update 检查。
- `results/participant_heldout_wp_fts_v2/test_trajectory_events.csv`：逐事件审计日志。

`participant_heldout_wp_fts_v1/` 保留为早期协议审计记录，不应作为最终论文表的来源。
