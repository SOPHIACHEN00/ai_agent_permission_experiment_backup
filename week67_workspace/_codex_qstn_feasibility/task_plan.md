# Task Plan: Simplified S-QSTN Feasibility

## Goal
判断能否将 Excel 中的 S-QSTN 规则先落地为 JSON/skill.md 形式，并以 human vs vanilla QSTN vs S-QSTN 的小规模实验支撑论文。

## Phases
- [x] Phase 1: Inspect local S-QSTN design and rule registry
- [x] Phase 2: Study the official QSTN repository and execution model
- [x] Phase 3: Map a minimal JSON/skill.md implementation to QSTN extension points
- [x] Phase 4: Assess the three-condition experiment and identify validity risks
- [x] Phase 5: Draft and verify the Chinese feasibility memo

## Key Questions
1. QSTN 的 agent、tool、permission/policy、memory 和评测接口分别在哪里？
2. 现有规则中哪些可以直接配置化，哪些需要程序状态或策略引擎？
3. 简化 S-QSTN 是否仍然能与 vanilla QSTN 做公平、可复现实验？
4. human vs vanilla QSTN vs S-QSTN 的小样本设计能回答什么、不能回答什么？

## Decisions Made
- 保留工作区已有的旧 `task_plan.md` 和 `notes.md`，本任务使用本目录独立记录。
- 优先使用 QSTN 官方 GitHub 仓库、README、源码和论文/官方文档作为证据。

## Errors Encountered
- 一次 PowerShell 汇总命令在 `for` 循环后直接接管道，产生空管道元素语法错误；改为先收集对象再格式化输出。

## Status
**Complete** - 已核对本地设计、Excel registry、现有 201 人/90 行 held-out 方案和 QSTN 官方源码；已形成 JSON + 外部 wrapper 的最小实现建议及 human/vanilla QSTN/S-QSTN 实验边界。
