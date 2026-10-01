# Empirical Profile to QSTN Persona Compilation

## 目的

本步骤把 discovery-only K=3 的经验型权限回答画像编译为 QSTN 可读取的 prompt inputs。它不调用 LLM API，也不使用 held-out 标签。

## 学到的内容与人工内容

- **从数据学到**：participant-to-profile assignment、三个 profile 的 cluster center、群组人数。
- **人工编写但受证据约束**：英文 prompt card 的自然语言措辞。它只总结中心中可观察到的授权持久性、再次确认倾向、总体限制倾向和必要性区分；不包含具体回答比例。
- **不声称学到**：心理人格、动机、风险偏好或人口总体比例。

## QSTN 接入方式

QSTN 没有独立的 persona inference 模块。每一个 persona 是一个 `LLMPrompt`，其中固定的 `system_prompt` 和 `questionnaire_instruction` 会与 `{{QUESTION_PLACEHOLDER}}` 所渲染的 permission scenario 一起发送给模型。

## 输出

- `personas_with_empirical_profiles.csv`：201 个校准用 persona。每人保留匿名背景字段，并附上仅由其 discovery 回答得到的 profile card。
- `qstn_empirical_profile_prototypes.csv`：3 个 canonical prototype persona，用于后续 simulator/RL 设计；不包含真实参与者背景。
- `empirical_profile_cards.json`：prompt card、其版本和从 cluster centers 自动导出的证据审计记录。

## 三张卡的审计摘要

### Broad Restrictors (n=30)

This participant generally takes a restrictive approach to sharing. They tend to decline or defer permission rather than grant broad standing permission, and show low willingness to share across the observed context types. When the scenario does not provide a clear reason to share, favor the restrictive or re-consent option that best fits the available choices. Treat this as a tendency, not a hard rule, and do not invent a purpose or personal fact.

### Persistent Granters (n=71)

This participant generally favors enduring permission grants rather than renewed consent. They are more willing to grant permission when the scenario appears to support the user's request than when it appears not to. Treat this as a tendency, not a hard rule, and do not invent a purpose or personal fact.

### Re-consent Seekers (n=100)

This participant generally prefers non-persistent permission. When willing to share, they tend to allow the current occasion and ask for renewed consent later rather than grant standing permission. They are more willing to share when the scenario appears to support the user's request than when it does not. Treat this as a tendency, not a hard rule, and do not invent a purpose or personal fact.

## 评价边界

后续校准必须仅使用 held-out response rows。应比较 raw participant profile only 与 raw participant profile plus empirical profile card，避免把 profile card 的作用与基础人口/AI 自报字段混为一谈。
