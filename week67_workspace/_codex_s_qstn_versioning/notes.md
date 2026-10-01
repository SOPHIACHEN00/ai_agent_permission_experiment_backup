# Notes: S-QSTN Profile Cards and RulePack Versioning

## Sources

### Local profile cards
- `D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards.json`
- `D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards_v2.json`
- v1 has top-level metadata plus three cards; each card only has `profile_id`, `profile_name`, and `prompt_card`.
- v1 describes stable tendencies: Persistent Granters favor enduring grants; Re-consent Seekers favor current-use sharing plus renewed consent; Broad Restrictors tend to decline/defer and have low willingness across contexts.
- v2 keeps the same `source_profile_method=behavior_profiles_v1`, `source_response_split=discovery_only`, and same three profiles. It adds `parent_card_version`, `authoring_constraints`, one shared decision rule, and per-profile `evidence_basis`.
- v2 makes the decision scope more explicit: evaluate exact data item, tool, and task separately; persistent consent requires a clear continuing task-specific need; ambiguous cases follow the profile default.
- v2 is a prompt-contract revision, not a new clustering result or a quantitative recalibration. It explicitly freezes v1 artifacts/diagnostic and excludes held-out labels, predictions, metrics, and numeric rates.

### Local QSTN wiring
- `ai_agent_permission_experiment/qstn_simulator/PERSONA_DESIGN_zh.md`
- `ai_agent_permission_experiment/qstn_simulator/README.md`
- QSTN persona is already implemented as stable `system_prompt` + `questionnaire_instruction` + `QUESTION_PLACEHOLDER` rendered into a constrained four-option response.
- Existing design explicitly separates stable profile from future mutable `memory_state`; current profile cards should not be treated as a complete longitudinal simulator.
- Existing runner has a 90-row held-out diagnostic and uses discovery-only profile cards; v1 and v2 diagnostics are intentionally frozen.

### Local evidence registry
- `QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`
- `Principle_Coverage` and source rule sheets to be reconciled.
- Workbook contains 56 rules and 12 principles.
- Fully covered principles: P4 Expectation Violation Effect, P5 Perceived Control, P6 Transparency Calibration, P7 Permission Fatigue, P10 Stable Privacy Trait, P11 Context Dependency.
- Partially covered: P1 Trust Loss Asymmetry, P2 Trust Recovery Lag, P9 Privacy Calculus, P12 Trust Calibration.
- Not covered: P3 Recency Dominance and P8 Severity Dominance.
- Important boundary: several rules are system-strategy/evaluation constraints or cross-domain evidence; they should not become direct human-consent coefficients.

## Findings

### Profile cards
- Profile card and RulePack should remain separate axes: profile card = stable prior/default; RulePack = context effects and mutable events; contract = decision order and prohibitions.

### Version roadmap
- Proposed major stages:
  - RulePack v1: static, direction-only context contract; implement P4/P5/P6/P10/P11 and partial P9; no persistent state or numeric weights.
  - RulePack v1.1: add current-turn burden/uncertainty fields and audit-only reason codes; do not claim longitudinal fatigue.
  - RulePack v2: external private StateStore and event boundaries; implement P7 longitudinally and partial P1/P2/P12 using categorical/bounded state, not calibrated probabilities.
  - RulePack v3: human-calibrated numeric decision layer; estimate profile×context×state effects, uncertainty, recency and severity only after new data/split; store coefficients with provenance and CIs.
  - RulePack v4: RL deployment freeze, state isolation audit, backward-compatible manifest and longitudinal validation.

### Quantification boundary
- JSON does not imply numeric values. Directional effects (`increase`, `decrease`, `prefer`, `avoid`, `bounded_recovery`) are valid JSON and are appropriate for the current evidence.
- Putting an arbitrary weight into a prompt does not make the LLM implement that probability. Genuine numeric behavior requires an external score/probability mapper or calibrated logprob policy.
- Current evidence can support triggers and direction, but not universal transferable weights for agent-permission labels; mobile permission coefficients, reason frequencies, qualitative findings, cross-domain trust effects, and assistant hard gates are not interchangeable.

### Implementation boundary
- Do not modify QSTN core now. Extend local questionnaire/context schema and wrapper; use QSTN `LLMPrompt`, presentation modes, JSON-constrained answer generation and parser as-is.
- v1: compile `profile_card_v2 + skill/contract + active directional rules` into a per-turn system prompt; use single-item and four canonical labels.
- v2: wrapper owns event classification and private state updates; QSTN receives only the compiled respondent contract and public context. Ordinary user denial must not count as an agent violation.
- v3: use QSTN for constrained/intermediate response if useful, but apply human-calibrated policy mapping outside prompt text; never rely on natural-language weight instructions alone.
