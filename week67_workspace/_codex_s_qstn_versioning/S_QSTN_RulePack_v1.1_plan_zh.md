# S-QSTN RulePack v1.1 计划（已确认并实施）

## 1. 先给结论

我建议把 v1.1 定义为“当前回合 context + uncertainty/burden audit extension”，而不是提前进入 v2 的 longitudinal StateStore。

v1.1 的默认运行模式应当是 `audit_compatible`：

- 增加显式 context schema；
- 增加基于字段完整性的 qualitative uncertainty bucket；
- 增加 current-turn prompt-burden bucket；
- 增加结构化 `reason_code` 和 rule activation trace；
- 保持 v1.0 的 permission-direction 行为不变；
- 不加入 numeric weight、confidence probability、trust/fatigue state 或跨题历史。

另外可以提供一个明确标记的 `qualitative_exploratory` 模式，用于 synthetic fixtures 和小规模 prompt ablation。它不能成为默认 S-QSTN，也不能直接作为论文主结果，除非后续单独冻结并验证。

这样做的核心原因是：当前 373 个 questionnaire item 只有 query、domain、tool、data type 和 necessity 等字段。请求方、purpose、scope、duration、expectedness、explanation、provenance、revocation、review 和 prompt frequency 并没有被结构化提供。v1.1 应先把“信息是否存在”记录清楚，而不是从题目文本或 participant label 中猜出这些变量。

## 2. v1.1 解决什么问题

### 2.1 从“unknown”变成可审计的 unknown

v1.0 已经不会推断缺失字段，但 audit 目前主要记录 unknown field 和 unknown rule。v1.1 要进一步回答：

- 缺少的是核心 context，还是可选 context？
- 当前问题是否适合做 privacy calculus？
- 当前 prompt burden 是没有发生、暂不适用、显式存在，还是未知？
- 这次行为方向来自 necessity、profile prior、context mismatch，还是仅仅来自信息不足？

### 2.2 让 P4/P5/P6 能通过公共 context 正确激活

v1.0 的 P4/P5/P6 engine 已经存在，但当前 questionnaire 没有 expectedness、control 和 transparency 字段，因此它们大多保持 unknown。v1.1 不直接改成数值规则，而是新增一个 sidecar context 文件，让 PA/wrapper 能够显式提供这些字段。

### 2.3 只处理 current-turn burden

Excel 中的 P7 证据支持 prompt burden 和 habituation 的设计动机，但当前 single-item runner 没有跨题 prompt history。因此 v1.1 只能记录：

- 当前请求是否被标记为重复或打扰性较高；
- 这个标记由谁提供、依据是什么；
- 当前 runner 是否根本不适合评估 burden。

不能把“当前题目有 burden”写成 participant 已经发生长期 fatigue，也不能自动把 burden 映射成 deny 或 allow。

## 3. v1.1 的边界

### 3.1 明确包含

1. 一个独立的 `context_schema_v1.1`。
2. 一个独立的 `config/v1.1/security_behavior_rules.json`，保留 v1.0 的六条 grouped rules，并增加 v1.1 的 audit/context rules。
3. 一个独立的 `config/v1.1/privacy_security_rule_skill.md`，继承 56 条完整 catalog，并补充 v1.1 的 operational boundary。
4. 一个独立的 `config/v1.1/respondent_contract.en.md`，说明 uncertainty 是信息完整性 bucket，不是 model confidence。
5. deterministic `uncertainty_bucket`、`prompt_burden_bucket` 和 `reason_code`。
6. compiler、held-out runner、manifest 和 audit CSV 的版本化支持。
7. v1.0 compatibility regression 和 v1.1 audit-only verification。

### 3.2 明确不包含

- 不修改 QSTN core。
- 不维护跨题 trust、fatigue、recency、violation、repair 或 recovery。
- 不引入 `weight`、`logit_delta`、probability、confidence threshold 或 softmax mapper。
- 不从 `question_content` 自然语言中自动推断 expectedness、purpose、risk、scope 或 burden。
- 不把 human `label_id`、`label_text` 或 observed Task 3 结果带入 prompt、context sidecar 或 rule audit。
- 不把 participant 的 ordinary denial 记为 agent violation。
- 不把 P8 severity 或高风险判断放入 respondent simulator；它仍属于独立 safety/task oracle。
- 不把 P1/P2/P3/P12 的长期 trust/recency 规则提前实现。

## 4. 推荐的 v1.1 runtime modes

### Mode A: `audit_compatible`（推荐默认）

这是 v1.1 的正式默认模式。

- 使用 v1.1 context schema；
- 运行 v1.0 的六条 permission rules；
- 计算 uncertainty、burden 和 reason codes；
- 将这些结果写入 audit 和 manifest；
- prompt 中只加入“不得从未知字段推断、burden 不等于长期 fatigue”的 bounded contract 信息；
- 不新增会直接改变四选项答案方向的 burden effect。

