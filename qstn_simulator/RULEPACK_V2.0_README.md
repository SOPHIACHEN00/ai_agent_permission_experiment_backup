# S-QSTN RulePack v2.0 README

## 中文说明

RulePack v2.0 在 v1.1 的当前问题 context/audit 层之上增加一个外部、有界的
memory/state substrate。它让 S-QSTN wrapper 能够在连续问题之间保存结构化事件、
执行显式的类别状态转移，并把一个有损的 `memory_view` 编译进 QSTN prompt。

这一版的目标是实现“记住什么、哪些事件可以改变状态、何时从 respondent view 中
消失”的工程机制，不是估计人的遗忘曲线，也不是给回答增加没有证据的 weight。

### v2.0 已实现的规则

- P1：只有 externally verified 的 agent error 或 scope violation 才能产生类别化 caution；不估计 trust-loss 幅度。
- P2：verified repair 进入 `recovery` 并保留 residual caution；不会一次 repair 就 full reset。
- P3：记录 turn/order 和 recency bucket，但不使用 decay coefficient 或 recency dominance。
- P7：显式 verified 的 prompt interruption、unresolved request 和 burden annotation 可以进入有界 burden state；不会机械地把 fatigue 映射成 allow/deny。
- P12：competence、integrity、benevolence 分开存储；只有事件明确提供 trust dimension 时才更新对应字段。
- P4/P5/P6/P9/P10/P11：继续继承 v1.1 的显式 current-context directional rules。
- P8：仍然是独立 safety boundary；v2 不实现 severity oracle。

普通 respondent denial 不会自动变成 agent violation。问题文本、LLM 输出、row count
也不会被 wrapper 当作 verified event 或 hidden history。

### 运行方式

在 `qstn_simulator/` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.v2.build_memory_fixtures_v2
.\.venv\Scripts\python.exe -m scripts.v2.compile_s_qstn_v2
.\.venv\Scripts\python.exe -m scripts.v2.smoke_test_openai_qstn_v2 --dry-run
```

去掉 `--dry-run` 后，smoke test 最多发送一个 QSTN/OpenAI 请求；这只是 wiring
check，不是 calibration、人类相似度或论文结果。

默认编译器使用 `stateful_audit_compatible` 和
`verified_scope_violation_visible` synthetic fixture。可以通过
`--fixture-id` 选择其他 fixture；`synthetic_exploratory` 只用于离线机制诊断。

### v2.0 文件

| 文件 | 作用 |
|---|---|
| `config/v2.0/security_behavior_rules.json` | 英文 machine-readable RulePack；继承 v1.1 grouped/audit rules，新增 state rules 和 principle boundary。 |
| `config/v2.0/privacy_security_rule_skill.md` | 英文完整 56 条 concrete evidence rules 以及 v2 memory/event 解释边界。 |
| `config/v2.0/respondent_contract.en.md` | 英文 respondent contract；规定只能使用 compiled memory view 和 verified events。 |
| `config/v2.0/context_schema.json` | v2 current-turn context schema。 |
| `config/v2.0/event_schema.json` | event vocabulary、source policy、verification status。 |
| `config/v2.0/state_schema.json` | categorical state snapshot 和 public memory-view fields。 |
| `config/v2.0/retention_policy.json` | `recent_only`、`until_repaired` 等 retention classes；没有人类遗忘时长。 |
| `config/v2.0/reason_codes.json` | deterministic context/event/memory audit codes。 |
| `config/v2.0/memory_diagnostic_v2.json` | label-free synthetic diagnostic configuration。 |
| `config/v2.0/VERSION.md` | v2.0 双语版本说明。 |
| `scripts/v2/state_store_v2.py` | private ledger、state transition、retention、memory view 和 audit。 |
| `scripts/v2/rulepack_v2.py` | v2 asset validator、v1.1 inheritance adapter、memory rendering 和 prompt injection。 |
| `scripts/v2/build_memory_fixtures_v2.py` | 生成六个无标签 synthetic memory fixtures。 |
| `scripts/v2/compile_s_qstn_v2.py` | 离线生成 v2 persona templates、1,119 条 profile × item audit 和 manifest。 |
| `scripts/v2/smoke_test_openai_qstn_v2.py` | 单题 QSTN prompt/API diagnostic。 |
| `tests/test_rulepack_v2.py` | v2 schema、state、retention、denial boundary 和 prompt tests。 |

输出位于 `outputs/s_qstn_v2/`，包括 `memory_fixtures_v2.json`、
`rule_context_audit.csv`、`memory_diagnostic.json`、`s_qstn_personas.csv` 和
`s_qstn_v2_manifest.json`。单题预检位于
`outputs/openai_qstn_rulepack_v2_smoke_test_preflight.json`。

## English summary

RulePack v2.0 adds an external bounded-memory and categorical-state substrate
on top of the v1.1 current-turn context and audit layer. The wrapper maintains
a private structured event ledger, applies deterministic transitions only for
explicitly verified events, and exposes a lossy `memory_view` plus a categorical
`state_snapshot` to the QSTN respondent prompt.

The implementation covers partial stateful P1, P2, P7, and P12, records P3
recency metadata without decay, and preserves the v1.1 directional coverage of
P4, P5, P6, P9, P10, and P11. P8 remains an independent safety boundary. No
numeric weights, probabilities, confidence scores, or human-calibrated
forgetting durations are defined.

All JSON and skill/contract assets in `config/v2.0/` are English-only. The
compiler and smoke test are label-free diagnostics; they do not constitute a
human calibration or human-likeness result. The v3.0 plan remains responsible
for multi-turn human data, retention calibration, and any externally auditable
decision mapper.
