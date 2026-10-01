# 四标签经典分类器：图目录与解释

本目录记录两张已经生成的科学图。两图均提供 PDF（矢量）与 PNG（预览）版本；PDF 用于后续排版，PNG 用于快速检查。主证据均来自固定 participant-held-out 测试集。

## Figure 01 — Participant-held-out 调参效应

- **文件**：
  - `figures/figure-01-heldout-tuning-deltas.pdf`
  - `figures/figure-01-heldout-tuning-deltas.png`
- **角色**：主比较图。
- **为什么存在**：回答“每种经典分类架构的调参是否改善主指标 Macro-F1，以及这种改善是否伴随过度分享风险变化”。
- **数据来源**：`participant_heldout/participant_bootstrap_deltas.csv`。
- **样本与单位**：固定测试集 `3,323` 行、`41` 名互不重叠的测试参与者；误差条由 `2,000` 次参与者配对聚类 bootstrap 得到。
- **绘图变量**：左面板为 Macro-F1 的 `tuned − baseline`；右面板为过度分享率的 `tuned − baseline`。两者均换算为百分点。
- **误差条**：点为观察差值，横线为 percentile 95% cluster-bootstrap CI；虚线为零差值。
- **方向规则**：左图正值较好；右图负值较好、正值较差。

### Caption 草案

**图 1｜固定 participant-held-out 测试集上的调参效应。** 点表示 tuned 相对同架构 baseline 的观察差值，横向误差条表示对 41 名测试参与者进行 2,000 次配对聚类 bootstrap 所得的 95% percentile CI；每次抽样保留被抽中参与者的全部行。左面板为 Macro-F1 差值，正值表示改善；右面板为过度分享率差值，负值表示改善。Flat 的 Macro-F1 为 `+0.375` 个百分点（95% CI `[-0.196, +0.958]`），过度分享率为 `-0.472` 个百分点（`[-1.358, +0.440]`）；Ordinal 分别为 `+1.148`（`[-0.361, +2.656]`）与 `+6.132`（`[+3.739, +9.046]`）；Factored 分别为 `+1.174`（`[-0.403, +2.764]`）与 `+10.613`（`[+7.838, +13.921]`）。

### 关键观察

1. 三种模型的 Macro-F1 差值区间均跨 0，调参对主指标的方向尚未被当前固定切分锁定。
2. Flat 的过度分享率点估计略降，但区间跨 0。
3. Ordinal 与 Factored 的过度分享率区间完全位于 0 以上，且增加幅度分别为 `6.132` 和 `10.613` 个百分点，表明调参把两者推向更激进的允许预测。

### 决策含义

- 图中没有证据支持“调参稳定提高 Macro-F1”。
- 对 Ordinal/Factored，按 Macro-F1 单目标选出的阈值不能直接作为权限策略默认值；下一轮应使用风险约束或 Pareto 选择。
- Flat tuned 可作为保守默认配置继续保留，但其收益需要多 outer splits 验证。

### 解释检查清单

- [x] 先检查区间是否跨 0，再看点估计大小；
- [x] 区分两个面板相反的好坏方向；
- [x] 只比较同一架构 tuned 与 baseline，不用此图做 tuned 架构间推断；
- [x] 不把“不跨 0 的 bootstrap CI”改写成未计算的 p 值结论；
- [x] 把风险变化与效用变化同时纳入决策。

### 局限

- 只有一个 outer split seed；CI 不包含外层切分和模型选择变异。
- 图仅展示 Macro-F1 与过度分享率；Accuracy、QWK 和持续授权过度率需结合统计附录阅读。
- 15 个指标—模型区间均为 marginal CI，未做 simultaneous 多重比较控制。
- bootstrap cluster 数仅为 41，尾部区间精度有限。

## Figure 02 — 固定测试集逐类 Recall

- **文件**：
  - `figures/figure-02-heldout-per-class-recall.pdf`
  - `figures/figure-02-heldout-per-class-recall.png`
