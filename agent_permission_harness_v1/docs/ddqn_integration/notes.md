# Source notes: task-Agent DDQN integration

> Historical preparation notes below describe the pre-implementation state. Update 2026-09-29: native DDQN bridge, CPU/CUDA execution and the remote pilot are now implemented; actual outcomes and limitations are in [the execution report](../06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md). Do not treat historical “pending” wording below as current status.

## Boundaries
- Source inspection and documentation only in this preparation stage.
- User-selected DDQN/task-Agent integration is separate from S-QSTN human-answer simulation.
- Family3-v2's original protocol and checkpoints remain unchanged.

## Verified local sources
- `../../../rl_personal_assistant/src/pa_rl/ddqn.py`: configurable model dimensions, shared candidate scorer, authoritative masks, replay/target-network training.
- `../../../rl_personal_assistant/src/pa_rl/family3_v2_policy.py`: forecast and synthetic-branch-specific observation fields; 37 base values plus six active-grant values.
- `../../../rl_personal_assistant/src/pa_rl/family3_v2_model.py`: the offer window closes after the first request; refresh is always invalid in that environment.
- `../../../rl_personal_assistant/src/pa_rl/family3_v2_outcome.py`: terminal binary reward with utility/task completion, prompt/exposure budgets and zero violation constraints.
- `../../contracts.py`: current ControlView includes pending call, grants, candidates, public history, control step and ordinary prompt count; explicit learner episode context is absent.
- `../../rl_policy.py`: mapping-valued public structural encoding and scorer/tabular inference plumbing; not a numeric DDQN training adapter.
- `../../runner.py`: currently chooses and dispatches a candidate, but does not deliver S/A/R/S'/done to a learner.
- `../../ledger_dispatch.py`: deny causes replanning; escalation/request/refresh can wait and resume. These are not old Family3 terminal transitions.
- `../../docs/00_DESIGN_zh.md`: modular six-action architecture and meaningful distinction between projection and revocation.
- `../../README.md`: original-query inventory is broad, but only q22 and an engineered adaptive lifecycle task have explicit executable business oracles.

## Initial findings
1. Reuse the existing DDQN algorithm. Fixed-seven restrictions belong to the Family3 adapter/checkpoint, not the general scorer.
2. Preserve exact scope/grant candidate binding and monitor enforcement after action selection.
3. Give the new environment an explicit feature/reward/checkpoint schema; arbitrary zero padding is not compatibility.
4. A human wait suspends a pending transition; repeated polling must not create extra actions, cost or learner updates.
5. Report actual disclosed fields separately from authorization-surface exposure. A narrow tool projection does not revoke a broad grant.
6. A local training pilot and a live-LLM validation are different evidence classes. No trained-policy performance has been established for the new Agent yet.

## Independent design audit incorporated
- Transition boundary: adjacent actionable controller decisions, exactly one dispatch; human waits and planner replanning advance the environment without extra actions. Terminal credit belongs to the last accepted action.
- Safety gate: current replay/hash verification flags are not already reward gates. New reward must require semantic ledger/monitor/receipt/local-effect reconciliation, not hash verification alone.
- Disclosure and authorization footprint are distinct. Pending/refused refresh retains the old grant; approved refresh supersedes it; narrow projections do not revoke it.
- The written specification deliberately uses a new 38/35/64 schema and grant-field/control-step proxy; it does not represent an old Family3 checkpoint or claim measured DDQN efficacy.
- Self-review corrected the actual permission enum name to `deny_persist`, separated resource-guard accepted decisions from committed tool effects, raised the offline planner limit for eight-step held-out tasks, and required an external evaluation RNG because even greedy native DDQN selection consumes RNG.
- See `../superpowers/specs/2026-09-29-ddqn-agent-integration-design.md`. The user approved this specification on 2026-09-29; the current steering is to preserve a local recap and design the auxiliary fine-tuned security checker. The approved DDQN implementation remains pending, not awaiting another routine approval.
