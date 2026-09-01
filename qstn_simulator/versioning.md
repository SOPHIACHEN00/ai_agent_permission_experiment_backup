# S-QSTN Rule Versioning / 规则版本路线

**Canonical location / 当前文件：** `ai_agent_permission_experiment/qstn_simulator/versioning.md`  
**Current implementation / 当前实现：** `RulePack v2.0.0` (v1.0/v1.1 directional and audit layers plus bounded event memory and categorical state)  
**Status / 状态：** implemented locally, offline-verified, and QSTN prompt smoke-tested offline; no v2 human calibration run has been claimed  
**Last updated / 最后更新：** 2026-08-06

## 1. Version axes / 版本轴

Profile cards and behavior rules are independent. A run must record the following tuple:

```text
profile_card_version
rule_pack_version
respondent_contract_version
state_schema_version
calibration_version
runner_version
model + seed + input hashes
```

Profile card = stable privacy tendency.  
RulePack = context triggers and directional effects.  
Respondent contract = decision order and non-inference boundaries.  
StateStore = later longitudinal events and bounded state.  
QSTN = questionnaire presentation, constrained response generation, and parsing.

语义版本规则：patch 只修文字、校验或日志；minor 增加向后兼容内容；major 改变决策顺序、状态含义、公开接口或概率解释。

## 2. Roadmap / 迭代路线

| Version | Scope | Principles / 原则 | Quantification / 状态 |
|---|---|---|---|
| v1.0 | Static directional context rules | P4, P5, P6, partial P9, P10, P11 | No weights; no long-term state |
| v1.1 | Current-turn context, uncertainty, and burden audit | Current prompt burden only; no longitudinal fatigue claim | Qualitative buckets and audit reason codes; implemented as `audit_compatible` by default |
| v2.0 | External StateStore, verified event boundaries, and bounded memory view | Partial stateful P1, P2, P7, P12; P3 recency metadata only; P8 safety boundary | Categorical state and explicit retention; no probabilities or weights |
| v3.0 | Human-calibrated decision layer | P3, P8, complete P9/P12 and profile × context effects | External mapper with coefficients, uncertainty, and held-out calibration |
| v4.0 | Longitudinal/RL integration freeze | Schema/state isolation and repeated validation | Backward-compatible freeze; no tuning on evaluation split |

At v1.0/v1.1, P1, P2, P3-longitudinal, P7-longitudinal, P8, and P12-calibration were deferred. v2.0 implements only their explicit memory/event substrate; human-calibrated behavioral effects remain deferred to v3.0.

## 3. RulePack v1.0 implementation / v1.0 实现

### Scope / 范围

v1.0 is a static, directional, single-item-compatible respondent layer. It does not modify QSTN core, maintain cross-question trust/fatigue/violation state, or translate evidence into arbitrary numeric weights.

v1.0 是静态、方向性、兼容 QSTN single-item 的 respondent layer。不修改 QSTN core，不维护跨题 trust/fatigue/violation 状态，也不把证据直接转成未经校准的数值权重。

### Implemented principles / 已实现原则

- **P4 Expectation Violation:** explicit unexpectedness or expectation mismatch increases caution, favors clarification, and avoids persistent grants.
- **P5 Perceived Control:** explicit scope, duration, revocation, or review information favors controlled permission options without forcing allow.
- **P6 Transparency Calibration:** explanation/provenance/timing calibrates understanding; transparency is not an allow nudge.
- **P9 Privacy Calculus (partial):** `necessity_status` distinguishes `necessary`, `not_useful_now`, `incorrect_explicit`, and `unknown`; necessity supports only scoped current sharing.
- **P10 Stable Privacy Trait:** the selected empirical profile remains a soft prior.
- **P11 Context Dependency:** exact data item, tool, requester, purpose, and scope are judged separately; missing context is not inferred.

The current questionnaire CSV exposes necessity, tool, and data-type fields but does not contain explicit expectedness, control, or transparency metadata. Consequently, the v1.0 audit activates P9/P10/P11 on the current inputs and records P4/P5/P6 as unknown. This is intentional non-inference; when the PA supplies those public context fields, the same engine activates the corresponding rules.

