# 四标签经典分类器：统计附录

## 1. 证据来源与分析口径

主目录：`classification_experiments/artifacts/nested_tuning_20260809/participant_heldout/`

使用的核心文件：

- `run_config.json`：切分、样本、随机状态、搜索网格与软件版本；
- `selected_hyperparameters.json`：内层 CV 选出的配置；
- `test_metrics.csv`：固定外层测试集点估计与风险计数；
- `participant_bootstrap_deltas.csv`：tuned − baseline 的参与者配对聚类 bootstrap 汇总；
- `classification_report_*.json`：逐类 precision/recall/F1/support；
- `test_predictions.csv`：逐行真实标签、预测与 participant ID；
- `convergence_diagnostics.csv`：优化收敛记录。

敏感性目录：`classification_experiments/artifacts/nested_tuning_20260809/row_stratified/`。

数据文件 SHA-256：`4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`。主运行脚本 SHA-256：`a476b363255808d6ea82f1f4c5fa18fe51e65d9bfd196323b8b603a34ee1ab2c`。

## 2. 指标定义、方向与单位

| 指标 | 定义 | 方向 | 报告单位 |
|---|---|---:|---|
| Accuracy | 正确预测行数 / 全部测试行数 | 越高越好 | `0–1` 分数；差值另给百分点 |
| Macro-F1 | 四个标签 F1 的未加权平均 | 越高越好 | `0–1` 分数；主指标 |
| QWK | 四级顺序标签的 quadratic weighted Cohen's kappa | 越高越好 | 理论范围 `[-1, 1]` 的无量纲分数；差值用原始 score units |
| 过度分享率 | 当真实标签属于拒绝类 `0/1` 时，预测为允许类 `2/3` 的比例 | 越低越好 | `0–1` 比例；主测试集分母 `848` |
| 持续授权过度率 | 当真实标签不为 `3` 时，预测为 `3` 的比例 | 越低越好 | `0–1` 比例；主测试集分母 `2,262` |

## 3. 样本量、切分与独立性

| 切分 | 训练行 | 测试行 | 训练参与者 | 测试参与者 | 参与者重叠 | 推断用途 |
|---|---:|---:|---:|---:|---:|---|
| participant-held-out | 13,038 | 3,323 | 160 | 41 | 0 | 主评价；未见参与者泛化 |
| row-stratified | 13,088 | 3,273 | 201 | 201 | 201 | 描述性敏感性检查，不作新参与者推断 |

主测试集四类支持数依次为 `510 / 338 / 1,414 / 1,061`。41 个测试参与者 cluster 每个包含 `68–91` 行，中位数 `82` 行。因为同一参与者贡献多行，行不是独立推断单位；因此没有把 `3,323` 行当作独立样本进行 t 检验或普通行级 bootstrap。

## 4. 模型、基线与调参空间

所有 baseline Logistic Regression 均使用 `C=1.0`、`class_weight=balanced`；Ordinal 和 Factored baseline 的决策阈值均为 `0.5`。

内层 participant-held-out 调参采用 3-fold GroupKFold，按参与者分组，选择指标为 Macro-F1。候选数为 Flat `10`、Ordinal `70`、Factored `900`；排序 tie-break 依次为更高 QWK、更高 Accuracy、更低过度分享率、更低持续授权过度率。

| 模型 | participant-held-out 选中配置 | 内层 OOF Macro-F1 | row-stratified 选中配置 | 内层 OOF Macro-F1 |
|---|---|---:|---|---:|
| Flat four-class LR | `C=3.0`, balanced | 0.338943 | `C=0.3`, balanced | 0.425370 |
| Cumulative Ordinal LR | `C=10.0`, balanced, threshold `0.45` | 0.347346 | `C=10.0`, no class weight, threshold `0.50` | 0.400660 |
| Factored LR | access: `C=3.0`, balanced, threshold `0.40`; persistence: `C=10.0`, balanced, threshold `0.50` | 0.348509 | access: `C=1.0`, balanced, threshold `0.40`; persistence: `C=1.0`, balanced, threshold `0.50` | 0.425313 |

搜索网格：`C ∈ {0.1, 0.3, 1, 3, 10}`；class weight 为 `{balanced, none}`；Ordinal threshold 为 `{0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}`；Factored 的 access/persistence threshold 各为 `{0.40, 0.50, 0.60}`。

## 5. 主测试集完整点估计

