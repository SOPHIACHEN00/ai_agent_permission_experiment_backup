# 语义分类模型介绍与当前结果对比

> 更新时间：2026-08-10  
> 任务：根据用户、场景、工具和数据类型等信息，预测四种 permission response。  
> 主评估协议：`participant_heldout`，160 名参与者训练、41 名未见参与者测试，共 3,323 条冻结测试行。  
> 用途：解释 DistilBERT、RoBERTa、DeBERTa、ModernBERT 分别是什么，并记录它们与经典 Logistic Regression 的当前结果。

## 一分钟结论

- 这四个模型都是**预训练 Transformer encoder + 四分类头**，不是 ChatGPT 一类的生成式聊天模型。
- 它们的“懂语义”是指：预训练使模型能够根据上下文表示词语和句子，例如把 `SSN`、`social security number` 和身份信息联系起来；这不等于模型天然理解某个用户的隐私偏好。
- 四个模型都进行了端到端 fine-tuning：Transformer 参数和最后的四分类线性层一起更新。Transformer 后面**没有再接一套 scikit-learn Logistic Regression**。
- RoBERTa 的 Accuracy 最高，但过度允许风险很高；DeBERTa 也有相同倾向；ModernBERT 是语义模型中最均衡的；DistilBERT 是较轻量的初始语义 baseline。
- 当前仍保留 **Flat LR tuned** 作为默认 benchmark：它并非每项指标第一，但 Macro-F1、QWK、风险、速度与可解释性更均衡。

## “语义分类”在本实验里到底是什么

经典 LR 和 Transformer 使用相同来源的数据字段，但表示方式不同：

- **经典 LR**：文本转成 TF-IDF 词/二元词组，类别字段做 One-Hot，数值字段直接输入。它擅长利用数据中已出现的词和类别，但不会通过预训练知识主动建立较强的上下文语义联系。
- **Transformer**：先把选定字段组织成自然语言，再用预训练 tokenizer 和 encoder 产生上下文表示，最后输出四类概率。它有机会利用预训练中学到的语言关系。

```mermaid
flowchart LR
    A["手工选择的场景、数据类型与用户字段"] --> B["序列化为自然语言 prompt"]
    B --> C["Tokenizer"]
    C --> D["预训练 Transformer encoder<br/>端到端 fine-tuning"]
    D --> E["可训练的线性四分类头 + Softmax"]
    E --> F["标签 0 / 1 / 2 / 3"]
```

所以，“使用语义模型”并不意味着没有人工设计：**输入哪些字段、怎样组织文本、怎样切分数据和选择指标仍然由实验者决定**。变化主要在于特征表示从 TF-IDF/One-Hot 换成了预训练上下文表示。

## 实际输入与输出

四个 Transformer 实验使用同一个、与 backbone 无关的输入模板，包含：

- 场景与数据：`query`、`tool`、`raw_data_type`、`generic_data_type`、`domain`、`necessity_status`；
- 参与者信息：`age`、`gender`、`education`；
- AI 与隐私态度：`ai_familiarity`、`ai_frequency`、`ai_trust`、`privacy_importance`、`concern_domain`。

输出仍是原始四个回答：

| 标签 | 回答 |
|---:|---|
| 0 | No, never share |
| 1 | No, but ask me next time |
| 2 | Yes, but ask me next time |
| 3 | Yes, always share |

注意：`necessity_status` 来自场景设计元数据。它不是目标标签，但如果真实部署时无法获得，就可能属于 privileged/oracle feature；因此本轮比较应理解为现有完整 pipeline 的比较。

## 四种语义模型分别是什么

### 1. DistilBERT：轻量压缩版 BERT

DistilBERT 通过 knowledge distillation 把 BERT 压缩为更小、更快的 encoder。本次分类模型共有 66,956,548 个可训练参数，约 67M。它保留了 BERT 的大部分语言表示能力，但容量和计算量较低。

