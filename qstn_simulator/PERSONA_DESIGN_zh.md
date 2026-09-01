# Persona 设计说明

## 什么是这里的 persona

Persona 不是给模型随意编的人设，也不是一个真实参与者的完整复刻。它是一组在每次回答中保持不变的、与数据共享偏好可能相关的背景条件。QSTN 将这组条件放入 prompt，使同一 persona 面对不同 permission scenario 时有一致的决策依据。

本项目的第一版采用 **profile-grounded persona**：每个有效匿名参与者对应一个 persona，但只使用结构化背景变量。这使生成回答能够与该参与者真实的 Task 3 回答逐条比较。

## 使用哪些原始 profile 字段

| 字段 | 在 persona 中的作用 |
| --- | --- |
| `age` | 保留为原始年龄响应类别，不猜测实际年龄。 |
| `gender`, `education` | 基本背景变量。 |
| `aiFamiliarity`, `aiFrequency`, `aiTrust` | 对 AI 的经验、使用频率和信任的原始量表响应。 |
| `privacyImportance` | 总体隐私重视程度的原始量表响应。 |
| `concern_domain` | 参与者报告的隐私担忧领域。 |

释放数据的 README 没有提供 1--5 量表和年龄编码的完整文字 codebook。因此 prompt 中保留 `response category` / `response`，而不把 `4` 擅自解释为“高”或“中高”。这避免给模型注入未经证实的语义。

## 明确不使用的字段

- `task3`：它是我们要预测和校准的目标答案；放入 prompt 会产生标签泄漏。
- `task1` 与 `task2`：它们属于同一研究任务的行为答案，不应当作为稳定人格特征。
- `aiPurposes` 与 `privacyDetails`：它们是开放文本。本轮默认不发送至外部模型 API，以减小可识别性、提示注入和不可控语言风格的风险。

## persona 与 RL 中的“用户状态”不同

Persona 是相对稳定的初始偏好，例如“隐私重要性回答为 5、对 Finance 有担忧”。RL 的长期反馈还需要一个会变化的 `memory_state`，例如近期越权次数、对代理的信任、近期拒绝/撤销、疲劳度。

```text
profile-grounded persona (stable) + memory_state (changes over time)
    -> permission answer / reward
    -> update memory_state after the agent action and outcome
```

因此现在的 `personas.csv` 是校准阶段的输入，不应被误称为已经具备长期偏好演化能力的“完整人类模拟器”。

## 推荐的验证顺序

1. 对每个 persona 和对应的 Task 3 scenario 生成一次四选项回答。
2. 只以真实 Task 3 标签做评估，报告准确率、macro-F1、over-sharing rate。
3. 检查模型是否只会输出某一个选项，以及是否在 Finance/Health 等 domain 发生系统性过度分享。
4. 通过校准后，再设计独立的 `memory_state` 与反馈转移规则，进入长期 RL simulation。

`outputs/calibration_assignments.csv` 已明确记录了这些实际观察到的 persona--scenario 配对；它包含 16,361 条可与真人答案比较的记录。

## K=3 empirical profile 扩展

目前的 `personas.csv` 仍是基础的 profile-grounded calibration persona：每位匿名参与者一行，只有其结构化背景字段。KMeans 得到的三类不是直接替换这 201 行，而是作为一个额外的、由 discovery responses 得到的稳定行为条件。

因此我们同时维护两种输出：

1. `personas_with_empirical_profiles.csv`：201 个**校准 persona**。每位参与者保留原有匿名背景，并被 join 到一个 empirical profile card。该 card 仅使用该参与者的 discovery 回答所产生的 cluster assignment；held-out 回答不进入 card。
2. `qstn_empirical_profile_prototypes.csv`：3 个**canonical prototype persona**，分别对应 `Persistent Granters`、`Re-consent Seekers` 与 `Broad Restrictors`。它们不含任何真实参与者背景，供后续 simulator/RL 作为稳定的初始用户类型使用。

## QSTN 中 persona 的实际机制

QSTN 没有独立的 persona-learning engine。一个 persona 是一个 `LLMPrompt`：

```text
system_prompt
  + questionnaire_instruction (profile card + optional participant background)
  + {{QUESTION_PLACEHOLDER}} rendered by QSTN
  -> one constrained four-option permission response
```

本项目把稳定 persona 放在 `questionnaire_instruction`，因为它是可检查、可版本化的输入数据；`system_prompt` 保持通用的“模拟 survey participant”约束。`{{QUESTION_PLACEHOLDER}}` 是必须保留的模板字段，QSTN 用它插入当前 permission scenario 和四个答案选项。没有该字段时，模型不会看到题目；`validate_empirical_personas.py` 会在任何 API 调用前检查这个条件。

## 什么来自数据，什么来自研究者

- **learned**：每位参与者的 profile assignment、每个 cluster center、每类人数，均由 `discover_empirical_profiles.py` 的 discovery-only 聚类输出。
- **manually authored but evidence-constrained**：三张英文 profile card 的自然语言措辞，位于 `config/empirical_profile_prompt_cards.json`。它只总结了可观察到的持续授权、再次确认、限制性和必要性区分行为；不含具体比例，不声称动机或心理特质。
- **not used**：held-out `label_id`、`label_text`、`task3` 和任何长期 RL state。

这一区分很重要：我们不是宣称“语言模型从 201 人中学到三个人格”，而是在已经学到的、可复现的行为分群上，使用公开、固定、可审计的 prompt wording 来让 QSTN 条件化。

## 可复现命令

```powershell
.\.venv\Scripts\python.exe scripts\discover_empirical_profiles.py
.\.venv\Scripts\python.exe scripts\compile_empirical_personas.py
.\.venv\Scripts\python.exe scripts\validate_empirical_personas.py
```

最后一条命令不调用 API；它会渲染 201 个校准 persona 和 3 个 canonical prototypes，检查每条 prompt 都包含 profile card、permission scenario、四个选项，且不含 target-answer columns。
