# Task Plan: RL Personal Assistant 后续路线审计

## Goal

结合项目标书、已完成的 classification/MAB、现有 S-QSTN 与 RL 设计，判断“经典深度 RL + 暂用 0/1 reward + 后续 LLM fine-tuning + privacy rules 监管 + 最后调 reward”的流程是否方法ologically coherent，并提出可实施的修订路线。

## Phases

- [x] Phase 1: 建立审计范围、研究问题和工作文件
- [x] Phase 2: 核对项目标书、现有代码/设计与术语
- [x] Phase 3: 检索并核验经典 deep RL、safe RL、LLM-agent privacy/security 文献
- [x] Phase 4: 比较 2–3 条实施路线并进行 Devil's-Advocate 审查
- [x] Phase 5: 形成结论、算法建议、实验矩阵和阶段门槛
- [x] Round 2 / Phase 6: 核对新增研究概述、五张流程图与现有项目边界
- [x] Round 2 / Phase 7: 重新判定 Step 3–5 的模型角色、训练信号与阶段顺序
- [x] Round 2 / Phase 8: 给出更新后的流程结论与下一步决策点

## Key Questions

1. 当前任务是否真的需要 deep RL；若需要，DQN 与 Actor–Critic 分别适合什么环境合同？
2. MAB 的 0/1 reward 可以作为哪一层 baseline，不能支撑哪些安全与长期决策结论？
3. privacy/security rules 应在训练后“监管”，还是从环境、动作 mask、reference monitor、reward/cost 设计阶段就介入？
4. LLM fine-tuning 与 structured RL controller 的先后顺序如何安排，才能与标书的 Step 3–5 对齐？

## Decisions Made

- 把合作者所说的 “DWNS actor creative” 暂按最可能的 “DQN / Actor–Critic” 解释，并在结论中明确这是待确认术语。
- 把流程拆成“可行性 baseline”和“论文主方法”两层，避免用早期 0/1 reward 实验支撑过强安全主张。
- 新增材料中的图 1–2 属于 safe support-response 目标，图 3–5 属于 Constitutional response-level SFT/RM/RL；它们不直接规定 Step 3 permission-controller RL 的算法。

## Errors Encountered

- `tools.shell_command` 在本轮不可用；已改用 `exec_command`，不影响审计。
- `rg --files` 遍历一个 semantic-analysis 目录时遇到 access denied；目标项目文档和正式结果文件均可直接读取，因此不影响结论。

## Status

**Round 2 Complete** — 已完成新增概述/流程图审计，并重新冻结 Step 3 structured RL、Step 4 security critic、Step 5 Constitutional LLM RL 的边界。
