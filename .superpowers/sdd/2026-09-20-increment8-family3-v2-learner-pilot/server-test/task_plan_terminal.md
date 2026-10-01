# Held-out test-once terminal record

Status: COMPLETE. Exactly one explicit held-out `test-once` run was opened and finished; no retry or resume was used.

## Fixed scope

- Three held-out graphs, seven methods, three validation-qualified seeds (17, 29, 43), two conditions, and 50 episodes per cell: 6,300 rows.
- Existing formal validation permit and final checkpoints were used. No retraining, tuning, seed replacement, source/config change, smoke rerun, or test reopening.
- The requested process environment selected physical GPU 1 through `CUDA_VISIBLE_DEVICES=1`, `PA_RL_DEVICE=cuda:0`; GPU 2 was not selected.

## Terminal verification

- Detached supervisor and runner ended with `exit_code=0` in 597.944 seconds; one unlock-ledger entry and one writer.
- Formal root state: `FINAL_RULE_PARITY_SIGNAL`.
- Validation: `READY_FOR_TEST`, 4,200 rows, 12/12 completed checkpoints, qualifying seeds 17/29/43.
- Test: 6,300 verified rows, one start marker, one final verdict, no duplicate rows.
- All test hard-integrity counters are zero, including invalid actions, unauthorized committed effects, test-before-unlock, source/config/checkpoint hash mismatch and split leakage.
- Scientific classification: `RULE_PARITY_SIGNAL`. `masked_ddqn_gamma1` and `forecast_rule` each have 737/900 terminal successes and both match all 900/900 first-request and forecast-rule coordinates. This is parity with the rule baseline, not a DDQN-over-rule result.

## Evidence

Downloaded archive: `formal_test_evidence/formal_test_once_evidence.zip` (23 entries, 780,834 bytes), SHA256 `78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0`.

CUDA overlay verification is 103/103; the unchanged local baseline package is 99/99. The server baseline verifier is expected to flag the three intentional CUDA-overlay files and is not treated as a test failure.
