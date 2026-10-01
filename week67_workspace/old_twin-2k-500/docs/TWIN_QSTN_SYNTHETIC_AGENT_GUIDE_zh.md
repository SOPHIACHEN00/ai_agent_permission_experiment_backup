# Twin-2K × Permission Condition QSTN（实施说明）

本模块实现的是一个**合成用户群体**：

```text
general_persona             = Twin-2K persona_summary
permission-policy condition = {Persistent Granter,
                               Re-consent Seeker,
                               Broad Restrictor}
synthetic agent             = (twin_id, policy_condition)
response                    = QSTN(general_persona, policy_condition, scenario)
```

它可用于为 permission-agent RL 提供可重复的、背景异质的问卷响应环境；它不把任何一名 Twin 受访者宣称为某个 permission profile，也不把模型生成结果称为该受访者的新真实回答。

## 1. 先准备 Twin-2K 输入

从官方 Twin-2K 数据集中导出一个本地 CSV 或 Parquet；本模块**只读取**下列两列：

```text
pid, persona_summary
```

不要把 `persona_text`（长文本）或原始 survey response 导入此流程。`persona_summary` 是 general persona 的唯一来源。数据下载不由脚本自动执行，以避免意外下载约 733 MB 的数据。

## 2. 编译 synthetic agents（无 API 调用）

在 `ai_agent_permission_experiment/qstn_simulator` 下运行：

```powershell
uv run python scripts/build_twin_synthetic_personas.py `
  --twin-personas <PATH_TO_TWIN_PID_AND_SUMMARY.csv> `
  --out outputs/twin_2k_x_permission_policy
```

默认会保留 `persona_summary` 全文，并产生 `2,058 × 3 = 6,174` 个 agent（当输入为 Twin-2K 全量）。若要先做小规模的 prompt/cost 检查：

```powershell
uv run python scripts/build_twin_synthetic_personas.py `
  --twin-personas <PATH_TO_TWIN_PID_AND_SUMMARY.csv> `
  --out outputs/twin_2k_x_permission_policy_100 `
  --max-twins 100
```

输出包括：

- `twin_synthetic_personas.csv`：QSTN 可直接读取的 persona 表。
- `twin_synthetic_persona_manifest.json`：输入 hash、card 版本、字符截断情况和科学边界。
- `twin_synthetic_policy_conditions.json`：冻结 V2 policy cards 的审计副本和 hash。

每行都有 `synthetic_agent_id`，例如 `twin_17__policy_reconsent_seekers`；它不是 Twin 受访者的真实 ID/真实 policy 标签。

## 3. 先生成并审阅一个无 API 的 QSTN plan

```powershell
uv run python scripts/run_twin_synthetic_survey.py `
  --personas outputs/twin_2k_x_permission_policy/twin_synthetic_personas.csv `
  --questionnaire outputs/questionnaire_items.csv `
  --out outputs/twin_2k_x_permission_policy/runs/pilot_20x8 `
  --max-twins 20 `
  --contexts-per-agent 8 `
  --model gpt-4.1-mini
```

这条命令默认是 **dry run**：它只生成并逐条验证 QSTN prompt，不会读取 human target label，也不会发 API request。该 pilot 的规模是 `20 × 3 × 8 = 480` 次未来请求。重点审阅：

- `inference_plan.csv`：`synthetic_agent_id × questionnaire_item_id` 的完整调用计划。
- `preflight_manifest.json`：每个 policy condition 的实际 system/user message 样例、输入 hash、model 名和 request 总数。

## 4. 明确允许后才执行 API

在 `qstn_simulator/.env` 写入 OpenAI-compatible 配置：

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
# OpenRouter 或 Gemini 的 OpenAI-compatible endpoint 可额外设置：
# OPENAI_BASE_URL=https://...
```

确认 preflight 后，在**同一条命令**末尾加 `--execute`。结果会以可恢复的方式写入 `predictions.csv`；中断后使用同一参数加 `--execute --resume`。

```powershell
uv run python scripts/run_twin_synthetic_survey.py `
  --personas outputs/twin_2k_x_permission_policy/twin_synthetic_personas.csv `
  --questionnaire outputs/questionnaire_items.csv `
  --out outputs/twin_2k_x_permission_policy/runs/pilot_20x8_execute `
  --max-twins 20 `
  --contexts-per-agent 8 `
  --model gpt-4.1-mini `
  --execute
```

脚本对超过 10,000 requests 的 plan 会停止，除非额外给出 `--allow-large-run`。全量 `2,058 × 3 × 373 = 2,302,902` calls 不应作为第一次运行；它是成本、时间和 provider rate limit 都很高的生产实验，而不是一个合理的 smoke test。

## 5. 给 RL 的接口

`predictions.csv` 就是静态 environment table。RL 侧不需要认识 Twin 文本，只需按下列键读取：

```text
environment user      = synthetic_agent_id
permission scenario   = questionnaire_item_id
simulated response    = predicted_label_id
response explanation  = raw_response   # 仅用于审计，不作为 reward target
```

四个 `predicted_label_id` 与现有 permission action 顺序一致：`0=No, never`、`1=No, ask next time`、`2=Yes, ask next time`、`3=Yes, always`。

## 6. 写作时必须保留的边界

可以表述为：我们用 `Twin-2K persona_summary` 引入 general-persona heterogeneity，并将 three-condition permission policy 作为实验控制变量，从而形成可重复的 synthetic survey environment。

不能表述为：Twin-2K 中的某位真实参与者就是 Persistent Granter / Re-consent Seeker / Broad Restrictor，或模型输出是该参与者的真实权限回答。该模块没有人类外部效度主张，也不会替代原论文数据上的 held-out evaluation。
