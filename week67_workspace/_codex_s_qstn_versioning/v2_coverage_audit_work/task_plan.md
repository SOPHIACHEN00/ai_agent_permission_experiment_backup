# Task Plan: S-QSTN v2.0 Rule and Principle Coverage Audit

## Goal

Reconcile the 56-rule Excel evidence registry and all 12 principles against the actual S-QSTN v2.0 catalog, executable rule/state implementation, and profile assets, then produce a defensible Chinese research-readiness record.

## Phases

- [x] Phase 1: Plan and setup
- [x] Phase 2: Audit all 56 rules and runtime statuses
- [x] Phase 3: Audit all 12 principles and implementation depth
- [x] Phase 4: Assess experimental readiness and allowable claims
- [x] Phase 5: Write and verify the final Markdown record

## Key Questions

1. Does v2.0 merely preserve all Excel rules, or independently execute all of them?
2. Which principles are directional, partial-stateful, audit-only, or external boundaries?
3. Is v2.0 plus the empirical profile card sufficient as an auxiliary human-side privacy respondent for the planned paper comparison?

## Decisions Made

- Treat catalog inclusion, machine activation, state substrate, and human calibration as distinct coverage levels.
- Assess the current v2.0 package as implemented, while separately documenting its code-level imports from v1/v1.1 helpers.
- Do not require v3 calibration if the human comparison remains secondary and claims are explicitly bounded.

## Errors Encountered

- The first artifact-tool audit printed a complete result but remained alive until the shell timeout. Add an explicit process exit after output and rerun.
- The initial v1/v1.1 import detector spread source strings into characters before checking substrings. Join the source texts and rerun the dependency check.
- `git status` was not applicable because `Week67` is not a Git repository.
- PowerShell `Remove-Item` raised a null-reference error while removing the temporary `node_modules` junction. The exact junction was verified and removed with `System.IO.Directory.Delete` without touching its target.

## Status

**Complete** - The final record contains all 56 unique Rule IDs, all 12 principle rows, runtime verification results, claim boundaries, and the experimental-readiness decision.
