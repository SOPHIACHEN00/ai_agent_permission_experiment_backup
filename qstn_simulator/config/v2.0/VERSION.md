# S-QSTN RulePack v2.0 Version Description / 版本说明

## Positioning / 定位

RulePack v2.0 adds an external, bounded-memory and event-aware state layer on
top of the v1.1 directional and audit layers. It does not modify QSTN core,
introduce a probability mapper, or claim human-calibrated forgetting.

v2.0 implements the memory substrate required by P1, P2, P3, P7 and P12:

- a private structured event ledger;
- explicit verification boundaries;
- categorical state snapshots;
- lossy respondent memory views;
- event-specific retention classes;
- deterministic transition and retention audits.

普通 respondent denial 不会被当作 agent violation。只有外部 verified event 或
synthetic oracle event 才能更新 trust/violation state。v2.0 的 state 是
categorical state，不是 probability、confidence 或 numeric behavior weight。

## v2.0 Files / 文件

| File | Description |
|---|---|
| `security_behavior_rules.json` | English-only v2.0 RulePack. Preserves v1.1 grouped/audit rules and adds bounded state rules. |
| `privacy_security_rule_skill.md` | English-only full 56-rule evidence catalog plus the v2.0 memory/event boundary. |
| `respondent_contract.en.md` | English-only respondent contract for compiled memory views and verified-event boundaries. |
| `context_schema.json` | English-only v2.0 current-turn context schema. |
| `event_schema.json` | English-only event ledger schema and verification policy. |
| `state_schema.json` | English-only categorical state snapshot and memory-view schema. |
| `retention_policy.json` | English-only event-specific retention classes; exact human durations remain deferred. |
| `reason_codes.json` | English-only deterministic v2.0 context, event, memory, and transition codes. |
| `memory_diagnostic_v2.json` | English-only synthetic memory diagnostic configuration. |
| `VERSION.md` | This bilingual version description and file inventory. |

## Runtime files / 运行文件

| File | Description |
|---|---|
| `scripts/v2/state_store_v2.py` | Private event ledger, categorical transitions, retention, bounded memory view, and transition audit. |
| `scripts/v2/rulepack_v2.py` | v2 asset validation, v1.1 inheritance adapter, memory rendering, and prompt injection. |
| `scripts/v2/build_memory_fixtures_v2.py` | Builds deterministic label-free memory fixtures. |
| `scripts/v2/compile_s_qstn_v2.py` | Offline v2 prompt/audit compiler. |
| `scripts/v2/smoke_test_openai_qstn_v2.py` | One-item QSTN v2 prompt/API wiring diagnostic. |
| `tests/test_rulepack_v2.py` | v2 regression tests for state, retention, denial boundaries, and prompt rendering. |

Generated artifacts are under `outputs/s_qstn_v2/`. The v2 diagnostic is not a
human calibration run and does not estimate human memory or human likeness.

## Principle boundary / 原则边界

| Principle | v2.0 status |
|---|---|
| P1 | Partial stateful support: verified negative events create categorical caution. |
| P2 | Partial stateful support: verified repair enters recovery without an instant reset. |
| P3 | Recency metadata only; no calibrated recency dominance or decay. |
| P4/P5/P6/P9/P10/P11 | v1.1 directional/context layer preserved. |
| P7 | Partial stateful support: bounded prompt/interruption history, not calibrated fatigue-to-choice effects. |
| P8 | Safety-boundary only; no respondent severity oracle. |
| P12 | Partial stateful support: trust dimensions are separated, but not calibrated to four-label choices. |

## Non-claims / 不应声称

- v2.0 is not a human-memory model.
- v2.0 does not estimate trust-loss magnitude, recovery duration, recency decay,
  fatigue coefficients, probabilities, or confidence scores.
- v2.0 does not use human target labels to activate events or state.
- v2.0 does not perform formal human calibration. That belongs to v3.0.
