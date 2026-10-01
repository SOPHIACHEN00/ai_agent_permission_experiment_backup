# 004｜DistilBERT 四分类语义模型（设计、实现与运行记录）

> **当前状态（2026-08-10）：RTX 3090 上的首个正式 run 与 max-5-epoch follow-up 均已完成。** 首个 run 是 train-only validation 选参后的初始结果；follow-up 是看过首轮 test 后的 exploratory/test-touched 运行。两者都没有超过 tuned Flat LR，当前保留为负面的语义 baseline，不替换 LR。完整运行记录见 [`runs/2026-08-10_distilbert_rtx3090_finetuning_zh.md`](../runs/2026-08-10_distilbert_rtx3090_finetuning_zh.md)。

## 一句话目标

保持现有四标签任务、输入信息和 participant-held-out 测试集不变，将 TF-IDF / one-hot 表示替换为可端到端微调的 DistilBERT 文本表示，快速检查预训练语义是否能让四分类结果优于当前 Flat Logistic Regression。

本轮只回答一个简单问题：

> **在同一批新参与者测试数据上，DistilBERT 四分类 fine-tuning 是否比当前 Flat LR 更好？**

本轮是初始对照试验，不以证明“真正理解隐私语义”、新 query 泛化或发表级统计结论为目标。

## 1. 为什么第一轮只做 Flat 四分类

DistilBERT 第一轮直接预测四个互斥类别，与现有 Flat LR 的任务定义完全对应：

\[
\hat y=\arg\max_{c\in\{0,1,2,3\}}P(y=c\mid x).
\]

这样只改变文本表示和模型容量，不同时改变标签结构，比较最容易解释：

- Flat LR：TF-IDF、one-hot、数值字段 → multinomial Logistic Regression。
- DistilBERT Flat：所有输入字段序列化为自然语言 → DistilBERT → 四分类头。

现有 Ordinal LR 和 Factored LR 的冻结结果可以保留为补充参考，不需要为了本轮重新运行。只有 DistilBERT Flat 出现值得继续验证的收益时，才考虑 DistilBERT Factored 或 Ordinal 输出头。

## 2. DistilBERT 与 Logistic Regression 的关系

标准 DistilBERT fine-tuning 已经包含一个可训练的线性分类头：

```text
自然语言输入 → DistilBERT encoder → pre-classifier → ReLU/dropout → Linear(768, 4) → softmax
```

因此，本轮**不在 DistilBERT 后再接 sklearn `LogisticRegression`**。分类头虽然也是对隐藏表示做线性映射，但它与 encoder 一起端到端更新，不是独立训练的传统 LR。

“冻结 DistilBERT embedding + sklearn LR”是另一个可选消融实验，用于区分预训练表示与端到端微调的贡献；它不是本轮回答核心问题所必需的模型。

## 3. 数据与四个 labels

计划继续使用：

- 数据文件：`ai_agent_permission_experiment/data/processed/four_label_dataset.csv`
- 样本：16,361 行
- 有效参与者：201 人
- Query：65 个

标签仍然是问卷中的四种原始回答：

| Label | 原始回答 | 解释 |
|---:|---|---|
| 0 | `No, never share` | 本次拒绝，并保持拒绝 |
| 1 | `No, but ask me next time` | 本次拒绝，下次重新询问 |
| 2 | `Yes, but ask me next time` | 本次允许，下次重新询问 |
| 3 | `Yes, always share` | 本次允许，并保持允许 |

本轮不删除中间标签 1、2，也不把任务缩减为二分类。

## 4. Outer split 与 inner validation

### 4.1 固定 outer split

主实验复用现有 `participant_heldout` 外层切分：

| 集合 | 参与者数 | 行数 | 用途 |
|---|---:|---:|---|
| Outer train | 160 | 13,038 | 训练及内部选参 |
| Frozen test | 41 | 3,323 | 参数冻结后只评估一次 |

Train 与 test 的参与者重叠为 0。必须复用现有参与者名单，而不是重新随机切分，确保 DistilBERT 与当前 LR 的测试分数可直接对照。

### 4.2 Outer-train 内部 validation

仅在 160 名 outer-train 参与者内创建 participant-grouped validation：

- 约 80% 参与者用于 fine-tuning train（约 128 人）。
- 约 20% 参与者用于 validation（约 32 人）。
- 同一参与者的所有行只能出现在一侧。
- 固定划分随机种子：`20260809`。
- validation 用于选择超参数和最佳 epoch；frozen test 不参与任何选择。