该模式的目的，是先确认数据和审计链条是否正确。它可以与 v1.0 做严格 regression comparison。

### Mode B: `qualitative_exploratory`

这是可选的探索模式，不作为 v1.1 默认，也不直接作为论文主条件。

它可以把两类当前回合 guardrail 编译为 prompt context：

- **Context insufficiency guardrail:** 如果核心 context 不完整，prefer clarification 或 lower-commitment interpretation，并避免跨 context generalization；不自动 deny。
- **Selective prompt-burden guardrail:** 如果 wrapper 明确提供 medium/high current-turn burden，避免 redundant re-asking；不能压制 mandatory consent refresh，也不能把 burden 机械地变成 deny。

这两个 guardrail 是 direction-only design constraints，不是从 Excel 直接估计出来的 participant probability。它们的 prompt effect 必须与 Mode A 分开记录、分开 ablate。

## 5. Context schema 设计

### 5.1 设计原则

每个字段都必须包含：

- allowed values 或类型；
- `source_policy`：`source_dataset`、`explicit_annotation`、`runner_default` 或 `unknown`；
- 是否允许进入 respondent prompt；
- 缺失时的处理；
- 关联 principle/rule IDs。

不能只在 CSV 中增加一列而不记录它是“原始事实、人工 annotation 还是 wrapper default”。

### 5.2 建议字段

| Field group | Fields | v1.1 treatment |
|---|---|---|
| Existing core | `questionnaire_item_id`, `query_id`, `domain`, `tool`, `raw_data_type`, `generic_data_type`, `necessity_status` | Preserve v1.0 values; direct source fields only. |
| Request context | `requester_id`, `requester_visibility`, `foreground_task`, `purpose_status` | Optional explicit fields; unknown is retained, never inferred from prose. |
| Expectation | `expectedness`, `expectation_match` | Explicit annotation or runner input; activates existing P4 only when present. |
| Scope and control | `scope`, `duration`, `scope_explicit`, `duration_explicit`, `revocable`, `review_available`, `required_vs_optional`, `consequence_of_decline` | Explicit public context; activates existing P5 only when present. |
| Transparency | `explanation_present`, `explanation_timing`, `provenance_present`, `explanation_source`, `explanation_readability` | Explicit public context; activates existing P6 only when present. |
| Current-turn burden | `prompt_burden_signal`, `prompt_burden_bucket`, `burden_basis`, `presentation_mode` | Current-turn only. `single_item` defaults to `not_applicable_single_item`, not to low or high fatigue. |
| Audit derivations | `uncertainty_bucket`, `unknown_context_fields`, `unknown_context_categories`, `reason_codes` | Deterministically computed by wrapper; not human labels and not model confidence. |

### 5.3 Sidecar rather than mutation

我建议生成独立的：

`outputs/questionnaire_context_v1.1.csv`

它以 `questionnaire_item_id` 为 key，与现有 `questionnaire_items.csv` 一对一关联。这样可以：

- 保留 v1.0 input 不变；
- 清楚区分原始数据和 v1.1 annotation；
- 允许 future PA 提供 context 时替换 sidecar，而不重写 benchmark；
- 在 manifest 中分别记录 questionnaire hash 和 context-sidecar hash。

当前 373 个 item 的 default sidecar 应只填入已有的直接字段，并将没有证据的字段写为 `unknown`。不因为 query 文本看起来像某种 purpose 就自动填值。

## 6. Qualitative bucket 定义

### 6.1 `uncertainty_bucket`

它表示“可用于当前 privacy decision 的显式 context 完整度”，不表示 LLM 的主观 confidence，也不表示某个答案的概率。

| Bucket | Deterministic condition | Behavioral meaning |
|---|---|---|
| `low` | Core request, requested data, tool/requester, and necessity are explicit; any scope field that is relevant to the item is also explicit. | Normal v1.0 evaluation; no extra uncertainty modifier. |
| `medium` | Core item and necessity are explicit, but one or more non-core expectation, control, transparency, visibility, or review fields are unknown. | Keep profile as a soft prior and log missing context; no automatic deny. |
| `high` | Core item/tool/task or necessity is unknown/ambiguous, or a scope/duration field needed to interpret the requested permission is unavailable. | Prefer clarification/lower commitment only in exploratory mode; audit-only mode records the limitation without changing the answer rule. |

The bucket must be computed from field status, not from model output, log probability, population frequency, or human labels. Thresholds must be schema conditions, not arbitrary numbers such as `confidence < 0.6`.

### 6.2 `prompt_burden_bucket`

Allowed values:

- `not_applicable_single_item`
- `none_explicit`
- `low_explicit`
- `medium_explicit`
- `high_explicit`
- `unknown`

