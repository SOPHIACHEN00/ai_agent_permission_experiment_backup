# Task Plan: QSTN Dynamic User-Simulator Assessment

## Goal
Determine whether QSTN or alternatives can support sequential, safety-critical RL for privacy-permission agents, and specify the strongest feasible research path.

## Phases
- [x] Phase 1: Load the project and applicable research-design workflow.
- [x] Phase 2: Inspect the proposal, current QSTN assessment, and experiment artefacts.
- [x] Phase 3: Verify QSTN, PrivacySIM, AlignSurvey, and dynamic candidates against primary sources.
- [x] Phase 4: Synthesize the recommendation, validation gates, and roadmap.

## Key Questions
1. Are the five stated requirements necessary and sufficient for an RL user environment?
2. Can an available simulator satisfy them without material extension?
3. Should the project build a calibrated hybrid simulator, fine-tune an LLM, or run only a frozen benchmark?

## Decisions Made
- Separate benchmark utility from training-environment validity.
- Treat asymmetric safety errors and policy-ranking agreement as release gates.
- Recommend a human-calibrated hybrid environment, not a prompt-only user proxy.

## Errors Encountered
- Initial multi-file patch had an encoding-sensitive context mismatch; no project content was changed and the patch was reapplied safely.
- The workspace root is not a Git worktree, so a scoped `git diff --stat` verification was unavailable; file-presence verification is used instead.

## Status
**Completed** - assessment, evidence record, validation gates, and roadmap written.
