# S-QSTN RulePack v2.0 / v3.0 设计草案

> 状态：待确认。本文档只敲定设计边界，不代表 v2 或 v3 已经实现。

## 1. 总体判断：需要记忆，但不需要完整记忆

P1、P2、P3、P7、P12 都依赖历史信息，但 S-QSTN 不应保存并暴露完整
conversation transcript。更合理的是实现一种有限、可遗忘、可审计的 memory：

```text
verified external events
        ↓
private event ledger
        ↓
bounded state transition
        ↓
lossy memory view / state snapshot
        ↓
current QSTN respondent prompt
```

这里的“遗忘”应当是显式的 retention policy，而不是依赖 LLM 自己决定
哪些历史还记得。过期事件可以从 respondent `memory_view` 中消失，但为了
reproducibility，完整的结构化 event ledger 可以由 wrapper 私下保存并审计。

## 2. v2.0：Memory and State Substrate

### v2.0 的目标

v2.0 只实现“记住什么、何时忘记、哪些事件可以改变状态”的机制，不实现
经过人类数据校准的行为强度和概率。

### v2.0 建议新增组件

#### 2.1 `event_ledger`

结构化记录，不保存完整 prompt 或 chain-of-thought。候选事件包括：

- `permission_request_presented`
- `permission_response_recorded`
- `explicit_grant`
- `explicit_revoke`
- `scope_change`
- `verified_agent_error`
- `verified_scope_violation`
- `repair_completed`
- `repair_rejected`
- `consent_refresh`
- `prompt_interruption`
- `unresolved_request`

事件必须带有明确的 source、turn/order、verification status 和 scope。
普通 respondent denial 不能自动变成 `verified_agent_error` 或
`verified_scope_violation`。

#### 2.2 `memory_view`

这是传给 respondent prompt 的有限历史摘要，而不是完整 ledger。它可以
只暴露：

- 最近仍然有效的 verified event 类型；
- 当前 trust/caution 的 categorical 状态；
- 最近请求/打断/未解决请求的摘要；
- 当前事件的 recency bucket；
- 哪些历史字段已经过期或 unknown。

#### 2.3 `state_snapshot`

v2.0 使用 bounded categorical state，不使用未经校准的 numeric weights。
候选状态例如：

- `baseline`
- `caution`
- `restricted`
- `repair_in_progress`
- `recovered_with_residual_caution`
- `unknown`

这些状态只能由显式 transition rules 更新，不能由 LLM 自行推断。

#### 2.4 retention / forgetting

v2.0 应支持 event-specific retention policy，而不是把所有历史永久保留。
建议先定义 retention class，例如：

- `recent_only`
- `until_repaired`
- `persistent_verified_boundary_event`
- `expired_after_policy_window`

具体时间窗口或 turn 数量不应在没有 evidence 时被包装成“人类遗忘参数”。
v2.0 可以用 synthetic fixtures 验证机制；正式 retention duration 进入 v3.0
校准。

### v2.0 与五个 principles 的关系

| Principle | v2.0 要实现的机制 | v2.0 不应声称的内容 |
|---|---|---|
| P1 | verified negative event、caution transition、非对称方向 | trust loss 的具体幅度 |
| P2 | repair/recovery event、不能立即 full reset | 恢复需要几题或几天 |
| P3 | event order、timestamp/turn、recency bucket | 固定 decay coefficient |
| P7 | prompt count、interruption、unresolved request ledger | fatigue 一定导致 allow 或 deny |
| P12 | competence/integrity/benevolence 等候选 trust dimensions | trust dimension 到四标签的概率映射 |

### v2.0 的文件边界

- JSON：`state_schema`、`event_types`、`transition_rules`、`retention_policy`、
  `state_schema_version`。
- skill.md：五个 principles 的语义、证据边界和禁止推断内容。
- wrapper code：StateStore、event adapter、memory summarizer、transition
  audit。
- respondent contract：说明只使用 compiled memory view，不要求或暴露隐藏
  chain-of-thought。
- QSTN core：保持不变。

## 3. v3.0：Human-Calibrated Decision Layer

### v3.0 的目标

v3.0 不重新发明 v2 state，而是在冻结的 v2 state schema 上，使用多轮、带
时间顺序、可验证事件的 human data，校准：

```text
profile card
+ current context
+ memory view / state snapshot
        ↓
calibrated decision mapper
        ↓
four-label permission choice
```

### v3.0 需要的数据

- participant/time-separated multi-turn sequences；
- 每一轮的 context、timestamp/turn index 和 prompt burden；
- 明确的 grant、revoke、repair、scope change 和 verified error annotation；
- 不把 ordinary denial 当作 agent violation；
- participant-level held-out split，避免同一人的历史泄漏到 evaluation。

### v3.0 的校准内容

- P1：负面 verified event 对后续 permission 的非对称影响；
- P2：repair 后的恢复速度和 residual caution；
- P3：recency window、decay 和 recent-event dominance；
- P7：重复 prompt、打断和 unresolved request 对 re-asking/timing/choice 的影响；
- P12：trust dimensions 与 permission choice 的关系；
- P9：profile × context × state 的交互效果。

v3.0 可以使用 coefficients、probabilities 和 uncertainty，但每个参数都必须
带有 calibration version、训练/验证 split、样本范围和不确定性记录。

### v3.0 的架构选择

推荐 calibrated decision mapper 位于 prompt 之外。QSTN 继续负责 survey
编排、single-item presentation 和四标签 parsing；mapper 负责可解释、可复现
的 structured decision。不要把 calibrated weight 写成自然语言 prompt 指令，
再宣称 LLM 实现了该概率。

## 4. 版本进入条件

### v2.0 开始前

- frozen event vocabulary；
- frozen public/private state boundary；
- verified event source 或 synthetic oracle；
- retention policy contract；
- memory leakage 和 ordinary-denial tests。

### v3.0 开始前

- v2.0 StateStore 和 transition audit 已验证；
- multi-turn human calibration data 已准备；
- participant/time-separated held-out split 已冻结；
- baseline、no-memory、profile-only 和 memory ablation 已定义；
- calibration metrics 和 failure criteria 已预注册。

## 5. 当前建议

先实现 v2.0 的 schema、StateStore 和 synthetic event fixtures，但暂不实现
v3.0 的 coefficients 或 probability mapper。v2.0 的结果只能说明“记忆机制和
状态边界工作正常”，不能说明“已经像人类一样遗忘或恢复信任”。
## Implementation status

RulePack v2.0 is now implemented and offline-verified under
`ai_agent_permission_experiment/qstn_simulator/config/v2.0/` and
`ai_agent_permission_experiment/qstn_simulator/scripts/v2/`. The v2 compiler
and QSTN smoke test use label-free synthetic memory fixtures only. v3.0 human
calibration, retention-duration calibration, and any numerical decision mapper
remain future work.

The canonical implementation record is
`ai_agent_permission_experiment/qstn_simulator/versioning.md`; the bilingual
runtime guide is
`ai_agent_permission_experiment/qstn_simulator/RULEPACK_V2.0_README.md`.