### Explicit v1.0 boundaries / 明确边界

- Rule effects use `increase`, `decrease`, `prefer`, `avoid`, `preserve`, and `require` only.
- `state_updates` is always an empty list and `state_schema_version` is `none`.
- Numeric keys such as `weight`, `logit_delta`, `probability`, and `coefficient` are rejected by validation.
- `pa_tool_policy`, `pa_rl_observation`, `pa_rl_reward`, real tool execution, and objective safety gating are forbidden targets.
- Unknown fields become audit information; the engine does not infer hidden facts.
- An ordinary respondent denial is a preference, not a verified agent violation.

## 3A. Full concrete-rule skill integration / 完整具体规则 skill 集成

The implementation now uses two coordinated layers:

| Layer | Source of meaning | Runtime role |
|---|---|---|
| `config/v1.0/privacy_security_rule_skill.md` | Full English translation of the 56 concrete rules in the evidence registry | Semantic reference and evidence-boundary catalog. It records every source rule, principle mapping, behavioral interpretation, evidence limit, and runtime status. |
| `config/v1.0/security_behavior_rules.json` | Six grouped v1.0 runtime rules | Machine-readable activation, qualitative directions, source-rule references, and audit behavior. It contains no numeric weights and no state updates. |

The catalog is complete at the concrete-rule level, while the JSON is intentionally selective. The six current grouped rules cover P4, P5, P6, partial P9, P10, and P11. The remaining catalog entries are explicitly marked as `deferred_longitudinal`, `candidate_future`, `evidence_only`, or `catalog_only_boundary`.

The default prompt mode is `active_excerpt`: the LLM receives the English respondent contract and only the active qualitative context for the current question. The optional `full_catalog_with_active_excerpt` mode also exposes the complete skill catalog to the LLM. In that mode, the contract states that only `active_grouped` entries may affect v1.0 behavior; future, evidence-only, and safety-boundary entries remain documentation and constraints.

This separation answers the implementation question directly: the LLM can see all 56 concrete rules only when the full-catalog mode is selected. In the default mode it sees the active grouped interpretation, while the complete catalog is still versioned locally and included in the run hash.

Both the full skill catalog and the new runtime contract are English-only. The previous bilingual contract remains frozen as a historical v1.0 asset; the S-QSTN diagnostic configuration uses `config/v1.0/respondent_contract.en.md`.

## 4. v1.0 file inventory / v1.0 文件清单

All paths below are relative to `ai_agent_permission_experiment/qstn_simulator/`.

