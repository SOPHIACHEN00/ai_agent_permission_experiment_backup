# S-QSTN 与 S&P 真人数据：4-shot ICL 全面对照

日期：2026-09-26。根据本地已完成、已冻结的实验记录整理；本次仅做本地统计，新增模型调用为 0。

## 1. 对照范围与核心区别

两条路线使用相同的 Gemini ICL 预测方法，但历史答案与测试标准答案的来源不同：

- **S&P 真人路线：** 公开用户背景 + 真人历史回答 → Gemini → 预测未展示的真人回答。
- **S-QSTN 模拟路线：** 用户背景 + 固定画像卡 + 规则 + 场景 → o4-mini 生成并冻结回答；公开用户背景 + 模拟历史回答 → Gemini → 预测未展示的模拟回答。

本报告保留 S&P 全部 201 人作为总体参照，同时提取与模拟实验完全对应的 20 人真人子集。该子集直接复用已完成的预测，并非另跑一次实验。

| 维度 | S&P 原始真人数据路线 | S-QSTN 模拟数据路线 |
|---|---|---|
| 回答者 | 原论文用户研究中的真人 | o4-mini 按固定 persona 回答 |
| 场景来源 | 作者公开的请求、工具与数据类型 | 沿用同一公开数据中的请求、工具与数据类型 |
| 用户背景 | 作者公开的匿名问卷背景 | 沿用选定真人的公开背景，附加行为画像卡 |
| 标签来源 | 真人实际四选一回答 | o4-mini 生成的四选一回答 |
| 数据生成阶段 | 已有公开数据，无需本轮生成 | 额外运行 S-QSTN，先生成历史和测试答案并冻结 |
| 画像类型 | ICL 不需要预先给真人分类型 | 使用已有三类倾向卡：长期允许、再次询问、偏向拒绝 |
| 预测模型 | `google/gemini-3.8-flash`，OpenRouter | 相同 |
| 生成模型 | 不适用 | 配置 `o4-mini`；返回 `o4-mini-2025-04-16` |
| 研究问题 | 四个真人历史场景能否帮助预测其其他回答 | 四个模拟历史场景能否帮助预测该固定模拟画像的其他回答 |
| 结果所指向的对象 | 这批真实参与者 | 这套生成器、画像与规则产生的模拟用户 |

S-QSTN 现有画像池有 201 行，本轮只抽取 20 行进行 pilot；20 不是模拟器的技术上限。每行由该参与者的背景和三类之一的画像卡构成，不等于训练了 20 个独立模型，也不等于只有三个相同用户。

## 2. Input、处理方式与信息边界

| 阶段 | S&P 真人路线 | S-QSTN 模拟路线 |
|---|---|---|
| 基础输入 | 公开用户问卷和真实权限回答，整理为统一 CSV | 同一 CSV 中的用户和场景，映射为 questionnaire item 与 persona |
| 基本记录单位 | 一名用户对一个 query 下一个 tool × raw data type 的回答 | 一个 persona 对同一权限项的生成回答 |
| 数据整理 | 保留 participant、query、tool、data type、背景、标签；统一四标签编码 | 匹配场景、规范化文本空白、连接 context sidecar；生成提示前移除当前记录的真人答案 |
| Gemini 背景输入 | 年龄段、性别、教育、AI 熟悉度、使用频率、用途、信任、隐私重要性、隐私顾虑文字、concern_domain，共 10 项 | 相同函数、相同字段；同一用户的背景保持一致 |
| Gemini 历史输入 | 四个完整 query 及其中全部真人权限回答 | 同样四个完整 query，答案替换为冻结的模拟回答 |
| Gemini 待预测输入 | query 文本、工具、raw data type；待预测答案为 `null` | 相同 |
| Gemini 额外标签或规则 | 不输入测试答案、必要性标注、隐藏画像卡 | 同样不输入；不输入 `profile_id`、RulePack 或生成器内部状态 |
| 生成器背景输入 | 不适用 | 8 个结构化背景字段；不含 AI 用途和隐私顾虑自由文本，年龄保留类别编码 |
| 生成器额外输入 | 不适用 | empirical profile card v2、RulePack 2.0.0、由 domain/data type/necessity 等 context 激活的定性规则 |
| 生成粒度 | 已有真人逐项回答 | QSTN 0.5.1 原生单项提示；一次生成一个权限项 |
| 跨轮状态 | ICL 历史来自已收集的回答 | 每项重新建立空记忆、无事件、turn=0；本轮不模拟跨轮状态演化 |
| 答案冻结 | 已有固定真人标签 | 全部 624 个答案完成并冻结后，才开始 Gemini 预测 |
| 模型训练 | 无权重更新；将示例放入 prompt | 相同，无权重更新 |

