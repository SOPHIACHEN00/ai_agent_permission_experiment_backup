# 统计附录：DistilBERT vs. Tuned Flat LR

## 输入与完整性检查

- DistilBERT run：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\classification_experiments\artifacts\distilbert_rtx3090_epoch5_codex_20260810`
- LR run：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\classification_experiments\artifacts\nested_tuning_20260809\participant_heldout`
- 两边都只选取 `variant=tuned`；LR 只选取 `model=flat_four_class_lr`。
- 预期并实际核验：3,323 行、41 位参与者、四个标签均为整数 0–3。
- 对齐方法：complete shared metadata (LR artifact has no _row_id)。
- 对齐键：`participant_id`, `query_id`, `query`, `domain`, `tool`, `raw_data_type`, `generic_data_type`, `necessity_status`, `label_id`, `label_text`。
- 对齐是一对一 outer merge；任何单边行、重复键、metadata/真值冲突都会立即报错，不生成分析结果。
- 两边的五个 stored test metrics 都必须与预测重算值在绝对误差 `1e-9` 内一致。

## 结果来源状态

- DistilBERT test-touched follow-up：`true`。
- 若为 `true`，表示该配置是在同一个 test 的更早结果已被查看后提出；数值与 participant bootstrap 仍可复核，但只允许 exploratory wording，不作为全新 confirmatory test。

## 指标定义

1. `accuracy`：预测标签等于真值的行比例。
2. `macro_f1`：四个类别 F1 的算术平均；零预测/零召回分母按 0 处理，与训练脚本一致。
3. `quadratic_weighted_kappa`：标签顺序 0,1,2,3，权重为 `(i-j)^2 / 9`。
4. `over_sharing_rate`：真值为 0 或 1 时，预测为 2 或 3 的比例；分母只含真值拒绝类。
5. `persistent_over_allow_rate`：真值不为 3 时，预测为 3 的比例；分母只含真值非 persistent allow 的行。

## Paired participant cluster bootstrap

- 抽样单元：participant，而不是 row。
- 每个 replicate 从 41 位测试参与者中有放回抽取 41 个 cluster；抽中的 participant 带入其全部测试行，被重复抽到时其 cluster 也重复出现。
- Estimand：在抽中 clusters 合并后的所有行上重算指标，即 row-pooled metric；不是先算每人指标再等权平均。
- 两个模型使用同一 replicate 的 participant draw，保持 paired comparison。
- 每个 replicate 分别重算五项指标，再计算 `DistilBERT - LR`。
- 重复次数：5,000；NumPy `default_rng` seed：20260810。
- 95% CI：delta empirical distribution 的 `[0.025, 0.975]` percentile；未做多重比较校正。

## 统计报告选择

- 主要效应量：两个固定模型的绝对指标差 `DistilBERT - LR`；表中同时以原始比例和百分点报告。
- 完成的 DistilBERT 训练 seed 数：1。没有可比较的多 seed 分布，因此不报告跨训练运行的 mean ± SD，也不把 participant bootstrap 当作训练随机性替代品。
- 不报告 p-value：这里使用配对 participant cluster bootstrap percentile CI 描述测试参与者抽样不确定性，而不是对 3,323 行做错误的独立样本检验。
- 未对五项指标做多重比较校正；它们是预先定义的效能与风险端点，当前结果只作探索性 effect/CI 报告，任何单项区间都不升级为 confirmatory 显著性宣称。
- Bootstrap 不依赖 participant-level metric 差值的正态性假设；因此没有为了选择参数检验而额外做 Shapiro-Wilk 或方差齐性检验。

## 输出文件

- `paired_cluster_bootstrap_summary.csv`：点估计、delta 与 percentile 95% CI。
- `paired_cluster_bootstrap_replicates.csv`：全部 bootstrap replicate，便于复核或重画图。
- `per_class_metrics.csv`：两个模型的四类 precision/recall/F1/support。
- `analysis_manifest.json`：输入哈希、运行环境、对齐规则与产物清单。

## 推断边界

本 bootstrap 描述固定训练结果在测试参与者层面的不确定性。它不覆盖 DistilBERT 初始化、mini-batch 顺序或训练随机种子造成的波动，也不应被解读为多随机种子模型比较。
