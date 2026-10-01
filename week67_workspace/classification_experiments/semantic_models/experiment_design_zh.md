# 非 DistilBERT 语义 NLP 四分类实验设计

> 状态（2026-08-10）：三个 RTX 3090 正式 run 与严格分析均已完成。本文保留预先设计；实际结果见[本轮正式报告](reports/2026-08-10--semantic-classification--r01--round-review.md)。

## 1. 实验目的

本轮不再继续增加 DistilBERT epoch，而是更换预训练语言模型 backbone，观察更强或更新的语义编码器能否改善四分类权限预测。核心问题是：在输入信息、参与者划分、标签和指标保持一致时，RoBERTa、DeBERTa 和 ModernBERT 是否能超过当前 Logistic Regression 与 DistilBERT 对照。

这是初始语义模型对照实验，不以证明“模型真正理解隐私语义”为目标。当前 participant-heldout 测试仍是“新参与者、已见场景”；它不能检验新 query、新 data type 或新 domain 的语义外推。

## 2. 固定数据、标签与输入

- 数据：`four_label_dataset.csv`
- SHA-256：`4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`
- 行数：16,361；参与者：201
- 四个标签：
  - `0`：No, never share
  - `1`：No, but ask me next time
  - `2`：Yes, but ask me next time
  - `3`：Yes, always share

每一行转换为英文自然语言 prompt，包含：

- query、tool、raw data type、generic data category、application domain；
- necessity status；
- age group、gender、education；
- AI familiarity、usage frequency、trust、privacy importance；
- privacy concern domains。

因此这些模型是“同一组已有字段的语义编码器”，不是完全自动发现 feature。相比 LR 的 TF-IDF + One-Hot + numeric 管道，字段选择仍由实验者固定，但词和句子的表示来自预训练语言模型。`necessity_status` 仍可能属于部署时不可获得的 privileged/oracle feature；本轮为保持对照一致而保留。

## 3. 固定评估协议

| 数据部分 | 行数 | 参与者 | 用途 |
|---|---:|---:|---|
| outer train | 13,038 | 160 | 调参与最终重训 |
| inner train | 10,417 | 128 | 候选训练 |
| inner validation | 2,621 | 32 | 选择 LR、loss weighting 和 epoch |
| frozen outer test | 3,323 | 41 | 每个选定模型最终评估一次 |

- Outer participant split seed：`42`
- Inner participant split seed：`20260809`
- 两层 split 的 participant overlap 都必须为 `0`
- frozen test 不参与候选、学习率、loss weighting 或 epoch 选择
- training/DataLoader seed：`42`

## 4. 三个首轮模型

| 实验 key | Hugging Face 模型 | 固定 revision | 选择理由 |
|---|---|---|---|
| `roberta_base` | `FacebookAI/roberta-base` | `e2da8e2f811d1448a5b465c236feacd80ffbac7b` | 经典强 MLM encoder；是 DistilBERT 的直接非蒸馏升级对照 |
| `deberta_v3_small` | `microsoft/deberta-v3-small` | `a36c739020e01763fe789b4b85e2df55d6180012` | disentangled attention + ELECTRA-style 预训练；优先观察其短文本 NLU 表现 |
| `modernbert_base` | `answerdotai/ModernBERT-base` | `8949b909ec900327062f0ebf497f51aef5e6f0c8` | 较新的 encoder 架构；检验现代预训练与结构是否带来增益 |

本轮不包括生成式 LLM、API embedding、prompt-only zero-shot 或多任务学习，避免一次引入太多变化。

## 5. Train-only 调参矩阵

| 模型 | Learning rates | Loss weighting | 默认 train/eval batch |
|---|---|---|---:|
| RoBERTa-base | `1e-5, 2e-5, 3e-5` | `balanced, none` | `32/64` |
| DeBERTa-v3-small | `1.5e-5, 3e-5, 4.5e-5` | `balanced, none` | `32/64` |
| ModernBERT-base | `1e-5, 2e-5, 3e-5` | `balanced, none` | `32/64` |

每个模型共有 `3 × 2 = 6` 个候选。每个候选最多训练 3 epochs，early-stopping patience 为 2。选择顺序固定为：

1. validation Macro-F1 较高；
2. validation QWK 较高；
3. validation Over-sharing 较低；
4. validation Persistent-over-allow 较低；
5. validation Accuracy 较高。

选中的 learning rate、loss weighting 和 best epoch 随后在完整 outer train 上从预训练 checkpoint 重新初始化并重训，最后才物化与评估 frozen test。

## 6. 其他固定训练参数

