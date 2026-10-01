# Research and archival notes

## Confirmed starting point

The sealed Family-3 v2 run is complete. Formal training/validation used 144,000 transitions, 12 checkpoints, and 4,200 validation records. The single authorized held-out evaluation has 6,300 records. DDQN gamma=1 and Forecast rule each succeeded in 737/900 test evaluations.

The result classifier gives rule parity precedence over credit signal. Both signals are present for training seeds 17, 29, and 43; “no credit signal” is an incorrect interpretation. Initial actions and terminal success match across the two methods, but some already-failing episodes have different termination paths. Full trajectories must not be described as identical.

## Task boundary

This task is experiment design plus evidence archival, not a new training run. Keep archival summaries separate from the frozen evidence ZIPs and source/configuration.

## Resolved research questions

- Placement: Increment 8 follow-up supporting the proposal's sequential-permission stage. Earlier s3_v3/s3_v4 records concern graph IDs in the old Family-3 review, not an already implemented competing new environment. Use a new budget_recourse identifier to avoid conflation.
- Integrity and per-seed counts were recomputed directly from archived JSONL and checkpoint manifests. Data files and RESULTS_ARCHIVE_zh.md preserve the results and limitations.
- The new candidate uses two tasks with shared exposure/prompt budgets, explicit additional broader consent, and newly disclosed second-stage forecast. The resource-conditioned action flip is an analytical witness, not a new exact certificate.

## Design choices and exclusions

- Keep a cost-aware current-task rule, a resource-reservation rule, and full-information-in-the-public-state exact planning; do not claim beating an optimal planner.
- Fixed ten-graph candidate set, 5/2/3 grouped split and prompt-budget interventions; no search and no claim that these are ten independent real-world mechanisms.
- Stage A is the next implementation. Proposed Stage B has only two DDQN learners, 72000 total transitions and three fresh seeds. No training/server/API task started.
- New thresholds are proposed versioned criteria, not retrospective edits to old v1/v2 thresholds.
- Primary references checked: van Hasselt et al. arXiv:1509.06461; Agarwal et al. arXiv:2108.13264. Environment and numeric thresholds are this project's design choices, not literature-established facts.

## Persistent records / recovery

Main progress and decision logs now include sealed test completion and ADR-IMPL-037. The main continuation checkpoint explicitly supersedes stale running/pre-test instructions. Historical sidecars retain their text with correction notices; original ZIPs and classification JSON are unchanged.

Local sandbox access errors were tool-environment failures. Add-file patches worked; updates used the verified apply_patch executable after the sandbox helper and batch-wrapper issues. One final consistency check passed: 14 method-summary rows, 42 per-seed rows, 2 pair-summary rows, matching ten-graph Chinese/JSON tables and planned budget arithmetic. No unit tests, new environment transitions, solver runs or model evaluation were performed.
