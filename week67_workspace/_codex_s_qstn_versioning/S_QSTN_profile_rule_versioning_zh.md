# S-QSTN Profile Card 与 RulePack 版本路线

## 结论

可行，而且目前最合适的不是把 S-QSTN 做成一个完整的“类人长期认知项目”，而是做成 QSTN 上面的项目专用 respondent layer：

```text
QSTN core
  └─ local wrapper
       ├─ profile card：稳定的隐私偏好先验
       ├─ RulePack JSON：情境触发器、方向性影响、版本和证据
       ├─ respondent contract / skill.md：判断顺序、边界和禁止事项
       └─ StateStore（后续）：历史事件和有限状态变化
```

当前没有可靠的行为权重时，JSON 仍然有用，因为 JSON 是数据格式，不等于必须包含数值权重。第一阶段可以保存“在什么条件下倾向于什么方向”的可审计规则；等有新的真人标注或纵向数据后，再把其中一部分升级为经过校准的数值模型。

本轮只形成设计，不修改现有 QSTN、profile-card JSON 或 Excel。

## 1. 两版 profile card 回顾

文件分别是：[empirical_profile_prompt_cards.json](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards.json) 和 [empirical_profile_prompt_cards_v2.json](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards_v2.json)。两版都来自 `behavior_profiles_v1`、`discovery_only` 数据切分，都是 K=3 的描述性行为 profile，不是经过验证的心理学构念。

| profile | v1 的核心默认 | v2 的收紧和澄清 |
|---|---|---|
| Persistent Granters | 偏好 enduring permission；有利于用户请求的情境更愿意授权。 | 只有当某个具体数据项对请求具有明确的持续性作用时，才支持 enduring grant；一次性或不清楚的需要应转为 temporary 或不分享。 |
| Re-consent Seekers | 愿意分享时，偏好当前 occasion，之后再次征求同意，而非 standing permission。 | 明确的当前、任务特定理由可以支持 temporary sharing，但不能自动推出 ongoing access。 |
| Broad Restrictors | 整体偏保守，倾向 decline/defer，跨观察情境分享意愿低。 | “对任务有帮助”本身不足以推翻不分享默认；不确定时优先 non-sharing，temporary 是例外，enduring 很少见。 |

真正的版本差异不是换了 profile 或重新聚类，而是 v2 增加了：

- `parent_card_version`，明确它继承自 v1；
- `evidence_basis`，说明每个 profile 的措辞依据；
- `authoring_constraints`，禁止使用 held-out label、结果、指标和未经依据的心理动机；
- 一个 shared decision rule，把“具体数据项—具体工具—具体任务”分开判断，并把“相关/有帮助”与“持续授权”分开。

因此，v1 是较简洁的稳定偏好卡；v2 是更明确、对 privacy scope 更谨慎的 prompt-contract revision。v2 不是新的经验模型，应该作为独立 prompt version 评估，不能把 v1 的结果和 v2 的结果混在一起解释。

## 2. 四个层次不要混在一起

| 层次 | 负责什么 | 当前是否需要数值 |
|---|---|---|
| Profile card | 长期相对稳定的默认偏好，例如偏好 persistent、re-consent 或 restrictive | 不需要；它是 qualitative prior |
| RulePack JSON | 当前情境的触发器、适用范围、方向性影响、证据等级 | v1 不需要；`prefer/avoid/increase_caution` 已足够 |
| respondent contract / skill.md | “类人 respondent 如何判断”的顺序、解释规则、禁止臆造事实等 | 不需要；它是可读的行为协议 |
| Wrapper / StateStore | 激活规则、记录事件、更新状态、写日志、保证版本复现 | v2 才加入有限状态 |
| QSTN | 提供问卷提示、上下文模式、受约束输出和解析 | 不应承担长期人格或 trust 学习 |

