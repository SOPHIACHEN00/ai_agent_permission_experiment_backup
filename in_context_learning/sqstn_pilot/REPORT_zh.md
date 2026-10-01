# S-QSTN 20 用户：o4-mini 生成，Gemini 0-shot / 4-shot 预测

状态：完成。日期：2026-09-26。20 位画像、624 条模拟回答、两组各 274 条测试预测均完整保存。

## 实验问题

在固定场景和用户画像下，Gemini 能否利用四个场景中的模拟回答，更准确地预测该模拟用户在其他场景中的权限选择？

## 主要结果

| 指标 | 0-shot | 4-shot | 4-shot − 0-shot |
|---|---:|---:|---:|
| Accuracy | 55.47%（152/274） | **74.09%（203/274）** | **+18.61 个百分点** |
| Macro-F1，固定四类 | 0.4568 | **0.5845** | **+0.1278** |
| Quadratic weighted kappa | 0.5428 | 0.7233 | +0.1805 |
| 拒绝记录中的错误允许率 | 36.59%（15/41） | 36.59%（15/41） | 0 个百分点 |
| 未选择永久允许的记录中，被错误预测为永久允许的比例 | 33.64%（72/214） | **13.08%（28/214）** | −20.56 个百分点 |

本批固定模拟数据中，提供四个历史场景后，Gemini 的总体分类表现提高，错误永久允许减少。拒绝记录中的错误允许数量仍为 15，不能据此说所有权限风险都得到改善。

测试标签分布：No, never share 12 条；No, but ask me next time 29 条；Yes, but ask me next time 173 条；Yes, always share 60 条。允许类占多数，因此同时报告固定四类 Macro-F1。

## 实验方案

- 从原 Gemini 40 人实验固定选取 20 位用户画像，覆盖三种偏好类型。
- 每人沿用原来的四个完整历史场景和四个 fold-0 测试场景；一个场景可能包含多项权限判断。
- S-QSTN 使用当前配置的 o4-mini、profile cards v2、RulePack v2 和逐题空状态生成回答。
- 先冻结模拟答案，再让 Gemini 3.8 Flash 分别执行 0-shot 与 4-shot；预测器不读取隐藏画像卡、规则或测试答案。
- 指标包括 Accuracy、Macro-F1、错误允许率和错误永久允许率，并记录按画像类型的结果。
- 样本构成：长期允许型 7 位、再次询问型 10 位、偏向拒绝型 3 位；生成 350 条历史权限回答和 274 条测试权限回答。
- 运行目录：`artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1`。

### 用户与问题清单

此前小实验实际为 40 人、599 条 fold-0 测试权限记录。本轮从该 manifest 的用户池中预先分层选择 20 人；选择不使用 Gemini 预测成绩。每位用户仍使用旧清单的 4 个完整历史 query 和 4 个测试 query。

- 选择种子：20260926；先排序 profile ID、再排序候选 participant ID，再按配额抽取。
- 原划分：fold 0，fold seed 42；原 4-shot seed 20260925。
- 20 位用户：P012、P015、P031、P032、P033、P040、P053、P055、P057、P073、P082、P103、P120、P125、P143、P144、P167、P174、P179、P183。
- 350 条历史权限项、274 条测试权限项，总计 624 个 persona × item 生成请求；映射到 250 个不同 questionnaire item。

### 模型与信息边界

| 角色 | 配置 | 实际返回模型 |
|---|---|---|
| S-QSTN 回答生成器 | OpenAI `o4-mini`，沿用本地配置 | `o4-mini-2025-04-16` |
| 0-shot / 4-shot 预测器 | OpenRouter `google/gemini-3.8-flash` | `google/gemini-3.8-flash` |

生成器使用 QSTN 0.5.1 原生单题提示与四选项 JSON schema、empirical profile cards v2、RulePack 2.0.0、`stateful_audit_compatible` 和 `active_excerpt`。每项新建空记忆，事件列表为空、turn 为 0，无违规事件 fixture，题间不更新状态。生成设置固定为 low reasoning、4,096 completion token 上限、seed 42；批量并发 4。

全部模拟答案生成并冻结之后，才启动 Gemini。它只接收原 baseline 允许的公开背景字段、当前测试请求，以及 0 或 4 个带模拟回答的历史场景。测试答案以 null 留空；隐藏 profile 卡、规则、内部状态和真人逐题标签均不进入预测提示。Gemini 沿用原 prompt、low reasoning、8,000 token 上限。两种条件的用户和测试行完全配对，不更新模型权重。

## 三类画像的表现

这三类来自既有行为画像聚类，是回答倾向的描述，不是经过验证的心理人格类型，也不会强制每道题选择同一答案。

