# Task Plan: RL Personal Assistant 与循环验证风险设计

## Goal
形成一个有研究依据、可实现、可被 reviewer 审查的 RL personal assistant 总体框架，并设计阻断 PA–S-QSTN 循环验证、正确率漂移与 simulator exploitation 的实验协议。

## Phases
- [x] Phase 1: 建立计划并盘点已有 MAB、S-QSTN、RL 设计证据
- [x] Phase 2: 检索 user simulator、simulation validation、safe RL 与独立评估文献
- [x] Phase 3: 综合系统架构、训练边界、研究问题与实验矩阵
- [x] Phase 4: Devil's-advocate 审查循环验证风险并修订
- [x] Phase 5: 交付中文研究框架和最小实施路线

## Key Questions
1. RL personal assistant 应学习什么，哪些权限和安全判断必须由不可训练组件保证？
2. S-QSTN 如何提供训练反馈而不同时成为安全真值和最终评价者？
3. 如何证明策略提升不是 PA 与 S-QSTN 共适应、奖励黑客或分布漂移造成的假象？
4. 在当前只有静态问卷与 sequential-replay MAB 的条件下，最小可辩护的 RL 路线是什么？

## Decisions Made
- 将 structured permission controller RL 与自然语言 response-policy RL 分开。
- 将 S-QSTN 暂定为训练环境候选和压力测试器，不预设为最终安全裁判。
- 最终主张必须依赖冻结、独立、PA 不可访问的评估源。

## Errors Encountered
- None.

## Status
**Completed** - 已形成带研究问题、系统边界、反循环协议、实验矩阵、release gates、reviewer 质疑与实施顺序的中文设计稿。
