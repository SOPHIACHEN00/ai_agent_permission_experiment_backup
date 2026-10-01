# 003｜Factored Logistic Regression

## 一句话结论

Factored 模型**已经实现，不是 TBD**。它把四标签拆成“当前是否允许访问”与“下次遇到请求是否再次询问”两个二分类任务。participant-heldout 调参提高 accuracy，但 macro-F1 增益的 bootstrap CI 跨 0，QWK 略降，而且两项安全风险都有区间不跨 0 的恶化；因此 tuned 版本不宜作为当前安全默认值。

## 模型定义

模型训练两个独立二分类 LR：

1. `access`：标签 0/1 为 deny（0），标签 2/3 为 allow（1）。
2. `persistence`：标签 1/2 为 ask-again（0），标签 0/3 为 persist（1）。

组合规则：

| access | persistence | 四分类输出 |
|---:|---:|---|
| deny (0) | persist (1) | 0：`No, never share` |
| deny (0) | ask-again (0) | 1：`No, but ask me next time` |
| allow (1) | ask-again (0) | 2：`Yes, but ask me next time` |
| allow (1) | persist (1) | 3：`Yes, always share` |

### `persistence` 的准确含义

这里的第二因子指**策略持久性**：下一次遇到数据访问请求时，是否沿用当前 deny/allow 决定而不再次询问。它**不是数据是否被保存、缓存、保留或长期存储**。因此本文档中的 persist/持久仅描述未来询问策略；不能把该因子解释为 data retention。

实现见 [`run_four_label_benchmark.py`](../../ai_agent_permission_experiment/src/run_four_label_benchmark.py) 中的 `FactoredLogisticModel`。

## 标签与特征

四标签映射为两个因子：

| ID | 标签 | access | 策略 persistence |
|---:|---|---:|---:|
| 0 | `No, never share` | deny | persist/no re-ask |
| 1 | `No, but ask me next time` | deny | ask again |
| 2 | `Yes, but ask me next time` | allow | ask again |
| 3 | `Yes, always share` | allow | persist/no re-ask |

数据由原始 [`user_study.json`](../../ai_agent_permission_experiment/external/ai-agent-permissions/data/user_study.json) 重建，共 16,361 行、201 名参与者、65 个 query。两个 head 使用相同输入特征；基线 runner 为两个 head 分别拟合完整 pipeline，本轮调参 runner 在每个 fold 的训练部分拟合一次预处理器，再把同一特征矩阵交给两个独立 LR：

- 文本：`query, tool, raw_data_type, generic_data_type, domain` 拼接后的 TF-IDF 1–2 gram，`min_df=2`，最多 20,000 维。
- 类别：`domain, tool, generic_data_type, necessity_status, gender, education, concern_domain` one-hot。
- 数值/序数：`age, ai_familiarity, ai_frequency, ai_trust, privacy_importance` 原值直通。

## 默认参数

access 与 persistence 两个 head 均使用 `C=1.0`、L2 正则、`solver=lbfgs`、`class_weight=balanced`、`max_iter=2000`、`random_state=42`，二者决策阈值均为 `0.5`。两个 head 不共享系数，也没有联合损失或组合后的二次校准。

## 是否已做

**已做，不是 TBD。** 两个二分类器、四标签重组、两种 outer split、分类报告与混淆矩阵都已经存在，并且旧结果已由当前代码逐值复现。

## 原始两 split 结果

以下为两个 head 均 `C=1, balanced, threshold=0.5` 的基线；风险率越低越好。

| split | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---:|---:|---:|---:|---:|
| row-stratified | 0.450351 | 0.408915 | 0.370662 | 32.97% | 19.93% |
| participant-heldout | 0.405958 | 0.365880 | 0.282585 | 44.10% | 18.70% |

`over_sharing_rate` 是真实 access 为 deny（标签 0/1）却预测 allow（2/3）；`persistent_over_allow_rate` 是真实标签不为 3 却预测 `Yes, always share`。后者同样是权限策略风险，不是数据存储率。

## 本轮 CV 选参与冻结 test 结果

