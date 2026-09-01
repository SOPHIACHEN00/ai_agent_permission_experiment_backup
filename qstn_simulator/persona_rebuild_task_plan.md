# Task Plan: Empirical Permission-Response Profiles

## Goal

Replace the forced four-archetype construction with a lightweight, behavior-driven, held-out-validated persona pipeline for QSTN.

## Phases

- [x] Phase 1: Confirm the research design and inspect the available human data.
- [x] Phase 2: Archive and remove the obsolete forced-four-archetype implementation.
- [x] Phase 3: Implement participant-level behavior features and held-out response splits.
- [x] Phase 4: Compare candidate cluster counts and report stability and interpretability.
- [x] Phase 5: Update the method document with results and publish it to Google Drive.
- [x] Phase 6: Verify generated artifacts and summarize the findings for discussion.
- [x] Phase 7: Compile discovery-only empirical profiles into auditable QSTN persona prompts and validate their local rendering.

## Key Questions

1. Which candidate cluster count is best supported by separation, stability, minimum size, and interpretability?
2. Are the resulting segments stable when participant features are estimated from disjoint response subsets?
3. Can the profiles be named only from observed permission behavior without psychological over-interpretation?

## Decisions Made

- Cluster only behavior-derived features; reserve self-reported profile fields for post hoc characterization.
- Keep `necessary`, `incorrect_explicit`, and `unknown` request statuses separate.
- Compare `k=2..6`; do not force a preselected number of personas.
- Treat clusters as descriptive permission-response profiles, not natural or independent psychological types.
- Use within-participant stratified held-out responses to prevent QSTN evaluation leakage.

## Errors Encountered

- `ai_agent_permission_experiment` is not an independent Git repository; verification will use file manifests, checksums, and runtime tests.
- `unknown` necessity status is too sparse for participant-level clustering: only 80 rows and 153 of 201 participants have no observations. Confirmed resolution is to retain all rows but use the score only for post hoc characterization.
- `k=4` has the strict maximum mean silhouette by only 0.001336 over `k=3`, but `k=3` has stronger split stability and minimum cluster support. The confirmed selection uses a one-standard-error-style parsimony rule: `k=3` is the smallest eligible solution within one standard error of the best eligible split silhouette.

## Archive

- Path: `archive/forced_four_archetypes_20260721.zip`
- SHA-256: `3F5EFC22B3C7DD05F3F3C37C44D7DD4C3BB8683DFDCDE68B6F6523B0FEFDE44A`
- Contents: 14 obsolete source, configuration, documentation, generated-output, and contextual snapshot files.

## Status

**Complete for profile discovery** - `k=3` is selected, outputs are regenerated, SHA-256 reproducibility is verified across two independent runs, and the decision rationale is recorded in the local plan and Google Doc. QSTN prompt integration and held-out LLM evaluation remain a later, separate phase.

**Persona compilation complete** - the active QSTN inputs now include 201 participant-level calibration personas with discovery-only empirical profile cards and three canonical profile prototypes. All 204 prompts render locally with the scenario and four options present; no LLM API request was made during compilation or validation.
