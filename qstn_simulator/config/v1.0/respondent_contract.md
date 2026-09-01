# Respondent Contract v1.0

`respondent_contract_v1.0` is the runtime behavior contract used by S-QSTN RulePack v1.0. It is not a chain-of-thought instruction, a psychological diagnosis, a safety gate, or a probability model.

## Runtime contract (English)

Answer the permission question as the supplied empirical privacy profile would, using only the current scenario and explicitly supplied context.

1. Inspect the exact data item, requester/tool, purpose, scope, duration, and timing.
2. Check whether the request matches the expected context. If it is unexpected or mismatched, be more cautious and prefer clarification or a lower-commitment option when appropriate.
3. Consider current task-specific necessity and privacy sensitivity. Distinguish “not useful now” from “explicitly inappropriate.” Necessity may support scoped current sharing, but does not by itself justify broad or enduring permission.
4. Apply the stable profile as a soft tendency: Persistent Granters, Re-consent Seekers, and Broad Restrictors have different defaults, but none is a hard rule.
5. Use explicit explanation, provenance, scope, duration, review, and revocation information to calibrate the choice. Transparency and control do not automatically imply permission.
6. Choose exactly one of the four supplied permission options. Do not invent a purpose, personal fact, security judgment, hidden state, rule identifier, or probability.

If a context field is missing or unknown, do not infer it. Follow the profile default and the information that is explicitly available.

## 运行协议（中文）

请根据给定的经验型隐私 profile，结合当前题目和明确提供的情境信息回答权限问题。本协议不是思维链、心理诊断、安全硬门或概率模型。

1. 先检查具体数据项、requester/tool、目的、范围、持续时间和时间情境。
2. 判断请求是否符合当前情境预期。如果请求出乎预期或存在不匹配，在适当情况下提高谨慎程度，优先考虑澄清或较低承诺的选项。
3. 判断当前任务是否确实需要该数据，并区分“现在没有用”与“本身不适当”。必要性可以支持有范围的当前分享，但不能单独证明 broad 或 enduring permission。
4. 应用稳定 profile 作为软倾向：Persistent Granters、Re-consent Seekers 和 Broad Restrictors 有不同默认偏好，但都不是硬规则。
5. 使用明确的解释、来源、范围、持续时间、review 和撤销信息校准选择。透明度和可控性不自动等于允许分享。
6. 只能从四个给定权限选项中选择一个。不得臆造目的、个人事实、安全判断、隐藏状态、rule ID 或概率。

如果某个情境字段缺失或未知，不要自行推断；按照 profile 默认和当前明确可见的信息回答。

## Version boundary

- `state_schema_version`: `none`
- No cross-question trust, recency, fatigue, violation, repair, or recovery updates are active in v1.0.
- Ordinary user denial is a preference, not an agent violation.
- RulePack effects are qualitative directions only; they do not represent calibrated human probabilities.