确定配置与最佳 epoch 后，重新初始化模型，并用全部 160 名 outer-train 参与者训练相同 epoch 数；最后只在 41 名 frozen-test 参与者上评估一次。

## 5. 输入字段与自然语言模板

第一轮目标是让 DistilBERT 与现有 LR 获得尽量相同的信息。以下字段全部序列化为英文自然语言：

### 5.1 请求与场景字段

- `query`
- `tool`
- `raw_data_type`
- `generic_data_type`
- `domain`
- `necessity_status`

### 5.2 用户字段

- `age`
- `gender`
- `education`
- `ai_familiarity`
- `ai_frequency`
- `ai_trust`
- `privacy_importance`
- `concern_domain`

### 5.3 预定模板

```text
User request: {query}
Agent tool: {tool}
Requested data: {raw_data_type}
Generic data category: {generic_data_type}
Application domain: {domain}
Data necessity: {necessity_status}

User profile:
Age: {age}
Gender: {gender}
Education: {education}
AI familiarity: {ai_familiarity}
AI usage frequency: {ai_frequency}
AI trust: {ai_trust}
Privacy importance: {privacy_importance}
Privacy concern domains: {concern_domain}
```

字段名和分隔顺序保持固定。实际 serializer 将 `age=1..5` 映射为问卷年龄段，将四个 Likert 字段写成“`<dimension> rating <n> out of 5`”，并把 `concern_domain` 的 `|` 改为逗号。缺失值统一写为 `unspecified`，不根据 label 人工补写“敏感”“安全”等评价词，避免把目标判断直接写入输入。

### 5.4 明确排除的字段

- `participant_id`：只用于 grouped split 和结果按参与者汇总。
- `query_id`：只用于追踪和审计，不作为模型输入。
- `label_id`、`label_text` 以及原始 permission answer：均为预测目标。
- `Valid` 等数据清洗标志：不作为模型特征。

第一轮保留 `necessity_status`，因为当前 LR 也使用它，便于快速公平对照。但它可能属于部署阶段不可得的 privileged/oracle metadata；若 DistilBERT 有提升，后续应补做去掉该字段的消融。

## 6. 模型与实际训练参数

初始配置固定为：

| 参数 | 预定值 |
|---|---|
| Backbone | `distilbert-base-uncased` |
| 分类头 | Hugging Face `DistilBertForSequenceClassification` 的标准四分类 head |
| Tokenizer | 对应 DistilBERT tokenizer |
| Max sequence length | 128 |
| Optimizer | AdamW |
| Learning rate | validation 候选：`2e-5`, `5e-5` |
| Train / eval batch size | 32 / 64 |
| Maximum epochs | 每个候选 2 |
| Early stopping | patience = 2 |
| Weight decay | `0.01` |
| Warmup ratio | `0.1` |
| Gradient clipping | `1.0` |
| Loss | training split 频率计算的 class-weighted cross-entropy |
| 最佳 epoch 指标 | validation Macro-F1 |
| Random seed | 42 |
| Mixed precision | RTX 3090 使用 FP16 AMP；`GradScaler` + autocast |

类别权重只能从当前训练部分计算，不能使用 validation 或 frozen test 的标签分布。

## 7. 有限调参计划

本轮不做大规模搜索。为了保持与 CPU 预注册设计一致，并避免换 GPU 后扩大搜索空间，仍只比较两个 learning rate：

| 参数 | 候选值 |
|---|---|
| AdamW learning rate | `2e-5`, `5e-5` |
| Loss weighting | 固定 `balanced` |

其余参数保持固定，因此共 2 个 validation 配置。每个配置使用相同的 grouped train/validation 划分和 seed 42，以 validation Macro-F1 作为主要选择指标；并列时依次使用：

1. 较高 QWK；
2. 较低 over-sharing rate；
3. 较低 persistent-over-allow rate；
4. 较高 Accuracy；
5. 若以上完全相同，则保留先运行的较低 learning rate。

本轮不搜索 backbone、max length、复杂 scheduler 或分类头结构。若最佳结果相对 Flat LR 的 Macro-F1 提升超过 1 个百分点，再补跑 seed 43 和 44；否则保留 seed 42 的探索性结果并停止扩展。

## 8. 指标与对照基线

测试指标与 LR 保持一致：

