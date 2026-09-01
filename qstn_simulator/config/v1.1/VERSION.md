# S-QSTN RulePack v1.1 版本说明

## 版本定位

`config/v1.1/` 是在 v1.0 静态方向性 RulePack 上增加的 current-turn context 与 audit extension。它的默认运行模式是 `audit_compatible`：记录当前可见信息的完整性、prompt burden 边界和 deterministic reason code，但不改变 v1.0 的 permission-direction 行为。

本版本明确不实现：

- numeric weight、probability、confidence threshold 或 softmax mapper；
- 跨题 trust、fatigue、recency、violation、repair、recovery 等 state；
- 从 question text、participant label、文本长度、deny 行为或数据行数推断 purpose、expectedness、scope、duration、burden 或 hidden state；
- 把 burden 或 uncertainty bucket 直接映射为 allow、deny 或安全决策。

`qualitative_exploratory` 是可选模式，仅用于 synthetic fixture 和小规模 prompt ablation；不能与默认 audit-compatible 结果混合，也不应直接作为论文主条件。

## v1.1 文件

| File | Description |
|---|---|
| `security_behavior_rules.json` | English-only executable RulePack. It preserves the six v1.0 grouped rules and adds two audit-only rules for context completeness and current-turn burden. |
| `privacy_security_rule_skill.md` | English-only inheritance of all 56 concrete evidence-registry rules plus the v1.1 operational boundary. |
| `respondent_contract.en.md` | English-only v1.1 contract describing audit-compatible behavior, unknown-field handling, and burden limits. |
| `context_schema.json` | English-only schema for explicit current-turn fields, source policies, missing-value handling, and derived audit fields. |
| `reason_codes.json` | English-only deterministic reason-code registry; it contains no numeric behavior parameters. |
| `heldout_calibration_s_qstn.json` | Version-pinned v1.1 held-out diagnostic configuration with `audit_compatible` as the default behavior mode. |
| `VERSION.md` | This version description and file inventory. |

## Sidecar and audit outputs

The default context sidecar is `outputs/questionnaire_context_v1.1.csv`. It is keyed by `questionnaire_item_id` and keeps source fields separate from wrapper-derived fields. The current single-item runner assigns `not_applicable_single_item` for prompt burden unless an explicit annotation is supplied.

The v1.1 compiler and held-out runner write versioned outputs under `outputs/s_qstn_v1_1/` and `outputs/minimal_heldout_calibration_s_qstn_v1_1/`. Their manifests record schema versions and file hashes so that audit-compatible and exploratory runs remain distinguishable.

The one-item API diagnostic is `scripts/v1_1/smoke_test_openai_qstn_v1_1.py`. It
reuses the held-out runner's v1.1 prompt path and writes
`outputs/openai_qstn_rulepack_v1_1_smoke_test_preflight.json` and
`outputs/openai_qstn_rulepack_v1_1_smoke_test.json`. The verified diagnostic
sent exactly one request with the default `audit_compatible` / `active_excerpt`
configuration; it is wiring evidence only, not a calibration result.

## Relationship to v1.0

The v1.1 grouped behavioral layer must regress against `config/v1.0/security_behavior_rules.json`. A v1.1 audit-compatible run is an audit and reproducibility upgrade, not evidence that the respondent became more human-like. The paper-facing comparison remains human vs vanilla QSTN vs profile-only S-QSTN, with RulePack variants treated as explicitly labeled ablations.
