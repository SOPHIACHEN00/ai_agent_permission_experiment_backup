# 2026-08-09：三类 Logistic Regression 无 test 泄漏调参

## 为什么重新调参

历史 `ai_agent_permission_experiment/results/tuning/flat_lr_tuning_*.csv` 只覆盖 Flat：

- `C ∈ {0.1, 0.3, 1, 3, 10}`；
- `class_weight ∈ {balanced, None}`。

这些表没有生成脚本、validation 字段或 run config；`C=1, balanced` 与最终 test 指标逐值相同，其他候选也直接报告同一个外层 test。因此它们只能标记为 **test-touched exploratory sweep**，不能用于无偏选择“最佳参数”。Ordinal 和 Factored 此前没有调参记录。

## 本轮新增内容

- 新脚本：[`../../ai_agent_permission_experiment/src/tune_four_label_classifiers.py`](../../ai_agent_permission_experiment/src/tune_four_label_classifiers.py)
- 固定原外层 test，不用 test 选参数。
- 在外层 train 内进行 3 折 CV：
  - `participant_heldout`：`GroupKFold`，按 participant 分组；
  - `row_stratified`：`StratifiedKFold`，seed `20260809`。
- 选择目标：CV pooled Macro-F1；依次以 QWK、Accuracy、较低 over-sharing、较低 persistent-over-allow 打破精确平局。
- 冻结参数后，在完整 outer train 重训并只评一次 outer test。
- 对主协议使用 2,000 次 paired participant-cluster bootstrap，单位是 41 名测试参与者，而不是 3,323 行。
- 每个 split 保存 192 条收敛诊断，全部 `converged=True`。

执行完成后，代码审查又加入了两个不改变拟合/搜索逻辑的前置护栏：检查 fold 中目标是否可训练、拒绝写入已有非空 run 目录。因此当前主脚本哈希为 `AFA95890...D7E51B`，而本轮 `run_config.json` 记录的执行时哈希为 `A476B363...1AB2C`。执行时源码已原样保存为 [`../artifacts/nested_tuning_20260809/source/tune_four_label_classifiers_run_snapshot.py`](../artifacts/nested_tuning_20260809/source/tune_four_label_classifiers_run_snapshot.py)，完整 SHA-256 与 run config 精确一致。

## 搜索空间

| 模型 | 搜索项 | 候选数 |
|---|---|---:|
| Flat | `C` 5 种 × `class_weight` 2 种 | 10 |
| Ordinal | Flat 的 10 种 × `τ ∈ {0.35,0.40,0.45,0.50,0.55,0.60,0.65}` | 70 |
| Factored | access 配置 10 × persistence 配置 10 × 两个阈值各 3 种 | 900 |

所有模型保持同一特征管线；本轮没有调 TF-IDF、one-hot 或数值特征，也没有移除潜在 oracle 特征 `necessity_status`。所以“best”只表示**该固定特征、固定外层 split、给定网格、以 Macro-F1 为选择目标**下的 CV 选择，不是全局最优。

## 实际运行命令

以下是本轮使用的核心参数。当前脚本会拒绝写入已有非空目录；复跑时必须把 `--out` 改成新的唯一 run ID。

```powershell
& .\.venv\Scripts\python.exe -B -u src\tune_four_label_classifiers.py `
  --data data\processed\four_label_dataset.csv `
  --out ..\classification_experiments\artifacts\<new_run_id> `
  --splits participant_heldout `
  --inner-folds 3 --random-state 20260809 --bootstrap-samples 2000 `
  --c-values 0.1 0.3 1 3 10 `
  --ordinal-thresholds 0.35 0.4 0.45 0.5 0.55 0.6 0.65 `
  --factored-thresholds 0.4 0.5 0.6
