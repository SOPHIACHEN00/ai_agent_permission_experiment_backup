# Task Plan: S-QSTN Profile Cards and RulePack Versioning

## Goal
回顾 v1/v2 profile-card JSON，设计从 skill/contract 到 JSON RulePack 的渐进式 S-QSTN 规则版本路线，并判断当前证据不足以量化权重时的可行实现方式。

## Phases
- [x] Phase 1: Inspect both profile-card JSON files and current QSTN prompt wiring
- [x] Phase 2: Reconcile RulePack roadmap with Excel evidence/principle coverage
- [x] Phase 3: Separate prompt-level behavioral contract, state transitions, and numeric calibration
- [x] Phase 4: Draft versioned implementation plan and decision criteria
- [x] Phase 5: Verify and deliver the Chinese design recap

## Key Questions
1. v1 与 v2 profile card 的真实差异是什么，哪些内容是 data-derived，哪些是手工措辞？
2. v1/v2/v3 RulePack 分别应实现哪些原则，何时才引入 state/weights？
3. 没有可靠数值参数时，skill.md/contract 是否足够，如何保证可审计和可复现？
4. QSTN core、wrapper、profile card、RulePack、state store 的职责如何分开？

## Decisions Made
- 本轮只做设计审查，不修改现有 QSTN、profile cards、Excel 或 runner。
- 机器可审计的规则 source of truth 仍然使用 JSON；Markdown 先承担 respondent contract 和行为解释层。

## Errors Encountered
- 一次 `rg` 查询把 `{{QUESTION` 当作未转义的正则量词，导致解析错误；改用文字 `QUESTION_PLACEHOLDER` 关键词重跑。

## Status
**Completed** - 已完成 profile card、QSTN 接入、Excel principle coverage 核对、版本化设计说明和一致性检查；未修改现有 QSTN、profile cards 或 Excel。

## Implementation Addendum (2026-08-05)

### Goal
按 v1.0 版本路线，在 qstn_simulator 中实现静态、方向性、无长期状态的 RulePack 接入，并形成双语 README 和可持续更新的 versioning.md。

### Phases
- [ ] I1: Read existing compiler, validator, and held-out runner before modification
- [ ] I2: Add v1.0 RulePack JSON, respondent contract, and pure rule-engine helpers
- [ ] I3: Add offline S-QSTN compiler and optional QSTN runner integration
- [ ] I4: Add bilingual README, versioning inventory, and change log
- [ ] I5: Run syntax, unit, prompt-rendering, and dry-run verification

### Implementation Decisions
- Do not modify QSTN core or existing profile-card JSON files.
- Keep RulePack v1.0 directional-only; no arbitrary weights, StateStore, fatigue accumulation, or trust updates.
- Unknown context fields are logged and do not trigger inferred rules.
- Existing held-out runner remains backward-compatible when no RulePack is supplied.

### Status
**Completed** - 已完成 RulePack v1.0、双语 contract、离线 compiler、可选 QSTN runner 接入、versioning/README 文件和本地验证。

### Implementation Results
- [x] I1: Read existing compiler, validator, and held-out runner before modification
- [x] I2: Add v1.0 RulePack JSON, respondent contract, and pure rule-engine helpers
- [x] I3: Add offline S-QSTN compiler and optional QSTN runner integration
- [x] I4: Add bilingual README, versioning inventory, and change log
- [x] I5: Run syntax, unit, prompt-rendering, and dry-run verification

### Verification Summary
- Python compileall: passed.
- Standard-library unit tests: 8 passed.
- Existing profile-card v1 validator: passed, 204 prompts, no target columns.
- Existing profile-card v2 validator: passed, 204 prompts, no target columns.
- RulePack offline compiler: passed, 201 personas × 373 items = 1,119 audit rows.
- RulePack held-out dry-run: passed, 90/90 prompts, no API call.
- Ruff: unavailable in the project environment (`No module named ruff`).

## Skill Catalog Integration Addendum — 2026-08-05

- [x] Created the English-only full catalog at `qstn_simulator/config/v1.0/privacy_security_rule_skill.md` with 56 evidence-derived rule entries and 12 principle mappings.
- [x] Kept JSON as the executable grouped layer and added concrete-rule `skill_section` references, source counts, and skill mode metadata.
- [x] Added the English-only runtime contract at `qstn_simulator/config/v1.0/respondent_contract.en.md`.
- [x] Added default `active_excerpt` and explicit `full_catalog_with_active_excerpt` modes to the compiler and held-out runner.
- [x] Updated the canonical project versioning file and this recap archive.
- [x] Final verification: 10 unit tests, compileall, 56-rule mapping check, default 90/90 dry-run, full-catalog 90/90 dry-run, and profile-only regression dry-run passed.

No QSTN core, profile-card JSON, benchmark data, or Excel workbook was modified. No LLM calibration call was made.

## RulePack v1.1 Implementation Addendum — 2026-08-06

- [x] Reorganized RulePack assets into `qstn_simulator/config/v1.0/` and `qstn_simulator/config/v1.1/`, with a `VERSION.md` description in each folder.
- [x] Added the English-only v1.1 RulePack, skill catalog, respondent contract, context schema, reason-code registry, and audit-compatible diagnostic config.
- [x] Added the label-free `outputs/questionnaire_context_v1.1.csv` sidecar for 373 questionnaire items.
- [x] Added the v1.1 context builder, compiler, runner integration, and regression tests.
- [x] Verified 1,119 profile-by-item compiler audit rows and a 90/90 held-out dry-run with no API call.
- [x] Confirmed no numeric behavior weights, longitudinal state, or human target labels are used by v1.1 context construction or audit activation.