- **为什么先试它**：成本低、训练快，适合作为第一个端到端语义 baseline。
- **本实验角色**：验证“把 TF-IDF 换成预训练语义 encoder”是否有明显收益。
- **当前观察**：首个正式 run 的效果和两个风险指标都落后于 Flat LR；增加最大 epoch 的 exploratory follow-up 也没有改变总体判断。

### 2. RoBERTa-base：更充分训练的 BERT 系列模型

RoBERTa 保留 BERT encoder 的基本结构，但修改了预训练方案，例如使用更多训练数据与训练步骤、动态 masking，并取消 Next Sentence Prediction。正式 run 记录了 124,648,708 个可训练参数。

- **为什么选择它**：它是成熟、强势、使用广泛的 BERT 类文本分类基线。
- **本实验表现**：Accuracy 最高，但 label 1 的 precision、recall、F1 均为 0，即该类没有产生 true positive；模型明显偏向允许类，导致 Over-sharing 很高。
- **如何理解**：高 Accuracy 并不代表四类都学得好；在类别不均衡数据上，必须同时看 Macro-F1 和风险指标。

### 3. DeBERTa-v3-small：分离内容与位置表示

DeBERTa 的核心思路是 disentangled attention：词内容和位置信息使用分离表示，再在 attention 中组合；v3 的预训练还采用 replaced-token detection 思路。正式 run 记录了 141,897,988 个可训练参数。

- **为什么选择它**：希望更细致的内容—位置建模能提升对 query、tool、data type 组合的理解。
- **为什么叫 small 但参数不少**：`small` 是该模型家族内部的配置名称；其较大的词嵌入部分使本次实际总参数仍约 142M。
- **本实验表现**：Accuracy 与 QWK 尚可，但 label 1 的 precision、recall、F1 同样均为 0，Over-sharing 与 RoBERTa 一样明显偏高。

### 4. ModernBERT-base：现代化的 encoder 架构

ModernBERT 是较新的 BERT 风格 encoder，采用 Pre-Norm、GeGLU、RoPE，以及交替的 local/global attention 等现代组件。正式 run 记录了 149,607,940 个可训练参数。

- **为什么选择它**：检验更新的 encoder 训练与架构设计能否提供更均衡的四分类表现。
- **本实验限制**：ModernBERT 的长上下文能力在这里没有真正发挥，因为输入最大长度仅为 128 token。
- **本实验表现**：三个新 semantic backbone 中 Macro-F1 最高、两个风险率最低，也是唯一能识别 label 1 的新模型；但总体仍未超过 Flat LR。

## 方法差异速查

| 方法 | 主要表示方式 | 约/实际参数量 | 本实验中的主要特点 |
|---|---|---:|---|
| Flat LR | TF-IDF + One-Hot + 数值字段 | 远小于 Transformer | 快、可解释、整体最均衡 |
| DistilBERT | 蒸馏后的 BERT encoder | 66.96M | 最轻量的端到端语义 baseline |
| RoBERTa-base | 强化预训练的 BERT encoder | 124.65M | Accuracy 高，但允许倾向和风险很高 |
| DeBERTa-v3-small | 内容/位置分离 attention | 141.90M | QWK 相对较好，但允许倾向仍很高 |
| ModernBERT-base | 现代 BERT encoder 组件 | 149.61M | 新语义模型中最均衡 |

## 当前统一结果

Accuracy、Macro-F1、QWK 越高越好；Over-sharing 和 Persistent-over-allow 越低越好。下表全部使用同一个冻结 participant-heldout 测试集。

- **Over-sharing**：在真实回答为拒绝（labels 0/1）的行中，模型预测为允许（labels 2/3）的比例；本测试集分母为 848。
- **Persistent-over-allow**：在真实回答不是永久允许（labels 0/1/2）的行中，模型预测成 `Yes, always share` 的比例；本测试集分母为 2,262。

