# Task Plan: QSTN Permission Simulator Setup

## Goal
Create a reproducible, isolated QSTN environment for the permission-response simulator without changing the existing four-label benchmark.

## Phases
- [x] Phase 1: Inspect the existing benchmark, data schema, and Python runtime.
- [x] Phase 2: Add isolated QSTN project configuration and documentation.
- [x] Phase 3: Create the environment and install locked dependencies.
- [x] Phase 4: Run installation and dataset-access smoke tests.
- [x] Phase 5: Convert permission contexts into QSTN questionnaire items and profile-grounded personas.
- [x] Phase 6: Verify one live OpenAI-backed QSTN response.
- [x] Phase 7: Archive the obsolete forced-four-archetype work and replace it with empirical permission-response profile discovery.

## Decisions Made
- Use a nested `qstn_simulator` project so its QSTN dependencies do not alter the benchmark `.venv`.
- Use Python 3.12 because QSTN requires Python 3.12 or newer.
- Read the existing processed four-label CSV as a calibration source; do not modify it.

## Errors Encountered
- `ai_agent_permission_experiment` is not an independent Git repository; configuration will be verified through file and runtime checks instead.
- The restricted shell cannot use uv's global cache; `uv sync` was completed with approved access, and direct `.venv` execution avoids this issue for local checks.
- A parallel validation attempted to read `calibration_assignments.csv` before the generator completed; rerun generation and validation sequentially.

## Status
Complete for QSTN setup and empirical profile discovery. The 201-person calibration baseline remains unchanged. The obsolete forced-four-archetype implementation is archived at `archive/forced_four_archetypes_20260721.zip`; the active pipeline selects three descriptive permission-response profiles from observed behavior using held-out splits. No LLM API call was made for profile discovery.

## RulePack v1.0 Addendum — 2026-08-05

- [x] Added static directional `config/v1.0/security_behavior_rules.json`.
- [x] Added bilingual `config/v1.0/respondent_contract.md`.
- [x] Added pure Python rule validator/evaluator and offline S-QSTN compiler.
- [x] Added optional RulePack/contract support to the held-out runner; the original profile-only path remains available.
- [x] Added bilingual README and canonical `versioning.md` inventory.
- [x] Verified compileall, 8 unit tests, profile-card v1/v2 validators, offline compilation, and 90-row QSTN dry-run.

The current version does not include numerical weights or longitudinal StateStore updates.

## RulePack v1.0.1 Skill Catalog Addendum — 2026-08-05

- [x] Added the English-only `config/v1.0/privacy_security_rule_skill.md` catalog with all 56 concrete evidence-registry rules.
- [x] Added English-only `config/v1.0/respondent_contract.en.md` while preserving the bilingual contract as a historical asset.
- [x] Added skill catalog metadata, source counts, hashes, and `skill_section` references to the JSON/compiler/runner manifests.
- [x] Added `active_excerpt` and `full_catalog_with_active_excerpt` prompt-exposure modes; JSON activation remains authoritative.
- [x] Verified default mode excludes the full catalog, full mode exposes `Cao-R1` and `Esterwood-R8`, and both modes preserve target-label isolation.
- [x] Updated `versioning.md`, README files, design change log, and the external versioning recap archive.

The latest successful skill-integrated offline compile is under `outputs/s_qstn_v1_skill_catalog/`; the two 90-row prompt preflights are under `outputs/minimal_heldout_calibration_s_qstn_v1_skill/` and `outputs/minimal_heldout_calibration_s_qstn_v1_full_skill/`. No LLM API call was made.

## RulePack v1.1 Addendum — 2026-08-06

- [x] Reorganized versioned RulePack assets into `config/v1.0/` and `config/v1.1/` and added `VERSION.md` in each folder.
- [x] Added v1.1 context schema, reason codes, audit-only rules, English skill/contract boundary, and the default `audit_compatible` mode.
- [x] Added `scripts/v1_1/build_context_v1_1.py`, `scripts/v1_1/rulepack_v1_1.py`, `scripts/v1_1/compile_s_qstn_v1_1.py`, and `tests/test_rulepack_v1_1.py`.
- [x] Built `outputs/questionnaire_context_v1.1.csv` for 373 questionnaire items and compiled 1,119 profile-by-item audit rows.
- [x] Verified the v1.1 held-out runner dry-run with 90/90 prompts and no API call.
- [x] Kept numeric weights, longitudinal state, QSTN core changes, and human target labels out of v1.1 behavior/context inputs.

## RulePack v2.0 Addendum — 2026-08-06

- [x] Created the complete `config/v2.0/` folder with English-only RulePack, skill, contract, current-turn schema, event schema, state schema, retention policy, reason codes, and memory diagnostic configuration.
- [x] Implemented private bounded event memory and categorical state transitions in `scripts/v2/state_store_v2.py`.
- [x] Implemented v2 asset validation, v1.1 inheritance rendering, bounded memory prompt injection, synthetic fixtures, offline compiler, and QSTN smoke test under `scripts/v2/`.
- [x] Reorganized v1/v1.1 scripts into `scripts/v1/` and `scripts/v1_1/`; shared held-out runner is under `scripts/runtime/` and active module commands were updated.
- [x] Generated `outputs/s_qstn_v2/` with six label-free fixtures and 1,119 profile-by-item audits; no human labels or calibration claims were introduced.
- [x] Verified JSON syntax, English-only v2 assets, QSTN prompt rendering, Python compilation, and all 29 v1/v1.1/v2 tests.
