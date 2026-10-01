# qualitative_profile_pilot_v1

## Scope

A 3 prototype by 3 scenario qualitative diagnostic. It is not a benchmark or a human-likeness claim.

## Selection Boundary

Scenarios are selected only from questionnaire metadata and the request-tool-data semantic relationship. No participant-level response labels are read or used.

## Selected Scenarios

| Role | Scenario | Rationale |
| --- | --- | --- |
| routine_aligned | permission_51_apple_music_music_playing_history | A routine request in which listening history directly supports creating a playlist from the user's most-played songs. |
| sensitive_aligned | permission_26_banking_account_number | A sensitive financial data request that is directly connected to scheduling the requested one-time rent payment. |
| sensitive_mismatched | permission_49_the_movie_database_parents__phone_numbers | A sensitive family-contact request that has no apparent relationship to finding movie recommendations. |

## Observed Response Matrix

| Scenario role | Persistent Granters | Re-consent Seekers | Broad Restrictors |
| --- | --- | --- | --- |
| routine_aligned | Yes, always share | Yes, but ask me next time | Yes, but ask me next time |
| sensitive_aligned | Yes, always share | Yes, but ask me next time | Yes, but ask me next time |
| sensitive_mismatched | No, never share | No, but ask me next time | No, never share |

## Interpretation Guardrails

- Inspect profile differentiation, permission persistence, and response to contextual mismatch descriptively.
- Do not compare pilot answers to participant labels or report accuracy, F1, significance, or human-likeness.
- Do not treat any individual pilot answer as a pass/fail criterion for a profile card.
- Use the audit artifacts to review the exact rendered prompts and raw model responses before any held-out calibration run.

The answer ordering 0=No, never; 1=No, ask next time; 2=Yes, ask next time; 3=Yes, always is retained in the CSV only as a descriptive display aid. It is not a validated interval scale or a pilot success metric.
