# Test-once monitoring record

旧的每 10 分钟只读监测已在终态核验后停止（automation `family-3-held-out-test`）。

| UTC | status | rows | process | note |
|---|---|---:|---|---|
| 2026-09-22 03:19 | RUNNING | 4,800 | supervisor/runner alive | fixed GPU-1 environment; one writer |
| 2026-09-22 03:23 | RUNNING | 5,400 | supervisor/runner alive | no retry or source/config change |
| 2026-09-22 03:29 | PROCESS_EXITED | 6,300 | exit code 0 | terminal postflight started |
| 2026-09-22 03:34 | FINAL_RULE_PARITY_SIGNAL | 6,300 | no test process | integrity and evidence archive verified |

Connection interruptions were not observed during the actual run. Earlier preflight failures were launcher-environment mismatches before test opening and are recorded in `notes.md`; they are not experiment failures.
