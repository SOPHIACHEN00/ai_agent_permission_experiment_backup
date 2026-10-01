# Task Plan: DistilBERT 分类资料集中整理

## Goal

在 `classification_experiments/` 下建立清晰、自包含的 `distilbert/` 子目录，将 DistilBERT 的设计文档、运行记录、分析报告、机器产物、服务器包和过程记录集中管理，并修复所有受影响的本地链接。

## Phases

- [x] Phase 1: 盘点全部 DistilBERT 相关文件、目录和引用关系
- [x] Phase 2: 设计目标目录结构和移动映射
- [x] Phase 3: 执行经验证的目录移动并建立 DistilBERT 总索引
- [x] Phase 4: 全局更新相对路径、文档链接与脚本中的默认引用
- [x] Phase 5: 核验文件数量、哈希、机器产物、Markdown 链接和测试

## Key Questions

1. 哪些文件是 DistilBERT 专属，哪些是多个分类模型共享、不能移动？
2. 如何保留主项目中的唯一 runner 源码，避免产生两份会分叉的 canonical code？
3. 移动 artifacts、analysis 和 server package 后，哪些 Markdown 或脚本路径必须同步更新？

## Decisions Made

- 主项目 `ai_agent_permission_experiment/src/run_distilbert_four_label.py` 保持为唯一 canonical runner；新目录只通过链接引用，不复制一份长期维护副本。
- 所有移动必须在执行前解析并验证源/目标都位于当前 workspace，不覆盖现有文件。
- 机器产物内容不做重写；移动前后用 SHA-256/文件数量核验。
- 目标根目录采用 `classification_experiments/distilbert/`，其下按 `design/`、`runs/`、`analysis/`、`artifacts/`、`pilot/`、`scripts/`、`server_packages/` 和 `maintenance/` 分区。
- 根级 README、经典 LR 模型文档、共享数据、共享调参产物与主项目 tests 留在原位；它们只是引用 DistilBERT，不属于 DistilBERT 专属资料。

## Errors Encountered

- 第一次重跑 runner tests 时误用了经典 LR 的 `.venv`；该环境按设计没有 PyTorch，因此在 import 阶段失败。改用系统 PyTorch，并临时只读加载项目 `.venv` 的 sklearn/scipy/pandas 后，7 项测试全部通过。该失败与代码或目录迁移无关。

## Status

**Completed** - DistilBERT 专属资料已集中到 `classification_experiments/distilbert/`；移动完整性、链接、脚本 CLI 和 runner tests 均已核验。
