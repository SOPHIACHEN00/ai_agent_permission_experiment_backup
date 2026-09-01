# Reward Weight 敏感性分析

## 1. 实验目的

本实验不是寻找一组让 test reward 最大的数字，而是回答四个预先确定的问题：

1. 提高 `task_utility_weight` 是否会提高必要数据的 allow 率？
2. 提高 `unnecessary_access_weight` 是否会减少不必要访问？
3. 提高 `interruption_weight` 是否会减少 ask-next-time？
4. 提高 `over_persistence_weight` 是否会减少错误 persist？

## 2. 测试范围

### Access Bandit

完整测试了 12 组组合：

```text
task_utility_weight = 0.0, 0.1, 0.25, 0.5
unnecessary_access_weight = 0.5, 1.0, 2.0
```

### Persistence Bandit

完整测试了 9 组组合：

```text
interruption_weight = 0.05, 0.1, 0.25
over_persistence_weight = 0.5, 1.0, 2.0
```

因为 Access 和 Persistence reward 已经因子化，没有再构造重复的 12×9=108 个跨分支组合。

## 3. 控制变量与实验单位

- `access_mismatch_weight = 1.0`；
- `persistence_mismatch_weight = 1.0`；
- sensitivity cost 未测试，因为数据没有 intrinsic data sensitivity 标注；
- 每个 reward 配置都从头训练 epsilon-greedy、UCB 和 Thompson Sampling；
- participant-held-out split 为 120/40/41 train/validation/test participants；
- 测试集为 3,323 行；
- 使用 10 个共同随机 stream seeds；
- 每种 reward 先除以该配置下最大绝对 action reward，使不同配置的探索尺度可比；
- Persistence 使用观察到的 access target 作为条件，只隔离研究 Persistence reward，不混入 Access policy 的错误。

统计单位是 10 个随机 stream seed，而不是把 3,323 行错误地当作独立重复实验。置信区间和显著性只描述同一个 participant split 上的算法随机性与行顺序敏感性，不能直接外推到所有用户。

## 4. 重新选择的探索参数

归一化默认 reward 只在 validation participants 上调参一次，之后对所有 reward 配置保持不变：

| 分支 | epsilon-greedy | UCB | Thompson Sampling |
|---|---:|---:|---:|
| Access | 0.01 | 2.0 | 0.25 |
| Persistence | 0.01 | 0.25 | 0.25 |

## 5. 预注册极端对比

下表的变化量均为“高 weight − 低 weight”，并先在每个 seed 内对另一个 factor 取平均。

| 问题 | epsilon-greedy | UCB | Thompson |
|---|---:|---:|---:|
| task 0.0→0.5 对 necessary allow | +1.48 pp | +2.60 pp | +2.05 pp |
| unnecessary 0.5→2.0 对 unnecessary access | −35.59 pp | −33.55 pp | −33.01 pp |
| interruption 0.05→0.25 对 ask rate | −15.15 pp | −15.28 pp | −14.37 pp |
| over-persistence 0.5→2.0 对 persistent over-allow | −23.41 pp | −23.34 pp | −23.94 pp |

12 个对比在全部 10 个 seeds 中方向一致。两侧 Wilcoxon signed-rank test 的原始 `p=0.001953`，对全部 12 个检验做 Holm correction 后均为 `p=0.023438`；matched-pairs rank-biserial effect size 均为 `|1.0|`。

`|1.0|` 表示这 10 个随机 stream 的变化方向完全一致，不表示 population effect 是 100%，也不能消除单一 participant split 的限制。

## 6. Access 结果如何理解

三个算法在整个 grid 中仍然高度倾向 allow。提高 unnecessary penalty 确实显著减少任务明确不需要的数据访问，但是 over-sharing 仍然很高，因为：

```text
任务上 necessary ≠ 用户愿意 allow
```

