# Notes: S-QSTN v2/v3 Memory and Calibration Design

## Local sources

- `ai_agent_permission_experiment/qstn_simulator/versioning.md`
- `ai_agent_permission_experiment/qstn_simulator/config/v1.1/security_behavior_rules.json`
- `ai_agent_permission_experiment/qstn_simulator/config/v1.1/privacy_security_rule_skill.md`
- `ai_agent_permission_experiment/qstn_simulator/config/v1.1/context_schema.json`
- `QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`

## Findings

### Current v1.1 boundary

- v1.1 is `audit_compatible` by default and preserves the v1.0 directional
  layer.
- `state_schema_version` is `none`; `state_updates` are empty.
- The current questionnaire supplies direct necessity/tool/data metadata but
  does not supply a reliable multi-turn event sequence, timestamps, repair
  outcomes, or verified agent-failure events.
- The current single-item runner cannot establish longitudinal fatigue or
  recency behavior.

### Memory is needed, but full transcript memory is not desirable

P1, P2, P3, P7, and P12 depend on history, but the simulator should not expose
or retain an unrestricted transcript as if it were a human memory. A bounded
design should separate:

1. `event_ledger`: structured, private, auditable event records;
2. `memory_view`: a lossy, time-bounded summary that may be exposed to the
   respondent prompt;
3. `state_snapshot`: categorical state derived from verified events and the
   current retention policy.

Expired details may disappear from `memory_view` while the audit ledger remains
available for reproducibility. This models limited respondent recall without
pretending that the system has human cognition.

### Why v2 and v3 must be separated

v2 should implement the memory substrate, event boundaries, deterministic
transitions, retention hooks, and audit traces. It should not estimate the
magnitude of a trust loss, recovery lag, recency decay, fatigue effect, or trust
to answer mapping.

v3 should consume a frozen v2 state schema and learn/calibrate the mapping from
profile, current context, and memory state to the four permission choices. The
calibrated mapper must live outside prose-only prompt instructions and must be
evaluated on participant/time-separated held-out data.

## Principle-to-version mapping

| Principle | v2.0 responsibility | v3.0 responsibility |
|---|---|---|
| P1 Trust Loss Asymmetry | Define verified negative events and categorical caution transitions. | Estimate asymmetric effect magnitude and answer mapping. |
| P2 Trust Recovery Lag | Define repair/recovery events and non-instant reset transitions. | Calibrate recovery timing and residual trust effects. |
| P3 Recency Dominance | Store event order/time and expose recency buckets. | Calibrate recency windows, decay, and dominance. |
| P7 Permission Fatigue | Track repeated prompts, interruptions, and unresolved requests. | Calibrate when fatigue changes re-asking/timing or permission choices. |
| P12 Trust Calibration | Define separate trust dimensions and their evidence sources. | Calibrate dimension-specific effects and uncertainty. |

P8 remains a separate safety-oracle concern rather than a respondent-memory
rule. P9 can use v2 state/context and v3 calibration, but its current v1.1
implementation remains partial.