- Accuracy ↑
- Macro-F1 ↑（主要比较指标）
- Quadratic Weighted Kappa（QWK）↑
- Over-sharing rate ↓
- Persistent-over-allow rate ↓
- 四类 precision / recall / F1
- Confusion matrix

当前主要对照是已经冻结的 Flat LR tuned 结果：

| 模型 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Flat LR tuned | 0.409269 | 0.370655 | 0.315495 | 0.425708 | 0.210433 |
| DistilBERT Flat（首个 GPU run） | 0.368643 | 0.327932 | 0.238761 | 0.505896 | 0.395225 |
| DistilBERT Flat（max-5 follow-up，实际选 epoch 1） | 0.388203 | 0.335093 | 0.252939 | 0.545991 | 0.438550 |

Ordinal LR 与 Factored LR 只作为补充参照，不作为本轮架构完全对应的主要基线。

## 9. Quick baseline 的成功判据

这是探索性试验，采用简单、预先写明的判断：

- **值得继续**：DistilBERT 的 frozen-test Macro-F1 至少比 Flat LR 高 `0.01`，同时 QWK 不明显下降，且 over-sharing 不增加超过 `0.01`。
- **差异很小**：Macro-F1 相对 Flat LR 的绝对差在 `±0.01` 内；暂不继续增加更复杂输出头。
- **性能—安全冲突**：Macro-F1 提高，但 over-sharing 或 persistent-over-allow 明显恶化；只能记录为分类性能提高，不能称为全面更好。
- **负面结果**：Macro-F1 低于 Flat LR，且没有带来风险指标改善；保留结果作为语义模型负基线。

以上 `0.01` 是本轮决定是否继续投入的实用阈值，不是统计显著性边界。

## 10. 为什么暂不同时运行 DistilBERT Ordinal / Factored

同时更换 encoder 和标签分解方式，会无法判断收益来自语义表示还是输出结构，而且会把第一轮的训练量扩大数倍。因此预定顺序是：

```text
DistilBERT + Flat 4-class head
        ├─ 无明显提升 → 记录结果并停止扩展
        └─ 有明显提升
             ├─ 优先尝试 DistilBERT Factored heads
             └─ 最后再考虑 DistilBERT Ordinal heads
```

若进入第二阶段，Factored 优先于 Ordinal，因为它能进一步区分语义表示改善的是 access 决策还是“下次是否再问”的策略；现有 Ordinal 实现还存在三个独立阈值输出不保证单调的问题。

## 11. 风险与解释限制

- 当前 participant-heldout 测试的是新参与者，但测试中的 query/context 在训练集中出现过；分数提升不等于新场景语义泛化。
- 虽有 16,361 行，但只有 65 个 query，且大量参与者回答相同场景；DistilBERT 可能学习场景平均偏好。
- 同一场景本身存在不同参与者给出不同标签的情况，纯场景语义不可能解释全部个体差异。
- 将数值和类别资料写成文本并不保证 DistilBERT 能像结构化模型一样有效利用其尺度与顺序。
- `necessity_status` 可能是 oracle 特征；本轮保留仅是为了与当前 LR 对齐。
- 四类分布不均衡，结果可能受 loss weighting 和少数类 recall 明显影响。
- 单个随机种子只能作为探索性结果；即使分数提高，也不能直接宣称稳定提升。
- 英文 tokenizer 与模板措辞、截断长度可能影响结果；需要保存实际 token 长度和截断比例。
- 若无 GPU，fine-tuning 可能较慢；这影响运行成本，但不改变实验定义。
- 安全指标与 Macro-F1 可能冲突，不能只依据 Accuracy 或 Macro-F1 判断权限模型“更好”。

## 12. 预期代码与机器可读产物

已实现代码入口：

```text
ai_agent_permission_experiment/src/run_distilbert_four_label.py
```

GPU server 上传包与正式 run 目录：

```text
classification_experiments/distilbert/server_packages/distilbert_rtx3090_20260809/
server_package/outputs/<unique_run_id>/
```

每次正式运行至少保存：

