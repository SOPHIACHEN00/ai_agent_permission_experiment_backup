# Learning Permission Decisions for AI Agents

Current four-action permission controller, stateful mock tools, S-QSTN user simulator,
and the retained logistic-regression and contextual-bandit baselines.

**Start here:** [Method](docs/METHOD.md) · [中文方法说明](docs/METHOD.zh-CN.md) ·
[Run the code](docs/RUNNING.md) · [Data and evaluation](docs/DATA_AND_EVIDENCE.md)

The agent receives a task, proposes tool calls, obtains actual user consent, and
chooses scoped permission actions before execution. A reference monitor enforces
consent. DDQN learns choices among legal candidates from task outcomes and costs.
The executable implementation uses **REQUEST, EXECUTE, RELEASE, END**.

## Agent workflow and reward

![Agent workflow: task query, planner, compiler and candidates, DDQN policy, dispatcher, reference monitor, S-QSTN, mock tools and evaluator](docs/images/agent-workflow-and-reward.png)

The task loop handles execution and permission interactions. The learning loop
updates the DDQN policy from observed outcomes and rewards during training.

## Components

| Directory | Purpose | Entry point |
| --- | --- | --- |
| [rl_agent_structure](rl_agent_structure/README.md) | Agent, consent ledger, gates, monitor, evaluator, DDQN | `run_noapi.py`; `rl_testing/run.py` |
| [mock_tools](mock_tools/README.md) | Minimal stateful read/write tools and receipts for 65 Wu tasks | `python -m mock_tools.run` |
| [s-qstn](s-qstn/README.md) | Retrieval-calibrated simulation of four human permission responses | `python s-qstn/run.py` |
| [classification](classification/README.md) | Flat, independent cumulative-threshold, and factored logistic regression | `classification/run_four_label_benchmark.py` |
| [bandit_experiment](bandit_experiment/README.md) | Canonical offline stated-policy contextual bandits | `bandit_experiment/run_stated_policy_bandit.py` |
| [online_bandit_experiment](online_bandit_experiment/README.md) | Warm-started Personalized Factored Thompson Sampling (WP-FTS) | `python -m online_bandit_experiment.run_wp_fts` |
| [online_mab](online_mab/README.md) | Detailed Chinese MAB methods and final result interpretation | Documentation |
| [in_context_learning](in_context_learning/README.md) | Retained four-label ICL implementation and S-QSTN adapter | `in_context_learning/run_ic_four_label.py` |
| [data/processed](data/processed/README.md) | Four-label survey table and build metadata | 16,361 answers, 201 participants |
| [external/ai-agent-permissions](external/ai-agent-permissions/README.md) | Attributed upstream task and survey inputs | `queries.json`, `data/` |

The LR/MAB **four permission-response labels** and the Agent's **four controller
actions** are different action spaces. A predicted permission label never grants
permission to execute a tool.

## Quick start: offline functional check

Python 3.12 is the reference runtime. From the repository root:

```bash
python -m venv .venv
# Activate .venv using your shell.
python -m pip install -r requirements-agent.txt
python rl_agent_structure/run_noapi.py --persist-rounds 3 --all-wu --output rl_agent_structure/outputs/functional_demo
```

Use a new output directory for every run. This command uses a scripted planner,
explicit fixture answers and a rule controller. It performs no LLM API calls and
no optimizer updates. The [running guide](docs/RUNNING.md) covers CPU DDQN checks,
S-QSTN installation, baseline reproduction, and all offline test suites.

## Current evidence

- The four-action workflow and all 65 task paths have passed offline functional checks.
- Native DDQN optimizer updates have been observed. Stable execution without
  exploration and individualized preference gains remain research questions.
- The retained DDQN comparison uses Q40/Q41/Q55 with a fixed simulated response
  rule. Its final success counts are 6/9 and 5/9 for the two exploration settings.
- LR, MAB and S-QSTN have their own evaluation protocols. Their scores do not
  establish the Agent's end-to-end task or personalization performance.

Evidence dates and compact original result files are listed in
[Data and evaluation](docs/DATA_AND_EVIDENCE.md). Shared-policy personalization,
few-shot/meta-RL and model-based alternatives are [research directions](docs/RESEARCH_DIRECTIONS.md),
not implemented methods in this release.

## Repository scope

This tree contains the current implementations, required inputs, tests, method
documentation and compact final evidence. Retired implementations, six-action
snapshots, local environments, model checkpoints, credentials and raw run logs
are excluded. Previous commits remain available through normal Git history.
See [third-party attribution](THIRD_PARTY_NOTICES.md) for upstream data licensing.
