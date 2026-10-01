# DistilBERT 四分类语义基线

本目录集中保存 S&P 四标签权限分类任务中与 DistilBERT 有关的全部耐久资料：实验设计、RTX 3090 运行记录、严格对照分析、CSV/JSON/图表、机器产物、pilot 日志、分析脚本和服务器运行包。

## 当前结论

当前 DistilBERT Flat 是一个**已完成但未超过 Logistic Regression 的负面语义 baseline**。它直接把相同任务信息序列化为英文文本，端到端微调 `distilbert-base-uncased` 的四分类 head；没有在 DistilBERT 后再单独接 sklearn LR。

主测试协议仍是固定的 `participant_heldout`：160 名参与者训练、41 名新参与者测试，参与者不重叠；但测试中的 query/context 在训练中出现过，因此这里只比较“新用户、已见场景”。

| 模型 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Tuned Flat LR | **0.409269** | **0.370655** | **0.315495** | **0.425708** | **0.210433** |
| DistilBERT 首个 GPU run | 0.368643 | 0.327932 | 0.238761 | 0.505896 | 0.395225 |
| DistilBERT max-5 follow-up | 0.388203 | 0.335093 | 0.252939 | 0.545991 | 0.438550 |

Follow-up 最多允许 5 epochs，但 validation 在 epoch 1 后持续下降，early stopping 于第 3 个 epoch 触发，最终模型实际重训 1 epoch。它是在看过首轮 frozen-test 结果后进行的 exploratory/test-touched follow-up，不能当成新的无偏 final。

相对 tuned Flat LR，follow-up 的 Macro-F1 差值为 `-3.56` 个百分点，participant-paired bootstrap 95% CI 为 `[-7.30,+0.24]`；Over-sharing 与 Persistent-over-allow 分别恶化 `+12.03` 和 `+22.81` 个百分点，且两个区间均不跨 0。当前继续保留 tuned Flat LR 作为主要经典 baseline，不再仅靠增加 DistilBERT epochs 调参。

## 建议阅读顺序

1. [设计、输入序列化与训练协议](design/004_distilbert_four_class_finetuning_zh.md)
2. [两次 RTX 3090 运行与结果决定](runs/2026-08-10_distilbert_rtx3090_finetuning_zh.md)
3. [严格配对分析报告](analysis/distilbert_epoch5_codex_20260810/analysis-report.md)
4. [统计附录](analysis/distilbert_epoch5_codex_20260810/stats-appendix.md)
5. [图表目录](analysis/distilbert_epoch5_codex_20260810/figure-catalog.md)

机器可读的核心结果：

- [首个 GPU run 测试指标](artifacts/distilbert_rtx3090_run1/test_metrics.csv)
- [Follow-up 测试指标](artifacts/distilbert_rtx3090_epoch5_codex_20260810/test_metrics.csv)
- [5,000 次 participant-paired bootstrap 摘要](analysis/distilbert_epoch5_codex_20260810/paired_cluster_bootstrap_summary.csv)
- [逐类指标](analysis/distilbert_epoch5_codex_20260810/per_class_metrics.csv)

## 目录说明

```text
distilbert/
├─ README.md
├─ design/             # 模型与实验设计
├─ runs/               # 人类可读的正式运行总结
├─ analysis/           # 报告、统计附录、CSV、PNG/PDF
├─ artifacts/          # 完成 run、smoke/中断 run 与传输归档
│  └─ archives/
├─ pilot/              # 本地 CPU pilot 的计划、笔记与日志
├─ scripts/            # DistilBERT 专用结果分析脚本
├─ server_packages/    # RTX 3090 自包含上传包与 ZIP
└─ maintenance/        # 本次整理的计划和完整性清单
```

`artifacts/` 中每个 run 自带当次实际使用的 `source/run_distilbert_four_label.py` 快照；这些快照用于审计，不应覆盖或去重。服务器包也保留部署时的 runner 副本。

## Canonical 代码与共享依赖

长期维护的唯一训练入口仍在主项目：

- [Canonical DistilBERT runner](../../ai_agent_permission_experiment/src/run_distilbert_four_label.py)
- [Runner 单元测试](../../ai_agent_permission_experiment/tests/test_run_distilbert_four_label.py)
- [本地 DistilBERT 依赖记录](../../ai_agent_permission_experiment/requirements-distilbert.txt)

分析脚本位于 [scripts/analyze_distilbert_results.py](scripts/analyze_distilbert_results.py)。它与 tuned Flat LR 的共享对照产物配合使用；LR 对照仍保留在 `classification_experiments/artifacts/nested_tuning_20260809/`，没有搬入本目录。

## 服务器包与历史运行

- [RTX 3090 服务器包说明](server_packages/distilbert_rtx3090_20260809/README_zh.md)
- [可上传 ZIP](server_packages/distilbert_rtx3090_20260809.zip)
- [首个完成 run](artifacts/distilbert_rtx3090_run1/)
- [Max-5 follow-up](artifacts/distilbert_rtx3090_epoch5_codex_20260810/)
- [本地 pilot 过程记录](pilot/notes.md)

历史 `run_config.json`、日志、分析 manifest 和统计附录中的绝对路径记录的是**生成当时的位置**，为保留 provenance 没有重写；当前可用位置以本 README 的链接为准。

## 整理完整性

本次集中整理前，对 91 个耐久文件记录了源路径、目标路径、字节数和 SHA-256；移动后逐项核验为 `91/91` 目标存在、`0` 哈希或大小不一致、`0` 源文件残留。

- [迁移前完整性清单](maintenance/pre_move_integrity_manifest.csv)
- [整理完成后的当前文件清单](maintenance/current_file_manifest.csv)
- [整理任务计划](maintenance/task_plan_distilbert_folder_reorg.md)
- [整理核验笔记](maintenance/notes_distilbert_folder_reorg.md)
