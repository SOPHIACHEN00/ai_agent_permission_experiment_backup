# Semantic classification experiments

这个目录以同一四标签权限数据上的非 DistilBERT 语义分类实验为主，同时提供一份包含 DistilBERT 的跨语义模型原理与结果速查。

## 当前状态

- 已选定 RoBERTa-base、DeBERTa-v3-small、ModernBERT-base。
- 已实现通用 Transformer fine-tuning runner 和独立 RTX 3090 服务器包。
- 三个 RTX 3090 正式 run 均已完成、下载、逐行复算并与 tuned Flat LR 对齐。
- 当前结论：没有一个新 backbone 在 Macro-F1 上超过 Flat LR；ModernBERT 是三个模型中最均衡的 semantic baseline。

## 入口

1. [语义分类模型介绍与当前结果对比](语义分类模型介绍与结果对比_zh.md)
2. [中文实验设计](experiment_design_zh.md)
3. [本轮中文正式报告](reports/2026-08-10--semantic-classification--r01--round-review.md)
4. [严格分析报告](analysis/semantic_backbones_20260810/analysis-report.md)
5. [统计附录](analysis/semantic_backbones_20260810/stats-appendix.md)
6. [全部模型指标 CSV](analysis/semantic_backbones_20260810/all_model_metrics.csv)
7. [配对 participant bootstrap CSV](analysis/semantic_backbones_20260810/semantic_vs_flat_lr_bootstrap_summary.csv)
8. [三个完整 server returns](artifacts/server_returns/)
9. [三个原始返回归档](artifacts/archives/)
10. [可复现分析脚本](scripts/analyze_semantic_backbones.py)
11. [工作计划](task_plan.md)与[核查笔记](notes.md)
12. [RTX 3090 上传包说明](server_packages/semantic_nlp_rtx3090_20260810/README_zh.md)

原始服务器归档保留其生成时路径与 source snapshot；不要手工修改。`results_without_model` 不包含 final checkpoint，但包含预测、配置、日志、模型锁和运行源码。
