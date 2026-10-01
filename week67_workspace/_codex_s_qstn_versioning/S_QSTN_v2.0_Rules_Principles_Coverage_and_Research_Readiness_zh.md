# S-QSTN v2.0 Rules / Principles Coverage 与实验可用性记录

**审计日期：** 2026-08-07  
**审计对象：** S-QSTN RulePack v2.0.0 + empirical profile cards v2  
**结论状态：** 在限定研究用途下“基本实验可用”；不是完整的人类认知模型或 human-calibrated behavior model  
**推荐研究定位：** privacy- and security-focused、profile-conditioned、rule-informed、bounded-memory 的 QSTN human-side respondent simulator

## 1. 结论摘要

本次重新逐项核对 Excel registry、v2.0 skill catalog、JSON RulePack、state/runtime、profile cards 和离线运行结果后，结论如下：

1. **v2.0 没有把 Excel 中 56 条 rules 全部做成 56 个独立、可执行、经人类数据校准的行为处理器。**
2. **v2.0 已经将 56/56 条 Excel rules 全部保存进英文 skill catalog，Rule ID 无缺失、无额外项。**
3. 其中 **33 条标记为 `active_grouped`**，全部被六个 grouped JSON behavior rules 引用；其余规则明确标记为 longitudinal defer、future candidate 或 catalog/safety boundary。
4. 12 个 principles 也不是同一实现深度：P4/P5/P6/P10/P11 已有定性 context behavior，P9 部分实现；P1/P2/P7/P12 有部分 state substrate；P3 只有 recency metadata；P8 是外部安全边界。
5. **v2.0 + empirical profile cards v2 足以作为本项目最后一小部分对照实验中的人类侧模拟器。** 适合比较 `vanilla QSTN vs S-QSTN v2.0 vs human`，前提是将该比较描述为 exploratory/secondary comparison，而不是把 S-QSTN 宣称为完整或经过心理学验证的人类模型。
6. 因为论文重点是 personal assistant 侧的安全，**当前没有必要继续实现 v3.0**。只有当论文需要量化 human-likeness、真实遗忘曲线、trust-loss magnitude 或 longitudinal choice calibration 时，才需要 v3。

推荐论文表述：

> S-QSTN v2.0 is a profile-conditioned, rule-informed, bounded-memory respondent simulator for privacy and data-permission judgments. It is used as an auxiliary human-side comparator rather than as a cognitively validated or fully human-calibrated model.

不应写成：

> S-QSTN fully implements all 56 human behavior rules and all 12 principles, or faithfully reproduces human privacy behavior.

## 2. “覆盖”必须区分的四个层级

| 层级 | 判断问题 | v2.0 结果 |
|---|---|---|
| Catalog coverage | Excel rule 是否被完整保存、可追溯？ | **56/56，完整** |
| Machine reference | rule 是否被 JSON grouped/audit rule 引用？ | 36 个 unique source IDs；其中 33 个 active，3 个仅进入 P7 audit |
| Executable behavior/state | 是否存在当前 context trigger、state transition 或 audit logic？ | 6 个 grouped rules + 2 个 audit rules + 5 个 state/audit entries |
| Human calibration | 是否由真实人类 longitudinal data 校准到四个 QSTN options？ | **没有；v2 明确不声称** |

所以，“all rules are present”是正确的；“all rules are fully implemented and calibrated”是不正确的。

默认 `active_excerpt` 模式只把当前被 wrapper 激活的定性上下文交给 LLM。`full_catalog_with_active_excerpt` 可以让 LLM 看见完整 56 条 catalog，但 deferred/boundary rules 仍不能自行激活。

## 3. 56 条 Excel rules 在 v2.0 中的总体状态

| Runtime status | 数量 | v2.0 含义 |
|---|---:|---|
| `active_grouped` | 33 | 进入六个 grouped qualitative behavior rules；没有数字 weight |
| `deferred_longitudinal` | 9 | rule prose 保留；部分有 audit/state substrate，但没有完整纵向行为效应 |
| `candidate_future` | 6 | 保存为未来候选，不影响当前回答 |
| `catalog_only_boundary` | 8 | 作为证据、评估、非推断或外部安全边界，不是 respondent preference |
| **总计** | **56** | 与 Excel 56 个 unique Rule IDs 一致 |

### 3.1 六个 active grouped behavior rules

