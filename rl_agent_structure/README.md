# Four-action permission agent

Current implementation: **REQUEST, EXECUTE, RELEASE, END**, with one task query
per episode and a separate DDQN policy for each user.

- [Full method](../docs/METHOD.md) / [中文说明](../docs/METHOD.zh-CN.md)
- [Installation and commands](../docs/RUNNING.md)
- [What has actually been evaluated](../docs/DATA_AND_EVIDENCE.md)

## Read the code in this order

| Area under `src/personal_assistant/` | Start with |
| --- | --- |
| Contracts and explicit limits | `contracts/permission.py`, `contracts/persistence.py`, `config.py` |
| Task integration | `integration/wu.py`, `integration/execution_assumptions.py` |
| Planner and call compilation | `planning/planner.py`, `planning/scripted.py`, `planning/compiler.py` |
| User/task lifecycle | `execution/user_session.py`, `execution/user_runner.py` |
| C, G and legal actions | `permissions/persistent_ledger.py`, `permissions/gates.py`, `permissions/user_candidates.py` |
| Action execution and exact permits | `permissions/user_dispatch.py`, `permissions/monitor.py` |
| Human/S-QSTN interaction | `interaction/history.py`, `interaction/sqstn_bridge.py` |
| State/candidate features | `learning/user_features.py`, `learning/public_state.py` |
| Transition/reward accounting | `learning/driver.py`, `learning/outcomes.py` |
| DDQN and checkpoints | `learning/policy.py`, `learning/ddqn.py`, `learning/checkpoint.py` |

`execution/runner.py` and the lower-level scope/receipt contracts also support the
standalone mock-tool harness. They are used by current tests and are not a
separate six-action controller. Retired six-action snapshots are excluded.

## Two useful runs

From the repository root after installing the relevant requirements:

```bash
python -B rl_agent_structure/run_noapi.py --persist-rounds 3 --all-wu --output rl_agent_structure/outputs/functional_demo
python -B rl_agent_structure/rl_testing/run.py update-check --config configs/ddqn_update_check.json --output rl_agent_structure/outputs/ddqn_update_demo --allow-training
```

The first uses rules and explicit fixtures. The second performs native CPU DDQN
updates. Neither invokes a live LLM or S-QSTN provider. `rl_testing/` contains
functional, update, exploration and frozen-history diagnostic runners; its
`tests/` suite is separate from the core `tests/` suite.

## Current research boundary

The monitor enforces authorization; learning chooses among legal actions. Training
is pure RL in the retained November 3 comparison. Shared-policy pretraining,
meta-RL and the proposed bounded bootstrap update have not been implemented.
Completion under exploration is not evidence of reliable greedy execution.
