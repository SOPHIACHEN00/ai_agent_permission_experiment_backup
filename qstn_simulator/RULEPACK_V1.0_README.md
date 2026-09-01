# S-QSTN RulePack v1.0 README

## 中文摘要

RulePack v1.0 是本项目第一版 S-QSTN respondent layer。它在现有 QSTN prompt、四选项输出和 empirical profile card 之上，增加静态、情境敏感、方向性 privacy rules。

这一版的边界是：

- 不修改 QSTN core；
- 不使用未经校准的 `weight`、`logit_delta` 或概率；
- 不维护跨题 trust、recency、fatigue、violation 或 recovery state；
- 不把普通用户拒绝视为 agent violation；
- 不执行真实工具调用，也不充当 personal assistant 的安全 gate；
- 缺失的情境字段不会被模型或 wrapper 推断，而会进入 audit。

### v1.0 实现的 rules

| Principle | v1.0 实现 | 说明 |
|---|---|---|
| P4 Expectation Violation | 已实现 | 显式 `expectation_match=false` 或 `expectedness=unexpected/mismatch` 时增加谨慎、偏好澄清、避免 persistent grant。 |
| P5 Perceived Control | 已实现 | 显式 scope、duration、revocation 或 review 信息时偏好可控、有限的 permission；不自动 allow。 |
| P6 Transparency Calibration | 已实现 | explanation、provenance、timing 影响理解和 informed choice；透明度不等于同意。 |
| P9 Privacy Calculus | 部分实现 | 使用 `necessity_status` 区分 necessary、not useful now、incorrect explicit、unknown；必要性只支持当前、具体、有限的 sharing。 |
| P10 Stable Privacy Trait | 已实现 | 保留 Persistent Granters、Re-consent Seekers、Broad Restrictors 的 profile prior，但只是软倾向。 |
| P11 Context Dependency | 已实现 | 要求分别判断具体 data item、tool、requester、purpose 和 scope，避免跨情境泛化。 |

P1、P2、P3、P7 longitudinal、P8 和 P12 没有在 v1.0 中激活。它们需要新的纵向事件定义、外部 oracle、真人校准或单独的 severity/recency 模型，计划放到 RulePack v2/v3。

当前的 `outputs/questionnaire_items.csv` 主要提供 `necessity_status`、tool 和 data-type 字段，没有显式的 expectedness、scope/revocation 或 explanation/provenance 字段。因此当前 audit 会实际激活 P9、P10、P11，并把 P4、P5、P6 的缺失字段记录为 unknown；这是一项“不推断未知情境”的保护，而不是漏实现。个人助理的未来公开 context 补充这些字段后，RulePack engine 会自动激活相应规则。

### 运行方式

从 `qstn_simulator` 目录运行：

```powershell
uv run python -m scripts.v1.compile_s_qstn_v1
```

该命令只做本地编译，不调用 LLM，默认读取：

- `outputs/empirical_personas_v2/personas_with_empirical_profiles.csv`
- `outputs/questionnaire_items.csv`
- `config/v1.0/security_behavior_rules.json`
- `config/v1.0/respondent_contract.md`

然后生成 `outputs/s_qstn_v1_0/` 下的静态 persona template、每个 profile × questionnaire item 的 rule audit 和 manifest。

验证 QSTN prompt rendering 和 v1.0 RulePack 接入：

```powershell
uv run python -m scripts.runtime.run_heldout_calibration `
  --config config/v1.0/heldout_calibration_s_qstn.json `
  --dry-run
```

`--dry-run` 不发送 API 请求。只有检查 prompt、split 和 audit 后，才可以考虑使用 `--execute`；论文正式比较必须使用新的、独立冻结的 evaluation split。

## English summary

RulePack v1.0 is the first project-specific S-QSTN respondent layer. It augments the existing QSTN prompt, constrained four-option response, and empirical profile card with static, context-sensitive, directional privacy rules.

The v1.0 boundary is intentionally narrow:

- QSTN core is unchanged.
- No uncalibrated `weight`, `logit_delta`, or probability is used.
- No cross-question trust, recency, fatigue, violation, repair, or recovery state is maintained.
- An ordinary respondent denial is not treated as an agent violation.
- The layer does not execute real tools or act as the personal assistant’s safety gate.
- Missing context fields are not inferred; they are recorded in the audit output.

The engine implements P4 Expectation Violation, P5 Perceived Control, P6 Transparency Calibration, partial P9 Privacy Calculus, P10 Stable Privacy Trait, and P11 Context Dependency. The current questionnaire CSV exposes necessity, tool, and data-type fields but not explicit expectedness, control, or transparency fields; therefore the current audit activates P9/P10/P11 and records P4/P5/P6 as unknown until those public context fields are supplied. P1/P2/P3/P7-longitudinal/P8/P12 are deferred to later versions.