| JSON grouped rule | Principle | Excel source Rule IDs | 当前作用 |
|---|---|---|---|
| `P4.expectation_mismatch` | P4 | Cao-R2; Wij2015-R2; Wij2017-R2 | 显式预期不匹配时提高谨慎、倾向澄清或较低承诺选项 |
| `P5.perceived_control` | P5 | Cao-R7; Elbitar-R6; Malkin-R6; Malkin-R7; Harborth-R6 | 根据 scope、duration、revocation、review 等显式控制信息调整定性倾向 |
| `P6.transparency_calibration` | P6 | Cao-R5; Elbitar-R1; Elbitar-R2; Elbitar-R7; Harborth-R1; Harborth-R2; Harborth-R7 | explanation/provenance/readability 用于理解校准，不把透明度当成 allow nudge |
| `P9.necessity_and_privacy_calculus` | P9 | Cao-R3; Cao-R4; Wij2015-R1; Wij2015-R6; Harborth-R3; Harborth-R4; Malkin-R2 | 区分 necessary、not useful now、explicitly inappropriate 和 unknown；保持 least privilege |
| `P10.stable_privacy_trait` | P10 | Cao-R8; Wij2015-R4; Wij2015-R8; Wij2017-R3; Elbitar-R4; Elbitar-R5 | empirical profile 是 soft prior，不是硬权限政策或心理诊断 |
| `P11.context_dependency` | P11 | Cao-R1; Wij2015-R2; Wij2015-R3; Wij2015-R6; Wij2017-R1; Wij2017-R2; Wij2017-R4; Harborth-R1; Harborth-R8 | 对具体 data item、tool/requester、purpose、scope 和 task 分别判断 |

六组 source IDs 有交叉；去重后对应 33 条 `active_grouped` rules。

### 3.2 P7 audit 引用但未形成 fatigue-to-choice behavior 的 rules

以下三条仍标记为 `deferred_longitudinal`，但被 `AUDIT.current_turn_prompt_burden` 引用：

- Wij2017-R8 — Prompt-burden and habituation rule
- Wij2015-R7 — Prompt-burden and selective-prompting rule
- Malkin-R4 — Prompt-burden and interruption rule

v2 可以保存 explicit burden、prompt interruption 和 unresolved request，并产生 bounded burden state；它不会机械地把 fatigue 映射为 allow、deny 或 consent refresh。

### 3.3 v2 state/audit entries

| State/audit entry | Principle | 已实现 | 未实现 |
|---|---|---|---|
| `STATE.P1.verified_negative_event` | P1 | verified error/scope violation 可进入 categorical caution | trust loss 数值、严重度分级、真实累积曲线 |
| `STATE.P2.repair_recovery_boundary` | P2 | repair 后进入 recovery/residual caution，不 instant reset | 恢复时长、连续正确行为门槛、恢复概率 |
| `STATE.P7.prompt_burden_ledger` | P7 | 保存有界 prompt/interruption history | fatigue 到四选项的校准效应 |
| `STATE.P12.trust_dimension_separation` | P12 | competence/integrity/benevolence 分开表示 | trust dimension 到 permission label 的映射 |
| `AUDIT.P3.recency_metadata` | P3 | 记录顺序、age/recency bucket | decay coefficient、recency dominance |

### 3.4 全部 56 条规则清单及状态

状态解释：`active_grouped` = 已进入当前 grouped behavior；`deferred_longitudinal` = 纵向语义保留但未完整校准；`candidate_future` = 候选；`catalog_only_boundary` = 边界而非 respondent behavior。

