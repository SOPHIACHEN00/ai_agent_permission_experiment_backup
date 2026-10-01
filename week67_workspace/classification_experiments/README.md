# S&P 四标签分类与 Bandit 实验知识库

本目录记录 *Towards Automating Data Access Permissions in AI Agents*（IEEE S&P 2026）公开数据上的经典/语义四分类实验，以及使用同一四标签 action space 的 Offline/Online contextual-bandit 扩展。后续增加新的 classifier 或 policy baseline 时，请保留模型说明、运行记录和原始产物，不要覆盖历史结果。

## 先回答这次的三个问题

1. **raw data 如何变成经典分类？**  使用 `external/ai-agent-permissions/data/user_study.json`，结合 `queries.json` 与 `data_types.csv`，由 [`build_dataset.py`](../ai_agent_permission_experiment/src/build_dataset.py) 把每个有效参与者的 Task 3 中每个 permission answer 展开为一行；四个原始回答完整映射到标签 `0..3`。最终得到 16,361 行、201 名参与者、65 个 query。详见 [`00_数据来源与处理链_zh.md`](00_数据来源与处理链_zh.md)。
2. **三种 Logistic 是否做过？** 都做过。Flat 是一个四类 LR；Ordinal 是三个独立累计阈值 LR 的启发式集成，并非严格 proportional-odds；Factored 是 access 与“下次是否再问”两个二元 LR 后重组四类，因此 **Factored 已完成，不是 TBD**。
3. **旧结果是不是已经最好？** 不能这样下结论。旧调参只扫过 Flat，而且直接复用了最终 test，没有独立 validation。本轮已固定外层 test、只在外层 train 内 3 折 CV 选参。Flat 获得小幅且方向一致的点估计改进，但 41 名测试参与者的 bootstrap 区间仍跨 0；Ordinal/Factored 的 macro-F1 点估计提高，却明确增加过度授权风险（风险差值 CI 不跨 0）。

## 模型状态

| 记录名 | 实际方法 | 已运行 | 当前判断 |
|---|---|---:|---|
| Flat four-class classifier | 四类 multinomial Logistic Regression | 是 | 历史默认基线；本轮 `C=3, class_weight=balanced` 是主协议下更合理的 tuned candidate，但改进证据仍弱 |
| Ordinal Model | 三个独立二元 LR：`y>0`、`y>1`、`y>2`，阈值后求和 | 是 | 应称“独立累积阈值 LR”；严格 proportional-odds 模型尚未做 |
| Factored Model | access LR + policy-persistence LR，再还原四类 | 是 | 已完成；默认版的 persistent-over-allow 较低，但调参版安全代价较大 |
| DistilBERT Flat | `distilbert-base-uncased` 端到端四分类 fine-tuning | 是，RTX 3090 | 首个 run 与 max-5-epoch follow-up 均未超过 tuned Flat LR；作为负面的初始语义 baseline 保留 |
| 非 DistilBERT semantic encoders | RoBERTa-base、DeBERTa-v3-small、ModernBERT-base | 是，RTX 3090 | 三个正式 run 均完成；没有一个在 Macro-F1 上超过 tuned Flat LR，ModernBERT 是其中最均衡的 semantic baseline |
| Four-label IC-only | 同一用户历史回答进入 LLM；按用户内部 query 做 5 折留出 | 单任务 API 试跑通过，完整 5 折待跑 | 个体历史预测协议；与下方整位用户留出主表分开报告 |
| Canonical Offline MAB | factored Thompson training + frozen global posterior-mean greedy test | 是，20 个 paired runs/streams | 静态 stated-policy bandit baseline；JEM 43.911%，但 False-allow 100% |
| Online WP-FTS | warm-started personalized factored Thompson sampling | 是，20 个 paired replay streams | sequential personalization baseline；JEM 51.083%，提升主要来自 persistence，但 False-allow 仍为 98.538% |

## 静态分类主结果：新参与者、已见场景

主协议是 `participant_heldout`：160 名参与者训练、41 名参与者测试，参与者不重叠；但 65 个 query/template 在训练和测试中都出现，因此只表示“新用户、已见场景”的泛化。

