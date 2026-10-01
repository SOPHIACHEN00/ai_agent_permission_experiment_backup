# Task Plan: S&P 经典分类实验盘点与调参

## Goal
还原 `external` 中 S&P 原始数据到经典分类任务的完整处理链，核实 Flat、Ordinal 与 Factored 三类模型的实现和结果，在可比且可复现的前提下补充调参，并建立可持续维护的中文实验文档。

## Phases
- [x] Phase 1: 建立任务计划与证据记录目录
- [x] Phase 2: 盘点仓库结构、数据处理脚本、模型代码与结果产物
- [x] Phase 3: 复现现有 Logistic Regression 实验并核对评价协议
- [x] Phase 4: 对已实现模型进行有边界的调参和严格比较
- [x] Phase 5: 编写分类实验中文文档、复核链接与结论
- [x] Phase 6: 实现并运行 DistilBERT 四分类语义 baseline，完成 RTX 3090 follow-up、配对分析与文档回填
- [x] Phase 7: 完成 RoBERTa、DeBERTa、ModernBERT 正式 GPU runs，回收归档、配对分析并形成全部方法综合比较

## Key Questions
1. `external` 中哪份 S&P 原始数据被转换成了哪些特征、标签与训练/验证/测试划分？
2. Flat four-class Logistic Regression、Ordinal Logistic Regression、Factored Model 是否都已实现？具体变体和超参数是什么？
3. 现有结果使用了哪些指标、随机种子和数据切分；是否存在数据泄漏或不可比之处？
4. 在相同评价协议下，合理调参能否带来稳定改进？
5. 如何组织文档，便于后续追加新的经典分类基线？

## Decisions Made
- 保留根目录已有的上一任务计划；本任务全部工作记录放入 `classification_experiments/`。
- 先复现和核实原始实验，再做调参；不把不同切分或特征条件下的分数直接比较。
- 若缺少多随机种子/折级结果，只报告描述性结果，不虚构显著性结论。
- 以 `participant_heldout` 作为主协议；`row_stratified` 因同一参与者同时出现在训练和测试中，仅作为较乐观的补充结果。
- 调参固定原外层 test，不读取 test 选参；只在外层 train 内交叉验证，以 macro-F1 为主目标，并同时报告 QWK 与过度授权风险。
- 原 `results/tuning/flat_lr_tuning_*.csv` 缺少独立 validation 证据，视为探索性 test-sweep，不作为无偏“最佳参数”结论。

## Errors Encountered
- Week67 根目录不是有效的 Git 工作树，无法用根目录 `git status` 审计改动；`external/ai-agent-permissions` 子仓库已单独确认干净。
- 当前项目环境没有 `matplotlib`；分析图改用已可用的 ReportLab 生成 PDF。
- ReportLab 的直接 PNG 后端缺少 `rlPyCairo/_rl_renderPM`；改为先输出 PDF，再用 `pypdfium2` 渲染 PNG，并完成目视检查。
- 调参脚本在完整运行后补加了输出目录与 CV 输入保护，因此当前文件哈希不同于运行时哈希；已保存与 `run_config` 哈希完全一致的运行时源码快照和 manifest。

## Status
**Completed** - 数据链、三种 Logistic 模型、基线复现、train-only 调参、DistilBERT 与三种新 Transformer 语义 baseline、participant-paired 统计核查、中文综合报告与链接检查均已完成。当前默认 benchmark 仍是 tuned Flat LR；ModernBERT 作为最均衡的 semantic baseline 保留。
