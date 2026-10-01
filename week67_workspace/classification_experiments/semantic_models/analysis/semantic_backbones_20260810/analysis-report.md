# 多种语义分类模型严格结果分析

## Executive conclusion

同一冻结 participant-heldout 测试集上，三个新语义 backbone 都没有超过 tuned Flat Logistic Regression 的主指标 Macro-F1。RoBERTa 的 Accuracy 最高，但其 Macro-F1、QWK 和两项权限风险更差；DeBERTa 也有明显的 over-sharing；ModernBERT 是三个语义模型中最均衡的，但相对 Flat LR 的五项点估计仍为 0/5 个期望方向改善。因此当前默认 benchmark 仍保留 **tuned Flat LR**，ModernBERT 作为后续最值得保留的语义 baseline。

## 可比性与审计结果

- 数据：16,361 行、201 participants；canonical SHA-256 `4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`。
- 外层测试：3,323 行、41 名 participant；训练 13,038 行、160 人；participant overlap=0。
- 三个新 run 均为 `completed`、`official_result=true`，inner participant validation 选参，冻结 test 各评估一次。
- 三模型的预测与 tuned Flat LR 在 participant/query/tool/raw data type/label 等字段上一对一对齐；stored metrics 已从预测逐项复算，绝对误差小于 `1e-9`。
- 服务器：RTX 3090、PyTorch 2.6.0+cu124、Transformers 5.5.0、FP16 autocast；正式 source snapshot SHA-256 `f8990f5996884a32d7d1bb9bcca3aaa1260b72d8af2a53a5f640a1ab0f699321`。

## 当前主要模型比较

| 模型 | 版本/证据状态 | Accuracy ↑ | Macro-F1 ↑ | QWK ↑ | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---|---:|---:|---:|---:|---:|
| Flat LR tuned | train-only CV | 40.927% | 37.065% | 0.3155 | 42.571% | 21.043% |
| Ordinal LR tuned | train-only CV | 42.732% | 37.436% | 0.3178 | 48.821% | 29.885% |
| Factored LR tuned | train-only CV | 43.635% | 37.762% | 0.2741 | 54.717% | 22.281% |
| DistilBERT initial | train-only validation | 36.864% | 32.793% | 0.2388 | 50.590% | 39.523% |
| RoBERTa-base | train-only validation | 44.689% | 33.514% | 0.2465 | 69.340% | 32.714% |
| DeBERTa-v3-small | train-only validation | 43.334% | 32.630% | 0.2903 | 68.750% | 28.824% |
| ModernBERT-base | train-only validation | 38.580% | 35.026% | 0.2823 | 43.278% | 23.342% |

最高 Accuracy 是 RoBERTa；最高 Macro-F1 是 Factored tuned；最高 QWK 是 Ordinal tuned。单看一个性能数字会掩盖风险：Factored tuned、RoBERTa 和 DeBERTa 都出现明显更高的 over-sharing。若目标是一个可解释且效果—风险较均衡的默认模型，Flat tuned 仍是当前最稳妥的选择。

## 三个新语义模型对 tuned Flat LR 的配对比较

主指标差值定义为 `semantic − Flat LR`：

| 语义模型 | Δ Macro-F1 (pp) | 95% CI low | 95% CI high |
|---|---|---:|---:|
| RoBERTa-base | -3.5514 | -7.3937 | 0.5145 |
| DeBERTa-v3-small | -4.4350 | -10.4441 | 1.7679 |
| ModernBERT-base | -2.0391 | -5.4349 | 1.4189 |

三项 Macro-F1 的 marginal 95% participant-bootstrap CI 均在 Flat LR 一侧或跨 0；同时输出了每个指标内针对三个 backbone 的 Bonferroni 98.333% CI。当前没有证据支持任何一个新 backbone 在主指标上优于 Flat LR。

权限风险差值为正表示语义模型更差：

| 语义模型 | 风险指标 | 语义−Flat (pp) | 95% CI low | 95% CI high |
|---|---|---:|---:|---:|
| RoBERTa-base | Over-sharing | 26.7689 | 15.0722 | 38.8441 |
| RoBERTa-base | Persistent over-allow | 11.6711 | 2.9052 | 20.7324 |
| DeBERTa-v3-small | Over-sharing | 26.1792 | 14.7749 | 38.2529 |
| DeBERTa-v3-small | Persistent over-allow | 7.7807 | -6.5103 | 22.3937 |
| ModernBERT-base | Over-sharing | 0.7075 | -6.5881 | 8.5941 |
| ModernBERT-base | Persistent over-allow | 2.2989 | -4.3830 | 8.9503 |

RoBERTa 与 DeBERTa 的 over-sharing 恶化很大；ModernBERT 的风险最接近 Flat LR，但不能据此称为等效或同样安全。

## 为什么 Accuracy 与 Macro-F1 给出不同印象

测试集 label 2 占 42.55%。RoBERTa 和 DeBERTa 的 Accuracy 高于 Flat LR，但对少数类、特别是 label 1 的表现弱；两者 label 1 F1 均为 0。因此 Accuracy 的提升没有转化为四类均衡识别能力，并伴随更多过度允许。

## Claim candidates

1. **Observation**：RoBERTa 的固定测试 Accuracy 为 44.689%，是当前表中最高点估计。  
   **Boundary**：它的 Macro-F1 只有 33.514%，Over-sharing 为 69.340%；不能称为综合最佳。
2. **Observation**：三个新语义模型中 ModernBERT 的 Macro-F1 最高（35.026%），两项风险也最接近 Flat LR。  
   **Boundary**：其五项点估计仍均未优于 Flat LR，且只有一个训练 seed。
3. **Observation**：当前所有主要候选中 Factored tuned 的 Macro-F1 最高（37.762%）。  
   **Boundary**：Over-sharing 为 54.717%，明显高于 Flat tuned 的 42.571%；只按 Macro-F1 选它会改变权限风险。
4. **Observation**：三个新 backbone 的主指标均未超过 tuned Flat LR。  
   **Support**：participant-paired cluster bootstrap，n=41、B=5,000，并提供三项主比较的 Bonferroni 区间。  
   **Boundary**：区间只覆盖测试 participant 抽样，不覆盖训练随机性或外层 split。

## Decision

- **继续**：Flat tuned 作为当前默认 classical benchmark；ModernBERT 作为语义模型负/中性 baseline 保存。
- **停止**：不要因为 RoBERTa/DeBERTa Accuracy 较高就将其升级为权限分类默认模型。
- **下一步**：若继续探索语义表示，优先做 Flat LR 与 frozen semantic embedding 的受控融合/ablation，或增加多 seed；不要先扩大端到端 backbone 数量。
- **论文边界**：当前结果可以作为单 split、单 seed 的初步负结果；还不支持“语义模型普遍无效”或“LR 显著优于所有 Transformer”的结论。