| 模型 | 版本 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---|---:|---:|---:|---:|---:|
| Flat | 原始 `C=1, balanced` | 40.656% | 36.690% | 30.941% | 43.042% | 21.176% |
| Flat | CV 选参 `C=3, balanced` | 40.927% | 37.065% | 31.549% | 42.571% | 21.043% |
| Ordinal | 原始 `C=1, balanced, τ=0.5` | 40.656% | 36.288% | 31.412% | 42.689% | 24.492% |
| Ordinal | CV 选参 `C=10, balanced, τ=0.45` | 42.732% | 37.436% | 31.785% | 48.821% | 29.885% |
| Factored | 原始两个因子均 `C=1, balanced, τ=0.5` | 40.596% | 36.588% | 28.258% | 44.104% | **18.700%** |
| Factored | CV 选参 | 43.635% | **37.762%** | 27.415% | 54.717% | 22.281% |
| DistilBERT Flat | 首个 GPU run，`lr=2e-5, epoch=2` | 36.864% | 32.793% | 23.876% | 50.590% | 39.523% |
| DistilBERT Flat | max-5 follow-up，early stop 后实际 `epoch=1` | 38.820% | 33.509% | 25.294% | 54.599% | 43.855% |
| RoBERTa-base | `lr=2e-5, none, epoch=1` | **44.689%** | 33.514% | 24.652% | 69.340% | 32.714% |
| DeBERTa-v3-small | `lr=1.5e-5, balanced, epoch=1` | 43.334% | 32.630% | 29.031% | 68.750% | 28.824% |
| ModernBERT-base | `lr=3e-5, balanced, epoch=2` | 38.580% | 35.026% | 28.234% | 43.278% | 23.342% |

注意：表中最高 macro-F1 不是自动的“最佳模型”。Factored tuned 相对默认的 macro-F1 差值为 `+1.174` 个百分点，95% participant-bootstrap CI 为 `[-0.403, +2.764]`；同时 over-sharing 明确恶化 `+10.613` 个百分点，CI 为 `[+7.838, +13.921]`。当前若需要一个均衡、可解释的 classical baseline，优先保留 **Flat**，并同时报告默认与 `C=3` tuned 版本。

DistilBERT follow-up 相对 tuned Flat LR 的 Macro-F1 为 `-3.556` 个百分点，95% participant-bootstrap CI `[-7.304,+0.236]`；Over-sharing 与 Persistent-over-allow 分别恶化 `+12.028` 和 `+22.812` 个百分点，且两个区间都不跨 0。Follow-up 是看过首轮 test 后的 exploratory/test-touched 结果，因此不能升级为新的无偏 final；它只说明继续增加 epoch 没有让当前配置成为更好的 baseline。

三个新 semantic backbone 也没有在 Macro-F1 上超过 tuned Flat LR。RoBERTa/DeBERTa 的 Accuracy 较高，但 Over-sharing 分别达到 69.340%/68.750%；ModernBERT 的效果与风险最均衡，但五项点估计仍没有优于 Flat。完整结论见 [`03_当前全部分类方法综合比较_zh.md`](03_当前全部分类方法综合比较_zh.md)。

## Bandit 扩展结果：顺序反馈与个体化适应

Offline 与 Online MAB 使用相同四个 action、相同 41 名 test participants、相同 3,323 行和同一 selected-action exact-match reward。下面是正式 v2 all-round、20 个 paired streams 的 pooled 指标；CI 用 5,000 次 participant-cluster bootstrap。

| 指标 | Offline canonical | Online WP-FTS | Online − Offline | 95% CI |
|---|---:|---:|---:|---:|
| JEM / Accuracy ↑ | 43.911% | **51.083%** | **+7.173 pp** | **[+2.789,+12.162]** |
| Macro-F1 ↑ | 20.473% | **28.058%** | **+7.585 pp** | **[+3.377,+11.006]** |
| Access accuracy ↑ | 74.481% | 74.634% | +0.153 pp | [−0.145,+0.645] |
| Persistence accuracy ↑ | 54.684% | **63.593%** | **+8.909 pp** | **[+3.450,+15.219]** |
| False-allow / Over-sharing ↓ | 100.000% | **98.538%** | **−1.462 pp** | **[−2.980,−0.281]** |

差值使用未四舍五入的底层数值计算，因此直接相减显示后的三位小数时可能有 `0.001 pp` 差异。

