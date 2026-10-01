# Test-once decision record — 2026-09-22 UTC

## ADR-IMPL-036 — sealed Family-3 v2 test classification

- Decision: accept the single held-out run as a valid, sealed terminal result.
- Integrity: pass. Exit code 0, 6,300/6,300 test rows, 4,200 validation rows, 12 checkpoints, zero hard-integrity counters, and no duplicate or premature test access.
- Scientific classification: `RULE_PARITY_SIGNAL`.
- Interpretation: γ=1 Masked DDQN matches the forecast rule (737/900 terminal successes and 900/900 first-request/forecast-rule matches) on all permitted seeds. The evidence is a rule-parity signal, not a demonstrated improvement over the rule baseline.
- Follow-up constraint: do not retune or reopen this sealed test. Any claim of DDQN credit beyond the rule must use a newly scoped, preregistered experiment with fresh authorization.