| File | Status | Description / 简介 |
|---|---|---|
| `config/v1.0/security_behavior_rules.json` | New | Machine-readable v1.0 RulePack: triggers, directional effects, evidence IDs, forbidden targets, and no-state boundary. |
| `config/v1.0/respondent_contract.md` | New | Bilingual runtime contract: decision order, soft-profile interpretation, and non-inference constraints. |
| `config/v1.0/respondent_contract.en.md` | New | English-only runtime respondent contract used by the RulePack-enabled diagnostic. |
| `config/v1.0/privacy_security_rule_skill.md` | New | Complete English catalog of all 56 concrete evidence-registry rules, principle links, evidence limits, and runtime statuses. |
| `config/v1.0/heldout_calibration_s_qstn.json` | New | Diagnostic configuration pairing profile-card v2 with RulePack v1.0; not a final paper evaluation split. |
| `config/v1.0/VERSION.md` | New | Chinese/English v1.0.0 and v1.0.1 description, folder inventory, and migration note from the old flat paths. |
| `config/v1.1/security_behavior_rules.json` | Implemented | English-only additive RulePack with unchanged v1.0 grouped rules and two audit-only rules. |
| `config/v1.1/privacy_security_rule_skill.md` | Implemented | English-only 56-rule catalog plus the v1.1 operational boundary. |
| `config/v1.1/respondent_contract.en.md` | Implemented | English-only v1.1 contract for information-completeness and burden boundaries. |
| `config/v1.1/context_schema.json` | Implemented | English-only explicit current-turn context schema; no numeric behavior parameters or state. |
| `config/v1.1/reason_codes.json` | Implemented | English-only deterministic audit reason-code registry. |
| `config/v1.1/heldout_calibration_s_qstn.json` | Implemented | Audit-compatible v1.1 held-out diagnostic configuration. |
| `config/v1.1/VERSION.md` | Implemented | Chinese/English v1.1 description and file inventory. |
| `config/v2.0/security_behavior_rules.json` | Implemented | English-only v2.0 RulePack preserving v1.1 grouped/audit rules and declaring explicit state rules and principle boundaries. |
| `config/v2.0/privacy_security_rule_skill.md` | Implemented | English-only complete 56-rule catalog plus v2.0 bounded-memory/event boundary. |
| `config/v2.0/respondent_contract.en.md` | Implemented | English-only v2.0 respondent contract for verified events, bounded memory, and categorical state. |
| `config/v2.0/context_schema.json` | Implemented | English-only v2.0 current-turn context schema. |
| `config/v2.0/event_schema.json` | Implemented | English-only event vocabulary, source policy, and verification boundary. |
| `config/v2.0/state_schema.json` | Implemented | English-only categorical state snapshot and public memory-view fields. |
| `config/v2.0/retention_policy.json` | Implemented | English-only event-specific retention classes without human forgetting durations. |
| `config/v2.0/reason_codes.json` | Implemented | English-only v2.0 deterministic context/event/memory audit codes. |
| `config/v2.0/memory_diagnostic_v2.json` | Implemented | English-only label-free synthetic memory diagnostic configuration. |
| `config/v2.0/VERSION.md` | Implemented | Bilingual v2.0 version description and folder inventory. |
| `scripts/v1/rulepack_v1.py` | Modified | Pure Python v1.0 RulePack loader, validator, condition evaluator, renderer, prompt injector, and English skill loader. No LLM call. |
| `scripts/v1/compile_s_qstn_v1.py` | Modified | Offline v1.0 compiler for persona templates, profile × questionnaire rule-context audits, and skill metadata/hashes. |
| `scripts/runtime/run_heldout_calibration.py` | Modified | Shared held-out runner with optional v1.0/v1.1 RulePack integration; profile-only path remains available. |
| `tests/test_rulepack_v1.py` | Modified | Standard-library tests for schema validation, trigger activation, unknown-field handling, prompt injection, and English full-catalog exposure. |
| `tests/test_rulepack_v1_1.py` | Implemented | Regression and audit-only tests for version inheritance, buckets, reason codes, sidecar leakage guards, and mode separation. |
| `scripts/v1_1/rulepack_v1_1.py` | Implemented | v1.1 schema loaders, deterministic bucket/reason-code derivation, audit evaluation, and prompt integration. |
| `scripts/v1_1/build_context_v1_1.py` | Implemented | Builds the label-free one-to-one current-turn context sidecar. |
| `scripts/v1_1/compile_s_qstn_v1_1.py` | Implemented | Version-specific v1.1 offline compiler with sidecar/audit hashes and behavior-mode metadata. |
| `scripts/v1_1/smoke_test_openai_qstn_v1_1.py` | Implemented | One-item v1.1 API diagnostic that reuses the runner prompt path and validates the contract, active context, audit boundary, and four-option response. |
| `scripts/v1/run_qualitative_profile_pilot.py` | Modified | v1.0 qualitative profile pilot moved under the v1 folder. |
| `scripts/v1/smoke_test_openai_qstn.py` | Modified | v1.0 profile-only API diagnostic moved under the v1 folder. |
| `scripts/v2/state_store_v2.py` | Implemented | Private structured event ledger, categorical transitions, retention logic, lossy memory view, and transition audit. |
| `scripts/v2/rulepack_v2.py` | Implemented | v2 asset validation, v1.1 inheritance adapter, memory-view rendering, and v2 prompt injection. |
| `scripts/v2/build_memory_fixtures_v2.py` | Implemented | Builds deterministic label-free fixtures for verified errors, repair, burden, expiry, and denial boundaries. |
| `scripts/v2/compile_s_qstn_v2.py` | Implemented | Offline v2 compiler producing persona templates, profile × item bounded-memory audits, and transition diagnostics. |
| `scripts/v2/smoke_test_openai_qstn_v2.py` | Implemented | One-item v2 QSTN prompt/API diagnostic with a bounded-memory fixture; not calibration. |
| `RULEPACK_V1.0_README.md` | New | Bilingual v1.0 rules, boundaries, commands, outputs, and file guide. |
| `RULEPACK_V1.1_README.md` | Implemented | Bilingual v1.1 context/audit scope, files, commands, outputs, and interpretation boundary. |
| `RULEPACK_V2.0_README.md` | Implemented | Bilingual v2.0 memory/state scope, files, commands, diagnostics, and non-claims. |
| `README.md` | Modified | Links the v1.0 README and canonical versioning file. |
| `SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md` | Modified | Added the v1.0 and v1.0.1 change-log entries while preserving the existing design history. |
| `versioning.md` | New | Canonical roadmap and implementation inventory for future recap. |
| `outputs/s_qstn_v1/` | Existing generated artifact | Earlier local compiler output; not a source-of-truth configuration. |
| `outputs/s_qstn_v1_0/` | Generated | Version-pinned v1.0 offline compiler output using the reorganized `config/v1.0/` assets. |
| `outputs/questionnaire_context_v1.1.csv` | Generated | One-row-per-questionnaire-item v1.1 context sidecar; current source distribution is 373 items with unknown optional fields retained. |
| `outputs/openai_qstn_rulepack_v1_1_smoke_test_preflight.json` | Generated | One-item v1.1 preflight containing version metadata, label-free context audit, and exact request messages; no API call is recorded in this artifact. |
| `outputs/openai_qstn_rulepack_v1_1_smoke_test.json` | Generated | One-item v1.1 API smoke-test result with the parsed four-option answer and raw model response. |
| `outputs/s_qstn_v1_1/` | Generated | Version-pinned v1.1 offline compiler output with 1,119 profile-by-item audit rows. |
| `outputs/s_qstn_v2/` | Generated | Version-pinned v2.0 offline compiler output with 1,119 profile-by-item audits, memory fixture, manifest, and memory diagnostic. |
| `outputs/openai_qstn_rulepack_v2_smoke_test_preflight.json` | Generated | One-item v2.0 QSTN preflight containing the exact bounded-memory prompt and transition audit; no API call is recorded. |
| `outputs/minimal_heldout_calibration_s_qstn_v1_1/` | Generated | 90-row v1.1 audit-compatible dry-run preflight; no API call was made. |
| `outputs/minimal_heldout_calibration_s_qstn_v1_1_full_skill/` | Generated | 90-row v1.1 full-catalog prompt-exposure audit; no API call was made. |
| `outputs/minimal_heldout_calibration_v1_regression/` | Generated | v1.0 profile-only regression dry-run after the folder migration; no API call was made. |
| `outputs/s_qstn_v1_skill_catalog/` | Generated | Latest successful offline compiler output using the English contract and full skill-catalog metadata; 201 personas × 373 questionnaire items = 1,119 audit rows. |
| `outputs/minimal_heldout_calibration_s_qstn_v1/` | Generated | RulePack-enabled 90-row dry-run preflight and audit output; no API call was made. |
| `outputs/minimal_heldout_calibration_s_qstn_v1_skill/` | Generated | 90-row default `active_excerpt` preflight using the English contract and skill catalog; no API call was made. |
| `outputs/minimal_heldout_calibration_s_qstn_v1_full_skill/` | Generated | 90-row `full_catalog_with_active_excerpt` preflight proving full-catalog prompt exposure; no API call was made. |

