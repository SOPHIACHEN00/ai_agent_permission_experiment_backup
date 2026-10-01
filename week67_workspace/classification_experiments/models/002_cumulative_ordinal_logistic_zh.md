# 002｜累计阈值 Ordinal Logistic Regression

## 一句话结论

该模型**已经实现并完成两种切分的基线复现与无 test 泄漏调参**，但名称容易造成误解：它不是 proportional-odds ordinal logit，而是三个彼此独立的二分类 LR。participant-heldout 调参后 macro-F1 从 `0.362884` 升至 `0.374360`，但 95% bootstrap CI 跨 0，同时两项安全风险明确恶化（风险差值 CI 不跨 0）；当前不应仅凭 macro-F1 替换默认版本。

## 模型定义

分别训练三个二分类器：

\[
q_k(x)=P(y>k\mid x),\quad k\in\{0,1,2\}.
\]

默认以 `0.5` 截断每个概率，并将三个二进制结果求和：

\[
\hat y=\sum_{k=0}^{2}\mathbb{1}[q_k(x)\ge t].
\]

### 重要：不是 proportional-odds 模型

三个 LR 各自拥有独立的系数与截距，没有 proportional-odds 模型所要求的共享斜率和有序 cutpoints。因此本文档使用更准确的名称“累计阈值 LR（cumulative-threshold LR）”，而不把它当作标准 ordered logit。

### 重要：没有单调约束

代码没有强制 `q_0 ≥ q_1 ≥ q_2`，也没有对阈值后的三个位做单调修复。合法累计位模式只有 `000, 100, 110, 111`；当前实现也会产生 `001, 010, 011, 101` 等不一致模式，再直接“求和”成 0–3。最终标签虽然合法，但其累计语义已经不一致。

在默认 `C=1, balanced, t=0.5` 的固定 test 上：

- participant-heldout：`238 / 3323 = 7.16%` 的样本出现不一致位模式；
- row-stratified：`303 / 3273 = 9.26%` 的样本出现不一致位模式。

实现见 [`run_four_label_benchmark.py`](../../ai_agent_permission_experiment/src/run_four_label_benchmark.py) 中的 `OrdinalLogisticModel`。

## 标签与特征

标签按分享意愿从低到高编码：

| ID | 标签 | 三个训练目标 `(y>0, y>1, y>2)` |
|---:|---|---|
| 0 | `No, never share` | `(0,0,0)` |
| 1 | `No, but ask me next time` | `(1,0,0)` |
| 2 | `Yes, but ask me next time` | `(1,1,0)` |
| 3 | `Yes, always share` | `(1,1,1)` |

数据由原始 [`user_study.json`](../../ai_agent_permission_experiment/external/ai-agent-permissions/data/user_study.json) 重建，共 16,361 行、201 名参与者、65 个 query。三个阈值器共享特征定义；基线 runner 为每个阈值器分别拟合完整 pipeline，本轮调参 runner 则在每个 fold 的训练部分拟合一次预处理器，再把同一特征矩阵交给三个独立 LR：

- 文本：`query, tool, raw_data_type, generic_data_type, domain` 拼接后的 TF-IDF 1–2 gram，`min_df=2`，最多 20,000 维。
- 类别：`domain, tool, generic_data_type, necessity_status, gender, education, concern_domain` one-hot。
- 数值/序数：`age, ai_familiarity, ai_frequency, ai_trust, privacy_importance` 原值直通。

## 默认参数

每个阈值器均使用 `C=1.0`、L2 正则、`solver=lbfgs`、`class_weight=balanced`、`max_iter=2000`、`random_state=42`；三个决策阈值共同使用 `t=0.5`。默认实现没有概率校准、共享系数、cutpoint 排序或单调投影。

## 是否已做

**已做。** 用户先前记录的 “Ordinal Logistic Regression” 对应的就是上述三个独立累计二分类器，而不是待实现模型。它已在 `row_stratified` 与 `participant_heldout` 两个固定 outer split 上运行并逐值复现。

## 原始两 split 结果

以下为 `C=1, balanced, t=0.5` 基线；风险率越低越好。

| split | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---:|---:|---:|---:|---:|
| row-stratified | 0.453407 | 0.403547 | 0.395507 | 34.31% | 25.00% |
| participant-heldout | 0.406560 | 0.362884 | 0.314125 | 42.69% | 24.49% |

`over_sharing_rate` 是真实 0/1 却预测 2/3；`persistent_over_allow_rate` 是真实不为 3 却预测 3。

