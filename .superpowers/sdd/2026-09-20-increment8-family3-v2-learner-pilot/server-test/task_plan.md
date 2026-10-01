# Task plan: sealed held-out test-once
Status: COMPLETE / SEALED — 6300/6300 test rows, FINAL_RULE_PARITY_SIGNAL. The detailed completed checklist is task_plan_terminal.md. The scope/checklist below is the historical pre-launch plan, not pending work or authority to run again.

## Scope
Run the existing CUDA pilot's explicit test-once command against the completed formal root on physical GPU 1. Use the existing validation permit and final checkpoints. No retraining, tuning, seed replacement, source/config change, retry, or smoke rerun. Test is opened exactly once.

## Fixed test
Three held-out graphs, 7 methods, 3 seeds, 2 conditions, 50 episodes per cell = 6300 rows. Validation-qualified seeds remain 17, 29, 43. Test resume is allowed only for durable missing coordinates after an interruption; no automatic retry.

## Phases
- [x] Read validation postflight and frozen handoff.
- [ ] Verify formal root/permit/test absence and remote resources.
- [ ] Launch exactly one detached test-once process and save credential-free receipt.
- [ ] Observe progress or first genuine failure; preserve evidence.
- [ ] Postflight verify 6300 rows, test integrity, classification, fingerprints, hard counts and no duplicate execution; download evidence.
- [ ] Update project logs and stop the test monitor after terminal verification.

## Guardrails
Physical GPU 1 only; GPU 2 unused. Never delete or overwrite formal results. A connection failure is not a test failure. If the process fails, preserve records and stop for discussion. Test access is now explicitly authorized by the user; no further test permission is inferred for any later rerun.
