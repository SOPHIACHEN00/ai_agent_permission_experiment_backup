# Continuation checkpoint — Family-3 v2 test-once terminal

更新时间：2026-09-22 UTC

## Authoritative terminal state

- Formal state: `FINAL_RULE_PARITY_SIGNAL`.
- Test process: one explicit `test-once`, exit code 0, 597.944 seconds; no retry/resume.
- Validation: `READY_FOR_TEST`, 4,200 rows, 12 completed checkpoint refs, qualifying seeds 17/29/43.
- Test: 6,300 verified rows, one unlock ledger entry, one start marker, one final verdict.
- Safety/integrity: every test hard-count is zero; GPU request was physical GPU 1 only, GPU 2 was not selected.

## Scientific result

`masked_ddqn_gamma1` = 737/900 and `forecast_rule` = 737/900. The final classifier is `RULE_PARITY_SIGNAL`; this is not evidence that DDQN exceeds the rule baseline.

## Evidence and next boundary

Test evidence archive: `ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/server-test/formal_test_evidence/formal_test_once_evidence.zip` (SHA256 `78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0`).

No further action is authorized on this sealed test root. Future training or a fresh test requires a new scope, frozen configuration and explicit authorization.