## 本轮 CV 选参与冻结 test 结果

固定 outer test，仅在 outer train 内做 3 折 OOF CV。participant-heldout 的 inner CV 按参与者 GroupKFold；row-stratified 按行 StratifiedKFold。搜索 `C ∈ {0.1,0.3,1,3,10}`、`class_weight ∈ {balanced,None}`、共同阈值 `t ∈ {0.35,0.40,0.45,0.50,0.55,0.60,0.65}`，以 macro-F1 选择。

| split | CV 选择 | CV Macro-F1 |
|---|---|---:|
| row-stratified | `C=10, class_weight=None, t=0.50` | 0.400660 |
| participant-heldout | `C=10, class_weight=balanced, t=0.45` | 0.347346 |

冻结 test 对比：

| split | 版本 | Accuracy | Macro-F1 | QWK | 过度授权率 | 持久过度允许率 |
|---|---|---:|---:|---:|---:|---:|
| row-stratified | baseline | 0.453407 | 0.403547 | 0.395507 | 34.31% | 25.00% |
| row-stratified | tuned | 0.522456 | 0.407493 | 0.379103 | 67.03% | 11.54% |
| participant-heldout | baseline | 0.406560 | 0.362884 | 0.314125 | 42.69% | 24.49% |
| participant-heldout | tuned | 0.427325 | 0.374360 | 0.317849 | 48.82% | 29.89% |

调参版本提高了主要 split 的 accuracy 与 macro-F1，但 participant-heldout 的两项安全风险同时恶化；row-stratified 中过度授权率更从 34.31% 跳到 67.03%。这说明单独优化 macro-F1 会选出不适合安全决策的阈值/权重组合。

## Participant bootstrap CI

对 41 名 held-out 参与者做 2,000 次 cluster bootstrap。下表为 `tuned − baseline`；风险率正值代表恶化。

| 指标 | 观测差值 | 95% CI | 判断 |
|---|---:|---:|---|
| Accuracy | +0.020764 | [0.006799, 0.034567] | 改善区间不跨 0 |
| Macro-F1 | +0.011475 | [-0.003608, 0.026561] | 跨 0 |
| QWK | +0.003725 | [-0.019412, 0.026167] | 跨 0 |
| 过度授权率 | +6.13 个百分点 | [+3.74, +9.05] 个百分点 | 明确恶化 |
| 持久过度允许率 | +5.39 个百分点 | [+3.80, +7.34] 个百分点 | 明确恶化 |

## 风险取舍

- Ordinal 表达了 0→3 的顺序结构，基线 QWK 在两个 split 上均略高于 Flat；但当前独立阈值实现不是严格 ordinal model。
- `t=0.45` 会让更多 `y>k` 判断变为 1，participant-heldout 上因此提高整体准确率，也扩大了过度授权与预测 3 的概率。
- 7.16%/9.26% 的不一致模式说明“最终输出仍在 0–3”不足以证明模型满足 ordinal 语义。
- row-stratified 仍存在参与者跨 train/test；participant-heldout 虽无参与者重叠，但 query 模板共享。单一固定 outer split 也不足以支持“最佳模型”结论。

## 可复现命令

从 `Week67` 根目录运行。脚本同时训练三类 LR；读取 `ordinal_lr` 行与相应报告。输出目录必须是新的空目录。

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
- Ordinal 报告：[participant baseline](../artifacts/nested_tuning_20260809/participant_heldout/classification_report_ordinal_lr_baseline.json)；[participant tuned](../artifacts/nested_tuning_20260809/participant_heldout/classification_report_ordinal_lr_tuned.json)
- Ordinal 混淆矩阵：[participant baseline](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_ordinal_lr_baseline.csv)；[participant tuned](../artifacts/nested_tuning_20260809/participant_heldout/confusion_matrix_ordinal_lr_tuned.csv)
- 配对 bootstrap：[participant_bootstrap_deltas.csv](../artifacts/nested_tuning_20260809/participant_heldout/participant_bootstrap_deltas.csv)

## 下一步

1. 实现真正的 cumulative-link/proportional-odds 基线，或对三个累计概率做单调投影，并把不一致率作为正式诊断产物保存。
2. 将安全约束加入 CV 选择，例如在过度授权率不高于基线的候选中最大化 macro-F1，而不是只作末位 tie-break。
3. 用 repeated participant-group outer splits 比较：独立阈值、单调修复、proportional-odds 三种实现；不要继续用当前 frozen test 迭代阈值。