**信息边界需要区分：两条路线中的 Gemini 输入模板一致；S-QSTN 生成器与 Gemini 预测器的背景字段和规则信息并不完全一致。** 生成器能利用必要性等 context 激活规则；Gemini 只从请求文本、工具与数据项推断。

预测输入的共同结构为：公开背景 + 历史 query 列表 + 待预测 query 列表。历史 query 带每个权限项的答案，测试 query 中对应位置留空。一个完整场景可能有多条权限项，因此一个 shot 不等于一条 CSV 记录。

## 3. 数据量：总体与相同 20 人对照

| 数据量或覆盖范围 | S&P 全部 201 人 | S&P 对应 20 人子集 | S-QSTN 本轮 20 个画像 |
|---|---:|---:|---:|
| 用户 / persona 数 | 201 | 20 | 20 |
| 对应用户在 S&P 源数据中的真人回答总数 | 16,361 | 1,628 | 1,628，同一批 20 人的来源数据 |
| 本轮新增生成的模拟回答 | 0 | 0 | 624 |
| 每人历史场景数 | 4 | 4 | 4 |
| 每人测试场景数 | 4 | 4 | 4 |
| 用户 × 历史场景数 | 804 | 80 | 80 |
| 用户 × 测试场景数 | 804 | 80 | 80 |
| 实际使用的历史权限回答 | 3,256 | 350 | 350 |
| 实际评测的测试权限回答 | 3,123 | 274 | 274 |
| 历史 + 测试权限回答 | 6,379 | 624 | 624 |
| 历史与测试合计覆盖的不同 query ID | 65 | 56 | 56 |
| 历史与测试合计覆盖的不同权限项 | 371 | 250 | 250 |
| 测试覆盖的不同 query ID | 30 | 21 | 21 |
| 测试覆盖的不同权限项 | 147 | 89 | 89 |
| 0-shot 对照 | 本次未跑 | 本次未跑 | 已跑，274 条预测 |
| 4-shot 预测输出行数 | 3,123 | 274 | 274 |

“不同权限项”按 query × tool × raw data type 去重；“权限回答”还包含用户维度。因此，20 个画像的 624 条回答对应 250 个不同权限项，不能写成 624 道互不相同的问题。

同一批 20 人的来源数据始终是 1,628 条真人回答。此次从中选取四个历史场景和四个测试场景，共 624 条权限记录：真人路线使用这 624 条记录已有的真人答案；模拟路线针对完全相同的记录生成 624 个模拟答案。其余 1,004 条真人记录未用于本轮 ICL 历史或测试，也未在本轮生成对应模拟答案。1,628 是来源数据总量，624 是本轮选中记录数，不能把两者作为真人与模拟的数据量差异。

完整公开数据共有 65 个 query、373 个不同权限项、16,361 条已观察真人回答。潜在的“201 人 × 373 项”并不是已收集的真人数据。201 人全量实验指覆盖所有有效用户，实际向 Gemini 提供的历史答案为 3,256 条，并未把全部 16,361 条答案作为上下文。

20 人从原 40 人 Gemini pilot 的用户池按画像类型抽取，选择种子 20260926，配额为长期允许型 7 人、再次询问型 10 人、偏向拒绝型 3 人；不按预测成绩选人。三类是回答倾向描述，不是经过验证的心理人格类型。

## 4. 实验设置与 Output