| Rule ID | Rule name | v2.0 status |
|---|---|---|
| Cao-R1 | Context rule | `active_grouped` |
| Cao-R2 | Expectation rule | `active_grouped` |
| Cao-R3 | Functionality and utility rule | `active_grouped` |
| Cao-R4 | Least-privilege rule | `active_grouped` |
| Cao-R5 | Explanation rule | `active_grouped` |
| Cao-R6 | Temporal and temporary-grant rule | `candidate_future` |
| Cao-R7 | Reversibility rule | `active_grouped` |
| Cao-R8 | Attitude and behavior separation rule | `active_grouped` |
| Wij2017-R1 | Context-change and no-blind-reuse rule | `active_grouped` |
| Wij2017-R2 | Observable runtime-context rule | `active_grouped` |
| Wij2017-R3 | Profile heterogeneity rule | `active_grouped` |
| Wij2017-R4 | Similar-history ledger rule | `active_grouped` |
| Wij2017-R5 | Cold-start and elicitation rule | `catalog_only_boundary` |
| Wij2017-R6 | Low-confidence re-ask rule | `catalog_only_boundary` |
| Wij2017-R7 | False-allow asymmetry and safety-evaluation rule | `catalog_only_boundary` |
| Wij2017-R8 | Prompt-burden and habituation rule | `deferred_longitudinal` |
| Elbitar-R1 | Rationale-presence rule | `active_grouped` |
| Elbitar-R2 | Timing and rationale interaction rule | `active_grouped` |
| Elbitar-R3 | Timing trade-off and no-universal-best rule | `candidate_future` |
| Elbitar-R4 | Individuality and profile-modulated communication rule | `active_grouped` |
| Elbitar-R5 | Attitude, sensitivity, and clarity separation rule | `active_grouped` |
| Elbitar-R6 | Decision and evaluation separation rule | `active_grouped` |
| Elbitar-R7 | Explanation attention and provenance rule | `active_grouped` |
| Elbitar-R8 | Rationale-integrity boundary rule | `catalog_only_boundary` |
| Wij2015-R1 | Perceived necessity and functionality rule | `active_grouped` |
| Wij2015-R2 | Expectation and contextual-integrity rule | `active_grouped` |
| Wij2015-R3 | Visibility and active-use rule | `active_grouped` |
| Wij2015-R4 | Individual-history calibration rule | `active_grouped` |
| Wij2015-R5 | Context-scoped authorization ledger rule | `candidate_future` |
| Wij2015-R6 | Context-over-data-type rule | `active_grouped` |
| Wij2015-R7 | Prompt-burden and selective-prompting rule | `deferred_longitudinal` |
| Wij2015-R8 | Static privacy-attitude insufficiency rule | `active_grouped` |
| Malkin-R1 | Scoped disclosure and requester-identity rule | `candidate_future` |
| Malkin-R2 | Denial-reason separation rule | `active_grouped` |
| Malkin-R3 | Anomaly attention and false-allow rule | `candidate_future` |
| Malkin-R4 | Prompt-burden and interruption rule | `deferred_longitudinal` |
| Malkin-R5 | Persistent-scope comprehension and renewal rule | `candidate_future` |
| Malkin-R6 | Automation-control heterogeneity rule | `active_grouped` |
| Malkin-R7 | Review and audit are not a safety substitute rule | `active_grouped` |
| Malkin-R8 | Consequential-action and sensitive-data safety rule | `catalog_only_boundary` |
| Harborth-R1 | Contextualized-purpose explanation rule | `active_grouped` |
| Harborth-R2 | Explanation is not an allow-nudge rule | `active_grouped` |
| Harborth-R3 | Current functional necessity and least-privilege rule | `active_grouped` |
| Harborth-R4 | Perceived privacy-danger rule | `active_grouped` |
| Harborth-R5 | Risk-perception gap and novel-sensor caution rule | `catalog_only_boundary` |
| Harborth-R6 | Scope, timing, and revocability disclosure rule | `active_grouped` |
| Harborth-R7 | Readability and progressive-detail rule | `active_grouped` |
| Harborth-R8 | Temporal foreground-scope rule | `active_grouped` |
| Esterwood-R1 | Repeated verified-violation accumulation rule | `deferred_longitudinal` |
| Esterwood-R2 | No full reset after verbal repair rule | `deferred_longitudinal` |
| Esterwood-R3 | Denial after verifiable error penalty rule | `deferred_longitudinal` |
| Esterwood-R4 | Trust-dimension separation rule | `deferred_longitudinal` |
| Esterwood-R5 | Integrity is not cheaply repairable rule | `deferred_longitudinal` |
| Esterwood-R6 | Do not over-rank apology, explanation, and promise rule | `deferred_longitudinal` |
| Esterwood-R7 | Verified-violation trigger boundary rule | `catalog_only_boundary` |
| Esterwood-R8 | No direct privacy-choice calibration rule | `catalog_only_boundary` |

## 4. 12 principles 的 v2.0 实现审计

