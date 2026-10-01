# 001｜Flat 四分类 Logistic Regression

## 一句话结论

该模型**已经实现并完成两种切分的基线复现与无 test 泄漏调参**。在主要的 participant-heldout 协议上，本轮 CV 选择 `C=3, class_weight=balanced`，冻结 test 的 macro-F1 从 `0.366901` 小幅升至 `0.370655`；但 participant bootstrap 的 95% CI 跨 0，尚不能称为稳定改进。row-stratified 切分反而略降，因此当前没有证据表明调参版本应无条件取代 `C=1` 基线。

## 模型定义

Flat 模型把四种权限回答直接视作互斥类别，使用一个四分类 Logistic Regression：

\[
\hat y=\arg\max_{c\in\{0,1,2,3\}}P(y=c\mid x).
\]

`lbfgs` 在四分类目标上拟合 multinomial/softmax 决策面。该模型不显式利用标签的顺序关系，也不拆分“当前允许访问”和“下次是否再问”两个决策。

## 标签与特征

数据由原始 [`user_study.json`](../../ai_agent_permission_experiment/external/ai-agent-permissions/data/user_study.json) 重建，而不是由已过滤中间回答的 `processed_dataset.json` 建模。只保留 `Valid is True` 的参与者，将 `task3` 中每个 `(query, tool, raw_data_type)` 权限回答展开成一行；最终为 16,361 行、201 名参与者、65 个 query。

| ID | 标签 | 行数 |
|---:|---|---:|
| 0 | `No, never share` | 2,361 |
| 1 | `No, but ask me next time` | 1,720 |
| 2 | `Yes, but ask me next time` | 7,056 |
| 3 | `Yes, always share` | 5,224 |

三个模型共享同一特征管线：

- 文本：拼接 `query, tool, raw_data_type, generic_data_type, domain`，使用 TF-IDF 1–2 gram，`min_df=2`，`max_features=20000`。
- 类别：`domain, tool, generic_data_type, necessity_status, gender, education, concern_domain`，使用 one-hot，未知类别忽略。
- 数值/序数：`age, ai_familiarity, ai_frequency, ai_trust, privacy_importance` 原值直通；缺失数值填 `-1`。

实现见 [`run_four_label_benchmark.py`](../../ai_agent_permission_experiment/src/run_four_label_benchmark.py) 中的 `FlatFourClassModel`。

## 默认参数

基线显式设置：`C=1.0`、L2 正则（sklearn 默认）、`solver=lbfgs`、`class_weight=balanced`、`max_iter=2000`、`random_state=42`。没有单独调文本特征、正则类型或类别专属决策阈值。

## 是否已做

**已做。** 旧实验的两种固定 outer split 均已逐值复现：

- `row_stratified`：按行分层 80/20，train/test 都包含同一批 201 名参与者，属于较乐观的“同参与者新记录”评估。
- `participant_heldout`：按参与者 80/20 留出，训练 160 人、测试 41 人，参与者重叠为 0；这是当前主要协议。

## 原始两 split 结果

以下为 `C=1, balanced` 基线；风险率越低越好。

| split | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---:|---:|---:|---:|---:|
| row-stratified | 0.466544 | 0.432445 | 0.386593 | 31.37% | 22.35% |
| participant-heldout | 0.406560 | 0.366901 | 0.309409 | 43.04% | 21.18% |

其中：

- `over_sharing_rate`：真实标签为 0/1，但预测为 2/3 的比例。
- `persistent_over_allow_rate`：真实标签不是 3，但模型预测为 3 的比例。

## 本轮 CV 选参与冻结 test 结果

固定原 outer test 不参与选参，仅在 outer train 内做 3 折 OOF CV。participant-heldout 使用按参与者分组的 `GroupKFold`；row-stratified 使用按行的 `StratifiedKFold`。搜索 `C ∈ {0.1, 0.3, 1, 3, 10}` 与 `class_weight ∈ {balanced, None}`，主目标为 macro-F1；依次用 QWK、accuracy、较低过度授权率、较低持久过度允许率打破并列。

| split | CV 选择 | CV Macro-F1 |
|---|---|---:|
| row-stratified | `C=0.3, balanced` | 0.425370 |
| participant-heldout | `C=3, balanced` | 0.338943 |

冻结 test 对比：

| split | 版本 | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---|---:|---:|---:|---:|---:|
| row-stratified | baseline | 0.466544 | 0.432445 | 0.386593 | 31.37% | 22.35% |
| row-stratified | tuned | 0.469600 | 0.432140 | 0.381137 | 32.84% | 22.44% |
| participant-heldout | baseline | 0.406560 | 0.366901 | 0.309409 | 43.04% | 21.18% |
| participant-heldout | tuned | 0.409269 | 0.370655 | 0.315495 | 42.57% | 21.04% |

