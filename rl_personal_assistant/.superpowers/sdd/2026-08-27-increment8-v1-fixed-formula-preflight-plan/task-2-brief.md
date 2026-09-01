# Task 2 — Family-3 ten-graph exact certificate

## Scope

Run exactly `i8_s3_v0` through `i8_s3_v9` with the reviewed runner. Do not
edit source or tests. Do not run any Family 0–2 graph, summary, policy,
learner, smoke, training, validation, or parameter search.

## Frozen entry and output

- Working directory:
  `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`
- Module: `pa_rl.increment8_v1_preflight`
- Output root: `results\increment8_v1_fixed_formula_preflight`
- Frozen source SHA-256:
  - `src/pa_rl/increment8_v1_preflight.py`:
    `8A6160BDA16F97354530933A25A2D180FE44DFDDAADB003FD0EB7E2DCD0187A2`
  - `tests/test_increment8_v1_preflight.py`:
    `40D4950A0D8B41B23C17E96A77ECB562B736F9EA4186AF2682C579694B1BEFE1`

## Execution

1. Confirm the output root is absent before the first command and the two
   source hashes match.
2. For each variant `0..9`, run:

   `$env:PYTHONPATH='src'; python -m pa_rl.increment8_v1_preflight --graph-id i8_s3_vN --output-root results\increment8_v1_fixed_formula_preflight`

3. At most three independent graph processes may run concurrently. Each has
   its own SQLite/checkpoint directory. This is execution parallelism only;
   no scientific parameter changes.
4. Exit `0` means `CERTIFIED_PASS`; exit `2` means a completed exact
   `CERTIFIED_FAIL` and is not a process error. Continue until all ten exact
   certificates exist even if one fails. A crash/interruption may be resumed
   once with the identical command and output directory; do not delete or
   replace its cache.
5. After ten certificate files exist, run:

   `$env:PYTHONPATH='src'; python -m pa_rl.increment8_v1_preflight --summary family3 --output-root results\increment8_v1_fixed_formula_preflight`

6. Record every graph's exact fraction, decimal, PASS/FAIL, state count,
   command exit, and whether it resumed. Record the summary's exact macro,
   minimum graph/value, counts, status, and exit.

## Stop gate

- If all ten pass `3/5`, report `DONE` and explicitly state Task 3 is
  unblocked.
- If any graph fails, still complete and preserve the ten-graph summary, then
  report `DONE_WITH_CONCERNS`; Task 3 remains blocked.
- If a command has a non-certificate error after one identical resume, report
  `BLOCKED` with the checkpoint path and error. Never change a parameter.

## Report

Write the full execution evidence to:
`.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-2-report.md`

Do not dispatch subagents and do not commit. Return only status, one-line
ten-graph summary, concerns, and report path.