| Principle | Excel coverage | v2.0 实现状态 | 当前能做什么 | 仍不能声称什么 |
|---|---|---|---|---|
| P1 Trust Loss Asymmetry | 部分覆盖 | **部分 stateful** | verified negative event 可进入 caution；普通 denial 不算 violation | 没有不对称幅度、事件严重度或人类累积曲线 |
| P2 Trust Recovery Lag | 部分覆盖 | **部分 stateful** | repair 进入 recovery/residual caution，不清空 ledger | 没有恢复时长、窗口或真实恢复轨迹 |
| P3 Recency Dominance | 未覆盖 | **audit metadata only** | 记录 event order、age 和 recency bucket | 没有 decay、近期支配或数值加权 |
| P4 Expectation Violation | 已覆盖 | **directional rule** | 显式 mismatch 时提高谨慎 | 当前 questionnaire sidecar 未提供 expectedness，因此默认 inactive/unknown |
| P5 Perceived Control | 已覆盖 | **directional + consent state** | 处理 scope/duration/revocation/review；维护 consent status | 当前 questionnaire sidecar 未提供大部分控制字段；没有控制感因果系数 |
| P6 Transparency Calibration | 已覆盖 | **directional rule** | explanation/provenance/readability 用于理解校准 | 当前 sidecar 未提供相关字段；透明度不等于 allow |
| P7 Permission Fatigue | 已覆盖 | **audit + 部分 stateful** | 保存 explicit burden、interruption、unresolved history | 没有 fatigue-to-choice 映射或真实疲劳概率 |
| P8 Severity Dominance | 未覆盖 | **external safety boundary only** | 明确阻止 respondent preference 代替 objective safety gate | 没有 respondent severity oracle；不应在 S-QSTN 内强行补齐 |
| P9 Privacy Calculus | 部分覆盖 | **partial directional** | necessity、privacy danger、scope、deny reason 的定性权衡 | 没有统一 benefit-cost 数值模型 |
| P10 Stable Privacy Trait | 已覆盖 | **profile soft prior** | 三类 empirical profiles 调节默认倾向 | 不是心理诊断或对所有 context 都有效的硬 policy |
| P11 Context Dependency | 已覆盖 | **directional/context active** | item/tool/requester/purpose/scope 分别判断；缺失保持 unknown | 不能从问题文本或全局 allow rate 推断隐藏 context |
| P12 Trust Calibration | 部分覆盖 | **部分 stateful** | 分开保存 competence/integrity/benevolence | 没有 reliability-to-reliance 或四标签选择校准 |

因此不能写“12/12 fully implemented”。更准确的总括是：

> v2.0 has explicit coverage or boundary handling for all twelve principles, but their operational depth ranges from active qualitative behavior to partial state substrate, audit-only metadata, and external safety separation.

## 5. 实际运行检查，而不只是文件检查

本次复核在不调用 API 的情况下重新运行了 v2.0：

- v2-specific unit tests：**9/9 passed**；
- inherited + v2 RulePack tests：**29/29 passed**；
- label-free memory fixtures：**6 个成功生成**；
- personas：**201**；
- profile distribution：71 `persistent_granters`、100 `reconsent_seekers`、30 `broad_restrictors`；
- questionnaire items：**373**；
- offline audit rows：**1,119 = 3 profiles × 373 items**；
- target answer columns：absent；
- numeric behavior parameters：absent；
- API call：**false**。

当前 questionnaire/context 输入的实际 activation 结果：

- 1,119/1,119 行激活 P9、P10、P11；
- 1,119/1,119 行将 P4、P5、P6 记录为 unknown，因为当前 sidecar 没有 expectedness、control、transparency 等显式字段；
- synthetic verified-scope-violation fixture 成功更新 `trust_integrity=caution`、`memory_caution=active`、`consent_status=refresh_required` 和 recency metadata。

这说明 engine 能运行且边界生效，但也说明“rule 文件存在”不等于“在当前每一道题上都会激活”。若最终小实验希望观察 P4/P5/P6，实验场景必须显式提供对应 context；不能让 LLM 自行猜测。

## 6. v2.0 + persona/profile 是否足以结束人类侧设计

### 6.1 本项目范围内：可以

如果人类侧的任务被限定为：

- 回答 privacy/data permission 四选一问题；
- 表现出不同 profile 的稳定倾向；
- 根据显式 context、necessity、scope、transparency 和 control 信息调整判断；
- 对 verified error、scope violation、repair 和 prompt burden 保留有限历史；
- 作为 personal assistant security 实验之外的辅助对照；

那么 v2.0 + empirical profile cards v2 已经足够作为本论文的 human-side S-QSTN 工具，可以冻结设计。

### 6.2 可以使用的名称

- human-inspired privacy-permission respondent simulator
- profile-conditioned S-QSTN respondent
- rule-informed and bounded-memory human-side agent
- privacy- and security-focused QSTN respondent simulator

### 6.3 不应使用的名称或结论

