# Task 8: bounded readiness and server handoff

Status: **LOCAL_BOUNDED_VERIFICATION_PASS**, 2026-09-21. Local Task 8 minimal
handoff complete; full crash matrix is not claimed. No process remains running.

- [x] Read approved Task 8 and Task 7 checkpoint; inspect known finalization gap.
- [x] Add bounded real-store permit/test-once/recovery checks; reproduce the
  TEST_CLASSIFIED / final-verdict gap, make the smallest verified fix if feasible.
- [x] Run focused and minimal adjacent checks, compile and read-only freeze audit.
- [x] Run the named NON_EVIDENCE_SMOKE once only if preceding checks pass.
- [x] Produce implementation report + server package manifest and commands;
  update existing project/decision/checkpoint logs with actual evidence.

## Boundaries

No formal training/test, server launch, API, criterion/budget/split changes,
exact DP or twelve-Gate rerun. Preserve results at the first real verification
failure; no repeated smoke or tuning. A deliberate RED reproduction is not a
scientific run. Work stays in the existing checkout (no commits/worktrees).

Use fixed CLI without --config/--output: Task 8 command examples are stale
against the approved fixed-CLI contract. Do not edit frozen plan/spec to hide it.
Keep tests bounded; any omitted full matrix remains explicitly unverified.

## Errors / findings

Latest checkpoint: focused 12/12 PASS (45.135 s), adjacent 27/27 PASS (0.311 s),
compile exit 0, FREEZE_VERIFIED. Independent scoped review found no Critical /
Important issue in the fix; existing exhaustive crash limits remain documented.
The one named NON_EVIDENCE_SMOKE finished: 62.969 s, exit 0. Read-only postflight
confirms 4 checkpoints / 1280 transitions / 28 validation rows / hard-count sum 0 /
stable fingerprints / both DDQN update counts 17 / no test or permit. Formal root
remains absent. Smoke root is now immutable and retained; DO NOT rerun it.
Package hash verification PASS: 99 transfer files, no mismatches. Archive byte
verification PASS: 100 entries (including manifest), 386928 bytes; 42 local smoke
audit files excluded from server transfer. Next is the user's server environment
precheck and decision to start the fixed formal train-validate command.
Archive SHA-256: d7064176d3f2b43b2b8917e486755d9dcf80998698251662d78e801851c8cb1f.
Manifest SHA-256: b81ec42be8a6ba24d09528828f1ee6fca5ff13aab74d23d1cbc0e76269375828.
Source manifest: bcb6e02c9c276f84809b5c529b50c769e57bfd7853875d08c5a1454a1c9c5189.

- Intermittent sandbox helper ACL error before process start; scoped escalated
  fallback succeeds. No test process started on that error.
- Known store rejects repeated classification at TEST_CLASSIFIED; runner also
  rejects that recovery point. Reproduce before changing either.
- Full synthetic row fixture must retain all 4200/6300 coordinates and frozen
  classifiers; use compact fixture materialization rather than reducing science.
