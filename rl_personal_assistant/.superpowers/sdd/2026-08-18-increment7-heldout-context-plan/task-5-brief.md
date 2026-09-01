### Task 5: One frozen pilot run, interpretation, and durable handoff

**Files:**
- Runtime-create: `results/increment7_paired_v0/**`
- Create: `docs/implementation_reports/task-7-heldout-context-report.md`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`
- Modify: `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`

**Interfaces:**
- Command: `python -m pa_rl.increment7_pilot --criteria configs/evaluation/heldout_context_v0.json --output results/increment7_paired_v0`
- Result classification: `ADVANTAGE_SIGNAL`, `PARITY`, or `NO_GO` under the saved criteria profile.

- [ ] **Step 1: Freeze pre-run evidence**

Write suite, split, config, criteria, source, and focused-test hashes to the continuation checkpoint. Verify the result directory does not already contain a completed run. Record status `READY_FOR_FROZEN_RUN` and the exact command before execution.

- [ ] **Step 2: Execute the default pilot exactly once**

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.increment7_pilot --criteria configs\evaluation\heldout_context_v0.json --output results\increment7_paired_v0
```

Do not edit source/config while active. Preserve complete stdout/stderr/exit status and measured wall time. During a long tool run, yield at most every 60 seconds for a user-visible progress update. If output capture or network/tool orchestration fails, write the exact phase and completed-seed checkpoint paths before requesting any identical recovery execution.

- [ ] **Step 3: Apply the frozen stop rule**

- `ADVANTAGE_SIGNAL`: report only an exploratory held-out context advantage signal.
- `PARITY`: prefer the best qualifying simple method and make no Deep-RL advantage claim.
- `NO_GO`: preserve artifacts, stop, and request manual inspection; do not tune/reseed/rerun.
- Any run-integrity safety failure overrides performance classification and stops interpretation.

- [ ] **Step 4: Verify artifacts without retraining**

Parse all JSON, verify checkpoint/result/source hashes, confirm 40 suite members and 24/8/8 rows, check each per-seed/per-scenario denominator, recompute aggregate macro values and gate classification from raw rows, and confirm all evaluation safety counts. Rerun only focused tests and targeted compile; never rerun training for verification.

- [ ] **Step 5: Write the implementation report**

Record exact suite/split, feature boundary, train/eval budgets, command, runtime, all macro/per-seed/per-family results, base-versus-protocol success, safety/automation metrics, gate booleans, classification, checkpoint/source hashes, interruption history, and limitations. State explicitly that the statistical units are eight held-out scenarios and three training seeds, not repeated episodes or users.

- [ ] **Step 6: Update plans and durable logs**

Update `task_plan.md` with Increment 7 status, append the decision and progress logs, and finish `CONTINUATION_CHECKPOINT.md` with final hashes and next recommended research step. Preserve the Increment 6 frozen artifacts and deferred B2B1 findings unchanged.

---

## Plan self-review checklist

- Spec coverage: suite, split, public firewall, family protocols, negative controls, balanced budget, validation/test freeze, hot-swappable gate, safety metrics, checkpoints, source hashes, interruption recovery, and report are each assigned to a task.
- Type consistency: suite, criteria, checkpoint, runner, and Rule interfaces are defined before consumption.
- Test limit: exactly three Increment-7 focused methods; later tasks extend method 3 rather than adding a fourth.
- Scope: no authority/evaluator/environment/replay/PPO/S-QSTN/reward-tuning work.
- Stop rule: one default run, no automatic tuning or recovery rerun.
