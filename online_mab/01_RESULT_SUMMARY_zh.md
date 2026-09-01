# WP-FTS Online MAB：最终结果摘要

## 1. 一句话结论

在 human stated-policy label 的 randomized sequential replay simulation 中，WP-FTS 比 canonical offline MAB 更能匹配用户的四类 permission policy；提升主要来自 persistence 决策的个体化适应，而不是 access 安全能力的根本改善。

## 2. 三个策略的 all-round 结果

| 指标 | Canonical offline greedy | Matched frozen control | WP-FTS online |
|---|---:|---:|---:|
| Joint exact match (JEM) | 43.911% | 42.212% | **51.083%** |
| Four-class macro-F1 | 20.473% | 18.806% | **28.058%** |
| Access accuracy | 74.481% | 74.272% | 74.634% |
| Persistence accuracy | 54.684% | 53.255% | **63.593%** |
| False-allow rate | 100.000% | 99.304% | **98.538%** |
| False-deny rate | 0.000% | 0.519% | 0.295% |
| Under-persistence rate | 87.362% | 90.083% | **69.443%** |

这些是 20 个 replay streams 的 pooled row-level metrics；置信区间的重抽样单位是 41 位 participant，而不是把 20 个随机 seeds 当成 20 个独立用户。

## 3. 两个必须同时报告的比较

### 3.1 WP-FTS vs canonical offline MAB

这是回答“online 方法相对原 offline baseline 是否更好”的比较：

| 指标 | 差值 Online − Canonical offline | 95% CI |
|---|---:|---:|
| JEM | **+7.173 pp** | **[+2.789, +12.162]** |
| Macro-F1 | **+7.585 pp** | **[+3.377, +11.006]** |
| Persistence accuracy | **+8.909 pp** | **[+3.450, +15.219]** |
| Access accuracy | +0.153 pp | [-0.145, +0.645] |
| False-allow rate | **-1.462 pp** | **[-2.980, -0.281]** |

这证明 v2 的 online 方法在本数据和本 replay 协议下优于 canonical offline baseline。但该比较同时改变了 personalization、tempering 和 action-selection mechanism，所以不能把 +7.173 pp 全部归因于“在线更新”本身。

### 3.2 WP-FTS vs matched frozen control

这是回答“同一个 online 协议中，吸收用户历史反馈有没有作用”的比较：

| 指标 | 差值 Online − Frozen | 95% CI |
|---|---:|---:|
| JEM | **+8.872 pp** | **[+4.595, +13.830]** |
| Macro-F1 | **+9.252 pp** | **[+5.390, +12.402]** |
| Persistence accuracy | **+10.339 pp** | **[+5.066, +16.472]** |
| Access accuracy | **+0.363 pp** | **[+0.108, +0.790]** |
| False-allow rate | -0.767 pp | [-2.241, +0.380] |
| Under-persistence rate | **-20.640 pp** | **[-30.769, -9.778]** |

这个比较的唯一有意差异是：WP-FTS 会在每个用户的后续 bundle 中更新自己的 posterior，frozen control 永远不更新。

## 4. 后期 round 10--18

所有 41 位 test participants 都有 round 10--18，因此可以观察个体化反馈后的阶段性结果：

| 指标 | Canonical offline | WP-FTS | 差值 Online − Offline | 95% CI |
|---|---:|---:|---:|---:|
| JEM | 43.598% | **53.863%** | **+10.265 pp** | **[+4.025, +17.250]** |
| Macro-F1 | 20.359% | **30.778%** | **+10.418 pp** | **[+4.989, +14.600]** |
| Persistence accuracy | 54.216% | **66.572%** | **+12.356 pp** | **[+4.770, +20.911]** |
| False-allow rate | 100.000% | **98.205%** | **-1.795 pp** | **[-3.866, -0.209]** |

## 5. 安全含义

可以写：

> WP-FTS improved prequential stated-policy fidelity relative to both the canonical offline greedy baseline and a matched frozen adaptation control. The improvement was driven primarily by persistence decisions.

不可以写：

- 真实 privacy leakage 已降低；
- agent 已经安全地自动收缩权限；
- 98.538% 的 false-allow 可以接受；
- 这个结果已经证明适合 deployment。

问卷 label 是 stated preference，不是 observed disclosure harm。false-allow 仍接近 100%，这正是后续 CMDP / safety constraint 研究仍然必要的原因。

## 6. 结果文件

- 主指标：[test_metrics_summary.csv](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/test_metrics_summary.csv)
- WP-FTS vs frozen CI：[participant_bootstrap_summary.csv](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/participant_bootstrap_summary.csv)
- WP-FTS vs offline CI：[online_vs_canonical_greedy_bootstrap_summary.csv](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/online_vs_canonical_greedy_bootstrap_summary.csv)
- 完整解释：[原始中文报告](../online_bandit_experiment/RESULTS_COMPARISON_zh.md)