The existing profile-card files remain unchanged:

- `config/empirical_profile_prompt_cards.json`
- `config/empirical_profile_prompt_cards_v2.json`

### Script folder migration

Version-specific scripts are now grouped so the active paths are unambiguous:

```text
scripts/v1/       v1.0 profile and RulePack utilities
scripts/v1_1/     v1.1 context/audit utilities
scripts/v2/       v2.0 memory/state utilities
scripts/runtime/  shared held-out runner
```

The Python package imports were updated to use these package paths, and the
active README, version records, tests, and v1.1 smoke diagnostic now point to
the reorganized locations. Historical design notes may still mention the old
flat paths when describing the earlier implementation state.

## 5. Runtime flow / 运行流程

```text
profile card v2
    + current questionnaire metadata
    + RulePack v1.0
    + English respondent contract v1.0
    + complete English skill catalog (stored; optionally injected)
        ↓
local wrapper evaluates explicit triggers
        ↓
QSTN receives compiled respondent instruction
        ↓
one constrained four-option answer
        ↓
offline audit stores rule IDs and versions, not hidden state in PA output
```

Offline compilation:

```powershell
uv run python -m scripts.v1.compile_s_qstn_v1
```

Prompt-only held-out diagnostic:

```powershell
uv run python -m scripts.runtime.run_heldout_calibration `
  --config config/v1.0/heldout_calibration_s_qstn.json `
  --dry-run
```