| 项目 | S&P 真人路线 | S-QSTN 模拟路线 |
|---|---|---|
| 划分单位 | 每位用户内部按完整 query 划分 | 沿用该用户原来的完整 query 划分 |
| fold | 5 折划分中的第 0 折，seed 42；仅运行这一折 | 相同 |
| 历史选例 | 从非测试 query 中固定选 4 个，shot seed 20260925 | 沿用相同 4 个 query |
| 历史与测试是否混入同一 query | 同一用户内不混入 | 相同 |
| 是否是真实时间序列预测 | 否；是打乱后的场景留出 | 否；相同划分，生成器也无跨轮状态 |
| Gemini reasoning / 输出上限 | low / 8,000 tokens | 相同 |
| Gemini 调用粒度 | 一名用户一次调用，批量预测其四个测试 query | 相同；0-shot 与 4-shot 各一次 |
| 生成器调用设置 | 不适用 | low reasoning、4,096 completion tokens、seed 42、并发 4 |
| 生成器 Output | 已有真人答案 | JSON 中的 `answer`，取四标签之一 |
| Gemini Output | 每个权限项的预测 `label` 与 0–1 `score` | 相同 |
| 评测 truth | 真人回答 | 冻结的模拟回答 |
| 最终文件 | 配置、题目清单、逐项预测、指标、混淆矩阵、checkpoint、费用 | 另有 persona 清单、逐项模拟答案、冻结哈希、生成提示和响应、0/4-shot 配对结果 |

这里应写 **4-shot、fold 0**，而不是“0 折交叉验证”。本轮只评测第 0 折，没有进行完整 5 折平均。Gemini 的 `score` 是模型自报置信度，本轮未校准，不能当作用户选择概率。

四个实际标签在两条路线完全一致：

| 编码 | 实际存储及调用字符串 | 中文含义 |
|---|---|---|
| 0 | `No, never share` | 拒绝，今后不再分享 |
| 1 | `No, but ask me next time` | 本次拒绝，下次再问 |
| 2 | `Yes, but ask me next time` | 本次允许，下次再问 |
| 3 | `Yes, always share` | 允许，并记住长期允许偏好 |

用户界面可以采用 “Always Allow”等展示名称，实验中使用上表的精确字符串。

## 5. 已有结果

所有指标以合并后的测试权限记录计算；不是每位用户指标的等权平均。Macro-F1 固定包含四类，QWK 使用编码 0–3 的顺序与平方权重。

| 指标 | S&P 201 人 4-shot | S&P 对应 20 人 4-shot | S-QSTN 20 人 0-shot | S-QSTN 20 人 4-shot |
|---|---:|---:|---:|---:|
| 测试权限记录 | 3,123 | 274 | 274 | 274 |
| 正确预测数 | 1,962 | 183 | 152 | 203 |
| Accuracy | 62.82% | 66.79% | 55.47% | 74.09% |
| Macro-F1 | 0.5451 | 0.5225 | 0.4568 | 0.5845 |
| QWK | 0.5590 | 0.6474 | 0.5428 | 0.7233 |
| 错误允许率 | 42.48%（274/645） | 45.00%（18/40） | 36.59%（15/41） | 36.59%（15/41） |
| 错误永久允许率 | 14.86%（282/1,898） | 11.45%（19/166） | 33.64%（72/214） | 13.08%（28/214） |

- 错误允许率：truth 属于两种 No，但预测为任一种 Yes；分母为所有 truth=No 的记录。
- 错误永久允许率：truth 不是 Yes, always share，但预测为该标签；分母为所有 truth≠3 的记录。
- 两项指标分母不同，也会随真人/模拟 truth 的变化而变化。

相同 20 人、相同 274 个测试权限项的标准答案分布如下：

| 测试标签 | S&P 真人答案 | S-QSTN 模拟答案 |
|---|---:|---:|
| No, never share | 20（7.30%） | 12（4.38%） |
| No, but ask me next time | 20（7.30%） | 29（10.58%） |
| Yes, but ask me next time | 126（45.99%） | 173（63.14%） |
| Yes, always share | 108（39.42%） | 60（21.90%） |
| 合计 | 274 | 274 |

模拟答案更集中在“本次允许，下次再问”。这说明即使题目完全配对，预测目标及其分布仍然不同。不能将 74.09% − 66.79% 解释为同一预测任务上的方法提升，也不能据此认定 S-QSTN 已还原真人。

可以直接比较的是同一批冻结模拟数据上的 0-shot 与 4-shot：准确率增加 18.61 个百分点，Macro-F1 增加 0.1278；错误永久允许率下降 20.56 个百分点，错误允许数量仍为 15。净增加的 51 条正确预测中，44 条来自再次询问型画像，收益并非各类型均匀分布。配对 bootstrap 和分组详情保留在原模拟实验报告中。

## 6. 运行量与费用

以下为已有实验费用，本次整理没有新增 API 费用。真人问卷采集成本不在本项目账目内，因此真人数据生成成本应写“本轮无需调用生成模型”，不能写成“获得真人数据没有成本”。

