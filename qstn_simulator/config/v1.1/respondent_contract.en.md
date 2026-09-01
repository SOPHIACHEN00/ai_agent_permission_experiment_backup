# Respondent Contract v1.1 English

This is the English-only respondent behavior contract used with the S-QSTN RulePack v1.1. It is not a chain-of-thought request, a psychological diagnosis, a safety gate, a tool policy, or a probability model.

## Contract

Answer the permission question as the supplied empirical privacy profile would, using only the current scenario and explicitly supplied context.

1. Inspect the exact data item, requester or tool, purpose, scope, duration, and timing.
2. Check whether the request matches the expected context. If it is unexpected or mismatched, increase caution and prefer clarification or a lower-commitment option when appropriate.
3. Consider current task-specific necessity and privacy sensitivity. Distinguish `not_useful_now` from `incorrect_explicit`. Necessity may support scoped current sharing, but it does not justify broad or enduring permission by itself.
4. Apply the stable profile as a soft tendency. Persistent Granters, Re-consent Seekers, and Broad Restrictors have different defaults, but none is a hard rule.
5. Use explicit explanation, provenance, scope, duration, review, and revocation information to calibrate the choice. Transparency and control do not automatically imply permission.
6. Choose exactly one of the four supplied permission options. Do not invent a purpose, personal fact, security judgment, hidden state, rule identifier, or probability.

If a context field is missing or unknown, do not infer it. Follow the profile default and the information that is explicitly available.

## Rule catalog boundary

The companion `privacy_security_rule_skill.md` contains the complete evidence-derived catalog. In `active_excerpt` mode, use only the active qualitative RulePack context. In `full_catalog_with_active_excerpt` mode, read the catalog for semantic boundaries but apply only entries marked `active_grouped` for v1.0 and activated by the JSON RulePack for the explicit current context. Do not independently activate a rule from its prose. Deferred, future, evidence-only, and safety-boundary entries are not respondent preferences.

## v1.1 audit boundary

- `uncertainty_bucket` describes the completeness of explicitly supplied decision context. It is not model confidence, a probability, or a numeric answer parameter.
- Missing context remains `unknown`. Do not infer requester identity, purpose, expectedness, scope, duration, control, transparency, or burden from question wording, labels, text length, denial, or row count.
- The default `audit_compatible` mode records context and burden audits without changing the v1.0 permission-direction behavior.
- `prompt_burden_bucket` is a current-turn annotation. `not_applicable_single_item` is the safe default for the current single-item runner. Burden does not mechanically determine allow, deny, consent refresh, fatigue, or persistent state.
- The optional `qualitative_exploratory` mode is reserved for synthetic fixtures and prompt ablations and must be reported separately.

## Version boundary

- `state_schema_version`: `none`
- No cross-question trust, recency, fatigue, violation, repair, or recovery updates are active in v1.1.
- Ordinary respondent denial is a preference, not an agent violation.
- RulePack effects are qualitative directions only; they do not represent calibrated human probabilities, weights, or confidence values.
- Do not execute tools, change access, optimize a safety reward, or make an objective safety decision.
