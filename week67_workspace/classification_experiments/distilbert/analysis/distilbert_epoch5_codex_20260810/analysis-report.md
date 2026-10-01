# DistilBERT 与经典 Logistic Regression 对照结果

## 结论先行

在固定的 participant-held-out 测试集上，DistilBERT 与 tuned Flat four-class Logistic Regression 已逐行配对比较。点估计上，DistilBERT 在 0/5 项指标的期望方向上优于 LR；其中 0/5 项的 participant-level bootstrap 95% 区间不跨 0 且方向有利于 DistilBERT。

> **Protocol warning：** 该 DistilBERT follow-up 是在首个 run 的同一 test 结果已被查看后提出的 exploratory/test-touched 运行。以下统计摘要在数值上可复核，但不得当作全新未接触 test 上的 confirmatory result。


这里的区间只反映 **41 位测试参与者的抽样不确定性**，不包含重新训练 DistilBERT 的随机种子不确定性。因此，本报告用于初始语义基线对照，不把“区间不跨 0”扩写成跨训练运行的稳定性结论。

## 总体指标

差值统一定义为 `DistilBERT - tuned Flat LR`。Accuracy、Macro-F1、Kappa 越高越好；两项风险率越低越好。

| 指标 | DistilBERT | Tuned Flat LR | 差值（百分点） | 95% percentile CI（百分点） | 解读 |
|---|---:|---:|---:|---:|---|
| 准确率 | 0.3882 | 0.4093 | -2.11 | [-7.06, +2.49] | 95% 区间跨 0 |
| 宏平均 F1 | 0.3351 | 0.3707 | -3.56 | [-7.30, +0.24] | 95% 区间跨 0 |
| 二次加权 Kappa | 0.2529 | 0.3155 | -6.26 | [-14.84, +2.20] | 95% 区间跨 0 |
| 过度分享率 | 0.5460 | 0.4257 | +12.03 | [+1.85, +23.42] | 95% 区间不跨 0，方向有利于 LR |
| 持续授权过度率 | 0.4385 | 0.2104 | +22.81 | [+13.84, +31.61] | 95% 区间不跨 0，方向有利于 LR |

## 各类别表现

| 类别 | Support | DistilBERT P / R / F1 | Tuned Flat LR P / R / F1 | F1 差值（百分点） |
|---|---:|---:|---:|---:|
| 0: No, never share | 510 | 0.328 / 0.445 / 0.378 | 0.363 / 0.318 / 0.339 | +3.88 |
| 1: No, but ask me next time | 338 | 0.170 / 0.112 / 0.135 | 0.147 / 0.317 / 0.201 | -6.57 |
| 2: Yes, but ask me next time | 1414 | 0.498 / 0.274 / 0.353 | 0.516 / 0.439 / 0.474 | -12.11 |
| 3: Yes, always share | 1061 | 0.391 / 0.601 / 0.474 | 0.497 / 0.443 / 0.468 | +0.58 |

## 比较协议

- 测试行数：3,323；参与者数：41。
- 对齐方式：complete shared metadata (LR artifact has no _row_id)。
- 配对 cluster bootstrap：以 participant 为抽样单元，有放回抽取 41 个参与者；每次同时重算两个模型，差值取同一 replicate 内的 `DistilBERT - LR`。
- 每次抽中的 participant 带入其全部行，并在合并后的行上重算指标；因此 estimand 是 **row-pooled metric**，测试行较多的 participant 对点估计和 bootstrap replicate 的影响更大，并非 participant-equal average。
- Bootstrap 次数：5,000；随机种子：20260810；区间：delta replicate 的 2.5% 与 97.5% percentile。
- 所有表中数值都由 `test_predictions.csv` 重新计算，并与两个 run 的 `test_metrics.csv` 交叉核验。

## 建议如何使用

这次结果回答的是“加入文本语义后的初始 DistilBERT baseline 是否在同一测试参与者上优于硬编码 LR”。若后续需要论文级结论，应至少增加多个训练随机种子，并预先固定模型选择规则；当前 participant bootstrap 不能替代该步骤。

## Claim Candidates

- Claim：本次固定训练 seed 的 DistilBERT 与 tuned Flat LR 存在如下 Macro-F1 差异。
  - Source evidence：Macro-F1 为 0.3351 vs. 0.3707，差值 -3.56 个百分点，participant-bootstrap 95% CI [-7.30, +0.24]。
  - Allowed wording：在这一个固定训练 seed、同一 frozen participant-held-out 测试集上，按上述差值和区间如实说明点估计方向及测试参与者抽样不确定性。
  - Forbidden stronger wording：所有 BERT/语义模型都比 LR 差；或该差异已经跨训练 seed 显著。
  - Uncertainty：只有一个训练 seed；bootstrap 只覆盖 41 位测试参与者的抽样变化。
  - Next check：若继续投入，预先锁定配置后运行多个训练 seed；否则保留 LR 为当前默认基线。
  - Decision：keep（作为 pilot 结论），weaken（不得上升为模型家族结论）。

- Claim：本次 DistilBERT 与 tuned Flat LR 的两项安全风险率存在如下差异。
  - Source evidence：Over-sharing 差值 +12.03 个百分点，95% CI [+1.85, +23.42]；Persistent-over-allow 差值 +22.81 个百分点，95% CI [+13.84, +31.61]。
  - Allowed wording：差值定义为 `DistilBERT - LR` 且风险率越低越好；只按上述符号与 CI 是否跨 0 说明固定模型间的方向。
  - Forbidden stronger wording：DistilBERT 本质上不安全；或该结果可直接外推到其他数据、编码器与训练策略。
  - Uncertainty：未覆盖训练 seed、不含多模型/多超参家族校正；本 run 已在同一 test 的更早结果被查看后提出，属于 test-touched exploratory follow-up。
  - Next check：若风险点估计恶化，下一版先在 validation 上约束风险指标；任何方向都应在新的未接触测试协议上评估。
  - Decision：keep（作为效能之外的独立 guardrail）。

- Claim：四个类别的 F1 差值并不均匀，其中最低差值出现在 label 2（Yes, but ask me next time）。
  - Source evidence：label 0 +3.88 pp；label 1 -6.57 pp；label 2 -12.11 pp；label 3 +0.58 pp；差值均为 `DistilBERT - LR`。
  - Allowed wording：这是固定测试集上的误差诊断；只描述实际最低差值类别及四类点估计模式。
  - Forbidden stronger wording：语义模型无法学习某类，或未做类别级区间/校正时宣称该模式具有统计显著性。
  - Uncertainty：per-class 差值未单独做多重校正的区间估计。
  - Next check：检查 label 2 的混淆矩阵与输入表达，再决定是否需要 class-aware、ordinal 或 factored head。
  - Decision：keep（作为下一步诊断方向）。