| 项目 | S&P 201 人 | S&P 对应 20 人 | S-QSTN 20 人 |
|---|---:|---:|---:|
| 成功回答生成调用 | 本轮无需 | 本轮无需 | 624 |
| 成功 Gemini 4-shot 调用 | 201 | 20，已包含于左侧 | 20 |
| 成功 Gemini 0-shot 调用 | 未跑 | 未跑 | 20 |
| Gemini 4-shot 费用，USD | $0.73903650 | $0.06845025 | $0.06897300 |
| Gemini 0-shot 费用，USD | — | — | $0.06020925 |
| o4-mini 成功生成估算费用，USD | — | — | $1.03926900 |
| 初次格式失败费用，USD | — | — | $0.00260480 |
| 本实验追踪总额，USD | $0.73903650 | $0.06845025，左侧子集 | $1.17105605，含生成和两种预测条件 |

S&P 201 人中复用早先 40 次成功调用，新增 161 次调用费用为 $0.59536725；复用部分不重复计费。S-QSTN 共 664 次成功调用和 1 次格式失败调用；修复 JSON schema 后重新生成失败项，失败答案未复用。Gemini 费用采用 OpenRouter 返回的 usage cost；o4-mini 费用按返回 token 用量估算，非账户账单。

相同 20 人下，Gemini 4-shot 预测费用接近；模拟路线的主要额外费用来自先生成回答。表内总额不含更早的画像构建、其他模型筛选或原论文收集真人数据的成本。

## 7. 解释边界与当前 baseline 定位

| 问题 | 当前能支持的判断 |
|---|---|
| 两条路线的 ICL 方法是否统一 | 是：相同预测器、prompt、四标签、按 query 划分和 4-shot 选例；相同 20 人的题目也完全一致 |
| 能否证明 ICL 对真人有效 | 当前真人 4-shot 给出真实用户预测表现；要量化“增加四个示例的收益”，还缺同一真人数据上的 0-shot 对照 |
| 能否证明 ICL 对本批模拟用户有效 | 本批冻结目标上 0-shot/4-shot 配对结果支持历史示例有帮助 |
| 能否证明模拟器忠实还原真人 | 不能，预测模拟器答案的准确率不是模拟器与真人答案的一致率 |
| 是否无泄漏地预测未见真人回答 | 不能据模拟结果这样宣称。画像卡来自真人 discovery 回答归纳，其划分与 ICL fold 0 不同，可能涉及 fold-0 真人回答 |
| 是否模拟长期行为变化 | 否，每个生成项采用空状态；不包含跨轮偏好演化 |
| 是否做了全面稳健性研究 | 否，仅固定选例、fold 0 和一次冻结生成；当前适合作为简单 pilot/baseline |

建议在实验记录中分别命名为 **Real-user 4-shot ICL baseline（S&P）** 与 **Synthetic-persona 4-shot ICL baseline（S-QSTN）**。前者提供真实用户预测的参照，后者观察在可控画像下利用历史回答的能力。两者可并列报告，避免将不同目标上的得分差写成方法优劣结论。

## 8. 来源与可复算文件

- [作者公开数据仓库](https://github.com/llm-platform-security/ai-agent-permissions)
- [S&P 201 人原实验报告](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/multi_model_screening/full_201_gemini_4shot_fold0_results.md)
- [S-QSTN 20 人原实验报告](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/REPORT_zh.md)
- [Gemini 输入构建函数](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/run_ic_four_label.py:112)
- [S-QSTN 原始背景字段构建](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/scripts/build_qstn_inputs.py:133)
- [S-QSTN 生成后替换标签与预测流程](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/run_pilot.py:364)
- [本次对比汇总 JSON](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/comparison_summary.json)
- [本次指标对比 CSV](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/comparison_metrics.csv)
- [相同 20 人的真人逐项预测](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/real20_4shot_predictions.csv)
- [本地复算脚本，不调用 API](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/in_context_learning/sqstn_pilot/comparison/build_comparison.py)

汇总脚本确认：同一 20 人的真人与模拟测试上下文、历史/测试 query 清单完全一致；模拟 0-shot 与 4-shot 的 truth 完全一致；真人 20 人预测与原 40 人运行的对应记录完全一致。所有新汇总保存在本 comparison 目录，没有修改原冻结结果。