The `--execute` path remains an experiment command. It must only be run after reviewing the preflight manifest, rule audit, split exclusions, model, and API budget.

To expose the full concrete-rule catalog for a controlled ablation or prompt audit:

```powershell
uv run python -m scripts.runtime.run_heldout_calibration `
  --config config/v1.0/heldout_calibration_s_qstn.json `
  --skill-mode full_catalog_with_active_excerpt `
  --dry-run
```

The skill catalog is hashed in the preflight fingerprint in either mode. Full-catalog mode changes prompt exposure and must therefore be recorded as a separate experimental condition.

## 6. RulePack v1.1 implementation / v1.1 实现

v1.1 is implemented as an additive current-turn context and audit layer. The default mode is `audit_compatible`; it preserves the v1.0 grouped rules and writes audit metadata without adding an answer effect.

### Implemented v1.1 assets

- `config/v1.1/security_behavior_rules.json`: six unchanged v1.0 grouped rules plus `AUDIT.context_completeness` and `AUDIT.current_turn_prompt_burden`. Both audit rules are stateless and have empty effects.
- `config/v1.1/privacy_security_rule_skill.md`: all 56 concrete English evidence-registry rules plus the v1.1 operational boundary.
- `config/v1.1/respondent_contract.en.md`: English-only contract distinguishing information completeness from model confidence and current-turn burden from longitudinal fatigue.
- `config/v1.1/context_schema.json`: explicit context fields and source-policy/missing-value rules.
- `config/v1.1/reason_codes.json`: deterministic audit code registry without numeric behavior parameters.
- `config/v1.1/heldout_calibration_s_qstn.json`: default `audit_compatible` diagnostic configuration.
- `config/v1.1/VERSION.md`: Chinese/English version description and file inventory.

### Implemented v1.1 code and outputs

- `scripts/v1_1/rulepack_v1_1.py` derives `uncertainty_bucket`, `prompt_burden_bucket`, and reason codes without numeric thresholds or label access.
- `scripts/v1_1/build_context_v1_1.py` creates `outputs/questionnaire_context_v1.1.csv`, keyed one-to-one by `questionnaire_item_id`.
- `scripts/v1_1/compile_s_qstn_v1_1.py` creates `outputs/s_qstn_v1_1/` with versioned compiler manifest and 1,119 profile-by-item audit rows.
- `scripts/runtime/run_heldout_calibration.py` accepts the v1.1 sidecar and behavior mode; the verified v1.1 dry-run is under `outputs/minimal_heldout_calibration_s_qstn_v1_1/` with 90 prompts and no API call.
- `scripts/v1_1/smoke_test_openai_qstn_v1_1.py` renders and optionally sends exactly one v1.1 RulePack prompt, validating the contract, active context, audit boundary, and four-option response format.
- The v1.1 dry-run and API smoke test were both verified. The API test used the default `audit_compatible` / `active_excerpt` settings and sent exactly one request; its answer was valid under the four-label constraint. This is wiring evidence only, not a calibration result.
- `tests/test_rulepack_v1_1.py` covers inheritance, buckets, reason codes, sidecar leakage guards, prompt preservation, and exploratory-mode separation.

### v1.1 evidence boundary

The current questionnaire has 373 items. Its default sidecar uses direct source fields, keeps unprovided context as `unknown`, and assigns `not_applicable_single_item` for burden. The observed dry-run distribution is recorded in the sidecar manifest; it is an information-availability audit, not a human-likeness result. Human labels are not used in context construction, prompt compilation, or rule activation.

The v1.1 implementation alone intentionally did not claim that P1/P2/P3/P7-longitudinal/P8/P12 were implemented. v2.0 now provides only the explicit event/state substrate for partial P1, P2, P7, and P12 plus P3 recency metadata; the calibrated behavioral mappings remain deferred.

## 7. Change log / 变更记录

### v1.0.0 — 2026-08-05

- Added static directional RulePack JSON.
- Added bilingual respondent contract.
- Added pure Python validation and trigger/effect evaluator.
- Added offline S-QSTN compiler and audit manifest.
- Added optional RulePack/contract support to the existing held-out runner while preserving the no-argument profile-only path.
- Added a separate v1.0 diagnostic configuration.
- Added bilingual README and this canonical versioning file.
- No QSTN core, profile-card JSON, benchmark dataset, or Excel workbook was changed.

### v1.0.1 — 2026-08-05

- Added `config/v1.0/privacy_security_rule_skill.md`, an English-only catalog containing all 56 concrete rules from the evidence registry.
- Added explicit runtime-status labels so complete evidence visibility does not activate deferred longitudinal, safety, evaluation, or system-strategy rules.
- Added `config/v1.0/respondent_contract.en.md`; the bilingual contract remains preserved for historical reproducibility.
- Added `active_excerpt` and `full_catalog_with_active_excerpt` skill modes to the RulePack wrapper and held-out runner.
- Added skill catalog version, mode, file hash, and prompt-exposure metadata to compiler, preflight, run, and calibration manifests.
- Added JSON `skill_section` references from the six grouped runtime rules back to the concrete evidence rules.
- No numeric weights, state schema, QSTN core code, profile-card JSON, benchmark dataset, or Excel workbook was changed.

### v1.1.0 — 2026-08-06

- Reorganized versioned RulePack assets into `config/v1.0/` and `config/v1.1/`; active code and Markdown records now use folder paths.
- Added the v1.1 context schema, reason-code registry, audit-only RulePack rules, English skill/contract boundary, and `audit_compatible` default mode.
- Added the one-to-one `outputs/questionnaire_context_v1.1.csv` sidecar and deterministic uncertainty/burden audit derivation.
- Added v1.1 compiler and runner integration with schema/hash manifests; completed a 373-item compiler run, 1,119 audit rows, and a 90-prompt held-out dry-run without an API call.
- Added `scripts/v1_1/smoke_test_openai_qstn_v1_1.py` and completed its dry-run plus one-request API wiring check with the default v1.1 configuration.
- Added v1.1 regression tests; all v1.0 and v1.1 RulePack tests pass.
- No numeric weights, longitudinal state, QSTN core changes, label leakage, Excel edits, or human-likeness claim was introduced.

### Planned v1.2+

Consider additional explicit event/context annotations only after their public schema and evidence boundaries are frozen. Do not introduce cross-turn fatigue or numerical weights without a separate calibration plan.

The current v2.0/v3.0 design discussion is recorded in
`../../_codex_s_qstn_versioning/S_QSTN_RulePack_v2_v3_design_zh.md`, with the
working plan and findings in the same versioning archive. These are draft
design artifacts for v3.0; v2.0 is now implemented and recorded below.

## 8. RulePack v2.0 implementation / v2.0 实现

v2.0 is implemented as an external memory/state layer. It does not modify QSTN
core and does not turn the 56 evidence-registry rules into numeric parameters.
The runtime path is:

```text
explicit verified event
        ↓
