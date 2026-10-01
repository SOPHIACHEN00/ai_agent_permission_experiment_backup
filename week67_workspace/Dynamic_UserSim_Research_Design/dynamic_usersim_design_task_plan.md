# Task Plan: Dynamic User Simulator Research Design

## Goal
Co-design, without implementation, a scientifically defensible dynamic user simulator for the project's privacy-permission and safe-support-agent research stages.

## Scope Boundary
- In scope: literature-grounded requirements, architecture, state/action schema, data-collection protocol, validation gates, baselines, and a staged design decision log.
- Out of scope: installing tools, coding an environment, fine-tuning models, running experiments, recruiting participants, or submitting an IRB application.

## Phases
- [x] Phase 1: Set up the persistent design workspace and recover project context.
- [x] Phase 2: Map comparable multi-turn user-simulator research, datasets, and reusable tools.
- [x] Phase 3: Convert the project/professor roadmap into an explicit simulator research contract.
- [x] Phase 4: Draft and critique candidate architecture and human-study/data protocol.
- [ ] Phase 5: Freeze a design specification only after user confirmation.

## Key Questions
1. What must be simulated, what must be measured from humans, and what must remain an external safety rule?
2. Which existing methods/components can be borrowed without overclaiming their validity in privacy permissions?
3. What is the minimum longitudinal data and validation design needed before simulator-supported RL is scientifically defensible?
4. What decisions must the researcher make before implementation begins?

## Initial Decisions
- Treat the current survey as static stated-policy evidence, not longitudinal transition evidence.
- Use static tools only as benchmarks or components; do not assume an off-the-shelf human replacement exists.
- Keep the design open for revision until evidence review and user approval are complete.

## Errors Encountered
- No local AGENTS.md instruction file was found by the workspace search.
- A broad `rg` filter for project documentation returned no matches; this does not affect the design work because the proposal and prior assessment files have already been read directly.
- An earlier documentation patch used an encoding-unstable context line and made no change; the final design files were re-read as UTF-8 before subsequent edits.

## Status
**Draft v0.1 complete; Phase 5 remains deliberately open** - the literature-grounded research contract, candidate architecture, and human-study/validation protocol are ready for the user's ontology and protocol review. No implementation decision has been made.