The source of `medium_explicit` or `high_explicit` must be an explicit scenario or runner annotation. v1.1 must not infer burden from text length, number of tokens, participant denial, or the number of rows in the dataset. In the current single-item held-out runner, the safe default is `not_applicable_single_item`.

## 7. Reason-code design

Reason codes are structured audit facts, not hidden chain-of-thought and not a request for the LLM to explain its private reasoning.

### Proposed codes

| Code | Meaning |
|---|---|
| `NECESSITY_CURRENT_TASK` | Explicit necessity supports current scoped sharing. |
| `NECESSITY_NOT_USEFUL_NOW` | Current request is explicitly not useful now. |
| `NECESSITY_INCORRECT_EXPLICIT` | Request is explicitly inappropriate or incorrect for the current task. |
| `NECESSITY_UNKNOWN` | Necessity is not explicitly available. |
| `EXPECTATION_MISMATCH` | P4 trigger matched from explicit context. |
| `EXPECTATION_UNKNOWN` | P4 could not be evaluated without inference. |
| `CONTROL_SCOPE_OR_REVOCATION_EXPLICIT` | P5 control information is explicitly available. |
| `TRANSPARENCY_EXPLICIT` | P6 explanation, provenance, or timing information is explicit. |
| `PROFILE_PRIOR_APPLIED` | P10 profile remains a soft prior. |
| `CONTEXT_SPECIFIC_JUDGMENT` | P11 requires item/tool/task-specific evaluation. |
| `CONTEXT_OPTIONAL_FIELDS_MISSING` | Optional context is missing; maps to medium uncertainty. |
| `CONTEXT_CORE_FIELDS_MISSING` | Core decision context is missing; maps to high uncertainty. |
| `BURDEN_NOT_APPLICABLE_SINGLE_ITEM` | No longitudinal/current repetition signal exists in single-item mode. |
| `BURDEN_EXPLICIT_CURRENT_TURN` | Current-turn burden was supplied by an explicit annotation. |
| `BURDEN_UNKNOWN` | Burden status was not supplied and cannot be inferred. |
| `PROFILE_DEFAULT_FALLBACK` | Unknown fields caused the wrapper to preserve the profile default. |

Each code should be accompanied by `rule_ids`, `field_basis`, and `source_policy` in a deterministic JSON trace. It should not contain free-form model reasoning.

## 8. Configuration folder convention

为了避免 `config/` 平铺文件混淆，所有 RulePack 版本资产现在按版本目录保存：

```text
config/
  v1.0/
    VERSION.md
    security_behavior_rules.json
    privacy_security_rule_skill.md
    respondent_contract.en.md
    respondent_contract.md
    heldout_calibration_s_qstn.json
  v1.1/
    VERSION.md
    security_behavior_rules.json
    privacy_security_rule_skill.md
    respondent_contract.en.md
    context_schema.json
    reason_codes.json
    heldout_calibration_s_qstn.json
```

文件名在版本目录内不再重复写版本后缀；真正的语义版本由父目录、JSON `version`、skill catalog version 和 manifest/hash tuple 共同确定。profile-card、legacy profile-only calibration 和其他非 RulePack 配置继续保留在 `config/` 根目录，不与 RulePack 资产混同。

## 9. RulePack v1.1 design

### 8.1 Versioning

Create a standalone file rather than mutate v1.0:

`config/v1.1/security_behavior_rules.json`

It should contain:

- `version: 1.1.0`;
- `parent_rule_pack_version: 1.0.0`;
- `context_schema_version: 1.1.0`;
- `audit_schema_version: 1.1.0`;
- `state_schema_version: none`;
- the unchanged six v1.0 grouped rules;
- explicit `audit_rules` for context completeness and current-turn burden;
- a `behavior_mode` declaration so audit-compatible and exploratory runs cannot be confused.

The first six grouped rule objects should be compared against v1.0 in tests. v1.1 should not silently alter their triggers or directional effects.

### 8.2 Skill and contract

Create:

- `config/v1.1/privacy_security_rule_skill.md`
- `config/v1.1/respondent_contract.en.md`

The skill file should preserve all 56 concrete entries and add a v1.1 operational section. It should explicitly distinguish:

- empirical source rules;
- wrapper-derived information-completeness guardrails;
- current-turn burden annotations;
- deferred longitudinal rules;
- independent safety boundaries.

The contract should add only the decision boundary needed for v1.1: buckets describe available information, not confidence or probability; missing data remains unknown; burden does not mechanically determine allow or deny.

## 10. Implemented code and output changes

### 9.1 New files

- `config/v1.1/security_behavior_rules.json`
- `config/v1.1/privacy_security_rule_skill.md`
- `config/v1.1/respondent_contract.en.md`
- `config/context_schema_v1.1.json`
- `config/reason_codes_v1.1.json`
- `scripts/v1_1/build_context_v1_1.py`
- `tests/test_rulepack_v1_1.py`
- `config/v1.1/heldout_calibration_s_qstn.json`