这不是新的静态 classifier 排名。WP-FTS 会在 test replay 中吸收同一用户此前 bundle 的 feedback；静态 LR/Transformer 不使用 test-time feedback。其 51.083% JEM 因此不能被解释为全面胜过静态模型。False-allow 仍接近 100%，所以它是 **sequential personalization baseline**，不是安全 policy。完整解释见 [`04_静态分类与Offline_Online_MAB扩展比较_zh.md`](04_静态分类与Offline_Online_MAB扩展比较_zh.md)。

## 目录导航

- [`00_数据来源与处理链_zh.md`](00_数据来源与处理链_zh.md)：raw → CSV 的完整转换过程。
- [`01_评估协议与防泄漏约定_zh.md`](01_评估协议与防泄漏约定_zh.md)：split、validation、指标和禁止事项。
- [`02_当前最佳结果_参数_特征与标签速查_zh.md`](02_当前最佳结果_参数_特征与标签速查_zh.md)：当前最佳参数、结果、features 与四标签的一页式 recap。
- [`03_当前全部分类方法综合比较_zh.md`](03_当前全部分类方法综合比较_zh.md)：七个静态 classifier 的统一比较，以及单列的 Offline/Online MAB 扩展摘要与当前决策。
- [`04_静态分类与Offline_Online_MAB扩展比较_zh.md`](04_静态分类与Offline_Online_MAB扩展比较_zh.md)：静态 classifier、Offline MAB 与 Online WP-FTS 的分协议对比、late-round 结果和可比性边界。
- [`models/`](models/)：三种经典 Logistic basic classifier 的独立说明。
- [`runs/2026-08-09_baseline复现_zh.md`](runs/2026-08-09_baseline复现_zh.md)：数据与旧分数的逐值复现。
- [`distilbert/README.md`](distilbert/README.md)：DistilBERT 专属入口；设计、两个 RTX 3090 runs、分析报告、CSV/JSON/图表、机器产物和服务器包均集中在此。
- [`semantic_models/README.md`](semantic_models/README.md)：RoBERTa、DeBERTa、ModernBERT 的设计、正式 RTX 3090 结果、严格分析、报告与服务器归档入口。
- [`semantic_models/语义分类模型介绍与结果对比_zh.md`](semantic_models/语义分类模型介绍与结果对比_zh.md)：DistilBERT、RoBERTa、DeBERTa、ModernBERT 的原理差异、fine-tuning 流程与当前结果解读。
- [`../ai_agent_permission_experiment/in_context_learning/README.md`](../ai_agent_permission_experiment/in_context_learning/README.md)：四标签 IC-only baseline 的论文对照、用户内 5 折协议、运行方式与产物。
- [`../ai_agent_permission_experiment/online_mab/README.md`](../ai_agent_permission_experiment/online_mab/README.md)：Online MAB 的最终中文文档总览、方法、正式 v2 结果与原始证据入口。
- [`tuning/2026-08-09_logistic_regression_调参记录_zh.md`](tuning/2026-08-09_logistic_regression_调参记录_zh.md)：本轮无 test 泄漏调参。
- [`analysis-output/analysis-report.md`](analysis-output/analysis-report.md)：严格结果审计与可允许结论。
- [`analysis-output/figures/`](analysis-output/figures/)：真实 PDF/PNG 图表。
- [`templates/基础分类模型实验模板_zh.md`](templates/基础分类模型实验模板_zh.md)：以后新增模型时复制使用。
- [`artifacts/`](artifacts/)：经典 LR 与共享对照的机器可读产物；不要手工修改。DistilBERT 产物见 [`distilbert/artifacts/`](distilbert/artifacts/)，新语义模型产物见 [`semantic_models/artifacts/`](semantic_models/artifacts/)。

## 后续增加 basic classifier 的规则

1. 从模板新建 `models/NNN_<model>_zh.md`，先写清问题、标签、特征和比较基线。
2. 使用唯一 run ID 输出到 `artifacts/<run_id>/`；不得覆盖旧 run。
3. 只用 train/validation 选参数，冻结后再看 test；主协议默认按 participant 分组。
4. 至少报告 Accuracy、Macro-F1、QWK、Over-sharing、Persistent-over-allow、逐类 recall 和混淆矩阵。
5. 更新本 README 的模型状态与主结果，但保留负结果和安全权衡。