```

`row_stratified` 使用相同搜索空间，但 `--bootstrap-samples 0`。

## 主协议选中的参数

| 模型 | CV 选中参数 |
|---|---|
| Flat | `C=3`, `class_weight=balanced` |
| Ordinal | `C=10`, `class_weight=balanced`, `decision_threshold=0.45` |
| Factored | access: `C=3, balanced, threshold=0.4`; persistence: `C=10, balanced, threshold=0.5` |

## Participant-held-out 冻结测试结果

| 模型 | 版本 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---|---:|---:|---:|---:|---:|
| Flat | baseline | 0.406560 | 0.366901 | 0.309409 | 0.430425 | 0.211760 |
| Flat | tuned | 0.409269 | 0.370655 | 0.315495 | 0.425708 | 0.210433 |
| Ordinal | baseline | 0.406560 | 0.362884 | 0.314125 | 0.426887 | 0.244916 |
| Ordinal | tuned | 0.427325 | 0.374360 | 0.317849 | 0.488208 | 0.298851 |
| Factored | baseline | 0.405958 | 0.365880 | 0.282585 | 0.441038 | 0.187003 |
| Factored | tuned | 0.436353 | 0.377619 | 0.274148 | 0.547170 | 0.222812 |

### Paired participant-bootstrap 差值

差值均为 tuned − baseline，括号为 95% percentile CI。

| 模型 | Δ Macro-F1 | Δ QWK（原始分数） | Δ Over-sharing ↓ | Δ Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|
| Flat | +0.375 pp `[-0.196, +0.958]` | +0.00609 `[-0.00399, +0.01545]` | −0.472 pp `[-1.358, +0.440]` | −0.133 pp `[-0.584, +0.265]` |
| Ordinal | +1.148 pp `[-0.361, +2.656]` | +0.00372 `[-0.01941, +0.02617]` | **+6.132 pp** `[+3.739, +9.046]` | **+5.393 pp** `[+3.803, +7.340]` |
| Factored | +1.174 pp `[-0.403, +2.764]` | −0.00844 `[-0.03159, +0.01793]` | **+10.613 pp** `[+7.838, +13.921]` | **+3.581 pp** `[+2.264, +5.035]` |

解释：三个模型的 Macro-F1 CI 都跨 0，不能说调参带来稳定提升。Flat 的五个点估计方向都较好，但幅度小；Ordinal/Factored 的安全风险恶化区间不跨 0，因此若权限安全是约束，不应因更高的点估计 Macro-F1 采用其 tuned 版本。

## Row-stratified 补充结果

| 模型 | CV 选中参数 | Baseline F1 | Tuned F1 | Baseline / Tuned over-sharing |
|---|---|---:|---:|---:|
| Flat | `C=0.3, balanced` | **0.432445** | 0.432140 | 0.313725 / 0.328431 |
| Ordinal | `C=10, none, τ=0.5` | 0.403547 | 0.407493 | 0.343137 / **0.670343** |
| Factored | 两因子 `C=1, balanced`; access `τ=0.4` | 0.408915 | 0.419119 | 0.329657 / **0.466912** |

该协议同一参与者跨 train/test，只作为历史可比。Flat 的原 `C=1` 在冻结 row test 上反而略高，说明不能看 test 后改回参数；Ordinal/Factored 再次显示 accuracy/F1 与安全指标之间的强烈冲突。

## 最终判断

- **Flat：** `C=3, balanced` 可作为主协议的 tuned candidate，同时保留 `C=1` 历史 baseline；不能宣称其已显著优于默认值。
- **Ordinal：** 已调参，但当前方法本身不是严格 ordered logit；降低阈值换来的 over-sharing 增长不适合作为默认权限模型。
- **Factored：** 已调参且 Macro-F1 点估计最高，但安全代价最大，不能称“最好”。默认 Factored 在 persistent-over-allow 上仍是三种默认模型中最低。

## 产物

- [`../artifacts/nested_tuning_20260809/participant_heldout/`](../artifacts/nested_tuning_20260809/participant_heldout/)
- [`../artifacts/nested_tuning_20260809/row_stratified/`](../artifacts/nested_tuning_20260809/row_stratified/)
- 每个 split 包含 `cv_results.csv`、`selected_hyperparameters.json`、`test_metrics.csv`、`test_predictions.csv`、分类报告、混淆矩阵、收敛诊断和 `run_config.json`。