- complete human behavior model
- psychologically validated human agent
- human-equivalent respondent
- fully calibrated human memory model
- complete implementation of all 56 rules and 12 principles

“security-focused”在这里表示它重视 least privilege、scope、revocation、verified violation 和 privacy boundaries；它不是客观安全 oracle，也不会替 personal assistant 做安全决策。P8 保留在 assistant/security layer 正好符合论文主线。

## 7. 最后小规模对照实验的建议定义

| Condition | 建议定义 |
|---|---|
| Human | held-out human responses；不参与 profile wording 或 rule tuning |
| Vanilla QSTN | 原始 QSTN respondent pipeline；不加入 S-QSTN RulePack/StateStore；保持相同 base model、问卷和解码设置 |
| S-QSTN v2.0 | 相同 base model + persona/profile card v2 + RulePack v2.0 + respondent contract + explicit context + bounded StateStore |

建议控制：

- 固定相同 questionnaire items、base model、temperature、seed/repetition policy；
- profile card 仅来自 discovery split，不读取 held-out target labels；
- 每次 run 保存 model、seed、input hashes 和完整 version tuple；
- 对 S-QSTN 提供的 historical events 必须是 externally verified 或预先定义的实验事件；
- 将比较报告为 descriptive/exploratory：agreement、response distribution、profile/context subgroup differences；
- 如果 reviewer 要求拆分“profile card 的作用”和“rules/memory 的作用”，再增加一个可选 profile-only ablation；这不是当前结束人类侧设计的必要条件。

## 8. 是否需要 v3.0

按当前研究目标：**不需要。**

只有在以下任一项成为论文核心 claim 时，才需要 v3：

- 声称 S-QSTN 在统计意义上接近真实人类；
- 估计四个 permission labels 的 calibrated probabilities；
- 估计 trust loss/recovery 的真实幅度与持续时间；
- 估计 human forgetting/recency decay；
- 将 permission fatigue 定量映射到选择；
- 将 competence/integrity/benevolence 校准到具体 permission behavior。

当前建议是冻结 human-side scope，把研究资源转回 personal assistant security 主线。

## 9. 版本冻结建议

最终实验应记录至少以下 tuple：

```text
profile_card_version = empirical_profile_cards_v2
rule_pack_version = 2.0.0
respondent_contract_version = respondent_contract_v2.0.en
state_schema_version = 2.0.0
behavior_mode = stateful_audit_compatible
skill_mode = active_excerpt
human_calibration = not_claimed
model + seed + input hashes
```

`full_catalog_with_active_excerpt` 如被使用，必须作为独立实验配置记录，因为它改变了 LLM 可见的 prompt 内容。

## 10. “不考虑 v1/v1.1 文件”的技术说明

从论文与实验条件角度，可以只把 **S-QSTN v2.0** 当作最终累计版本，不需要再单独报告 v1.0/v1.1。

但从当前代码包装角度，`scripts/v2/rulepack_v2.py` 和 `scripts/v2/compile_s_qstn_v2.py` 仍导入 `scripts.v1` 与 `scripts.v1_1` 中的冻结 helper/validator。也就是说：

- 可以不把 v1/v1.1 当作独立实验版本；
- **暂时不能物理删除 v1/v1.1 代码目录**；
- 如未来要发布真正 standalone 的 v2 package，需要做一次纯 packaging refactor，但这不影响当前实验使用，也不要求开发 v3。

## 11. 审计来源与当前文件

- Excel registry：`QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`
- Canonical versioning：`ai_agent_permission_experiment/qstn_simulator/versioning.md`
- v2 config：`ai_agent_permission_experiment/qstn_simulator/config/v2.0/`
- v2 full rule catalog：`ai_agent_permission_experiment/qstn_simulator/config/v2.0/privacy_security_rule_skill.md`
- v2 machine RulePack：`ai_agent_permission_experiment/qstn_simulator/config/v2.0/security_behavior_rules.json`
- v2 runtime：`ai_agent_permission_experiment/qstn_simulator/scripts/v2/`
- profile cards：`ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards_v2.json`

## 12. 最终冻结结论

> S-QSTN v2.0 does not fully execute or human-calibrate every rule and principle in the evidence registry. It does, however, preserve the complete rule catalog, operationalize the active privacy/context rules, provide auditable bounded state for selected longitudinal principles, and combine these with empirical privacy profiles. This is sufficient for the paper's scoped, auxiliary human-side privacy-permission comparison, while the personal assistant remains the primary security research object.