| 画像类型 | 用户数 / 测试记录 | 0-shot Accuracy | 4-shot Accuracy | 0-shot / 4-shot 错误允许 |
|---|---:|---:|---:|---:|
| 长期允许型 Persistent Granters | 7 / 106 | 54.72% | 57.55% | 2/11 → 4/11 |
| 再次询问型 Re-consent Seekers | 10 / 133 | 57.89% | 90.98% | 2/15 → 1/15 |
| 偏向拒绝型 Broad Restrictors | 3 / 35 | 48.57% | 60.00% | 11/15 → 10/15 |

总体净增加的 51 条正确预测中，44 条来自再次询问型，7 条来自其余两组。长期允许型的错误永久允许从 19/46 增至 28/46；另外两组则降至 0。因此，本轮增益主要体现为识别再次询问倾向，不能概括为对所有类型均改善风险判断。分组样本很小，仅作描述。

## 配对区间

使用 1,000 次参与者聚类 bootstrap，seed 20260926；每次有放回抽取 20 位画像，保留各自全部测试记录，两个条件共享同一抽样。点估计是合并权限记录后的指标。

| 4-shot − 0-shot | 点估计 | 95% 百分位区间 |
|---|---:|---:|
| Accuracy | +18.61 个百分点 | [+7.89, +31.56] 个百分点 |
| Macro-F1 | +0.1278 | [+0.0506, +0.2167] |
| 错误允许率 | 0 个百分点 | [−8.82, +10.53] 个百分点 |
| 错误永久允许率 | −20.56 个百分点 | [−40.18, −2.06] 个百分点 |

这些是固定画像、题目、模拟标签和模型输出条件下的描述性区间，不包含重新生成模拟回答、更换 fold 或更换历史示例的变异。

## 解释范围

这是小规模模拟用户可预测性实验。现有画像根据真人 discovery 回答归纳，其划分与 ICL fold 0 不相同；本实验不声称真人还原度或真实时间序列泛化。20 人和单次固定选例仅用于初步观察。

4-shot 得分提高说明本批模拟历史对预测有帮助，不能直接证明 S-QSTN 还原了真人。该 20 人模拟实验与此前 201 人真人实验的样本、目标答案均不同，两个总体分数不能直接作为方法优劣的配对比较。

## 费用与运行记录

| 项目 | USD |
|---|---:|
| o4-mini：624 次成功生成，按 token 用量估算 | $1.03926900 |
| 初始 JSON 字段格式错误的 1 次调用 | $0.00260480 |
| Gemini：20 次 0-shot，提供方报告费用 | $0.06020925 |
| Gemini：20 次 4-shot，提供方报告费用 | $0.06897300 |
| **本轮总追踪费用** | **$1.17105605** |

o4-mini 费用采用返回的输入、缓存输入和输出 token 数，按官方每百万 token $1.10 / $0.275 / $4.40 估算，区别于账户账单；Gemini 使用 OpenRouter 返回的实际 usage cost。[o4-mini 官方价格](https://developers.openai.com/api/docs/models/o4-mini)

初始请求仅使用 json_object，模型返回了合法选项，但键为 permission，严格 answer 解析拒绝了该响应。补齐 QSTN 原生 JSON schema 后，在新的运行目录重新生成该项；原错误记录逐字保留并计费一次，其答案未复用。其后 624 次生成及 40 次预测均成功，无在途请求。总费用低于本轮 $8 上限。

## 完整性与交付

已核对：20 位用户及配额、624 项原场景映射、逐题空状态、公开数据来源、全部成功模型 ID、冻结文件哈希，以及两种条件各 274 条预测的真实标签均对应冻结模拟答案。所有生成完成时间早于首条预测开始时间，费用账目与状态一致。

运行目录内主要文件：

- `run_config.json`、`participants.csv`、`job_manifest.json`：配置、源码/资产哈希、画像清单和题目划分。
- `generator_preflight.json`、`predictor_preflight.json`：准确请求消息及 prompt 哈希。
- `calls/`：逐次原始响应、解析结果、模型标识、token 和费用记录。
- `synthetic_answers.csv`、`synthetic_freeze.json`：冻结模拟回答与校验信息。
- `predictions_0shot.csv`、`predictions_4shot.csv`：逐记录预测。
- `metrics_*.json`、`classification_report_*.json`、`confusion_matrix_*.csv`：总体指标及四类明细。
- `metrics_by_profile.csv`、`paired_bootstrap.json`：分组结果与配对区间。
- `cost_accounting.json`、`final_audit.json`、`format_fix_provenance.json`：费用账目、最终对应关系核查和格式修复来源。

脚本与恢复命令见同目录 `README.md`。已完成的调用在恢复时会被跳过。
