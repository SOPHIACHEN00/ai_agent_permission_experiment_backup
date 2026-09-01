# Online MAB 复现与结果文件说明

## 1. 最终结果目录

最终 v2 输出目录：

```text
online_bandit_experiment/results/participant_heldout_wp_fts_v2/
```

早期 v1 目录仍然保留，但它使用了尚未修正 global training / online exploration 混合问题的协议，不作为最终论文结果。

## 2. 推荐运行环境

从项目目录 `ai_agent_permission_experiment` 运行，使用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe
```

系统 Python 缺少本实验所需的 SciPy，不建议直接使用系统 `python`。

## 3. 运行最终 online MAB

```powershell
.\.venv\Scripts\python.exe -m online_bandit_experiment.run_wp_fts `
  --data data\processed\four_label_dataset.csv `
  --out online_bandit_experiment\results\participant_heldout_wp_fts_v2 `
  --bootstrap-replicates 5000
```

如果输出目录已经存在，需要显式使用 `--overwrite`；正常复现时建议使用新的输出目录，避免覆盖原始结果。

关键默认参数为：

```text
split_seed = 42
validation_seeds = 11,29,47
test_seeds = 1001,...,1020
kappa_grid = 0.01,0.03,0.1,0.3,1.0
personal_exploration_grid = 0.25,0.5,1.0,2.0
global_training_exploration = 2.0
bootstrap_replicates = 5000
bootstrap_seed = 20260727
```

最终 validation 选择：

```text
kappa = 0.01
personal_exploration = 0.5
```

## 4. 运行测试

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  online_bandit_experiment\wp_fts.py `
  online_bandit_experiment\run_wp_fts.py `
  online_bandit_experiment\test_wp_fts.py

.\.venv\Scripts\python.exe -m unittest `
  online_bandit_experiment.test_wp_fts `
  bandit_experiment.test_stated_policy_bandit -v
```

最终验证结果：14/14 tests passed。

## 5. 结果文件说明

| 文件 | 用途 |
|---|---|
| `run_config.json` | action、reward、feature、split、参数和限制的冻结记录 |
| `validation_tuning_summary.csv` | 所有 \(\kappa\) / personal exploration candidates 的 validation 指标 |
| `validation_search_runs.csv` | validation 每个 seed、每个 policy role 的明细 |
| `test_metrics_summary.csv` | canonical offline、matched frozen、WP-FTS 三类 role 的 all-round / late-round metrics |
| `participant_bootstrap_summary.csv` | WP-FTS − matched frozen 的主要机制比较和 CI |
| `online_vs_canonical_greedy_bootstrap_summary.csv` | WP-FTS − canonical offline 的 baseline 比较和 CI |
| `participant_metrics.csv` | participant × stream × policy role 的指标 |
| `participant_paired_deltas.csv` | WP-FTS 与 matched frozen 的 participant paired differences |
| `online_vs_canonical_greedy_participant_deltas.csv` | WP-FTS 与 canonical offline 的 participant paired differences |
| `test_trajectory_events.csv` | 每个 row 的 bundle position、动作、evaluator label、selected reward 和 update flag |
| `bundle_orders.csv` | 每个 participant 每个 replay seed 的 atomic bundle 顺序 |
| `offline_greedy_reference_summary.csv` | canonical global-greedy reference 的每 stream 汇总 |
| `offline_greedy_reference_predictions.csv` | canonical reference 的逐行预测 |
| `leakage_checks.json` | split、feature、bundle timing、state update 和三角色 alignment 检查 |

## 6. 结果审计数字

最终输出应满足：

```text
test participants = 41
test rows per stream = 3,323
replay streams = 20
policy roles = 3
event rows = 3,323 × 20 × 3 = 199,380
bootstrap replicates = 5,000
```

三个 policy roles 是：

```text
wp_fts_online
frozen_tempered_fts_control
canonical_offline_global_greedy_reference
```

`leakage_checks.json` 中所有布尔检查都应为 `true`。

## 7. Offline MAB 的复现位置

Canonical offline runner：

```text
bandit_experiment/run_stated_policy_bandit.py
```

历史 participant-heldout 输出：

```text
bandit_experiment/stated_policy_results/participant_heldout/
```

其中 canonical Factored Thompson 的历史 test JEM 为约 43.780%，false-allow 为 100%。v2 的 seed-101 regression 与这个 canonical runner 逐行一致；v2 额外使用 20 个 test replay streams 来评估 online trajectory。

## 8. 当前结果不能支持的分析

这批日志明确不是：

- IPS / doubly robust off-policy evaluation；
- 真实用户 online deployment log；
- 真实 privacy leakage measurement；
- task success / prompt burden 的长期轨迹；
- CMDP constraint satisfaction result。

`action_probability_estimate` 当前没有估计，`propensity_draws=0`。因此不能把这些 CSV 直接当作 OPE 数据使用。

## 9. 推荐引用方式

如果在论文中只需要一句结果，可以写：

> In a participant-held-out randomized sequential replay using stated-policy feedback, WP-FTS improved joint exact-match accuracy by 7.17 percentage points over the canonical frozen offline greedy baseline and by 8.87 percentage points over a matched frozen adaptation control. The gain was driven primarily by persistence decisions; false-allow remained above 98%, so the method is not a safety guarantee.

中文解释和全部表格见：

- [最终结果摘要](./01_RESULT_SUMMARY_zh.md)
- [Online MAB 方法流程](./02_ONLINE_MAB_METHOD_zh.md)
- [Offline vs Online 对比](./03_OFFLINE_VS_ONLINE_COMPARISON_zh.md)
