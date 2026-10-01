---
title: "S-QSTN 20 用户画像：Gemini 0-shot / 4-shot、fold 0 小实验记录"
experiment_id: "APA-ICL-260926-001"
date: 2026-09-26
status: completed
project: Agent Auto Permission
experiment_type: synthetic_persona_icl_baseline
run_id: pilot20_seed20260926_o4mini_gemini_fold0_schema_v1
generator: o4-mini-2025-04-16
predictor: google/gemini-3.8-flash
participants: 20
history_permission_rows: 350
test_permission_rows: 274
conditions: [0-shot, 4-shot]
fold: 0
fold_seed: 42
shot_seed: 20260925
participant_selection_seed: 20260926
total_tracked_cost_usd: 1.17105605
tags: [experiment-log, agent-permission, sqstn, icl, baseline]
---

# S-QSTN 20 用户画像 ICL 小实验记录

## 1. 本轮目的与状态

**目的：** 做一个简单的经典 ICL baseline，观察 Gemini 在看到某个模拟用户的四个已回答场景后，能否更准确地预测该用户在其他场景中的四选一权限决定。

**状态：已完成。** 624 条模拟回答已冻结，0-shot 与 4-shot 各 274 条测试预测已保存。本日志记录已有结果和后续与真人数据的对照；写入日志没有新增模型调用。

## 2. 数据来源与数量口径

来源是 S&P 作者公开数据中原 40 人 Gemini pilot 的固定 20 人子集。按画像类型预先选择，选择不依据模型成绩：长期允许型 7 人、再次询问型 10 人、偏向拒绝型 3 人。

参与者：P012、P015、P031、P032、P033、P040、P053、P055、P057、P073、P082、P103、P120、P125、P143、P144、P167、P174、P179、P183。

| 口径 | S&P 同一 20 人 | S-QSTN 本轮 20 个画像 |
|---|---:|---:|
| 对应用户在源数据中的全部真人回答 | 1,628 | 同一份 1,628 条来源数据 |
| 本轮历史：每人 4 个场景 | 350 条真人答案 | 350 条生成答案 |
| 本轮测试：每人 4 个场景 | 274 条真人答案 | 274 条生成答案 |
| 本轮实际使用的历史＋测试 | 624 条 | 624 条 |
| 覆盖的不同权限项 | 250 | 250 |

**口径澄清：1,628 是来源数据总量；624 是本轮选中的权限记录数。** 两条路线实际使用相同的 624 个用户×权限项，差别是答案来源。其余 1,004 条真人记录未用于本轮 ICL 历史或测试，本轮也未生成其对应模拟答案。此说明不意味着画像构建阶段从未利用过其他真人记录。

一个 shot 是一个完整 query，可能包含多项权限判断；因此 4-shot 不等于四条权限回答。20 是本次 pilot 的选样规模，不是 S-QSTN 的技术上限。

## 3. 固定实验方案

| 设置 | 本轮值 |
|---|---|
| 数据划分 | 用户内部按完整 query 分成 5 折，仅使用 fold 0；seed 42 |
| 历史选择 | 保留旧实验每人的四个历史 query，shot seed 20260925 |
| 用户选择 | seed 20260926，固定三类画像配额 |
| 生成模型 | OpenAI `o4-mini`；实际返回 `o4-mini-2025-04-16` |
| 模拟器资产 | QSTN 0.5.1、empirical profile cards v2、RulePack 2.0.0 |
| 生成设置 | low reasoning、4,096 completion token 上限、seed 42、并发 4；原生四选项 JSON schema |
| 模拟状态 | 每个权限项重新建立空记忆；events 为空、turn=0，不更新跨题状态 |
| 冻结顺序 | 先生成并冻结全部 624 条答案，再进行两组预测 |
| 预测模型 | OpenRouter `google/gemini-3.8-flash` |
| 预测设置 | 原 ICL prompt、low reasoning、8,000 token 输出上限；每人每条件一次调用 |
| 两个条件 | 0-shot：无历史；4-shot：四个场景的模拟历史答案 |
| 预测器信息 | 公开背景、历史场景及答案、待预测请求；不含测试答案、隐藏画像卡、RulePack 或内部状态 |
| Output | 每个权限项的四分类 label 与自报 confidence；后者未经校准 |
| 参数训练 | 无模型权重更新 |

实际四个标签为：`0=No, never share`；`1=No, but ask me next time`；`2=Yes, but ask me next time`；`3=Yes, always share`。

生成器与预测器的信息不同：生成器使用 8 项结构化背景、画像卡及规则条件；Gemini 使用原 baseline 的 10 项背景字段，包括 AI 用途和隐私顾虑文字。两条数据路线中的 Gemini 模板一致。

## 4. 主要结果

所有点估计按合并的 274 条权限记录计算；Macro-F1 固定包含四类。

| 指标 | 0-shot | 4-shot | 变化 |
|---|---:|---:|---:|
| 正确预测 | 152/274 | 203/274 | +51 条 |
| Accuracy | 55.47% | 74.09% | +18.61 个百分点 |
| Macro-F1 | 0.4568 | 0.5845 | +0.1278 |
| QWK | 0.5428 | 0.7233 | +0.1805 |
| 错误允许率 | 36.59%（15/41） | 36.59%（15/41） | 0 个百分点 |
| 错误永久允许率 | 33.64%（72/214） | 13.08%（28/214） | −20.56 个百分点 |