| 模型 | 版本 | Accuracy | Macro-F1 | QWK | 过度分享率（计数） | 持续授权过度率（计数） |
|---|---|---:|---:|---:|---:|---:|
| Flat four-class LR | baseline | 0.406560 | 0.366901 | 0.309409 | 0.430425（365/848） | 0.211760（479/2262） |
| Flat four-class LR | tuned | 0.409269 | 0.370655 | 0.315495 | 0.425708（361/848） | 0.210433（476/2262） |
| Cumulative Ordinal LR | baseline | 0.406560 | 0.362884 | 0.314125 | 0.426887（362/848） | 0.244916（554/2262） |
| Cumulative Ordinal LR | tuned | 0.427325 | 0.374360 | 0.317849 | 0.488208（414/848） | 0.298851（676/2262） |
| Factored LR | baseline | 0.405958 | 0.365880 | 0.282585 | 0.441038（374/848） | 0.187003（423/2262） |
| Factored LR | tuned | 0.436353 | 0.377619 | 0.274148 | 0.547170（464/848） | 0.222812（504/2262） |

这些是一个固定外层测试集的点估计，不是跨 run/seed 的均值。因此没有可合法报告的 `mean ± SD` 跨运行统计量。

## 6. 参与者配对聚类 bootstrap

### 方法

- 重抽样单位：测试参与者，`n_units = 41`；
- 重复次数：`B = 2,000`；随机状态 `20260809`；
- 每次有放回抽取 41 个参与者，并保留每个被抽中参与者的全部行；
- baseline 与 tuned 在每次重抽样中使用完全相同的参与者集合，因此为配对 cluster bootstrap；
- 效应量：`Δ = tuned − baseline` 的绝对差值；
- 区间：bootstrap 差值分布的 2.5% 与 97.5% 分位数，即 percentile 95% CI；
- 没有计算 p 值，也没有把 marginal CI 当成经过多重比较校正的 simultaneous CI。

### 所有调参差值的精确汇总

下表保持 `0–1` 原始单位；风险率的正差值代表更差。

| 模型 | 指标 | 方向 | Baseline | Tuned | 观察 Δ | Bootstrap 平均 Δ | 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|
| Flat | Accuracy | ↑ | 0.406560 | 0.409269 | +0.002708 | +0.002731 | [-0.002396, +0.007898] |
| Flat | Macro-F1 | ↑ | 0.366901 | 0.370655 | +0.003754 | +0.003820 | [-0.001957, +0.009581] |
| Flat | QWK | ↑ | 0.309409 | 0.315495 | +0.006086 | +0.006025 | [-0.003985, +0.015449] |
| Flat | 过度分享率 | ↓ | 0.430425 | 0.425708 | -0.004717 | -0.004675 | [-0.013581, +0.004399] |
| Flat | 持续授权过度率 | ↓ | 0.211760 | 0.210433 | -0.001326 | -0.001360 | [-0.005838, +0.002648] |
| Ordinal | Accuracy | ↑ | 0.406560 | 0.427325 | +0.020764 | +0.020417 | [+0.006799, +0.034567] |
| Ordinal | Macro-F1 | ↑ | 0.362884 | 0.374360 | +0.011475 | +0.011156 | [-0.003608, +0.026561] |
| Ordinal | QWK | ↑ | 0.314125 | 0.317849 | +0.003725 | +0.004005 | [-0.019412, +0.026167] |
| Ordinal | 过度分享率 | ↓ | 0.426887 | 0.488208 | +0.061321 | +0.061812 | [+0.037393, +0.090457] |
| Ordinal | 持续授权过度率 | ↓ | 0.244916 | 0.298851 | +0.053935 | +0.053849 | [+0.038032, +0.073400] |
| Factored | Accuracy | ↑ | 0.405958 | 0.436353 | +0.030394 | +0.030539 | [+0.014366, +0.049303] |
| Factored | Macro-F1 | ↑ | 0.365880 | 0.377619 | +0.011740 | +0.011919 | [-0.004027, +0.027636] |
| Factored | QWK | ↑ | 0.282585 | 0.274148 | -0.008436 | -0.007741 | [-0.031594, +0.017929] |
| Factored | 过度分享率 | ↓ | 0.441038 | 0.547170 | +0.106132 | +0.106594 | [+0.078384, +0.139213] |
| Factored | 持续授权过度率 | ↓ | 0.187003 | 0.222812 | +0.035809 | +0.035911 | [+0.022642, +0.050355] |

### 区间判读摘要

| 指标族 | Flat | Ordinal | Factored |
|---|---|---|---|
| Accuracy | CI 跨 0，方向未锁定 | CI 全高于 0 | CI 全高于 0 |
| Macro-F1（主指标） | CI 跨 0 | CI 跨 0 | CI 跨 0 |
| QWK | CI 跨 0 | CI 跨 0 | CI 跨 0 |
| 过度分享率（越低越好） | CI 跨 0 | CI 全高于 0，风险变差 | CI 全高于 0，风险变差 |
| 持续授权过度率（越低越好） | CI 跨 0 | CI 全高于 0，风险变差 | CI 全高于 0，风险变差 |