一个数据项可能确实有助于完成任务，但参与者仍然选择 deny。当前 `task_utility` 鼓励必要数据访问，而 symmetric mismatch cost 没有把“错误 allow”设置成比“错误 deny”更严重。

### UCB 的三个参考点

| 配置 | Necessary allow | Unnecessary access | Over-sharing | Access accuracy |
|---|---:|---:|---:|---:|
| `task=0, unnecessary=2` | 98.13% | **4.64%** | **66.88%** | 76.84% |
| `task=0.1, unnecessary=2` | **99.90%** | 13.34% | 72.16% | **76.95%** |
| 原默认 `task=0.25, unnecessary=0.5` | 100.00% | 83.57% | 95.24% | 74.68% |

前两组进入 UCB 的三目标 Pareto front。`task=0.1, unnecessary=2` 是当前测试范围内较合理的折中候选，但 72.16% 的 over-sharing 仍然不能称为 privacy-safe。

因此，科学结论不是“已经找到最终 Access weights”，而是：

- `unnecessary_access_weight=0.5` 明显过弱；
- `unnecessary_access_weight=2.0` 能有效阻止任务不需要的数据；
- 仅调这两个权重无法解决“必要但用户 deny”的 over-sharing；
- 下一步需要 asymmetric false-allow cost、validation over-sharing constraint 或 CMDP-style safety constraint，而不能继续盲目增大同一个 penalty。

## 7. Persistence 结果如何理解

Persistence 存在清晰的 interruption-versus-over-persistence tradeoff。以 UCB 为例：

| interruption | over-persistence | Ask rate | Persistent over-allow | Accuracy |
|---:|---:|---:|---:|---:|
| 0.05 | 2.0 | 98.03% | **1.95%** | 52.63% |
| 0.10 | 1.0 | 87.56% | 10.54% | 54.05% |
| 0.25 | 1.0 | 73.18% | 22.11% | 56.23% |
| 0.25 | 0.5 | **51.13%** | 35.59% | **64.07%** |

这里 accuracy 最高的配置并不最安全：它减少 ask，但更频繁地错误 persist。相反，安全优先配置几乎每次都要询问用户。

因此现有数据不能决定唯一的 Persistence weights。必须先说明：系统更不能接受频繁打扰，还是更不能接受错误长期记住授权。

## 8. 当前允许与禁止的结论

允许表述：

- 在固定 held-out participant split 上，四个 reward weight 都对策略行为产生了跨随机 stream 稳定的方向性影响。
- 提高 unnecessary penalty 能明显减少任务不需要的数据访问。
- Persistence 呈现稳定的 interruption 与 over-persistence 权衡。
- 当前 weight grid 没有消除 Access majority-allow collapse。

不能表述：

- 已经找到了适合真实用户的最优 reward weights；
- 当前 Bandit 已经是 privacy-safe controller；
- 10 个 seeds 等价于 10 个独立用户样本或 10 次独立人群实验；
- 这些 proxy cost 是用户真实感受到的长期成本。

## 9. 输出文件

- `sensitivity_results/access_per_seed.csv`：Access 每个配置、算法与 seed 的原始结果；
- `sensitivity_results/persistence_per_seed.csv`：Persistence 每个配置、算法与 seed 的原始结果；
- `sensitivity_results/access_summary.csv`：均值、标准差、95% CI 与 Pareto 标记；
- `sensitivity_results/persistence_summary.csv`：Persistence 汇总；
- `sensitivity_analysis/analysis-output/contrast_tests.csv`：Wilcoxon、Holm 与 effect size；
- `sensitivity_analysis/analysis-output/analysis-report.md`：严格分析报告；
- `sensitivity_analysis/analysis-output/stats-appendix.md`：统计附录；
- `sensitivity_analysis/analysis-output/figure-catalog.md`：图的目的、观察与限制；
- `sensitivity_analysis/analysis-output/figures/`：PDF 与 600-DPI PNG 图。
