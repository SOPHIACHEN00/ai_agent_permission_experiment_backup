# Notes: S-QSTN v2.0 Coverage Audit

## Sources

- Excel evidence registry: `QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`
- Canonical versioning: `ai_agent_permission_experiment/qstn_simulator/versioning.md`
- v2.0 configuration: `ai_agent_permission_experiment/qstn_simulator/config/v2.0/`
- v2.0 runtime: `ai_agent_permission_experiment/qstn_simulator/scripts/v2/`
- Profile cards: `ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards_v2.json`

## Findings

### Registry reconciliation

- The workbook contains 56 unique rules: seven evidence sheets with eight rules each.
- `config/v2.0/privacy_security_rule_skill.md` contains exactly the same 56 IDs, with no missing or extra entries.
- v2 catalog statuses: 33 `active_grouped`, 9 `deferred_longitudinal`, 6 `candidate_future`, and 8 `catalog_only_boundary`.
- All 33 `active_grouped` IDs are referenced by the six grouped JSON rules.
- Three deferred P7 sources (`Wij2015-R7`, `Wij2017-R8`, `Malkin-R4`) are referenced by an audit rule, but this does not activate a fatigue-to-choice effect.
- The machine RulePack contains six grouped directional rules, two audit rules, and five state/audit entries. It is not a 56-handler implementation.

### Principle reconciliation

- Directional/context behavior: P4, P5, P6, P10, P11; P9 remains partial.
- Partial state substrate: P1, P2, P7, P12.
- Audit metadata only: P3 recency.
- External boundary only: P8 severity/safety.
- No calibrated trust-loss magnitude, recovery duration, recency decay, fatigue coefficient, four-label probability mapper, or human-memory calibration is present.

### Actual current-input activation

- Recompiled v2 offline using 201 personas and 373 questionnaire items, producing 1,119 profile-by-item audit rows without API calls or target labels.
- Profile distribution: 71 `persistent_granters`, 100 `reconsent_seekers`, and 30 `broad_restrictors`.
- All 1,119 current rows activate P9/P10/P11.
- All 1,119 current rows leave P4/P5/P6 unknown because expectedness/control/transparency sidecar fields are not supplied. This is intentional non-inference.
- The synthetic verified-scope-violation fixture correctly updates integrity caution, memory caution, consent refresh, and recency metadata. It is a mechanism diagnostic, not human calibration.

### Verification

- Nine v2-specific unit tests passed.
- All 29 inherited/v2 RulePack tests passed.
- Six label-free memory fixtures compiled.
- Offline v2 compilation passed: 201 personas, 373 items, 1,119 audit rows, target columns absent, numeric behavior parameters absent, API not called.

### Research-readiness decision

- v2.0 plus empirical profile cards is adequate as an auxiliary, profile-conditioned, rule-informed, bounded-memory privacy-permission respondent simulator.
- It is suitable for a secondary `vanilla QSTN vs S-QSTN v2.0 vs human` comparison when claims are exploratory/descriptive and the personal-assistant security system remains the paper's primary object.
- It must not be described as a complete implementation of all 56 rules/all 12 principles, a validated cognitive model, a calibrated human-memory model, or a human-equivalent agent.
- P8 must remain outside the respondent simulator as the personal-assistant/security-oracle boundary.
- v3 is unnecessary for the stated limited role; it becomes necessary only for calibrated human-likeness or quantitative longitudinal claims.

### Packaging caveat

- v2 is the cumulative scientific version, but the current Python implementation imports helper modules from `scripts.v1` and `scripts.v1_1`. The older folders should not be deleted unless a standalone packaging refactor is performed.

## Deliverable

- `_codex_s_qstn_versioning/S_QSTN_v2.0_Rules_Principles_Coverage_and_Research_Readiness_zh.md`
- Verified to contain all 56 unique registry Rule IDs and 12/12 principle table rows.
