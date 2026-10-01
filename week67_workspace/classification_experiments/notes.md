# Notes: S&P 经典分类实验

## 仓库与数据来源

- 主项目：`ai_agent_permission_experiment/`。
- S&P 论文配套仓库：`ai_agent_permission_experiment/external/ai-agent-permissions/`，论文为 *Towards Automating Data Access Permissions in AI Agents*（IEEE S&P 2026）。
- 四分类数据必须从 `data/user_study.json` 重建；上游 `processed_dataset.json` 只保留经过筛选的 181 名参与者，并为原论文二分类式推断过滤了中间响应，不适合作为四标签来源。
- 原始三项输入 SHA-256 已记录；重建 CSV 与现有 `data/processed/four_label_dataset.csv` 的 SHA-256 均为 `4A6F61191318EAA79BA2FAC1AB80E6FB850E099F1F0178EEF2F53B3B527FE463`。

## 数据处理链

- `src/build_dataset.py` 读取 `user_study.json`、`queries.json` 和 `data_types.csv`。
- 只保留 `Valid is True` 的参与者；展开每名参与者 `task3` 中每个 query 的每个 `(tool, raw_data_type) -> permission response` 为一行。
- 四标签映射为：`No, never share=0`、`No, but ask me next time=1`、`Yes, but ask me next time=2`、`Yes, always share=3`。
- 通过 query 元数据补充 query/domain，通过 data-type 表补充 generic data type，并构造 `necessary / incorrect_explicit / unknown`。
- 最终 16,361 行、201 名有效参与者、65 个 query；标签计数为 2,361 / 1,720 / 7,056 / 5,224。

## 模型实现

- `flat_four_class_lr`：四类 `sklearn.linear_model.LogisticRegression`；LBFGS、`C=1`、`class_weight=balanced`、`max_iter=2000`。
- `ordinal_lr`：并非单一 proportional-odds 模型，而是三个独立的累计二分类 LR，目标分别为 `y>0`、`y>1`、`y>2`；三个概率以 0.5 截断后求和得到 0..3。
- `factored_lr`：已经实现，并非 TBD。两个二分类 LR 分别预测 access（0/1 vs 2/3）与 persistence（1/2 vs 0/3），再重组为四标签。
- 共用特征：query/tool/raw/generic/domain 拼接文本的 TF-IDF（1–2 gram，`min_df=2`，最多 20,000）；7 个类别字段 one-hot；5 个数值/序数字段原值直通。

## 现有结果

- 旧 `row_stratified`：Flat macro-F1 0.432445；Ordinal 0.403547；Factored 0.408915。该切分的 201 名参与者均同时出现在 train/test。
- 旧 `participant_heldout`：Flat macro-F1 0.366901；Ordinal 0.362884；Factored 0.365880；训练 160 人、测试 41 人。
- 数据重建以及两种切分的三模型指标均在 `classification_experiments/artifacts/` 中逐值复现。
- 旧 flat 调参表尝试 `C={0.1,0.3,1,3,10}` 与 `class_weight={balanced,None}`，但文件没有 validation 划分或运行脚本，且数值正是外层 test 指标，因此不能据此无偏选最佳参数。

## 调参与复现记录

- 已固定原外层 test，只在外层 train 内做 3 折 CV；主目标 macro-F1，QWK/accuracy/两个风险率用于完整报告和 tie-break。
- `participant_heldout` 的内部 CV 按 participant 分组，同一参与者不跨 fold；最终测试仍是原来冻结的 41 人。
- 搜索范围：三模型均搜索 `C={0.1,0.3,1,3,10}`、`class_weight={balanced,None}`；Ordinal 另搜索阈值 0.35–0.65；Factored 分别搜索两个因子的参数及 0.4/0.5/0.6 阈值。
- participant-heldout 选中：Flat=`C=3, balanced`；Ordinal=`C=10, balanced, threshold=0.45`；Factored access=`C=3, balanced, threshold=0.4`，persistence=`C=10, balanced, threshold=0.5`。
- 冻结 test 的 macro-F1：Flat `0.366901 -> 0.370655`，Ordinal `0.362884 -> 0.374360`，Factored `0.365880 -> 0.377619`。
- 2,000 次 participant-paired cluster bootstrap 中，三者 macro-F1 增量的 95% CI 都跨 0，因此不能声称调参已稳定提高 macro-F1。
- Flat 的分数与两个安全风险方向均小幅改善，但区间跨 0；可作为保守的候选默认参数。Ordinal 与 Factored 的 accuracy 点估计提高，但过度授权和 persistent-over-allow 明确恶化，因此不能只按 accuracy 或单个 macro-F1 点估计称为“最好”。
- 共记录每种 split 192 个 LR 拟合诊断，全部收敛；运行时源码快照、参数、预测、混淆矩阵和 bootstrap 结果均已保存。

