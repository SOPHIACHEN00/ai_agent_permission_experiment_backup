# 图表目录：DistilBERT vs. Tuned Flat LR

## Figure 1：Paired metric deltas

- 文件：`figures/figure-01-paired-metric-deltas.png`、`figures/figure-01-paired-metric-deltas.pdf`
- Purpose：回答 DistilBERT 相对 tuned Flat LR 在五项主指标上的差值及测试参与者抽样不确定性。
- 数据源：`paired_cluster_bootstrap_summary.csv`
- 编码：点为完整测试集上的 `DistilBERT - LR`；横线为 participant paired cluster bootstrap percentile 95% CI；虚线为 0。
- Caption requirements：说明 n=41 participants、3,323 rows、5,000 次配对 cluster bootstrap、单一训练 seed，以及前 3 项越高越好、后 2 项越低越好。
- Key observation：DistilBERT 在期望方向上的点估计为 0/5；CI 不跨 0 且支持 DistilBERT 的指标为 0/5，CI 不跨 0 且支持 LR 的指标为 2/5。
- Interpretation：图只支持按每项指标方向与区间逐项判断；跨 0 的区间不能升级为固定测试参与者上的明确方向证据。
- Decision implication：同时应用预先声明的 Macro-F1 主指标与两项风险 guardrail，不因单个点估计自动替换 baseline。
- 推断边界：只有一个固定训练 seed；CI 只重采样 41 名测试参与者，不包含训练随机性。指标是在抽中参与者的全部行上重算的 row-pooled metric。

## Figure 2：Per-class performance

- 文件：`figures/figure-02-per-class-performance.png`、`figures/figure-02-per-class-performance.pdf`
- Purpose：定位总体 Macro-F1 差异由哪些回答类别驱动。
- 数据源：`per_class_metrics.csv`
- 编码：四个回答类别上，DistilBERT 与 tuned Flat LR 的 precision、recall、F1 并排比较。
- Caption requirements：说明四类标签短名、每组柱的模型、分数范围，以及图中不含训练 seed 或 participant CI。
- Key observation：四类 F1 差值为 label 0 +3.88 pp；label 1 -6.57 pp；label 2 -12.11 pp；label 3 +0.58 pp；最低差值是 label 2（Yes, but ask me next time），最高差值是 label 0（No, never share）。
- Interpretation：总体 Macro-F1 由不同类别方向和幅度不一的变化组成，不能只看一个平均数推断所有类别同时改善或恶化。
- Decision implication：后续误差分析优先检查 label 2 的混淆与输入表达，再选择 class-aware、ordinal 或 factored 改动。
- 推断边界：图中是一个固定训练 seed 的点估计，不表示跨训练运行稳定性。

PNG 为 300 DPI；PDF 为 matplotlib 直接输出的矢量图。
