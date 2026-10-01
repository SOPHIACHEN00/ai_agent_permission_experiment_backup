# Task Plan: Permission Experiment Gap Positioning

## Goal

Determine whether the current automating-permission research addresses Gap 1 in Deng et al. (2025), map the completed experiments to all four gaps, and produce a defensible paper/related-work positioning.

## Phases

- [x] Read the survey definitions and formal section mapping for Gaps 1–4.
- [x] Audit the original four-label permission experiments and online WP-FTS replay.
- [x] Audit the latest structured RL / multi-step permission-controller experiments.
- [x] Verify survey-cited and newer primary related work.
- [x] Separate supported claims from planned or unsupported claims.
- [x] Synthesize the final positioning and recommended paper narrative.

## Final decision

- The sequential preference-learning component addresses a bounded slice of Gap 1: user-specific, history-dependent categorical permission feedback.
- The strongest current systems contribution is centered on Gap 2: explicit Agent-to-Tool authorization, complete mediation, and auditability.
- Tool trust creates a Gap 2/Gap 4 boundary, but the completed experiments do not test malicious tools, other agents, or external-memory poisoning.
- Gap 3 is not empirically addressed; remote execution used for training is an engineering setting, not a cross-environment treatment.

## Deliverables

- `permission_gap_analysis.md` — integrated answer and paper-positioning recommendation.
- `experiment_audit.md` — experiment-by-experiment evidence audit.
- `survey_audit.md` — exact survey taxonomy and cited-work audit.
- `related_work_map.md` — broader related-work map with claim boundaries.

## Status

**Complete.**
