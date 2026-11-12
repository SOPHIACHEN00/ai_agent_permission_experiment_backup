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
| Opt-in API transport and inference | `integration/online.py`, `../../run_online.py` |
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

## Online API inference

`run_online.py` connects `StructuredPlanner` and `SQSTNResponder` to the existing
OpenRouter client. Compilation, the four-action controller, consent ledger,
dispatcher and reference monitor remain on every execution path. Tools remain
local stateful mocks. S-QSTN represents a simulated user in this experiment;
its replies are not consent from a real person for real external tools.

Follow the [root setup](../README.md#online-api-setup) to install
`requirements-online.txt` and `requirements-rl.txt`, copy [.env.example](.env.example) to a local `.env`,
set `OPENROUTER_API_KEY`, and explicitly initialize a new campaign ledger if none
exists. The process environment takes precedence; the default file is resolved
relative to this Agent directory, independent of the current working directory.

```bash
# Preview DDQN configuration: no checkpoint/key loading or network requests.
python rl_agent_structure/run_online.py --queries 40 41 --user-id online-demo --persist-rounds 3

# Paid API inference with the default DDQN permission controller.
python rl_agent_structure/run_online.py --queries 40 41 --user-id YOUR_CHECKPOINT_USER --checkpoint PATH_TO_CHECKPOINT --persist-rounds 3 --execute --output rl_agent_structure/outputs/online_ddqn_demo
```

DDQN is the default. Execution requires an existing **user-local DDQN checkpoint**;
no trained checkpoint is bundled, and no checkpoint means an error before any API
request. The CLI does not silently replace DDQN with rules or a randomly initialized
network. The no-network preview can run without a checkpoint.

The rule controller remains available only as an explicitly selected baseline:

```bash
python rl_agent_structure/run_online.py --queries 40 41 --user-id rule-demo --persist-rounds 3 --policy rule --execute --output rl_agent_structure/outputs/online_rule_demo
```

- The checkpoint must match the current four-action/feature schema and user ID.
- The CLI supports checkpoints that do not require an external retention bank.
- Inference uses CPU and epsilon 0. Replay, weights and optimizer state are not updated.
- A checkpoint restores the model, not past authorization, gates or simulator memory.
- The default `--profile` is `persistent_granters`; alternatives are `reconsent_seekers` and `broad_restrictors`.
- `--max-model-calls 32` bounds combined request attempts across both API roles and all queries in this invocation.
- The cumulative USD 5 ledger is shared with standalone S-QSTN; the invocation does not reset it.
- Demo runtime limits are 64 control decisions, 16 planner turns and 32 permission messages per query, plus the existing bounded cleanup phase. These are execution bounds, not tuned research hyperparameters.
- A malformed proposal or reply does not authorize tool access. Provider failure stops the sequence; calls are not automatically retried.
- Q54's authored-content item, Q63/Q64 setup items and clarification requests may require manual handling. The run records `awaiting_human` and stops; a persistent interactive inbox is not implemented by this CLI.

`config.json` contains non-secret run settings. `summary.json` contains per-task
metrics, consent/monitor audit evidence and provider job IDs. Individual provider
records and cumulative accounting remain in `s-qstn/outputs/` and `s-qstn/state/`.
These generated files are Git-ignored. Request attempts may fail before payment;
inspect the budget ledger for settled costs and unresolved reservations.

This API inference entry is separate from `rl_testing/online_check.py`, which
tests online **RL updates** using offline fixtures, and from the online MAB
experiments. No live API training or new performance result is claimed here.

## Current research boundary

The monitor enforces authorization; learning chooses among legal actions. Training
is pure RL in the retained November 3 comparison. Shared-policy pretraining,
meta-RL and the proposed bounded bootstrap update have not been implemented.
Completion under exploration is not evidence of reliable greedy execution.
