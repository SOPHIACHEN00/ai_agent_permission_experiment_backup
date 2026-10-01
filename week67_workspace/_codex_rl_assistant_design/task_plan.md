# Task Plan: RL Personal Assistant and S-QSTN Validation Design

## Goal
Develop an evidence-backed, reviewer-defensible architecture and experimental protocol for an RL personal-assistant agent that interacts with S-QSTN without circular validation or uncontrolled accuracy drift.

## Phases
- [x] Phase 1: Inspect project context, existing classification/MAB work, and rules/principles
- [x] Phase 2: Search and verify primary literature on personalized RL, simulated users, reward modeling, and independent evaluation
- [x] Phase 3: Synthesize architecture, formal problem definition, and anti-circularity protocol
- [x] Phase 4: Specify experiments, ablations, drift checks, reviewer-facing claims, and next implementation steps
- [x] Phase 5: Review and deliver

## Key Questions
1. What state, action, transition, and reward design naturally extends the existing classification and MAB components?
2. Which information from S-QSTN may be used for interaction/training, and which must be isolated from reward and evaluation?
3. How can fixed holdouts, independent oracles, human calibration, and cross-simulator testing prevent circular validation and drift?
4. What evidence and ablations will make the design defensible to reviewers?

## Decisions Made
- Keep training feedback, model selection, and final evaluation as separate information channels.
- Treat S-QSTN as one stochastic environment instance, not as ground truth or the sole evaluator.
- Reuse the compatible authority FSM and typed-interface ideas in `personal_assistant_rl_plan_zh.md`; the new deliverable is a reviewer-facing synthesis and anti-circularity protocol, not a competing plan.
- Do not select a large neural optimizer before the typed environment, sequential data coverage, and residual cost structure are known. The method family is a masked, preference-conditioned constrained policy; implementation complexity scales only after the plumbing gates pass.

## Errors Encountered
- A broad `rg --files` inventory crossed an access-restricted semantic-model artifact directory and returned exit code 1 after producing useful results. Resolution: narrow all subsequent reads to explicit project files; no required source is in the restricted artifact cache.
- The nature-academic-search OpenAlex fallback script could not open a network socket inside the filesystem sandbox (`WinError 10013`). Resolution: continued the T1/T2 workflow through the available web research tool and verified claims on primary proceedings/publisher pages.
- One exploratory `rg` call used PowerShell-incompatible trailing glob arguments after the paths. It still returned the relevant evidence before exit; subsequent searches use explicit files or PowerShell-compatible filters.

## Status
**Complete** - Architecture, anti-circularity protocol, drift controls, experiments, reviewer responses, and implementation sequence are documented and reviewed.