| 方法 | 当前比较版本 | Accuracy ↑ | Macro-F1 ↑ | QWK ↑ | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---|---:|---:|---:|---:|---:|
| Flat LR tuned | `C=3, balanced` | 40.927% | 37.065% | 0.3155 | **42.571%** | **21.043%** |
| Ordinal LR tuned | `C=10, balanced, τ=0.45` | 42.732% | 37.436% | **0.3178** | 48.821% | 29.885% |
| Factored LR tuned | 两因子 train-only CV | 43.635% | **37.762%** | 0.2741 | 54.717% | 22.281% |
| DistilBERT initial | `lr=2e-5, balanced, epoch=2` | 36.864% | 32.793% | 0.2388 | 50.590% | 39.523% |
| RoBERTa-base | `lr=2e-5, none, epoch=1` | **44.689%** | 33.514% | 0.2465 | 69.340% | 32.714% |
| DeBERTa-v3-small | `lr=1.5e-5, balanced, epoch=1` | 43.334% | 32.630% | 0.2903 | 68.750% | 28.824% |
| ModernBERT-base | `lr=3e-5, balanced, epoch=2` | 38.580% | 35.026% | 0.2823 | 43.278% | 23.342% |

这里的粗体只表示该列点估计最优，不等于存在一个“所有方面都最好”的模型。

表中 `balanced` 表示按训练标签频率使用类别权重，`none` 表示不加类别权重；`epoch` 是最终重训轮数；`τ` 是将二元概率转成类别判断的阈值；QWK 是 Quadratic Weighted Kappa，用来衡量有序标签上的一致程度。

## 如何读这些结果

### RoBERTa 的 Accuracy 最高，但不是综合最佳

冻结测试集中的 label 2 占 42.55%。RoBERTa 倾向预测允许类，因此 Accuracy 达到 44.689%，但 label 1 没有 true positive，Macro-F1 只有 33.514%。它的 Over-sharing 为 69.340%，比 Flat LR 高 26.769 个百分点；participant-paired bootstrap 的 95% CI 为 `[+15.072,+38.844]`。

### DeBERTa 也出现了相似的类别偏置

DeBERTa 的 Accuracy 为 43.334%、QWK 为 0.2903，但 label 1 也没有 true positive。Over-sharing 比 Flat LR 高 26.179 个百分点，95% CI 为 `[+14.775,+38.253]`。因此不能仅凭 Accuracy 把它视为提升。

### ModernBERT 是语义模型中最均衡的

从 Macro-F1 和两个风险率的点估计来看，ModernBERT 的组合最均衡：Macro-F1 为 35.026%，Over-sharing 为 43.278%，Persistent-over-allow 为 23.342%。其 Macro-F1 相对 Flat LR 的差值为 −2.039 个百分点，95% CI 为 `[−5.435,+1.419]`：当前证据既不能说明它更好，也不能据此证明二者等效。这里的“最均衡”是定性判断，并非预先定义的综合评分。

### Flat LR 为什么仍是默认 benchmark

Flat LR 不拥有最高 Accuracy 或 Macro-F1，但它在效果、两个风险率、训练成本和可解释性之间没有明显极端短板。尤其相较 RoBERTa/DeBERTa，它没有为了提高 Accuracy 而产生大幅 Over-sharing。因此目前最合理的记录方式是：

- Flat LR tuned 继续作为主要决策 benchmark；
- Ordinal/Factored LR 保留为结构化性能—安全权衡实验；
- ModernBERT 保留为当前最有价值的 semantic baseline；这里的三个新 semantic backbones 特指 RoBERTa、DeBERTa 和 ModernBERT；
- DistilBERT、RoBERTa、DeBERTa 作为有信息量的负结果保留。

## 为什么预训练语义没有直接带来提升

以下是与结果一致的可能解释，不是已证明的因果结论：