结论仅限本轮有限搜索空间：participant-heldout 上各项略好，但 row-stratified 的 macro-F1、QWK 和风险率略差，且两个 split 选择了不同的 `C`。这不是“全局最优参数”的证据。

## Participant bootstrap CI

在 41 名 held-out 参与者上做 2,000 次 participant-cluster bootstrap。下表为 `tuned − baseline`；对两个风险率，负值才表示改善。

| 指标 | 观测差值 | 95% CI | 判断 |
|---|---:|---:|---|
| Accuracy | +0.002708 | [-0.002396, 0.007898] | 跨 0 |
| Macro-F1 | +0.003754 | [-0.001957, 0.009581] | 跨 0 |
| QWK | +0.006086 | [-0.003985, 0.015449] | 跨 0 |
| 过度授权率 | -0.47 个百分点 | [-1.36, +0.44] 个百分点 | 跨 0 |
| 持久过度允许率 | -0.13 个百分点 | [-0.58, +0.26] 个百分点 | 跨 0 |

因此应把调参收益描述为“小幅、方向较好但不确定”，不能宣称稳定优于基线。

## 风险取舍

- Flat 的优点是结构最简单、没有 Ordinal 阈值不一致问题，且本轮 participant-heldout 的安全指标没有恶化。
- 它忽略标签的顺序与因子结构；少数类 0/1 的边界可能被总体 macro-F1 目标掩盖。
- row-stratified 中参与者跨 train/test，分数不能代表新参与者泛化；即使 participant-heldout 无参与者泄漏，65 个 query 模板仍在两侧共享。
- 目前只有一个固定 outer participant split。bootstrap 量化的是该 test 集内部按参与者聚类的不确定性，不等于跨多次随机外层切分的稳定性。

## 可复现命令

从 `Week67` 根目录运行。调参脚本会同时训练三类 LR；读取 `flat_four_class_lr` 对应行即可。使用新的输出目录，避免覆盖已冻结产物。

```powershell
& .\ai_agent_permission_experiment\.venv\Scripts\python.exe `
  .\ai_agent_permission_experiment\src\run_four_label_benchmark.py `
  --data .\ai_agent_permission_experiment\data\processed\four_label_dataset.csv `
  --split row_stratified `
  --out .\classification_experiments\artifacts\reproduced_baseline_rerun

& .\ai_agent_permission_experiment\.venv\Scripts\python.exe `
  .\ai_agent_permission_experiment\src\run_four_label_benchmark.py `
  --data .\ai_agent_permission_experiment\data\processed\four_label_dataset.csv `
  --split participant_heldout `
  --out .\classification_experiments\artifacts\reproduced_baseline_rerun

& .\ai_agent_permission_experiment\.venv\Scripts\python.exe `
  .\ai_agent_permission_experiment\src\tune_four_label_classifiers.py `
  --data .\ai_agent_permission_experiment\data\processed\four_label_dataset.csv `
  --out .\classification_experiments\artifacts\nested_tuning_rerun `
  --splits row_stratified participant_heldout `
  --inner-folds 3 --random-state 20260809 --bootstrap-samples 2000 `
  --c-values 0.1 0.3 1 3 10 `
  --ordinal-thresholds 0.35 0.4 0.45 0.5 0.55 0.6 0.65 `
  --factored-thresholds 0.4 0.5 0.6
```

## 产物链接

- 基线指标：[row-stratified](../artifacts/reproduced_baseline/row_stratified/metrics.csv)；[participant-heldout](../artifacts/reproduced_baseline/participant_heldout/metrics.csv)
- CV 选参：[row-stratified](../artifacts/nested_tuning_20260809/row_stratified/selected_hyperparameters.json)；[participant-heldout](../artifacts/nested_tuning_20260809/participant_heldout/selected_hyperparameters.json)
- 冻结 test：[row-stratified](../artifacts/nested_tuning_20260809/row_stratified/test_metrics.csv)；[participant-heldout](../artifacts/nested_tuning_20260809/participant_heldout/test_metrics.csv)
- Flat 混淆矩阵：[participant baseline](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_flat_four_class_lr_baseline.csv)；[participant tuned](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_flat_four_class_lr_tuned.csv)
- 配对 bootstrap：[participant_bootstrap_deltas.csv](../artifacts/nested_tuning_20260809/participant_heldout/participant_bootstrap_deltas.csv)

## 下一步

1. 用 repeated participant-group outer splits 或 nested group CV 检验 `C=3` 是否稳定，而不是继续读取当前冻结 test 选参。
2. 在 macro-F1 之外加入安全约束或多目标选择，例如限制过度授权率不得高于基线。
3. 保持相同数据、特征和 split，追加 Linear SVM、朴素贝叶斯、树模型等经典基线；每个新模型单独建编号文档。