错误允许率：truth 为任一种 No 时，预测成任一种 Yes 的比例。错误永久允许率：truth 不是永久允许时，预测成永久允许的比例。

采用 1,000 次参与者聚类配对 bootstrap，seed 20260926。4-shot 减 0-shot 的 95% 百分位区间：Accuracy 为 [+7.89, +31.56] 个百分点；Macro-F1 为 [+0.0506, +0.2167]；错误允许率为 [−8.82, +10.53] 个百分点；错误永久允许率为 [−40.18, −2.06] 个百分点。区间仅针对本批固定画像、标签和预测，不包含重新生成标签或更换 fold/示例的变异。

### 按画像类型观察

| 类型 | 用户 / 测试记录 | 0-shot Accuracy | 4-shot Accuracy | 错误允许数量 |
|---|---:|---:|---:|---:|
| 长期允许型 | 7 / 106 | 54.72% | 57.55% | 2/11 → 4/11 |
| 再次询问型 | 10 / 133 | 57.89% | 90.98% | 2/15 → 1/15 |
| 偏向拒绝型 | 3 / 35 | 48.57% | 60.00% | 11/15 → 10/15 |

净增加的 51 条正确预测中，44 条来自再次询问型。长期允许型的错误永久允许从 19/46 增至 28/46，因此不能将总体分类提升概括为所有类型的权限风险都改善。

## 5. 与真人结果的对照

同一 20 人的真人结果由已完成的 40 人/201 人运行提取，未重新调用模型。双方历史与测试 query 清单、274 个测试权限上下文完全一致，答案来源不同。

| 数据与条件 | 测试记录 | Accuracy | Macro-F1 | 错误允许率 | 错误永久允许率 |
|---|---:|---:|---:|---:|---:|
| S&P 全部 201 人，4-shot | 3,123 | 62.82% | 0.5451 | 42.48% | 14.86% |
| S&P 同一 20 人，4-shot | 274 | 66.79% | 0.5225 | 45.00% | 11.45% |
| S-QSTN 20 人，4-shot | 274 | 74.09% | 0.5845 | 36.59% | 13.08% |

同一 274 项测试 truth 的标签 0/1/2/3 数量：真人为 20/20/126/108；模拟为 12/29/173/60。**74.09% 与 66.79% 不对应相同标准答案，不能将差值写成同一预测任务上的方法提升。** 真人 20 人和 201 人在本轮均没有对应 0-shot 对照。

## 6. 费用与异常记录

| 项目 | USD |
|---|---:|
| o4-mini：624 次成功生成，token 估算 | 1.03926900 |
| 初始一次 JSON 格式失败，token 估算 | 0.00260480 |
| Gemini：20 次 0-shot，提供方返回费用 | 0.06020925 |
| Gemini：20 次 4-shot，提供方返回费用 | 0.06897300 |
| 合计 | **1.17105605** |

共 664 次成功调用与 1 次失败尝试，总费用低于原 $8 上限。费用不含前期画像构建、其他模型筛选或真人问卷采集成本。

**异常与处理：** 初次调用仅使用 `json_object`，模型将合法选项放在 `permission` 键，严格的 `answer` 解析器拒绝了该响应。补齐 QSTN 原生 JSON schema 后，在当前 `_schema_v1` 运行目录重新生成该项。原失败记录保留并计费一次，其答案没有复用；随后 624 次生成与 40 次预测均完成。

**记录口径修正：** 初始对比表将“1,628 条已有真人回答”和“624 条本轮模拟回答”放在同一行，容易误读为实验样本量不同。现已统一为“来源总量”与“本轮使用量”两行；未改变样本、标签或预测结果。

## 7. 当前结论与使用范围

本轮支持的结论：在这批固定模拟用户上，四个历史场景提高了总体分类表现，并减少错误永久允许；错误允许数量没有减少，收益主要来自再次询问型画像。

本轮定位为简单的 **Synthetic-persona ICL baseline / pilot**。三种画像是行为倾向描述；生成器使用静态逐项状态。画像 discovery 的真人回答划分与 ICL fold 0 不同，可能间接使用 fold-0 真人信息，因此不能将本结果作为无泄漏的真人还原验证，也不能声称真实时间序列上的长期适应。

后续若需量化 ICL 对真人的增益，可在相同真人测试记录上补 0-shot；本次仅记录已有实验，没有启动后续实验。

## 8. 原始材料与追溯入口

完整冻结运行目录：`ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1`。

- [完整结果报告](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/REPORT_zh.md)
- [S-QSTN 与 S&P 全面对比](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/COMPARISON_zh.md)
- [精确配置与来源哈希](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/run_config.json)
- [用户与场景清单](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/job_manifest.json)
- [冻结模拟答案](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/synthetic_answers.csv)
- [0-shot 逐项预测](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/predictions_0shot.csv)
- [4-shot 逐项预测](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/predictions_4shot.csv)
- [配对 bootstrap](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/paired_bootstrap.json)
- [费用账目](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/cost_accounting.json)
- [最终完整性审计](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1/final_audit.json)
- [真人与模拟数值汇总](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/comparison_summary.json)

准确生成/预测提示、原始响应、token 用量、冻结哈希、画像选择及格式修复来源均保留在上述运行目录。本日志仅作为标准化入口，原始实验记录不移动、不重写。
