# Task Plan: RL Personal Assistant 详细设计

## Goal

在不覆盖现有 classification、MAB、S-QSTN 产物的前提下，形成一份可直接指导后续实现、实验和论文写作的 RL personal assistant 详细设计。批准的路线为：基础 privacy/authorization rules 与 RL environment → Double DQN/PPO + binary reward → reward/constraints → security LLM → Constitutional AI + final LLM RL。

## Phases

- [x] Phase 1: 建立新目录、范围和研究合同框架
- [x] Phase 2: 审计现有项目设计、数据合同、结果与可复用资产
- [x] Phase 3: 核验关键算法、safe-RL、security critic 和 Constitutional AI 依据
- [x] Phase 4: 比较架构方案，冻结推荐分层与接口
- [x] Phase 5: 起草详细设计、实验矩阵、阶段门槛和实施顺序
- [x] Phase 6: 记录开放决策、默认假设、替代方案与讨论问题
- [x] Phase 7: 执行一致性、placeholder、可复现性和 fresh-reader 自检
- [x] Phase 8: 完成交付并进入用户审阅 gate

## Key Questions

1. 如何把 survey 四标签映射为 authorization ledger v0，同时不把 stated preference 误写成客观安全真值？
2. 哪些规则属于立即生效的 hard authorization boundary，哪些属于后续 security sub-agent/Constitution 的 learned principles？
3. 第一轮 0/1 reward 如何同时支持 MAB parity 与真正的 delayed-credit RL 检验？
4. Double DQN 与 PPO 如何在相同 observation、action、monitor 和 interaction budget 下公平比较？
5. S-QSTN 如何提供公开反馈而不泄露 private state、不自我验证、不夸大 human fidelity？
6. 何时才有资格从 shielded MDP 升级为 CMDP、security LLM 和 Constitutional LLM RL？

## Decisions Made

- 新目录固定为 `RL_Personal_Assistant_Design/`，不修改现有实验代码和正式结果。
- 主交付物为 `RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md`；`notes.md` 保存证据与审计轨迹。
- 用户已批准第一版简化 authorization ledger；设计默认采用 structured permission controller 与 support/security LLM 分层。
- 第一轮 deep-RL 候选是 masked Double DQN 与 masked PPO；是否最终保留两者由 matched baseline 结果决定。
- 第一轮不做 token-level LLM RL，不让 LLM 绕过 ledger/reference monitor。
- 现有 survey 数据用于 preference/parity 与 scenario seed，不被描述成自然连续交互轨迹，也不被描述成安全 ground truth。
- S-QSTN 只作为训练/开发阶段的一个版本冻结的反馈源；其 private state、rules 和 future labels 不进入 PA observation 或 reward。
- `necessity_status` 默认属于 evaluator/oracle-only 字段，不进入可部署 policy observation；只有显式 oracle-ablation 可使用。

## Errors Encountered

- 一次将四组网页检索合并的查询返回内容过长而被截断。处理：改为每次两组官方文档或四篇明确论文的小批查询，并将最终采用的证据重新核验。
- PowerShell 默认输出编码导致中文 `Get-Content` 在工具回显中出现 mojibake；源文件仍为 UTF-8。处理：后续校验显式设置 UTF-8，并以脚本级 UTF-8 读取检查标题和占位符。
- 一次根目录 `rg --files` 遇到 `classification_experiments/semantic_models/analysis/...` 的访问拒绝。处理：未绕过权限；改为对设计引用的已知文件做显式 `Test-Path`，10 个本地证据路径全部存在。

## Status

**Complete — awaiting user review.** 主设计约 3,206 行；新增了 §8.4.1–8.4.4 的结构化 observation JSON、S-QSTN 统计特征、时间顺序和禁止字段，并重新通过 UTF-8、代码围栏与占位符检查。下一 gate 是项目组确认主设计 §25–26 的关键默认值，之后再开始代码实现。
