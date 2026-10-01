# 统计附录：语义 backbone 对比

## Estimand 与抽样单位

- 点估计是在冻结测试集全部 3,323 行上计算的 row-pooled metric。
- Bootstrap 单位是 participant cluster：每次从 41 位测试参与者中有放回抽取 41 个 participant，并带入被抽中 participant 的全部行。
- 同一 bootstrap draw 同时用于 Flat LR 和三个 semantic 模型，保持 paired comparison。
- B=5,000，随机种子 `20260810`；percentile interval。

## 指标定义与方向

- Accuracy、Macro-F1、Quadratic Weighted Kappa：越高越好。
- Over-sharing：真实标签为 0/1 时预测为 2/3 的比例，越低越好；分母 848。
- Persistent-over-allow：真实标签不是 3 时预测为 3 的比例，越低越好；分母 2,262。

## 多重比较策略

- 主比较家族：三个新 backbone 各自相对 tuned Flat LR 的 Macro-F1。
- 保留 marginal 95% CI，便于与既有 DistilBERT 分析一致。
- 同时提供每个指标内三项对比的 Bonferroni 98.333% CI（alpha=0.05/3）。
- 不报告行级 p-value；3,323 行不是独立实验单位。

## 训练重复与推断边界

- 每个 Transformer 只有一个训练 seed（42）与一个固定 outer split。
- Participant bootstrap 不包含初始化、mini-batch 顺序、模型选择、超参数搜索或 outer-split 不确定性。
- 因此不报告跨训练 run 的 mean±SD，也不把 CI 不跨 0 扩写为跨训练 seed 的显著性结论。
- Transformer 与 LR 比较的是完整 pipeline；输入字段来源相同，但表示、缺失值处理与调参空间不同，不能把差异因果归因于“语义”本身。

## 输出文件

- `all_model_metrics.csv`：11 个 run/variant 的复算指标。
- `semantic_vs_flat_lr_bootstrap_summary.csv`：3×5 个配对差值及 95%/Bonferroni CI。
- `paired_cluster_bootstrap_replicates.csv`：全部 bootstrap replicate。
- `per_class_metrics.csv`：逐类 precision/recall/F1/support。
- `selected_hyperparameters.csv`：三个新 backbone 的锁定模型、参数与 provenance。