## 风险与限制

- `row_stratified` 测的是同一批参与者的新行，不能代表新参与者泛化。
- 65 个 vignette/query 模板在 participant-heldout 的 train/test 中仍共享，因此也不能代表新 query/template 泛化。
- 每名参与者贡献多行；统计不确定性应按 participant 聚类重采样，不能把 3,323 行当成独立样本。
- 目前只有一个固定外层 test split；最终只报告参与者 bootstrap CI，不宣称跨随机切分的显著优势。

## DistilBERT 语义 baseline（2026-08-10）

- RTX 3090 首个完成 run：在 outer-train validation 中从 `lr={2e-5,5e-5}`、最多 2 epochs 选择 `2e-5, epoch=2`；test Accuracy `0.368643`、Macro-F1 `0.327932`、QWK `0.238761`、Over-sharing `0.505896`、Persistent-over-allow `0.395225`。
- 在看过首轮 test 后执行 exploratory follow-up：固定 `lr=2e-5`，`max_epochs=5`、patience 2；validation 在 epoch 1 最好，epoch 2/3 连续恶化后 early stop，最终只重训 1 epoch。
- Follow-up test：Accuracy `0.388203`、Macro-F1 `0.335093`、QWK `0.252939`、Over-sharing `0.545991`、Persistent-over-allow `0.438550`。效能点估计略高于首轮，但安全风险更差。
- Follow-up 相对 tuned Flat LR 的 Accuracy/Macro-F1/QWK 点估计分别低 `2.11/3.56/6.26` 个百分点；两项风险率高 `12.03/22.81` 个百分点。5,000 次 participant-paired bootstrap 中，三项效能 CI 跨 0，两项风险 CI 不跨 0 且偏向 LR。
- 两个 DistilBERT runs 的完整预测、配置与 source snapshot 已集中到 `distilbert/artifacts/`；严格分析位于 `distilbert/analysis/distilbert_epoch5_codex_20260810/`。
- 当前决定：保留 DistilBERT 为负面的语义 baseline，不再只靠增加 epoch 调参，不替换 tuned Flat LR。该结果不能泛化为“所有 BERT/语义分类都更差”。

## 其他语义 backbone（2026-08-10）

- RoBERTa-base、DeBERTa-v3-small、ModernBERT-base 的 RTX 3090 正式 run 已完成；每个模型只在 outer-train 的 inner participant validation 选参，冻结 test 各评估一次。
- 固定测试点估计：RoBERTa Accuracy/Macro-F1=`0.446885/0.335141`；DeBERTa=`0.433343/0.326304`；ModernBERT=`0.385796/0.350264`。
- RoBERTa/DeBERTa 的 Over-sharing 为 `0.693396/0.687500`，明显高于 tuned Flat LR 的 `0.425708`；ModernBERT 为 `0.432783`，最接近 Flat。
- 5,000 次 participant-paired bootstrap 中，三个新模型的 Macro-F1 差值区间均跨 0；RoBERTa/DeBERTa 的 Over-sharing 恶化区间不跨 0。
- 当前决定：Flat tuned 继续作为默认 benchmark；ModernBERT 保留为最均衡的 semantic baseline，不继续无差别增加端到端 backbone。
- 入口：`03_当前全部分类方法综合比较_zh.md` 与 `semantic_models/reports/2026-08-10--semantic-classification--r01--round-review.md`。
