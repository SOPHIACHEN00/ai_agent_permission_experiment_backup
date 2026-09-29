# Task plan: DDQN integration into the single-Agent harness

## Goal
Connect the existing masked, candidate-scoring DDQN to the modular task-Agent harness, with explicit public state, six-action bindings, episode transitions, constrained terminal reward, training and frozen evaluation. Preserve Family3-v2 as its original synthetic benchmark.

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation preparation / experiment design
- Origin Date: 2026-09-29
- Verification Status: ANALYZED (source inspection only; no new training or tests)
- Version Label: agent-ddqn-integration-design-v1

## User decisions
- The user approved the integration direction and requested execution.
- Use academic-research-suite throughout subsequent turns in this chat.
- S-QSTN belongs only to the human-response simulation side, not the task-Agent RL design or implementation.
- Reuse DDQN and six controller actions; do not replace the research policy with tabular Q or a handcrafted rule.
- Do not silently map the new environment into the old Family3 43/7/7 checkpoint schema.
- Initial work is local/offline; no paid API calls in this preparation stage.

## Phases
- [x] Inspect the existing architecture, learner interfaces and prior approvals.
- [x] Write and self-review the new state/action/reward/transition specification.
- [ ] Obtain review of the written specification (architectural-design gate).
- [ ] Produce the detailed implementation plan and obtain its review/execution selection.
- [ ] Implement test-first; verify real DDQN inference, training transitions, lifecycle behavior and checkpoint isolation.
- [ ] Run the approved small offline pilot with frozen-policy controls; report raw metrics without efficacy overclaim.

## Status
Written specification complete and self-reviewed. Awaiting user review of `../superpowers/specs/2026-09-29-ddqn-agent-integration-design.md`. No production code, experiment script or dependency change has been made; no training or paid API call has run.

## Errors encountered
- A scoped rg invocation included a nonexistent top-level `docs` path. Resolved by using the existing package documentation directories.
- A combined skill read was truncated. Re-read the affected skill files completely before using them.
- Git reports dubious ownership. Use a command-local safe.directory exception for this exact repository only; do not change global Git configuration.

## Evidence / next artifact
See `notes.md` and `../superpowers/specs/2026-09-29-ddqn-agent-integration-design.md`.
