# 三模型四标签 ICL 小规模筛选

**已完成：**40 位参与者、599 条相同测试行、三个模型各 40 次成功调用。累计追踪费用 USD 0.296232641，未达到 USD 10 提醒线。主要结果、配对区间及下一轮模型建议见 [`screening_results.md`](screening_results.md)。

## 目的和范围

沿用 [`../run_ic_four_label.py`](../run_ic_four_label.py) 的四标签 prompt、同一用户内按 query 留出的 5 折和严格 JSON 解析。默认用固定随机种子抽 **40 位参与者**，每人只取第 0 折测试；每个模型回答完全相同的 40 个任务。一个任务包含该用户若干个留出 query 下的全部工具/数据类型请求。其余四折仍不参与本轮筛选。

筛选只用于决定下一步保留哪 2–3 个模型；它不替代 201 人 × 5 折的正式结果，也不能与现有 `participant_heldout` 分类分数直接比较。测试 query 的全部四类真实答案均不会进入 prompt。

| 简称 | API 渠道 | 固定模型 ID | 2026-09-25 可见价格（USD / 百万输入、输出 token） |
|---|---|---|---|
| `luna` | OpenRouter | `openai/gpt-6-luna` | 0.10 / 0.50 |
| `deepseek` | OpenRouter | `deepseek/deepseek-v4-flash-0731` | 最低可见路由约 0.03 / 0.32；供应商价格会变化 |
| `gemini` | OpenRouter | `google/gemini-3.8-flash` | 0.75 / 3.75，当前促销标准价 |

模型与价格来源：[OpenRouter Luna](https://openrouter.ai/openai/gpt-6-luna)、[OpenRouter DeepSeek 0731](https://openrouter.ai/deepseek/deepseek-v4-flash-0731)、[OpenRouter Gemini 3.8 Flash](https://openrouter.ai/google/gemini-3.8-flash)、[Google 官方模型页](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)。用户说的 DeepSeek V4 Flash 有旧的无后缀模型；这里明确选择较新的 **0731 GA 版**。运行配置会保存精确 ID，不能静默换版。

## API key 设置

现有 `ai_agent_permission_experiment/qstn_simulator/.env` 已设置 `OPENROUTER_API_KEY`。三个模型都通过这个 key 调用并在 OpenRouter 账户计费。**模型名称固定在 `screen_models.py` 的 `MODEL_SPECS`，不需要写进 `.env`。**原有的 OpenAI key 可保留供其他实验使用，本筛选不会用它。不要把 key 的值写进命令行、日志或提交到 Git。

脚本只在 `--execute` 时从指定的 `.env` 读取 OpenRouter key；也可用 `--env-file` 指向另一个未提交的 dotenv 文件。

## 运行步骤

从 `Week67` 根目录执行，使用现有 `ai_agent_permission_experiment/.venv`。旧目录分别保存了 4,000 token 试跑、8,000 token 默认推理试跑及一次针对 DeepSeek 的诊断。默认推理时 DeepSeek 曾耗尽 8,000 token 而没有正文；新正式筛选将三个模型统一设为 `reasoning.effort=low`，并保持 8,000 输出 token 上限。此前全部费用 USD 0.0284769655 计入累计预算。

```powershell
$Python = 'ai_agent_permission_experiment/.venv/Scripts/python.exe'
$Runner = 'ai_agent_permission_experiment/in_context_learning/multi_model_screening/screen_models.py'
$Out = 'ai_agent_permission_experiment/in_context_learning/multi_model_screening/artifacts/screen_40_seed20260925_8k_low'

# 纯离线查看或恢复已准备的任务，不会调用 API。
& $Python $Runner --out $Out --prior-spend-usd 0.0284769655 --max-cost-usd 24

# 运行或续跑正式筛选。完成的 checkpoint 会跳过。
& $Python $Runner --out $Out --prior-spend-usd 0.0284769655 --max-cost-usd 24 --execute
```

同一目录仅在模型列表、版本、样本、fold、输出上限、数据、脚本及旧试跑费用均未变化时续跑。遇到错误会保存带计费记录的 `.errorN.json` 并停止；检查原因后用 `--retry-errors` 显式重试。先前失败调用的预留费用仍计入本地限制。

完成后查看 `screening_summary.csv`，以及每个模型目录下的 `metrics.json`、`classification_report.json`、`participant_bootstrap_ci.json` 和 `predictions.csv`。运行目录已被此文件夹的 `.gitignore` 排除。

## 预算边界

正式筛选在请求前按 UTF-8 输入字节数、**8,000 个输出 token**及各模型的 OpenRouter 路由价格上限预留费用；请求同时设置 `provider.max_price`，过滤更贵的路由。OpenRouter 回传 `usage.cost` 时记实际价格，否则按路由价格上限估算。路由设为 `sort: price`、`data_collection: deny`；若没有合适路由，调用会失败并停止。[路由参数说明](https://openrouter.ai/docs/guides/routing/provider-selection)。

用户授权的累计费用规则是：**优先控制在 USD 10；达到 USD 10 时提醒并继续；在 USD 24 前停止新调用。**先前试跑与诊断的 USD 0.0284769655 已计入。当前固定样本 120 次正式调用加此前费用的离线预留上界约 **USD 1.9770**；这只是按当前价格上限和 token 上限计算的请求前估算，最终以供应商账单为准。本地限制不涵盖同一 key 的其他应用或充值手续费。

本轮是筛选预算；对 201 位用户做完整 5 折实验需要另按实际 token 和费用重新估算。

## 筛选时看什么

先检查三个模型是否全部完成同一测试行、四类输出是否完整。随后并列查看 macro-F1（主指标）、QWK、过度共享率、错误地预测“永久允许”的比例、四类逐类结果及 40 位用户的 bootstrap 区间，最后看费用和失败率。若差异很小或区间重叠，就保留 3 个进入下一轮；若某个模型明显较差且安全风险或费用也更高，可筛掉它。不要只按一次小样本的 accuracy 选胜者。

这比较的是**相同可见 prompt、相同 OpenRouter `reasoning.effort=low` 设置下的表现**。不同提供商的内部推理量、token 计数和路由行为可能不同；正式论文中应报告这些设置与实际 token/费用，并使用完整 5 折确认差异。