- **角色**：支持图 / 错误结构分解图。
- **为什么存在**：说明调参后的总体分数变化来自哪些类别 Recall 的增减，避免只看总体 Accuracy 或 Macro-F1。
- **数据来源**：`participant_heldout/classification_report_*_baseline.json` 与 `classification_report_*_tuned.json`。
- **样本与单位**：固定 participant-held-out 测试集 `3,323` 行、`41` 名参与者；类别支持数为 Never `510`、No + ask `338`、Yes + ask `1,414`、Always `1,061`。
- **绘图变量**：每个模型面板内，灰色柱为 baseline Recall，模型色柱为 tuned Recall；纵轴为 Recall（`0–1`）。
- **不确定性表示**：本图没有误差条；只呈现固定测试集点估计。

### Caption 草案

**图 2｜固定 participant-held-out 测试集上的逐类 Recall。** 三个面板依次展示 Flat four-class、Cumulative Ordinal 与 Factored Logistic Regression；灰色为 baseline，彩色为 tuned。测试集共 `3,323` 行、`41` 名未见参与者，四类支持数分别为 `510`、`338`、`1,414` 与 `1,061`。Flat 调参后的四类 Recall 变化分别为 `+0.392`、`+1.183`、`0.000`、`+0.283` 个百分点；Ordinal 为 `-5.294`、`-0.888`、`+2.334`、`+6.221`；Factored 为 `-3.137`、`-7.101`、`+8.487`、`+1.979`。图中不含置信区间，柱高仅为该固定测试集的点估计。

### 精确绘图数据

| 模型 | 版本 | Never | No + ask | Yes + ask | Always |
|---|---|---:|---:|---:|---:|
| Flat | baseline | 0.313725 | 0.304734 | 0.439180 | 0.440151 |
| Flat | tuned | 0.317647 | 0.316568 | 0.439180 | 0.442978 |
| Ordinal | baseline | 0.464706 | 0.180473 | 0.369873 | 0.499529 |
| Ordinal | tuned | 0.411765 | 0.171598 | 0.393211 | 0.561734 |
| Factored | baseline | 0.294118 | 0.355030 | 0.483027 | 0.373233 |
| Factored | tuned | 0.262745 | 0.284024 | 0.567893 | 0.393025 |

### 关键观察

1. Flat 的逐类 Recall 基本不变，符合其总体调参效应很小的结果。
2. Ordinal tuned 降低两个拒绝类的 Recall，同时提高两个允许类的 Recall，尤其 Always 增加 `6.221` 个百分点；这与其过度分享率和持续授权过度率上升方向一致。
3. Factored tuned 的 Yes + ask Recall 增加 `8.487` 个百分点，但 No + ask Recall 降低 `7.101` 个百分点；该再分配解释了总体 Accuracy 上升与过度分享风险上升可以同时发生。
4. 最少类别 No + ask 只有 `338` 个样本，视觉上的变化需要带不确定性复核。

### 决策含义

- 不能仅凭 Factored 的最高 Accuracy/Macro-F1 点估计选择模型；它的收益部分来自向允许类重新分配预测。
- Ordinal 与 Factored 下一轮阈值调优应显式限制拒绝类 Recall 损失与两项过度授权风险。
- 若当前目标是建立稳定、可解释的经典基线，Flat 的较小类别重分配更适合作为默认对照。

### 解释检查清单

- [x] 在每个模型面板内比较 baseline 与 tuned；
- [x] 同时查看类别支持数，避免把不平衡类别等量解释；
- [x] 将拒绝类 Recall 下降与定向风险率一起阅读；
- [x] 不把 Recall 的变化解释为 precision、校准或总体安全性的充分证据；
- [x] 不作跨参与者或跨 seed 的稳定性主张。

### 局限

- 本图没有 CI 或误差条，不能判断逐类变化的参与者层不确定性。
- Recall 不显示误报方向与 precision；需要结合混淆矩阵和风险计数。
- 三个模型使用相同测试集，但图本身没有给出跨模型配对差值区间。
- 类别不均衡，柱形的视觉幅度不等于相同数量的错误变化。

## 图级总决策

Figure 01 决定“是否接受调参带来的总体效用—风险变化”；Figure 02 解释“这种变化由哪些类别的预测重分配构成”。两图共同支持保留 Flat tuned 作为保守默认经典基线，并把 Ordinal/Factored 转入带风险约束的下一轮阈值研究；它们不支持宣布跨模型普遍赢家。