这里的 skill.md 不应被理解为一个会自动学习的 agent。它是行为解释层；真正的激活、状态更新和可复现日志要由 wrapper 完成。QSTN 官方定位也是 questionnaire inference framework，现有的 prompt、presentation mode、response generation 和 parser 可以复用，长期 respondent memory 需要由项目 wrapper 提供：[QSTN GitHub](https://github.com/dess-mannheim/QSTN)，[QSTN EACL 2026 paper](https://aclanthology.org/2026.eacl-demo.37/)。

## 3. 建议的版本路线

版本号建议独立记录，不把所有变化塞进一个版本：

```text
profile_card_version       = empirical_profile_cards_v2
rule_pack_version          = security_behavior_rules_v1.0
respondent_contract_version= respondent_contract_v1.0
state_schema_version       = none / state_schema_v2
calibration_version        = qualitative_v1 / human_calibrated_v3
runner_version, model, seed, input_hash
```

语义版本规则如下：patch 只修文字、schema 校验或日志；minor 只增加向后兼容的规则；major 改变决策顺序、状态含义、输出标签或概率解释。每一次实验都保存完整 version tuple，held-out 的真人答案、目标标签和结果不能进入 prompt 编译过程。

### RulePack v1.0：静态、方向性、无长期状态

这是当前最应该实现的版本，配合 profile card v2。每道题开始时状态重置，不维护跨题 trust、fatigue 或 violation count。

可实现的 principle：

- P4 Expectation Violation Effect：情境与预期不匹配时，提高谨慎、拒绝或要求解释的倾向；
- P5 Perceived Control：有 scope、duration、revocation、review 或 user control 时，更容易接受可控的授权方式；
- P6 Transparency Calibration：解释的存在、时机、可读性和 provenance 影响理解与选择，但不能写成“有解释就应该 allow”；
- P10 Stable Privacy Trait：由 profile card 提供稳定先验，但不是硬策略；
- P11 Context Dependency：把 data type、requester、task、timing、visibility、scope 与历史相似性作为情境字段；
- P9 Privacy Calculus 的一部分：区分当前必要性、实用性、scope 和 deny reason，但不声称已有统一的 benefit-minus-privacy-cost 数值公式。

v1 的 respondent contract 可以按以下顺序工作：

```text
解析具体数据项、requester、tool、task、scope、duration
→ 判断是否符合当前情境预期
→ 判断当前必要性与隐私风险；区分“现在没用”与“本身不合适”
→ 应用 profile 的稳定默认
→ 应用 explanation、control、scope、revocation 等方向性修正
→ 在四个固定选项中选择一个；不补造目的、事实或安全结论
```

v1 JSON 中可以写成如下语义，而不必填任意 `weight`：

```json
{
  "rule_id": "P4.expectation_mismatch",
  "trigger": ["request_is_unexpected", "purpose_not_explained"],
  "effect": {
    "caution": "increase",
    "ask_for_explanation": "prefer",
    "persistent_grant": "avoid"
  },
  "strength": "qualitative",
  "scope": "current_item_only",
  "evidence_level": "directional"
}
```

### RulePack v1.1：当前回合的 burden 和 uncertainty

Excel 对 permission fatigue 的覆盖较好，但它不足以直接证明“连续多次提问后某个 participant 必然 deny”。所以 v1.1 只加入当前实验中可观察、可审计的字段，例如 prompt 是否重复、选项是否含糊、当前请求是否缺少必要信息，并输出 `reason_code` 或 `uncertainty_bucket` 供日志和分析使用。

这一版可以实现“当前题更可能要求澄清或选择较低承诺选项”的方向，但不声称已经实现跨轮次 fatigue、habituation 或长期变化。不要在 v1.1 中放一个未经校准的 `fatigue_weight = 0.7`。

### RulePack v2.0：有限状态和历史事件

只有在 v1 的静态比较完成后，再引入外置 `StateStore`。QSTN core 仍不改，wrapper 负责把公开历史和经过判定的内部状态编译进 respondent contract。

建议第一批只使用 bounded/categorical state，不使用概率：

```text
similar_history_ledger: none / weak / strong
prompt_burden_bucket: low / medium / high
verified_violation_count: 0 / 1 / 2+
caution_level: baseline / elevated / high
recovery_status: none / pending / gradual
```

状态事件必须有明确边界：

| 事件 | 状态处理 |
|---|---|
| respondent 普通 deny | 这是用户偏好，不是 agent violation；不扣 trust |
| 重复出现的 permission prompt | 有界地增加 prompt burden；不能无限累积 |
| 外部 oracle 验证的 scope violation、false statement 或错误行为 | 增加 caution/violation state；必须由 oracle 或实验标签确认，不能由模型自判 |
| 透明、正确、及时的 repair | 只做 bounded mitigation，不立即完全恢复信任 |
| 后续连续的正确行为 | 允许慢速、有限 recovery；不因一次成功就清零 |

这一版可以承接 Excel 中的 P7 longitudinal fatigue，以及 P1 Trust Loss Asymmetry、P2 Trust Recovery Lag、P12 Trust Calibration 的部分内容。P1/P2/P12 目前主要是方向性、且有跨领域证据，不能直接变成 privacy choice 的普适系数。P3 Recency Dominance 和 P8 Severity Dominance 仍应暂缓；severity 还要区分 respondent 的感知谨慎与系统的客观安全 oracle。

v2 的隐藏状态只用于模拟 respondent 的后续判断和审计，不应作为问卷题目答案泄露给被模拟的公共代理人，也不应成为系统安全 gate。必须加入 event-classification tests、transition tests、state-isolation tests 和固定 trajectory fixtures。

### RulePack v3.0：真人数据校准后的数值层

只有当我们收集了新的真人标注、明确 train/calibration/held-out split，并且有足够的 profile × context × state 覆盖后，才引入 `weight`、`logit_delta` 或概率。

四个答案选项可以使用外部 policy mapper：

```text
z_y = alpha_profile,y
    + beta_y · context_features
    + gamma_y · state_features
    + eta_y · profile_context_interactions
P(y) = softmax(z_y)
```

这时每个系数必须附带 estimator、样本量、数据切分、置信区间或 bootstrap 区间、校准日期和 calibration version。把 `weight: 0.6` 写入 prompt 并不能让 LLM 产生 60% 的人类选择概率；如果需要数值行为，应由外部 mapper 控制，或严格校准 QSTN 的 logprob 输出。QSTN 的 token logprob 也不能直接当成人类回答概率。

v3 才适合处理 P3 recency/time decay、P8 severity、完整的 P9 privacy calculus、P12 actual reliability 与 trust/reliance calibration，以及 profile × context interaction。skill/contract 在这一版仍保留，用来解释 feature 的含义和保证规则边界，但不再独自决定概率。

### RulePack v4.0：纵向/RL 集成冻结

如果以后确实需要接入 RL 或长期运行，v4 才做 schema freeze、backward compatibility、独立 runner、状态隔离审计、重复纵向验证和 evaluation freeze。RL 不应成为弥补 v1/v2 没有证据的方式；它只能在已有状态定义、事件 oracle 和真人校准基础上优化。

## 4. QSTN 要不要改结构？

当前建议不修改 QSTN core。保留 QSTN 负责的四件事：问卷提示生成、single/sequential/battery presentation、受约束的四选项输出、结果解析。项目 wrapper 在外面增加结构化 context，例如：

```text
candidate_id, data_type, requester, tool, purpose,
scope, duration, timing, visibility, explanation,
expectedness, necessity_status, history_summary
```

v1 由 wrapper 把 `profile_card_v2 + respondent_contract_v1.0 + active directional rules + 当前 context` 编译为 system/questionnaire instruction；用同一组四个 canonical labels 运行。v2 才由 wrapper 读取公开历史、更新私有 StateStore，并选择 single-item 或带公共历史的 sequential presentation。v3 才在 QSTN 输出和最终 label 之间增加外部 calibrated mapper。

因此，不是“JSON 或 skill.md 二选一”，而是：

```text
JSON = 机器可读的规则、触发器、版本、状态 schema 和证据
skill/contract = 人类可读的判断程序、语义边界和禁止事项
wrapper = 执行、状态更新、日志和实验复现
QSTN = 问卷推理和受约束回答接口
```

不要要求 respondent 暴露隐藏 chain-of-thought。若需要分析，记录结构化的 `reason_code`、触发的 rule id、状态 bucket 和最终 label 即可。

## 5. 目前的实验闸门

推荐的操作顺序是：

1. 冻结 profile card v2，并保持 v1 与第一批 held-out diagnostic 不变。
2. 创建 `config/v1.0/security_behavior_rules.json` 和 `config/v1.0/respondent_contract.md`，只放方向性规则。
3. 做 schema validation、rule activation tests 和 prompt compilation tests；不改 QSTN core。
4. 在同一批 held-out questions 上比较 human、vanilla QSTN、profile-only S-QSTN 与 profile-plus-RulePack S-QSTN。论文主结果可以报告前三个预注册条件，profile-only 作为内部 ablation，帮助判断提升究竟来自 profile 还是 RulePack。
5. 只有 v1 的结果和错误类型稳定后，才新建 v2 StateStore 和纵向事件实验；状态版必须使用新的 evaluation split。
6. 真人数据足够后，才建立 v3 calibration model 和数值权重。

所以答案是“可行”，但论文中要准确地把当前 S-QSTN 定义为：基于经验 profile、方向性 privacy behavior rules 和受约束 respondent contract 的 QSTN conditioning layer，而不是已经验证的完整类人认知或长期信任模拟器。这个范围既能支持 human vs vanilla QSTN vs S-QSTN 的小规模比较，也能为后续状态和数值校准留下清楚的迭代路径。

## 6. RulePack v1.0 已实现的文件记录

项目内的 canonical versioning 文件为：

`D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/versioning.md`

v1.0 已新增或修改以下文件：

| 文件 | 位置 | 简介 |
|---|---|---|
| `config/v1.0/security_behavior_rules.json` | `qstn_simulator/config/v1.0/` | 机器可读的静态方向性 RulePack，包含 P4、P5、P6、部分 P9、P10、P11；无 weight、state update 或安全硬门。 |
| `config/v1.0/respondent_contract.md` | `qstn_simulator/config/v1.0/` | 中英文 respondent 行为协议，规定判断顺序、profile 软先验和未知字段不推断。 |
| `config/v1.0/heldout_calibration_s_qstn.json` | `qstn_simulator/config/v1.0/` | profile-card v2 + RulePack v1.0 的独立诊断配置，不等于最终论文 evaluation split。 |
| `config/v1.0/VERSION.md` | `qstn_simulator/config/v1.0/` | v1.0.0/v1.0.1 版本说明、文件清单和从旧平铺路径迁移的记录。 |
| `rulepack_v1.py` | `qstn_simulator/scripts/` | JSON 校验、触发器评估、方向性 effect 渲染、prompt 注入和 audit helper；不调用 LLM。 |
| `compile_s_qstn_v1.py` | `qstn_simulator/scripts/` | 离线生成 persona template、profile × questionnaire rule audit 和 manifest。 |
| `run_heldout_calibration.py` | `qstn_simulator/scripts/` | 增加可选 `--rulepack`/`--contract` 接口；不传这两个参数时保持原 profile-only 行为。 |
| `RULEPACK_V1.0_README.md` | `qstn_simulator/` | 中英文实现说明、规则范围、命令和文件清单。 |
| `versioning.md` | `qstn_simulator/` | canonical 版本路线、v1.0 实现记录和后续 recap 清单。 |

本次未修改：QSTN core、`empirical_profile_prompt_cards.json`、`empirical_profile_prompt_cards_v2.json`、benchmark 数据集和 Excel workbook。`outputs/s_qstn_v1_0/` 只作为本地编译产物，不是规则 source of truth。

## RulePack v1.0.1 skill catalog integration record

The canonical archive was updated at:

`D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/versioning.md`

This iteration keeps the v1.0 JSON semantics but adds the requested two-layer implementation:

- `qstn_simulator/config/v1.0/privacy_security_rule_skill.md`: English-only complete catalog of all 56 concrete evidence-registry rules. Each rule records its source ID, principle, evidence rating, behavioral interpretation, evidence boundary, and runtime status.
- `qstn_simulator/config/v1.0/security_behavior_rules.json`: English-only executable layer with six grouped rules. Its `skill_section` fields point back to the concrete catalog; it still has no numerical weights and no state updates.
- `qstn_simulator/config/v1.0/respondent_contract.en.md`: English-only respondent contract used by the new diagnostic configuration. The bilingual contract remains unchanged for historical reproducibility.
- `qstn_simulator/scripts/v1/rulepack_v1.py`: validates and loads the English catalog and supports `active_excerpt` and `full_catalog_with_active_excerpt` prompt modes.
- `qstn_simulator/scripts/v1/compile_s_qstn_v1.py`: records skill version, mode, and hash in offline compiler outputs.
- `qstn_simulator/scripts/runtime/run_heldout_calibration.py`: loads the catalog, injects it only when the full-catalog mode is explicitly selected, and records catalog metadata in preflight and run manifests.
- `qstn_simulator/config/v1.0/heldout_calibration_s_qstn.json`: now points to the English contract and skill catalog with default mode `active_excerpt`.
- `qstn_simulator/tests/test_rulepack_v1.py`: adds English-only and full-catalog prompt-exposure tests.

Runtime visibility is versioned explicitly: default `active_excerpt` exposes only the active qualitative RulePack context; `full_catalog_with_active_excerpt` exposes all 56 concrete rules but instructs the LLM to apply only entries marked `active_grouped`. Deferred longitudinal, future-candidate, evidence-only, and safety or system-strategy entries remain catalog constraints rather than active respondent behavior.

No QSTN core, profile-card JSON, benchmark data, or Excel workbook was modified. No LLM calibration call was made by this iteration.

## RulePack v1.1 implementation record

The canonical archive now records the approved v1.1 plan and implementation. Versioned configuration assets are grouped under `qstn_simulator/config/v1.1/`:

- `security_behavior_rules.json`: six unchanged v1.0 grouped rules plus two audit-only rules for context completeness and current-turn prompt burden.
- `privacy_security_rule_skill.md`: all 56 concrete English rules plus the v1.1 operational boundary.
- `respondent_contract.en.md`: English-only contract; uncertainty is information completeness, not model confidence.
- `context_schema.json`: explicit current-turn context fields and missing-value policy.
- `reason_codes.json`: deterministic audit reason-code registry without numeric behavior parameters.
- `heldout_calibration_s_qstn.json`: default `audit_compatible` held-out configuration.
- `VERSION.md`: Chinese/English version description and file inventory.

The implementation also added `scripts/v1_1/rulepack_v1_1.py`, `scripts/v1_1/build_context_v1_1.py`, `scripts/v1_1/compile_s_qstn_v1_1.py`, and `tests/test_rulepack_v1_1.py`. The generated `outputs/questionnaire_context_v1.1.csv` contains one row per questionnaire item; the verified compiler has 1,119 profile-by-item audit rows and the held-out audit-compatible dry-run validates 90 prompts without an API call.

The current single-item runner uses `not_applicable_single_item` for burden unless an explicit annotation is supplied. No label, numeric weight, longitudinal state, or hidden model confidence is used in v1.1 context construction or audit activation. `qualitative_exploratory` remains a separate synthetic/ablation mode.
