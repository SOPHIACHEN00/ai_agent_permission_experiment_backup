# S-QSTN RulePack v1.1 README

## 中文摘要

RulePack v1.1 是 v1.0 的 current-turn context + audit extension。它的默认模式是 `audit_compatible`：保留 v1.0 的六条 grouped directional rules，同时记录显式 context 的完整程度、当前回合 prompt burden 和 deterministic reason codes。

这一版不把 Excel 中尚未量化的证据强行变成 weight，也不把 uncertainty bucket 当成 LLM confidence 或答案概率。当前 `single_item` runner 默认使用 `not_applicable_single_item`，表示当前运行没有跨题重复 prompt 的 burden 证据；它不是 low fatigue，也不是 allow/deny 信号。

`qualitative_exploratory` 只用于 synthetic fixture 或 prompt ablation。它可以显示 bounded clarification / anti-redundancy guardrail，但必须与默认模式分开记录，不能直接当作论文主结果或 calibrated human model。

### v1.1 实现的内容

- 保留 v1.0 的 P4、P5、P6、partial P9、P10、P11 grouped rules，测试确认 grouped JSON objects 未改变。
- 新增 `context_schema.json`，把 requester、purpose、expectedness、scope、duration、control、transparency 和 burden 定义为显式字段。
- 新增 `reason_codes.json`，以确定性的 audit code 记录 necessity、unknown context、profile prior、burden 等来源。
- 新增一对一 `outputs/questionnaire_context_v1.1.csv` sidecar；没有证据的字段写为 `unknown`，不从 `question_content`、participant label、文本长度、deny 行为或 row count 推断。
- 新增 `scripts/v1_1/build_context_v1_1.py`、`scripts/v1_1/compile_s_qstn_v1_1.py` 和 `scripts/runtime/run_heldout_calibration.py` 的 v1.1 集成。
- 不修改 QSTN core，不引入 StateStore，不向 prompt/context/audit input 传入 human target labels。

## English summary

RulePack v1.1 is an additive current-turn context and audit layer. The default `audit_compatible` mode preserves the six v1.0 grouped directional rules and records explicit information completeness, current-turn prompt burden, and deterministic reason codes. It does not add numeric weights, probabilities, confidence thresholds, or longitudinal state.

The optional `qualitative_exploratory` mode is reserved for synthetic fixtures and prompt ablations. It may expose bounded clarification or anti-redundancy guardrails, but it is not the default S-QSTN condition and must be reported separately.

## Version-pinned files

All v1.1 configuration assets are grouped under `config/v1.1/`:

| File | Description |
|---|---|
| `config/v1.1/security_behavior_rules.json` | English-only RulePack. Inherits the six v1.0 grouped rules and adds audit-only context-completeness and current-turn-burden rules. |
| `config/v1.1/privacy_security_rule_skill.md` | English-only inheritance of all 56 concrete evidence-registry rules plus the v1.1 operational boundary. |
| `config/v1.1/respondent_contract.en.md` | English-only contract for unknown-field handling, audit-compatible mode, and burden limits. |
| `config/v1.1/context_schema.json` | English-only current-turn context schema and source-policy contract. |
| `config/v1.1/reason_codes.json` | English-only deterministic audit reason-code registry. |
| `config/v1.1/heldout_calibration_s_qstn.json` | Audit-compatible held-out diagnostic configuration. |
| `config/v1.1/VERSION.md` | Chinese/English version description and inventory. |

## Offline commands

From `qstn_simulator/`:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1_1.build_context_v1_1
.\.venv\Scripts\python.exe -m scripts.v1_1.compile_s_qstn_v1_1
.\.venv\Scripts\python.exe -m scripts.v1_1.compile_s_qstn_v1_1 `
  --behavior-mode qualitative_exploratory `
  --out outputs\s_qstn_v1_1_exploratory
.\.venv\Scripts\python.exe -m scripts.runtime.run_heldout_calibration `
  --config config\v1.1\heldout_calibration_s_qstn.json `
  --dry-run
```

The sidecar contains one row per questionnaire item. The compiler contains one audit row per profile-by-item pair. The held-out dry-run validates 90 prompts without an API call. Manifests record the v1.1 schema versions and SHA-256 hashes.

## One-item API diagnostic / 单题 API 诊断

The v1.1 API diagnostic loads the version-pinned RulePack, context sidecar,
English contract, and skill catalog, then renders exactly one QSTN permission
prompt. Use `--dry-run` first; without that flag it sends exactly one request
to the configured model and validates the four-option JSON response:

```powershell
.\.venv\Scripts\python.exe -m scripts.v1_1.smoke_test_openai_qstn_v1_1 --dry-run
.\.venv\Scripts\python.exe -m scripts.v1_1.smoke_test_openai_qstn_v1_1
```

The default is `audit_compatible` with `active_excerpt` skill exposure. This
diagnostic verifies API wiring and v1.1 prompt activation only; it is not a
calibration result, a formal comparison, or evidence of human-likeness. The
preflight and result artifacts are written to:

- `outputs/openai_qstn_rulepack_v1_1_smoke_test_preflight.json`
- `outputs/openai_qstn_rulepack_v1_1_smoke_test.json`

## Interpretation boundary

`uncertainty_bucket` is an information-completeness bucket. `prompt_burden_bucket` is a current-turn annotation. Neither is a numeric participant preference, a model confidence value, or a safety decision. Missing context remains unknown, and ordinary respondent denial remains a preference rather than an agent violation.
