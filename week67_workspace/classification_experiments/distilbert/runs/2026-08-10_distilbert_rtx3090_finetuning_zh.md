# 2026-08-10｜DistilBERT RTX 3090 fine-tuning 运行记录

## 结论先行

DistilBERT 已在 RTX 3090 上完成端到端四分类 fine-tuning，并与同一个 participant-heldout 测试集上的 tuned Flat Logistic Regression 做了逐行配对比较。

- 首个按 train-only validation 选参的 GPU run 没有超过 LR。
- 在看到首个 test 结果后追加的 `max_epochs=5` follow-up，validation 在第 1 epoch 最好并于第 3 epoch early stop；最终只按 1 epoch 重训。
- Follow-up 的 Accuracy、Macro-F1、QWK 比首个 DistilBERT run 略高，但两项过度授权风险也更高。
- Follow-up 相对 tuned Flat LR 在五项主指标上仍是 `0/5` 占优，因此当前不应以 DistilBERT 替换 Flat LR。

第一轮是本任务较干净的初始语义 baseline；follow-up 因已经看过同一 test 的首轮结果，必须标为 **exploratory / test-touched**，不能当成新的无偏 final result。

## 1. 固定任务与数据协议

- 数据：16,361 行、201 名参与者、四个原始 permission labels。
- Outer split：`participant_heldout`，seed 42；13,038 行/160 人训练，3,323 行/41 人测试，参与者重叠为 0。
- Inner validation：只在 outer-train 内按参与者切分，seed `20260809`。
- 主选择指标：validation Macro-F1；test 不参与首个 run 的候选和 epoch 选择。
- 输入：将 query/tool/data type/domain/necessity 以及用户人口统计和隐私态度字段序列化为带字段名的英文文本。
- 模型：`distilbert-base-uncased` + 标准四分类 head；encoder 与 head 端到端更新。
- 标签：0=`No, never share`；1=`No, but ask me next time`；2=`Yes, but ask me next time`；3=`Yes, always share`。

数据 SHA-256：`4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`。

## 2. 首个 GPU run：预定的有限搜索

Run ID：`distilbert_rtx3090_run1`

| 参数 | 值 |
|---|---|
| Learning-rate candidates | `2e-5`, `5e-5` |
| Loss weighting | `balanced` |
| Maximum epochs | 2 |
| Train / eval batch | 32 / 64 |
| Max length | 128 |
| Weight decay / warmup | 0.01 / 0.1 |
| Seed | 42 |
| Device | RTX 3090, CUDA FP16, TF32 allowed |

Validation 选中 `lr=2e-5, epoch=2`，validation Macro-F1=`0.317720`。随后在完整 outer-train 上重新初始化并训练 2 epochs，运行总耗时约 110.5 秒。

## 3. Follow-up：最多 5 epochs + early stopping

Run ID：`distilbert_rtx3090_epoch5_codex_20260810`

固定 `lr=2e-5`、`balanced`，其余 batch/seed/数据/模型均保持不变；将 `max_epochs` 改为 5，`early_stopping_patience=2`。

| Epoch | Train loss | Validation loss | Validation Accuracy | Validation Macro-F1 | Validation QWK |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.343986 | 1.341854 | 0.393361 | **0.312958** | 0.302560 |
| 2 | 1.244978 | 1.354126 | 0.347959 | 0.303736 | 0.294696 |
| 3 | 1.175351 | 1.459749 | 0.331553 | 0.288766 | 0.274528 |

Epoch 2、3 的 train loss 继续下降，但 validation loss 上升且 Macro-F1 连续下降，因此在 patience=2 时 early stop。最终选中 epoch 1，在完整 outer-train 上重新初始化并训练 1 epoch；总耗时约 78.8 秒。

注意：这不是从首个 run 的 epoch 2 checkpoint “继续训练”。Runner 每个 run 都重新初始化模型，而且 linear scheduler 的总步数取决于 `max_epochs`；因此把 2 改成 5 也改变了前几个 epoch 的学习率轨迹，两个 run 的 epoch 1 不应被视为完全相同的训练状态。

## 4. Frozen-test / fixed-test 结果

| 模型/运行 | Accuracy ↑ | Macro-F1 ↑ | QWK ↑ | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Tuned Flat LR | **0.409269** | **0.370655** | **0.315495** | **0.425708** | **0.210433** |
| DistilBERT 首个 run | 0.368643 | 0.327932 | 0.238761 | 0.505896 | 0.395225 |
| DistilBERT 5-epoch follow-up（实际选 epoch 1） | 0.388203 | 0.335093 | 0.252939 | 0.545991 | 0.438550 |

Follow-up 相对首个 DistilBERT run 的配对变化如下。区间来自相同 41 名参与者上的 5,000 次 participant-paired cluster bootstrap，差值为 `follow-up - initial run`：

