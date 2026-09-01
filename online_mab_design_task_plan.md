# Task Plan: Single Online MAB Design

## Goal

Produce a research-grounded, implementation-ready design for one online contextual-MAB baseline that bridges the existing offline stated-policy benchmark to the later CMDP security-agent study, without prematurely duplicating the CMDP contribution.

## Phases

- [x] Phase 1: Scope the online-MAB role against the professor's Step 1--5 roadmap.
- [x] Phase 2: Inspect the existing permission-agent code, data, and simulator prerequisites.
- [x] Phase 3: Verify applicable primary literature on safe/interactive contextual bandits and unbiased feedback collection.
- [x] Phase 4: Select one recommended formulation, feedback protocol, data schema, metrics, and fair offline-to-online comparison.
- [x] Phase 5: Write and review the implementation-ready proposal; stop for user approval before coding.

## Key Questions

1. What single online-MAB formulation is a defensible Step-2 baseline rather than an early CMDP?
2. What feedback can be observed safely after automatic permission decisions?
3. How can the study legitimately improve on the frozen offline MAB without test-label leakage or an unfair oracle?
4. Which outcomes remain logged diagnostics or future CMDP costs rather than scalar reward terms?

## Decisions Made

- The online MAB will remain a one-step contextual-bandit baseline; persistent-rule effects and safety-constrained long-horizon optimization are reserved for CMDP.
- The proposed design must use a safe feedback/audit mechanism, since silence after automatic allow is not valid consent feedback.
- The single recommended method is warm-started personalized Factored Thompson Sampling (WP-FTS): an independent tempered user posterior starts from a frozen global prior and updates only from that user's selected-action binary joint reward.
- The primary evaluation is randomized sequential online-feedback replay from original human survey labels. It is not a live online study, and QSTN is excluded as a primary feedback source because its current held-out calibration does not validate it as human-like feedback.
- A complete Chinese proposal was written as `ONLINE_MAB_DESIGN_PROPOSAL_zh.md`, including a beginner-oriented explanation of WP-FTS before the full technical protocol.
- The deliverable is an implementation-ready design proposal only. No implementation begins until user approval.

## Errors Encountered

- None.

## Status

**Design complete; awaiting user approval before implementation.**