- `run_config.json`：模型、数据、split、seed、包版本和全部参数。
- `split_manifest.json`：outer train/test 与 inner train/validation 参与者名单；调参完成前不写 test label counts。
- `candidate_results.csv`：每个候选配置及最佳 epoch。
- `training_history.csv`：每个 epoch 的 train loss 和 validation 指标。
- `test_metrics.csv`：冻结测试集总指标。
- `classification_report_distilbert_flat_tuned.json`：逐类 precision、recall、F1 和 support。
- `confusion_matrix_distilbert_flat_tuned.csv`：四分类混淆矩阵。
- `test_predictions.csv`：`_row_id`、metadata、真实标签、预测标签和四类概率。
- `serialization_manifest.json`：输入字段、模板、token 长度与截断比例。
- `environment.json`：Python、PyTorch、Transformers、CUDA/GPU 信息。
- `source/run_distilbert_four_label.py`：本次实际运行的源码快照。
- `final_model/`：最终重训后的 tokenizer 与模型权重。

## 13. RTX 3090 实际运行结果

### 13.1 运行元数据

两个完成 run 共用：

- 数据 SHA-256：`4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`
- 代码/source snapshot SHA-256：`69a58db1d2801b31dc7835797657bb1392d2d02090149ab3534ecbe60b3ce174`
- Python `3.10.16`；PyTorch `2.4.0+cu121`；Transformers `5.5.0`；Tokenizers `0.22.2`
- GPU：NVIDIA GeForce RTX 3090，24 GB；CUDA `12.1`；FP16 AMP；TF32 allowed
- Outer seed `42`；inner validation seed `20260809`

| Run | 搜索/上限 | 选中配置 | 完成耗时 | 证据状态 |
|---|---|---|---:|---|
| `distilbert_rtx3090_run1` | `lr={2e-5,5e-5}`，最多 2 epochs | `2e-5`, balanced, epoch 2 | 110.5 s | 首个 train-only validation 结果 |
| `distilbert_rtx3090_epoch5_codex_20260810` | 固定 `2e-5`，最多 5 epochs，patience 2 | balanced, epoch 1；第 3 epoch early stop | 78.8 s | 看过首轮 test 后的 exploratory/test-touched follow-up |

Follow-up 的 validation Macro-F1 从 epoch 1 的 `0.312958` 降到 epoch 2 的 `0.303736` 和 epoch 3 的 `0.288766`；train loss 同期持续下降，呈现明确的 validation 过拟合。由于 scheduler 总步数随 `max_epochs` 改变，follow-up 不是简单从首个 run checkpoint 继续训练。

### 13.2 测试结果

| 模型 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Flat LR tuned | **0.409269** | **0.370655** | **0.315495** | **0.425708** | **0.210433** |
| DistilBERT 首个 run | 0.368643 | 0.327932 | 0.238761 | 0.505896 | 0.395225 |
| DistilBERT follow-up | 0.388203 | 0.335093 | 0.252939 | 0.545991 | 0.438550 |

Follow-up 逐类结果：

| Label | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| 0 — No, never share | 510 | 0.328 | 0.445 | 0.378 |
| 1 — No, but ask me next time | 338 | 0.170 | 0.112 | 0.135 |
| 2 — Yes, but ask me next time | 1,414 | 0.498 | 0.274 | 0.353 |
| 3 — Yes, always share | 1,061 | 0.391 | 0.601 | 0.474 |

### 13.3 统计比较与决定

Follow-up 相对 tuned Flat LR：Macro-F1 `-3.56` 个百分点，participant-paired bootstrap 95% CI `[-7.30,+0.24]`；Over-sharing `+12.03` 个百分点，CI `[+1.85,+23.42]`；Persistent-over-allow `+22.81` 个百分点，CI `[+13.84,+31.61]`。区间来自 5,000 次、以 41 名测试参与者为 cluster 的配对 bootstrap，不包含训练 seed 不确定性。

- 未达到“Macro-F1 至少提高 1 个百分点且风险不恶化”的继续门槛。
- 增加最大 epoch 并未产生更好的 validation epoch；early stopping 最终选择 epoch 1。
- 当前 tuned Flat LR 仍是主要经典分类 baseline。
- 不继续盲目增加 epochs，也不因本次负结果宣称所有语义模型均无效。

完整细节与产物：

- [`2026-08-10_distilbert_rtx3090_finetuning_zh.md`](../runs/2026-08-10_distilbert_rtx3090_finetuning_zh.md)
- [`analysis-report.md`](../analysis/distilbert_epoch5_codex_20260810/analysis-report.md)
- [`distilbert_rtx3090_run1/`](../artifacts/distilbert_rtx3090_run1/)
- [`distilbert_rtx3090_epoch5_codex_20260810/`](../artifacts/distilbert_rtx3090_epoch5_codex_20260810/)