固定 outer test，仅在 outer train 内做 3 折 OOF CV。分别搜索两个 head 的 `C ∈ {0.1,0.3,1,3,10}`、`class_weight ∈ {balanced,None}`，并搜索 access/persistence 阈值 `∈ {0.4,0.5,0.6}`；两个 head 的候选做笛卡尔组合。主选择目标为组合后四分类 macro-F1。

| split | CV 选择 | CV Macro-F1 |
|---|---|---:|
| row-stratified | access `C=1, balanced, t=0.4`；persistence `C=1, balanced, t=0.5` | 0.425313 |
| participant-heldout | access `C=3, balanced, t=0.4`；persistence `C=10, balanced, t=0.5` | 0.348509 |

冻结 test 对比：

| split | 版本 | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---|---:|---:|---:|---:|---:|
| row-stratified | baseline | 0.450351 | 0.408915 | 0.370662 | 32.97% | 19.93% |
| row-stratified | tuned | 0.490070 | 0.419119 | 0.375503 | 46.69% | 23.92% |
| participant-heldout | baseline | 0.405958 | 0.365880 | 0.282585 | 44.10% | 18.70% |
| participant-heldout | tuned | 0.436353 | 0.377619 | 0.274148 | 54.72% | 22.28% |

### 关键安全结论

**tuned Factored 的安全性变差。** 在主要 participant-heldout test 上，过度授权率增加 `10.61` 个百分点，持久过度允许率增加 `3.58` 个百分点；row-stratified 也分别增加 `13.73` 和 `3.99` 个百分点。较低的 access 阈值 `0.4` 是允许预测增多的直接机制之一。

## Participant bootstrap CI

对 41 名 held-out 参与者做 2,000 次 cluster bootstrap。下表为 `tuned − baseline`；风险率正值代表恶化。

| 指标 | 观测差值 | 95% CI | 判断 |
|---|---:|---:|---|
| Accuracy | +0.030394 | [0.014366, 0.049303] | 改善区间不跨 0 |
| Macro-F1 | +0.011740 | [-0.004027, 0.027636] | 跨 0 |
| QWK | -0.008436 | [-0.031594, 0.017929] | 跨 0，点估计下降 |
| 过度授权率 | +10.61 个百分点 | [+7.84, +13.92] 个百分点 | 明确恶化 |
| 持久过度允许率 | +3.58 个百分点 | [+2.26, +5.04] 个百分点 | 明确恶化 |

## 风险取舍

- 拆因子有清晰的权限语义，也允许分别调 access 与再次询问策略；基线的持久过度允许率是三个模型中最低的。
- 当前 CV 只最大化 macro-F1，安全率仅作为并列候选的后续 tie-break，无法阻止明显更危险但 macro-F1 略高的候选胜出。
- participant-heldout 的 tuned accuracy 明确提高，但主要来自哪些四类/两个因子仍需结合两个 head 的独立指标解释；四分类 QWK 并未改善。
- row-stratified 有参与者重叠；participant-heldout 仍共享 query 模板。当前单一 outer split 不能证明参数跨参与者抽样稳定。

## 可复现命令

从 `Week67` 根目录运行。脚本同时训练三类 LR；读取 `factored_lr` 行与相应报告。输出目录必须是新的空目录。

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
- Factored 报告：[participant baseline](../artifacts/nested_tuning_20260809/participant_heldout/classification_report_factored_lr_baseline.json)；[participant tuned](../artifacts/nested_tuning_20260809/participant_heldout/classification_report_factored_lr_tuned.json)
- Factored 混淆矩阵：[participant baseline](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_factored_lr_baseline.csv)；[participant tuned](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_factored_lr_tuned.csv)
- 配对 bootstrap：[participant_bootstrap_deltas.csv](../artifacts/nested_tuning_20260809/participant_heldout/participant_bootstrap_deltas.csv)

## 下一步

1. 将安全约束纳入候选选择，例如限定过度授权率和持久过度允许率不高于基线，再优化 macro-F1；当前 tuned 参数先不升格为默认值。
2. 分别输出 access head 与 ask-again/persist head 的 ROC/PR、校准、混淆矩阵和 participant bootstrap，定位 accuracy 增益与安全损失来自哪个 head。
3. 用 repeated participant-group outer splits 检查 access `t=0.4` 的稳定性，并尝试联合多任务或组合后校准，但始终保留“策略持久性 ≠ 数据存储”的术语约束。
