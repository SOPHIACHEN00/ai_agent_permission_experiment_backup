# S&P 全部有效用户：Gemini 3.8 Flash、4-shot、fold 0

日期：2026-09-26。状态：完成。201/201 位有效用户，3,123/3,123 条测试预测，0 个调用错误。

## 主要结果

| 指标 | 全部 201 位用户 | 95% 置信区间 |
|---|---:|---:|
| Accuracy | **62.82%** | 59.62%–65.88% |
| Macro-F1 | **0.5451** | 0.5113–0.5745 |
| Quadratic weighted kappa | 0.5590 | 0.5022–0.6092 |
| False allow：真实拒绝记录中的错误允许率 | 274 / 645 = **42.48%** | 36.26%–48.93% |
| Persistent over-allow：未选择永久允许的记录中，被预测为永久允许的比例 | 282 / 1,898 = **14.86%** | 11.50%–18.71% |

点估计在合并后的全部 3,123 条权限记录上计算。95% CI 使用参与者聚类 bootstrap 百分位法，重采样 1,000 次；每次有放回抽取 201 位参与者并保留其全部测试记录。该区间没有纳入更换 fold、4-shot 示例或重复模型生成的变异。

False allow 的真实类别是两种 No，预测类别是两种 Yes。Persistent over-allow 还包括将临时允许预测成永久允许；两项有交集，不能相加。当前结果可作为固定协议下的简单 ICL baseline，拒绝类别仍有明显的错误允许现象。

## 实验设置

- 数据：作者公开发布的匿名 S&P 问卷，经现有四标签预处理得到 201 位有效用户、16,361 条权限回答。
- 模型：通过现有 OpenRouter 路由调用 `google/gemini-3.8-flash`。
- 协议：用户内按完整 query 分五折，fold seed 42；只运行 fold 0，覆盖 3,123 条测试权限判断。
- 上下文：在每位用户的训练部分随机选择 4 个完整 query，shot seed 20260925；一个 query 可以包含多条权限判断。沿用现有 demographic/profile + history prompt。
- 生成设置：`reasoning.effort=low`，最大输出 8,000 token；同一用户该折的测试请求在一次调用中预测。
- 不更新模型权重；将用户资料及 4 个带回答的历史 query 放入 prompt，再预测留出的 query。
- “全量”指覆盖全部 201 位有效用户。“fold 0”指五折划分中的第 0 折；本次只评估该折的 3,123 条记录。S&P 使用随机 query 留出，不能将本结果解释为真实时间顺序的后续行为预测。

建议实验名称：**Personalized 4-shot ICL — Gemini 3.8 Flash, fold 0**。

## 四类表现

沿用数据集原始类别名称；类别 0–3 的编码保持不变。

| 类别 | 测试记录数 | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| 0 · No, never share | 345 | 0.5089 | 0.5826 | 0.5432 |
| 1 · No, but ask me next time | 300 | 0.3641 | 0.2367 | 0.2869 |
| 2 · Yes, but ask me next time | 1,253 | 0.6181 | 0.7247 | 0.6672 |
| 3 · Yes, always share | 1,225 | 0.7350 | 0.6384 | 0.6833 |

其中临时拒绝类别（No, but ask me next time）的 F1 最低，为 0.2869。

## 已有结果复用

此前 40 位用户的 Gemini 4-shot 成功 checkpoint 与本次数据、原始问卷、源代码、模型、选例和 prompt 完全一致，已复用；新增 161 次调用。每个复用 checkpoint 的来源、文件哈希与重建 prompt 哈希保存在运行目录的 `reuse_provenance.json`。原有 40 人实验文件保持原样。

| 参与者来源 | 用户数 | 测试记录数 | Accuracy | Macro-F1 |
|---|---:|---:|---:|---:|
| 复用的模型筛选用户 | 40 | 599 | 67.78% | 0.5475 |
| 本次新增用户 | 161 | 2,524 | 61.65% | 0.5426 |
| 全部有效用户 | 201 | 3,123 | 62.82% | 0.5451 |

全量结果包含曾参与模型筛选的 40 位用户，因此不应称为完全独立于模型选择的测试结果。新增 161 位用户的指标单独保存，便于区分；两组用户不同，表中差异不是同一测试集上的方法优劣比较。

## 费用

| 项目 | USD |
|---|---:|
| 本次新增 161 次调用 | **$0.59536725** |
| 复用的 40 次 Gemini 调用 | $0.14366925 |
| 本实验全部 201 份 Gemini 结果 | $0.73903650 |
| 本地追踪账目累计，含此前多模型实验 | $1.103527968 |

执行前已有累计费用 $0.508160718。runner 的 prior offset 为 $0.3644914680000001，排除了复制进本目录的旧 Gemini 费用，因此没有重复计数。全部调用完成，未触及累计 $10 的执行上限。详细账目见 `cost_accounting.json`。

## 数据来源核查

本地 `user_study.json` 和 `queries.json` 的解析内容与作者公开 GitHub 文件完全相同，全部 16,361 条 CSV 记录均已逐条核对来自公开数据。证据保存在 `public_data_provenance.json`。

完成后独立只读核查确认：201 个成功 checkpoint、0 个 error 文件；预测逐条覆盖 manifest，无重复和缺失；真实标签与原数据一致；每位用户 4 个历史 query 与测试 query 无重叠；40 份复用文件的哈希未变化；请求和返回模型均为 `google/gemini-3.8-flash`；重新计算的指标及费用与保存结果一致。

启动记录：曾因自动审批要求确认数据来源而暂停，提交公开来源验证后获准。另一次启动因 PowerShell 改写预算小数格式而被配置一致性检查终止；修正参数表示后启动成功。这两次启动均未调用模型 API。

## 输出

运行目录：`artifacts/full_201_gemini_4shot_fold0_seed20260925_8k_low`，位于本报告同级目录下。

- `run_config.json`：固定配置和数据、源码哈希。
- `job_manifest.json`：每位用户的训练、测试和实际 4-shot query 清单。
- `checkpoints/`：逐用户预测、模型和 token/费用记录。
- `execution_plan.json`：准确的离线准备和 API 执行参数。
- `resume_run.ps1`：保留精确参数的执行命令；成功 checkpoint 会被跳过。
- `status.json`、`cost_accounting.json`：完成状态与费用账目。
- `gemini/predictions.csv`：全部 3,123 条逐记录预测。
- `gemini/metrics.json`、`classification_report.json`、`participant_bootstrap_ci.json`：总体、分类别指标和置信区间。
- `gemini/confusion_matrix.csv`：四分类混淆矩阵。
- `gemini/provenance_group_metrics.json`：复用 40 人和新增 161 人的分组结果。
- `screening_summary.csv`：本实验汇总表。
