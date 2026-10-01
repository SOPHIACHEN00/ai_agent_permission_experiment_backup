# Task Plan: Personal Assistant Agent RL 启动路线

## Goal
基于项目 profile、教授既定路线、已完成的 human-side simulator 与 MAB，形成可执行、可验收的 personal assistant agent 强化学习研究计划。

## Phases
- [x] Phase 1: 盘点工作区证据并定位 profile、教授路线、human simulator、MAB 与既有 RL 设计
- [x] Phase 2: 提炼约束、研究缺口、状态/动作/奖励/环境接口与风险
- [x] Phase 3: 设计分阶段 RL 路线、实验矩阵、里程碑和 Go/No-Go 门槛
- [x] Phase 4: 交叉审阅、校验与交付中文计划

## Key Questions
1. 教授路线对 personal assistant agent 的目标、研究顺序与论文贡献有哪些明确约束？
2. MAB 已经解决了什么，RL 必须新增什么“长期/序列决策”价值？
3. human-side simulator 能否直接作为训练环境；还缺哪些接口、校准和有效性验证？
4. 最小可行 RL（MVP）应选何种形式，何时升级到 POMDP/CMDP/离线或安全 RL？
5. 怎样定义能阻止 reward hacking、simulator exploitation 与无效实验的门槛？

## Decisions Made
- 使用任务专属三文件，避免覆盖工作区已有的通用 `task_plan.md` 与 `notes.md`。
- 冻结 WP-FTS/MAB 为教授 Step 2 的高层 permission baseline，不继续扩展 MAB 变体。
- 第一轮只实现 authority-aware deterministic environment、reference monitor、matched myopic baseline 与 DP/tabular smoke；不从端到端 token-level LLM RL 开始。
- S-QSTN v2 立即用于接口工程和 synthetic stress test；在 sequential calibration、sealed fidelity 与 policy-ranking gate 前，不作为 validated human-like RL feedback source。
- profile 仅作 soft preference prior；simulator 私有 trust/burden/profile state 不进入 PA observation、reward 或 replay buffer。
- assistant 不得自我授权：request→public authority feedback→validated ledger update→execute-with-auth。
- hard authorization invariants 由独立 reference monitor 处理；CMDP 只优化会产生非零信号的 residual exposure/prompt/fallback budgets。
- 长期价值用同 observation/action/monitor 的 `gamma>0` sequential policy 与 `gamma=0` matched myopic policy识别；legacy WP-FTS 只作历史/系统基线。
- 教授 Step 3 拆成 structured PA RL（3A）与 support-response LLM interaction RL（3B），再进入 security critic 与 Constitutional RL。

## Errors Encountered
- `git status --short` 报错“not a git repository”；根目录虽有 `.git` 目录，但不是可识别的 Git 工作树。本任务只需只读盘点与新增计划文件，不影响继续执行。
- 一次 Markdown QA 命令因 JavaScript template literal 与 Markdown backtick 冲突触发语法错误；改用普通引号/拆分命令后继续，不影响文件内容。

## Status
**Completed** - 证据盘点、方法/工程/证据三路交叉审阅、P0 修订和 Markdown QA 均已完成。