1. **标签不仅是数据敏感度。** `SSN` 通常比 `name` 更敏感，但最终回答还取决于用户本人是否信任 AI、是否愿意本次授权、下次是否要再次询问。
2. **四类边界很细。** labels 1/2 的差别同时涉及 deny/allow 与 ask-next-time 策略，不是单纯做“敏感/不敏感”二分类。
3. **类别不均衡会奖励允许倾向。** label 2 是测试集最大类，所以偏向允许可能提高 Accuracy，却损害 Macro-F1 和安全指标。
4. **当前 split 不是新场景测试。** 测试参与者未见过，但 65 个 query/templates 在训练中都出现过；本轮衡量的是“新用户、已见场景”。
5. **比较的是完整 pipeline。** LR 和 Transformer 的 preprocessing 不同，所以当前差异不能被解释成语义表示的纯因果效果。
6. **训练不确定性尚未完全覆盖。** 当前正式 Transformer 结果主要来自单一 training seed；participant bootstrap 只反映 41 名测试参与者的抽样不确定性。

## 与 Offline / Online MAB 的关系

MAB 不是第五种或第六种“懂语义的 Transformer”。它不依赖预训练语言模型，而是把同样的四个 permission labels 当作四个 actions，研究 **frozen policy 与 same-user feedback adaptation** 的差别。

| MAB 方法 | Test 时更新 | JEM / Accuracy | Macro-F1 | False-allow | 主要结论 |
|---|---:|---:|---:|---:|---|
| Canonical Offline MAB | 否 | 43.911% | 20.473% | 100.000% | 冻结 global stated-policy baseline |
| Online WP-FTS | 是 | 51.083% | 28.058% | 98.538% | 个体化主要改善 persistence，但没有解决 deny/access 安全问题 |

Online 相对 Offline 的 all-round JEM 差值为 `+7.173 pp`，95% CI `[+2.789,+12.162]`；Persistence accuracy 提高 `+8.909 pp`，Access accuracy 只提高 `+0.153 pp` 且 CI 跨 0。这个结果在 MAB 协议内部有效，但不能直接加入上面的静态 classifier 排名：WP-FTS 在测试 replay 中使用同一用户此前反馈，而 LR/Transformer 的 test prediction 完全冻结。

跨范式的完整结果、post-adaptation rounds 10–18、matched frozen control 与安全边界见 [静态分类与 Offline/Online MAB 扩展比较](../04_静态分类与Offline_Online_MAB扩展比较_zh.md)。

## 当前可以和不可以说什么

可以说：

> 在同一个冻结 participant-heldout 测试集和当前训练配置下，四种 fine-tuned Transformer 按本轮点估计均未在 Macro-F1 与风险的综合表现上超过 tuned Flat LR；ModernBERT 是其中最均衡的语义 baseline。

不应说：

- “Transformer 不懂隐私语义”；
- “所有 BERT/语义模型都不适合这个任务”；
- “Flat LR 在任何新场景都一定优于 Transformer”；
- “某个差值是由语义表示本身造成的”；
- “单次训练 seed 的差异已经证明了模型间的普遍优劣”。

## 证据与延伸阅读

- [静态分类与 Offline/Online MAB 扩展比较](../04_静态分类与Offline_Online_MAB扩展比较_zh.md)
- [Online MAB 最终文档总览](../../ai_agent_permission_experiment/online_mab/README.md)
- [全部分类方法综合比较](../03_当前全部分类方法综合比较_zh.md)
- [语义模型正式结果报告](reports/2026-08-10--semantic-classification--r01--round-review.md)
- [严格分析报告](analysis/semantic_backbones_20260810/analysis-report.md)
- [全部模型指标 CSV](analysis/semantic_backbones_20260810/all_model_metrics.csv)
- [新语义模型 vs Flat LR 配对 bootstrap](analysis/semantic_backbones_20260810/semantic_vs_flat_lr_bootstrap_summary.csv)
- [DistilBERT 独立实验索引](../distilbert/README.md)
- [DistilBERT 模型卡](https://huggingface.co/distilbert-base-uncased)
- [RoBERTa-base 模型卡](https://huggingface.co/FacebookAI/roberta-base)
- [DeBERTa-v3-small 模型卡](https://huggingface.co/microsoft/deberta-v3-small)
- [ModernBERT-base 模型卡](https://huggingface.co/answerdotai/ModernBERT-base)