- Flat four-class sequence-classification head
- max length：128
- AdamW weight decay：0.01
- linear warmup/decay；warmup ratio：0.1
- max gradient norm：1.0
- FP16 mixed precision；RTX 3090 上允许 TF32
- 单模型单 GPU；不做 DataParallel/DDP
- tokenizer 与 model 都按 40 位 commit 锁定
- 正式训练只从已校验的本地 Hugging Face cache 加载
- 默认保存最终模型；回传分析包时可排除权重

DeBERTa-v3-small 的官方权重是 PyTorch `.bin`。按当前 Transformers 安全检查，需要 `torch>=2.6`；服务器包会新建隔离 `.venv` 并安装 CUDA PyTorch 2.6，不修改服务器 base 环境，也不绕过安全门。

## 7. 指标与当前参照线

五项指标完全沿用经典模型和 DistilBERT 实验：

- Accuracy ↑
- Macro-F1 ↑，主指标
- Quadratic Weighted Kappa（QWK）↑
- Over-sharing rate ↓
- Persistent-over-allow rate ↓

当前 frozen participant-heldout 参照：

| 模型 | Accuracy ↑ | Macro-F1 ↑ | QWK ↑ | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| tuned Flat LR | 0.409269 | 0.370655 | 0.315495 | 0.425708 | 0.210433 |
| DistilBERT follow-up | 0.388203 | 0.335093 | 0.252939 | 0.545991 | 0.438550 |

初步判断规则：

- 若 Macro-F1 高于 tuned Flat LR，且两个风险率都没有明显恶化，则值得补多 seed；
- 若 Macro-F1 提高但风险恶化，只能称为 performance–safety trade-off；
- 若五项都不优于 tuned Flat LR，则保留为负面语义 baseline，不继续扩大调参；
- 单个 seed 的点估计不能表述为统计稳健优势。回收 predictions 后，再按 41 名 participant 做 paired cluster bootstrap。

## 8. 服务器执行与失败隔离

本地上传包位于：

`classification_experiments/semantic_models/server_packages/semantic_nlp_rtx3090_20260810/`

服务器建议路径：

`/hyperai/home/AutoPermission_exp/semantic_nlp_rtx3090_20260810/`

每个模型都先执行两批 train/eval smoke；smoke 不物化、不序列化、不评估 frozen test，候选选择也不使用其标签，因此不能作为结果。正式 run 必须使用唯一 run ID，输出、日志、PID 和退出码彼此隔离。服务器有三张空闲 GPU 时可使用 GPU 0/1/2 一卡一模型并行；否则可在一张 GPU 上顺序执行。

若 OOM，不复用已失败目录；使用新 run ID，并通过 batch override 从 `32/64` 降为 `16/32`。本轮不通过改变 max length、梯度累积或其他训练参数静默“自救”。

## 9. 每个正式 run 的关键产物

- `candidate_results.csv`：六个 validation 候选
- `training_curves.csv` / `training_history.csv`
- `selected_hyperparameters.json`
- `validation_predictions.csv`
- `test_metrics.csv` / `test_predictions.csv`
- `confusion_matrix.csv` / `classification_report.json`
- `run_config.json` / `environment.json`
- `split_manifest.json` / `serialization_manifest.json`
- `training_diagnostics.json`
- `source/run_transformer_four_label.py`
- 可选 `final_model/`

模型预下载还会单独保存 model lock，记录 requested/resolved commit、模型/tokenizer class、参数量及缓存文件 SHA-256。

## 10. 解释边界

- 该实验只证明在当前固定数据协议上的相对表现，不证明模型理解了隐私规范。
- 65 个 query 和测试 context 已在 outer train 出现；participant-heldout 只测新用户，不测新语义场景。
- 模型可能利用 demographic/profile shortcut，而不一定利用 SSN、name 或 domain 的语义关系。
- 如果本轮出现明显提升，下一阶段才考虑 query-heldout、data-type-heldout、去掉 `necessity_status`、text-only/profile-only ablation 和多 seed。

## 11. 官方资料

- RoBERTa-base：[模型卡](https://huggingface.co/FacebookAI/roberta-base)、[固定 commit](https://huggingface.co/FacebookAI/roberta-base/commit/e2da8e2f811d1448a5b465c236feacd80ffbac7b)
- DeBERTa-v3-small：[模型卡](https://huggingface.co/microsoft/deberta-v3-small)、[论文](https://arxiv.org/abs/2111.09543)
- ModernBERT-base：[模型卡](https://huggingface.co/answerdotai/ModernBERT-base)、[Transformers 文档](https://huggingface.co/docs/transformers/v5.4.0/en/model_doc/modernbert)
- Transformers `.bin` / PyTorch 安全要求：[官方 issue](https://github.com/huggingface/transformers/issues/38464)