private StateStore v2.0 ledger
        ↓
categorical transition audit + bounded memory_view
        ↓
v1.1 directional context + v2.0 respondent contract
        ↓
QSTN single-item prompt
```

### v2.0 principle coverage

- **P1:** verified agent error or scope violation can create categorical caution; no trust-loss magnitude is claimed.
- **P2:** verified repair enters recovery/residual caution; one repair does not perform a full reset.
- **P3:** event order and recency buckets are recorded as metadata only; no decay or recency-dominance rule is active.
- **P4/P5/P6/P9/P10/P11:** inherited v1.1 explicit-context directional rules remain active where their triggers are supplied.
- **P7:** verified prompt interruption, unresolved request, and explicit burden annotations can enter a bounded burden state; no mechanical fatigue-to-choice effect is claimed.
- **P8:** remains an independent safety-boundary concern; v2 does not implement a severity oracle.
- **P12:** competence, integrity, and benevolence are separate categorical fields when the event explicitly identifies a dimension; no four-label calibration is claimed.

### v2.0 data and prompt boundary

The wrapper keeps the full structured event ledger private. The respondent sees
only `visible_events`, `visible_verified_event_types`, categorical state, a
recency bucket, and explicit unknown/expired markers. The wrapper never infers
verified events from question prose, a model response, an ordinary denial, or
row count. Expiry is not treated as forgiveness or repair.

The default behavior mode is `stateful_audit_compatible`. The
`synthetic_exploratory` mode is reserved for deterministic fixture diagnostics.
The v2 compiler and smoke test do not use human labels and do not constitute a
human-memory or human-likeness result.

### v2.0 commands

```powershell
\.\.venv\Scripts\python.exe -m scripts.v2.build_memory_fixtures_v2
\.\.venv\Scripts\python.exe -m scripts.v2.compile_s_qstn_v2
\.\.venv\Scripts\python.exe -m scripts.v2.smoke_test_openai_qstn_v2 --dry-run
```

The offline compiler creates `outputs/s_qstn_v2/` with 1,119 profile-by-item
audits, a label-free fixture file, a transition/memory diagnostic, and a hash
manifest. The smoke test verifies the exact prompt path used by QSTN and, only
when the dry-run flag is omitted, can send one API request.

The current implementation is intentionally a standalone v2 diagnostic. A
multi-turn human held-out calibration runner that feeds real verified events
into the StateStore is a v3 data/protocol task, not silently inferred from the
current static questionnaire.

### v2.0.0 — 2026-08-06

- Created the versioned `config/v2.0/` folder and added the English-only RulePack, full skill catalog, respondent contract, current-turn schema, event schema, state schema, retention policy, reason-code registry, and synthetic diagnostic configuration.
- Implemented `scripts/v2/state_store_v2.py` with a private event ledger, verified-source boundary, categorical state transitions, event-specific retention, bounded memory view, and transition audit.
- Implemented `scripts/v2/rulepack_v2.py`, `scripts/v2/compile_s_qstn_v2.py`, `scripts/v2/build_memory_fixtures_v2.py`, and `scripts/v2/smoke_test_openai_qstn_v2.py`.
- Reorganized version-specific scripts into `scripts/v1/`, `scripts/v1_1/`, and `scripts/v2/`; shared held-out execution is under `scripts/runtime/`, with imports, tests, and active documentation updated.
- Generated `outputs/s_qstn_v2/` with six label-free memory fixtures, 1,119 profile-by-item audit rows, a transition/memory diagnostic, and a hash manifest.
- Verified JSON syntax, English-only v2 assets, Python compilation, QSTN prompt rendering, and all 29 v1/v1.1/v2 unit tests.
- No QSTN core, profile-card JSON, benchmark dataset, Excel workbook, numeric behavior weights, or human-calibration claim was changed.