## 7. 逐类 Recall

| 模型 | 版本 | Never（n=510） | No + ask（n=338） | Yes + ask（n=1,414） | Always（n=1,061） |
|---|---|---:|---:|---:|---:|
| Flat | baseline | 0.313725 | 0.304734 | 0.439180 | 0.440151 |
| Flat | tuned | 0.317647 | 0.316568 | 0.439180 | 0.442978 |
| Ordinal | baseline | 0.464706 | 0.180473 | 0.369873 | 0.499529 |
| Ordinal | tuned | 0.411765 | 0.171598 | 0.393211 | 0.561734 |
| Factored | baseline | 0.294118 | 0.355030 | 0.483027 | 0.373233 |
| Factored | tuned | 0.262745 | 0.284024 | 0.567893 | 0.393025 |

逐类 Recall 只给固定测试集点估计，当前产物没有其 participant-bootstrap CI。类别支持数不均衡，尤其 “No + ask” 仅 `338` 行，因此不能仅凭柱高判断跨样本稳定性。

## 8. Row-stratified 敏感性结果

| 模型 | 版本 | Accuracy | Macro-F1 | QWK | 过度分享率 | 持续授权过度率 |
|---|---|---:|---:|---:|---:|---:|
| Flat | baseline | 0.466544 | 0.432445 | 0.386593 | 0.313725 | 0.223519 |
| Flat | tuned | 0.469600 | 0.432140 | 0.381137 | 0.328431 | 0.224417 |
| Ordinal | baseline | 0.453407 | 0.403547 | 0.395507 | 0.343137 | 0.250000 |
| Ordinal | tuned | 0.522456 | 0.407493 | 0.379103 | 0.670343 | 0.115350 |
| Factored | baseline | 0.450351 | 0.408915 | 0.370662 | 0.329657 | 0.199282 |
| Factored | tuned | 0.490070 | 0.419119 | 0.375503 | 0.466912 | 0.239228 |

该切分的风险分母为过度分享 `816`、持续授权过度 `2,228`。由于训练/测试参与者完全重叠，且没有 cluster-bootstrap 文件，这些数值只作协议敏感性描述，不进入主推断。

## 9. 收敛与实现检查

- participant-held-out 的 `convergence_diagnostics.csv` 共 `192` 条记录，全部为 `converged=True`；未观察到静默优化失败。
- 外层训练的 baseline 与 tuned 模型也均收敛。
- 运行环境：Python `3.12.3`，NumPy `2.5.0`，pandas `3.0.3`，scikit-learn `1.9.0`，SciPy `1.18.0`。

## 10. 推断边界与未满足项

1. **无多 outer seeds**：只有一个 outer split seed `42`。因此不能报告跨运行 `mean ± SD`，也不能证明结论对参与者切分稳定。
2. **无 p 值**：本分析没有执行 t-test、Wilcoxon 或 permutation test，也没有 p 值。使用“区间跨/不跨 0”的描述，不使用“统计显著”措辞。
3. **无 simultaneous multiplicity control**：共查看 3 个模型 × 5 个指标的 15 个 marginal 95% CI；没有 Holm/Bonferroni/FDR 或 simultaneous bootstrap 校正。主指标预先锁定为 Macro-F1，其余为辅助/风险指标。
4. **bootstrap 条件性**：区间覆盖参与者抽样变异，但条件于固定外层切分、已选超参数和已训练模型；不覆盖训练随机性、超参数选择变异或数据处理变异。
5. **无跨模型 CI**：bootstrap 文件只比较同一架构的 tuned 与 baseline。不同 tuned 架构之间只允许点估计排名。
6. **类别与 cluster 数有限**：测试集只有 41 名参与者，类别支持不均衡；尾部风险和少数类区间可能较宽。
7. **row-stratified 非独立参与者评价**：同一 201 名参与者同时进入训练和测试，不能用于未见参与者泛化主张。

## 11. 下一轮统计检查

- 使用多个 participant-level outer split seeds 或重复 grouped nested CV，至少报告每个模型跨 outer run 的均值、SD、95% CI 与失败/收敛次数；
- 预先指定风险约束或效用函数，再进行阈值选择，避免仅凭 Macro-F1 排名；
- 对三种 tuned 模型进行参与者配对 cluster bootstrap 的两两差值比较；
- 为逐类 Recall、过度分享率及持续授权过度率补充 participant-level CI；
- 若同时保留多项正式主张，预先规定比较家族并使用 simultaneous interval 或适当的多重比较控制。
