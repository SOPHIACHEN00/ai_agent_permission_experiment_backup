# Task Plan: PA–S-QSTN 闭环漂移缓解文献研究

## Goal

基于核验过的原始论文，形成一套可映射到本项目的闭环误差累积与长期状态漂移缓解方案，并区分可立即实施、需真人校准和仅作研究消融的措施。

## Phases

- [x] Phase 1: Plan and setup
- [x] Phase 2: Multi-source literature search and source verification
- [x] Phase 3: Synthesize mechanisms and map them to the current experiment
- [ ] Phase 4: Produce and review the final research brief

## Key Questions

1. 双向/多智能体在线学习的非平稳性与振荡如何缓解？
2. user simulator / model-based RL 的 compounding error 与 policy exploitation 如何检测和约束？
3. preference learning 中的 performative feedback、selection bias 与偏好漂移如何处理？
4. permission ledger、shield、OOD 与真人 policy-ranking 如何形成独立安全防线？
5. 哪些方法最适合当前 WP-FTS、S-QSTN v2 与未来 shielded CMDP？

## Decisions Made

- 使用 `nature-academic-search` 的 `multi-source-search` 工作流；学术搜索 MCP 不可用时，按技能规则转用论文官方 proceedings、期刊页与 arXiv 原始预印本。
- 采用四条检索线：耦合在线学习、learned-environment/model-based RL、动态偏好与因果识别、safe RL 与外部评估。
- 仅用原始论文支撑关键方法主张；博客、媒体与二手综述未进入证据矩阵。
- 用标题、DOI/arXiv ID 与作者年份去重；同一工作优先保留正式会议/期刊版本。
- 将措施分为 P0 主实验前硬门、P1 推荐增强和 P2 sandbox 研究项。
- 最终协议遵循“训练可用 simulator，验证必须有 simulator 外部锚点”。

## Errors Encountered

- Academic-search MCP 未在当前工具集中提供；已记录并使用官方原始论文页面完成检索。
- AAAI OJS 的 shielding 页面一次返回 502；通过官方 DOI/论文元数据交叉核验，未依赖二手来源。

## Status

**Currently in Phase 4** — 写作并复核最终研究简报、文献证据矩阵与本项目实施清单。
