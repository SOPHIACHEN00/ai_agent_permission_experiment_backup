# Figure catalog

## Figure 1：Fixed-test metric overview

- 文件：`figures/figure-01-fixed-test-metric-overview.png` / `.pdf`
- 目的：同时查看当前 7 个主要模型的三项性能指标与两项权限风险。
- 编码：每列颜色只在该指标内部排序；绿色更符合该指标方向，单元格显示点估计。
- 观察：RoBERTa Accuracy 最高，Factored tuned Macro-F1 最高，Flat tuned 风险更均衡。
- 决策含义：不能用单一 Accuracy 或 Macro-F1 取代多指标选择。
- 局限：固定 outer split、Transformer 单 seed；颜色不表示统计显著性。

## Figure 2：Paired bootstrap deltas

- 文件：`figures/figure-02-paired-bootstrap-deltas.png` / `.pdf`
- 目的：比较三个新 backbone 相对 tuned Flat LR 的 participant-paired 差值与不确定性。
- 编码：方向标准化后正值表示语义模型更好；粗线为 marginal 95% CI，细灰线为 Bonferroni 98.333% CI，点为观察差值。
- 观察：没有新模型在 Macro-F1 上形成有利差值；RoBERTa/DeBERTa 的风险明显朝不利方向移动。
- 决策含义：Flat tuned 继续作为默认 benchmark，ModernBERT 仅保留为语义 baseline。
- 局限：B=5,000 只重采样 41 位测试 participant，不覆盖训练 seed 或 outer split。

## Figure 3：Per-class F1

- 文件：`figures/figure-03-per-class-f1.png` / `.pdf`
- 目的：解释 Accuracy 与 Macro-F1 分歧来自哪些类别。
- 编码：四个 label 分面；柱高为固定测试集 F1；比较 Flat tuned 和三个新 semantic 模型。
- 观察：RoBERTa、DeBERTa 的 label 1 F1 为 0，是总体 Macro-F1 偏低的重要原因。
- 决策含义：后续改进应针对少数类和权限方向，而不是只优化 Accuracy。
- 局限：逐类图只显示点估计，没有 participant CI，也没有多 seed 误差条。