| 指标 | 差值（百分点） | 95% percentile CI（百分点） | 解读 |
|---|---:|---:|---|
| Accuracy | +1.956 | [-0.298, +4.351] | 小幅点提升，CI 跨 0 |
| Macro-F1 | +0.716 | [-1.023, +2.586] | 小幅点提升，CI 跨 0 |
| QWK | +1.418 | [-1.526, +5.073] | 小幅点提升，CI 跨 0 |
| Over-sharing | +4.009 | [+2.337, +6.003] | 越低越好；follow-up 更差，CI 不跨 0 |
| Persistent-over-allow | +4.332 | [+1.903, +6.799] | 越低越好；follow-up 更差，CI 不跨 0 |

因此，增加最大 epoch 后只得到不确定的小幅效能点估计改善，却伴随在这些测试参与者上方向一致的更高风险率，不是全面提升。该 bootstrap 仍不覆盖重新训练 seed 的变化。

## 5. Follow-up 与 tuned Flat LR 的严格配对比较

差值定义为 `DistilBERT follow-up - tuned Flat LR`。对 41 名测试参与者进行了 5,000 次 paired participant cluster bootstrap；每次把被抽中的参与者全部行合并后重算 row-pooled metric。

| 指标 | 差值（百分点） | 95% percentile CI（百分点） | 方向 |
|---|---:|---:|---|
| Accuracy | -2.11 | [-7.06, +2.49] | 点估计偏向 LR，区间跨 0 |
| Macro-F1 | -3.56 | [-7.30, +0.24] | 点估计偏向 LR，区间跨 0 |
| QWK | -6.26 | [-14.84, +2.20] | 点估计偏向 LR，区间跨 0 |
| Over-sharing | +12.03 | [+1.85, +23.42] | 越低越好；区间不跨 0，偏向 LR |
| Persistent-over-allow | +22.81 | [+13.84, +31.61] | 越低越好；区间不跨 0，偏向 LR |

这些区间只重采样测试参与者，不包含重新训练的 seed 波动。Follow-up 还是 test-touched，因此允许的结论是：**在这个固定 seed 和既定测试参与者上，当前 DistilBERT baseline 未显示出相对 tuned Flat LR 的提升，而且两项安全风险率明显更高。** 不能据此声称所有 BERT 或语义模型都比 LR 差。

## 6. 各类别诊断（follow-up）

| Label | Support | Precision | Recall | F1 | 相对 LR 的 F1 差值 |
|---|---:|---:|---:|---:|---:|
| 0 — No, never share | 510 | 0.328 | 0.445 | 0.378 | +3.88 pp |
| 1 — No, but ask me next time | 338 | 0.170 | 0.112 | 0.135 | -6.57 pp |
| 2 — Yes, but ask me next time | 1,414 | 0.498 | 0.274 | 0.353 | -12.11 pp |
| 3 — Yes, always share | 1,061 | 0.391 | 0.601 | 0.474 | +0.58 pp |

主要 Macro-F1 缺口来自两个 “ask me next time” 中间类别，尤其 label 2；当前模型更倾向预测 `always share`，这也解释了较高的 persistent-over-allow。

## 7. 决定与下一步

- 本轮预设的“值得继续”门槛未达到，当前默认 classic baseline 仍是 tuned Flat LR。
- 不建议继续只增加 epoch；validation 已呈现过拟合，且 early stopping 已选回 epoch 1。
- 作为初始语义对照，DistilBERT Flat 的负结果已经足够完整，应保留而非删除。
- 若以后仍想研究语义表示，优先做一个能隔离原因的低成本实验，例如 frozen DistilBERT/Sentence-BERT embedding + LR，或专门针对中间类别的 ordinal/factored semantic head；它们应使用新的 validation 设计，不再依据当前 test 反复选参。

## 8. 产物索引

- [首个 GPU run 机器产物](../artifacts/distilbert_rtx3090_run1/)
- [5-epoch follow-up 机器产物](../artifacts/distilbert_rtx3090_epoch5_codex_20260810/)
- [严格分析报告](../analysis/distilbert_epoch5_codex_20260810/analysis-report.md)
- [统计附录](../analysis/distilbert_epoch5_codex_20260810/stats-appendix.md)
- [图表目录](../analysis/distilbert_epoch5_codex_20260810/figure-catalog.md)
- [DistilBERT 模型设计与实现总览](../design/004_distilbert_four_class_finetuning_zh.md)

服务器保留两个 run 的 `final_model/` 权重；本地回收包为审计所需的全部配置、预测、指标、报告、曲线和 source snapshot，不含约 259 MB 的最终模型权重。

下载归档已逐字节校验：首个 run 的 tar.gz SHA-256 为 `ac1c48b09d20c81802615d64d0498f8239f5f5859d757d27f9073a0686b4f6a5`；follow-up 为 `4262a9019f5409cc7a32932ccf79a61eb1ee22b04e04b16bbb276a467e2ccea8`。两次服务器 stdout 日志也已保存为各自 artifact 目录中的 `server_stdout.log`。