### Full evidence-derived skill catalog

The JSON file is the executable grouped layer. The companion `config/v1.0/privacy_security_rule_skill.md` is the complete English catalog of all 56 concrete rules in the evidence registry. Each entry retains its source rule ID, principle link, behavioral interpretation, evidence boundary, and runtime status.

The default `active_excerpt` mode injects only the current active qualitative RulePack context. The optional `full_catalog_with_active_excerpt` mode injects the complete catalog as a reference together with the active context. In that mode, the LLM must apply only entries marked `active_grouped`; deferred longitudinal rules, future candidates, evidence-only entries, and safety or system-strategy boundaries are not respondent preferences.

This means the LLM sees all concrete rules only in the full-catalog mode. Both modes record the skill catalog version and SHA-256 hash in manifests so that prompt exposure is reproducible.

## v1.0 files / 文件清单

| File | Description |
|---|---|
| `config/v1.0/security_behavior_rules.json` | Machine-readable RulePack. Defines triggers, qualitative effects, evidence IDs, forbidden targets, and the `state_schema_version=none` boundary. |
| `config/v1.0/respondent_contract.md` | Bilingual respondent contract. Defines the decision order and non-inference rules; it is not chain-of-thought or a probability model. |
| `config/v1.0/respondent_contract.en.md` | English-only respondent contract used by the RulePack-enabled diagnostic. |
| `config/v1.0/privacy_security_rule_skill.md` | Complete English evidence-derived catalog of all 56 concrete rules and their runtime boundaries. |
| `config/v1.0/heldout_calibration_s_qstn.json` | Separate diagnostic configuration pairing profile-card v2 with RulePack v1.0. |
| `config/v1.0/VERSION.md` | Chinese/English version description, v1.0.0/v1.0.1 boundary, and folder inventory. |
| `scripts/v1/rulepack_v1.py` | Pure Python loader, schema validator, trigger evaluator, directional effect renderer, prompt injector, English skill loader, and audit helpers. It performs no LLM call. |
| `scripts/v1/compile_s_qstn_v1.py` | Offline compiler producing S-QSTN templates, profile × item RulePack audit rows, and skill metadata. |
| `scripts/runtime/run_heldout_calibration.py` | Held-out runner with optional RulePack, English contract, and skill-catalog support. It supports both prompt-exposure modes while preserving the profile-only path. |
| `tests/test_rulepack_v1.py` | Standard-library tests for stateless validation, trigger activation, unknown-field handling, prompt injection, and full-catalog exposure. |
| `RULEPACK_V1.0_README.md` | This bilingual implementation and usage guide. |
| `versioning.md` | Project-level version roadmap and implementation inventory; update it whenever a RulePack-related file or interface changes. |
| `SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md` | Existing design document updated with the v1.0 change-log entry. |
| `outputs/s_qstn_v1_0/` | Generated local artifacts from the reorganized v1.0 compiler; normally not a source file. |

## Output artifacts / 输出产物

The offline compiler writes:

- `s_qstn_personas.csv`: existing persona rows plus RulePack version and a per-question prompt-template marker;
- `rule_context_audit.csv`: active, inactive, and unknown rule IDs, explicit context, rendered directional context, and no target labels;
- `s_qstn_v1_manifest.json`: versions, input hashes, counts, and label-leakage guard.

The current v1.0 compile using the reorganized `config/v1.0/` assets is stored under `outputs/s_qstn_v1_0/` (201 personas, 373 questionnaire items, and 1,119 profile-by-item audit rows). Earlier skill-integrated outputs remain historical generated artifacts.

The held-out dry run additionally writes `preflight_manifest.json`, `inference_plan.csv`, `sampled_heldout_contexts.csv`, and, when RulePack is enabled, `rule_context_audit.csv` under its selected output directory.

To run the full-catalog prompt audit without an API call:

```powershell
uv run python -m scripts.runtime.run_heldout_calibration `
  --config config/v1.0/heldout_calibration_s_qstn.json `
  --skill-mode full_catalog_with_active_excerpt `
  --dry-run
```

## Version boundary / 版本边界

The profile card version and RulePack version are independent. A run should record at least:

```text
profile_card_version
rule_pack_version
respondent_contract_version
state_schema_version
runner_version
model
seed
input hashes
```

Do not tune v1.0 using the same held-out targets that are later reported as evidence. Any change to the decision order, state schema, public response interface, or probability interpretation requires a new major version or a separately documented calibration version.