### 9.2 Modified files

- `scripts/v1/rulepack_v1.py`: keep v1.0 API compatible; add schema validation, bucket derivation, audit-rule evaluation, and reason-code rendering.
- `scripts/v1/compile_s_qstn_v1.py`: add optional v1.1 context sidecar and versioned audit output, or use a thin v1.1 wrapper to preserve the v1.0 command unchanged.
- `scripts/runtime/run_heldout_calibration.py`: accept `--context`, `--behavior-mode`, and v1.1 version tuple; write sidecar hash and audit fields.
- `tests/test_rulepack_v1.py`: retain all v1.0 regression tests.
- `versioning.md`, `RULEPACK_V1.0_README.md`, `README.md`, and the Chinese design change log: record v1.1 after implementation is accepted.

I recommend a separate `compile_s_qstn_v1_1.py` thin wrapper rather than changing the default v1.0 compiler semantics. This reduces accidental cross-version output mixing.

## 11. Verification plan

### Phase A: Static schema verification

- Validate all v1.1 JSON files.
- Confirm all 56 skill entries remain present and English-only.
- Confirm sidecar has exactly one row per questionnaire item and no target columns.
- Confirm all unknown fields remain unknown.

### Phase B: Rule and audit verification

- Test low, medium, and high uncertainty fixtures.
- Test all burden bucket values and reject unsupported values.
- Test deterministic reason-code ordering and source mapping.
- Test that ordinary denial never creates a violation reason.
- Test that high burden never creates a safety decision.
- Test that v1.0 and v1.1 grouped rules are unchanged in compatibility mode.

### Phase C: QSTN prompt verification

- Run compiler without an API call.
- Validate the QSTN placeholder exactly once.
- Confirm all four canonical answer labels remain present.
- Confirm `label_id`, `label_text`, and `task3` do not appear in prompt/context/audit inputs.
- Run both `audit_compatible` and `qualitative_exploratory` preflight separately.

### Phase D: Regression and comparison

- Profile-card v1/v2 validators must still pass.
- v1.0 profile-only and RulePack dry-runs must still pass.
- v1.1 audit-compatible output must include 90/90 preflight prompts and version hashes.
- Report bucket distributions and unknown-field rates before any LLM call.
- Do not claim human-likeness or RulePack benefit from the dry-run.

### 已完成的 verification 结果

- v1.0 + v1.1 RulePack tests：20 tests passed。
- v1.1 context sidecar：373/373 questionnaire items，target columns absent。
- v1.1 compiler：201 personas × 373 items = 1,119 audit rows。
- v1.1 audit-compatible held-out dry-run：90/90 prompts validated，no API call。
- v1.1 full skill exposure dry-run：90/90 prompts validated，separate output directory。
- v1.0 profile-only held-out regression dry-run：90/90 prompts validated，no API call。

## 12. Experimental role

The paper-facing comparison should remain frozen as:

1. Human responses.
2. Vanilla QSTN.
3. Profile-only S-QSTN.
4. Profile plus v1.0 RulePack, if the paper scope supports the ablation.

v1.1 audit-compatible mode is primarily an engineering and audit upgrade; because it should preserve v1.0 behavior, it can be used as a reproducibility check rather than silently replacing v1.0 in the main comparison.

The exploratory qualitative mode should first use synthetic fixtures with explicit context annotations. It should not be tuned on the held-out human labels. If it later becomes a paper condition, it needs a separately frozen prompt version, evaluation split, and pre-registered analysis.

## 12. Acceptance criteria for calling v1.1 complete

I would consider v1.1 complete only when:

- the user-approved context schema is frozen;
- v1.0 files remain reproducible;
- v1.1 has a standalone rulepack, skill, contract, schema, and config;
- all 56 source rules remain traceable;
- uncertainty and burden are categorical and source-auditable;
- no numeric probability or state update is present;
- compatibility and exploratory modes are clearly separated;
- all prompt, label-leakage, and dry-run tests pass;
- `versioning.md` contains the full file inventory and version tuple;
- no LLM calibration result is claimed before a separate approved run.

## 13. Decisions needed before implementation

请确认以下三项：

1. 是否同意把 v1.1 默认模式定为 `audit_compatible`，不直接改变四选项答案方向？（推荐同意）
2. 是否同意使用独立 `questionnaire_context_v1.1.csv` sidecar，而不修改 v1.0 的 `questionnaire_items.csv`？（推荐同意）
3. 是否同意把 `qualitative_exploratory` 只用于 synthetic/context fixture 和单独 ablation，不作为论文默认 S-QSTN？（推荐同意）

在这三项确认之前，不开始写 v1.1 代码、不覆盖 v1.0 配置、不运行 LLM calibration。
