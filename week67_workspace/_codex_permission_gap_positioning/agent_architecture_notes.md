# Notes: Agent Architecture Gap Audit

Working evidence log. The final synthesis will be written to `agent_architecture_audit.md`.

## Current project: observed runtime boundary

- The design explicitly rejects end-to-end token-level RL for the current Step 3A and adopts a hierarchical structured controller. The current milestone is a public-observation-only, ledger-backed, reference-monitored sequential environment, not the final agent system.
- The documented final system still places an `LLM planner / support model` before the structured controller and a tool/output layer after the reference monitor. Those components are a target architecture, not the completed r2 implementation.
- In the implemented environment, task steps are authoritative entries in a frozen `ScenarioManifest`; the controller does not infer or generate the plan from the user's natural-language goal.
- The tool is literally `MockTool`, described as a plan-driven synthetic tool. Outcomes come from a frozen `(scenario_id, task_step_id, attempt_index)` mapping.
- The LLM used in the S-QSTN integration is prompted as a `synthetic respondent`, not as the task-performing agent.
- The r2 learner traverses a precomputed audited response graph during training/evaluation. It selects among a supplied candidate catalog; it does not invoke a planner or real tool backend online.
- There is no implemented user-facing final-answer generation or observation-to-replanning loop in the completed r2 experiment.

## Wu et al. (IEEE S&P 2026)

- The paper provides a conceptual AI-agent system model (LLM, prompt, memory, tools, plan) and envisions placing a permission assistant in trusted scaffolding.
- Its empirical artifacts are an immersive vignette website plus a permission-prediction system (IC, CF, and hybrid IC+CF).
- The paper explicitly states that implementation and deployment of the permission assistant are out of scope and later lists enforcement, robustness, and usable interfaces as remaining challenges.
- The official repository lists only data, queries, website screenshots, three permission-prediction approaches, and evaluation utilities; it does not expose a planner/tool-execution agent runtime.
- Therefore Wu et al. should not be treated as an end-to-end agent baseline. It has a stronger user-facing framing and permission-prediction prototype, while the current project has a stronger simulated authorization/enforcement kernel.

## Provisional comparison

Neither project currently demonstrates a complete end-to-end agent. The missing pieces differ:

- Wu et al.: no implemented runtime authorization/enforcement or task-performing agent loop.
- Current project: real structured authorization lifecycle and mock execution loop, but no LLM task interpretation/planning, real tool selection/execution, observation-driven replanning, or final user response.

The current implementation is best named a `permission-aware sequential controller testbed` or `authorization-control environment`, not a complete RL-based agent.

## Independent audit synthesis

- A useful evidence vector is `P2/C2/E2/A1`: operational permission learning, controller, and bounded effect enforcement; only a scripted end-to-end agent shell.
- Wu et al. is approximately `P2/C0-1/E0/A1`: an operational permission predictor embedded in a conceptual agent setting, without runtime enforcement or a task loop.
- The current project therefore advances beyond Wu at the controller/enforcement layers, but neither system reaches an operational end-to-end agent (`A2`).
- The architecture gap affects external validity and agent-level wording, not the internal validity of component-level controller/enforcement results.
- The minimum credible next stage is a frozen planner plus stateful sandbox tools, canonical intent-to-scope compilation, existing permission/authority stack, observation-driven replanning, and a receipt-grounded final answer.
