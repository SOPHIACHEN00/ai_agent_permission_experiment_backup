# Running the current implementation

Run commands from the repository root unless a command changes directory. Use
Python 3.12 and a virtual environment. The functional and research-diagnostic
examples below are offline. Only the explicitly marked `--execute`/`--send` modes
in the [online API setup](../README.md#online-api-setup) send paid LLM requests.
Use a fresh output directory to preserve existing evidence.

## Installation

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# bash: source .venv/bin/activate
python -m pip install -r requirements-agent.txt
```

Install only the components you need:

| Component | Additional installation |
| --- | --- |
| Mock tools and rule-controlled agent | No additional packages |
| CPU DDQN and plots | `python -m pip install -r requirements-rl.txt` |
| Logistic regression and MAB | `python -m pip install -r requirements.txt` |
| S-QSTN prompt compilation and integration | `python -m pip install -r s-qstn/requirements.txt` |
| Live Planner + S-QSTN with default DDQN inference | `python -m pip install -r requirements-online.txt -r requirements-rl.txt` |
| ICL prompt preparation and tests | `python -m pip install -r in_context_learning/requirements.txt` |

S-QSTN pins its numerical stack. For all-module verification, install the pinned
S-QSTN/ICL requirements together with the root requirements. The lockfiles record
the source environment; do not copy a local `.venv` into the repository.

## 1. Functional agent and mock tools

```bash
python -B rl_agent_structure/run_noapi.py --persist-rounds 3 --all-wu --output rl_agent_structure/outputs/functional_demo
python -B -m mock_tools.run --all --output outputs/mock_demo
```

The first command exercises the current persistent-consent, four-action agent
over query IDs 0–64. The second checks minimal tool dataflow through the standalone
mock-tool harness. Both use scripted proposals and fixed explicit permission
answers. Neither trains DDQN or measures real business-answer quality.

## 2. Small CPU DDQN update check

```bash
python -B rl_agent_structure/rl_testing/run.py update-check --config configs/ddqn_update_check.json --output rl_agent_structure/outputs/ddqn_update_demo --allow-training
```

This is a short optimizer/checkpoint diagnostic on Q40/Q41, not a learning-quality
experiment. It collects transitions with the rule behavior policy and uses them
to verify DDQN updates; it is not the pure online exploration experiment below.
Its small replay buffer and warm-up are deliberate test settings.
It requires explicit reward weights, runtime limits, query-episode semantics and
CPU selection. Inspect `summary.json` and the generated audit records rather than
assuming that optimizer updates imply a good policy.

To reproduce the retained three-query exploration protocol, run each declared
seed separately. Each invocation runs both candidate and family exploration:

```bash
python -B rl_agent_structure/rl_testing/exploration_trial.py --seed 3 --device cpu --output rl_agent_structure/outputs/exploration_seed3 --allow-training
```

Repeat with seeds 7 and 11 and distinct output directories. The protocol is fixed
in `rl_testing/exploration_trial.py`; hardware/library differences can change
numerical trajectories. A new run does not overwrite the retained result summaries.

## 3. S-QSTN without API calls

```bash
python -B s-qstn/run.py --list-items
python -B s-qstn/run.py --profile persistent_granters --sample-id demo --output s-qstn/outputs/prompt_demo.json
```

The second command previews the first supported questionnaire item. To choose
another item, supply `--query-id`, `--tool`, and `--data-item` together, using the
exact values returned by `--list-items`. Other profiles are `reconsent_seekers`
and `broad_restrictors`.

`--send` is the explicit paid mode. It requires a locally configured provider key
and an existing cumulative budget ledger in `s-qstn/state/budget.json`. The
distribution omits credentials and runtime budget state. `--init-budget` creates
a new ledger explicitly and refuses to overwrite one. See
[the S-QSTN README](../s-qstn/README.md) before using that mode. Repository tests
and the examples above do not require a key or a budget ledger.

For the full Agent with real LLM planning and S-QSTN replies, use
[`rl_agent_structure/run_online.py`](../rl_agent_structure/README.md#online-api-inference).
It previews by default and requires `--execute` for paid calls. The default
controller is DDQN; execution requires `--checkpoint ...` and the matching user
ID for frozen CPU inference. Missing checkpoints fail before any API call.
Use `--policy rule` only for the explicit rule baseline. Both API roles share
one key and one cumulative budget ledger.
This entry performs no online RL updates. The API wiring is covered by mocked
provider tests, not a live paid validation run.

## 4. Logistic regression

The processed dataset is included. To rebuild it in a new directory:

```bash
python classification/build_dataset.py --repo external/ai-agent-permissions --out outputs/rebuilt_data/four_label_dataset.csv
```

Run the fixed baseline or the nested tuning protocol:

```bash
python classification/run_four_label_benchmark.py --data data/processed/four_label_dataset.csv --split participant_heldout --out outputs/lr_baseline
python classification/tune_four_label_classifiers.py --data data/processed/four_label_dataset.csv --splits participant_heldout --out outputs/lr_tuned
```

The tuning run is substantially longer. The participant-held-out split is the
primary evaluation; row-stratified results answer a different question because
the same participant can appear in training and test.

## 5. Offline and online MAB

```bash
python bandit_experiment/run_stated_policy_bandit.py --data data/processed/four_label_dataset.csv --split participant_heldout --out outputs/offline_mab
python -m online_bandit_experiment.run_wp_fts --data data/processed/four_label_dataset.csv --out outputs/online_mab --bootstrap-replicates 5000
```

These are label-feedback simulations. They do not authorize tool calls. The
online runner performs sequential replay per held-out participant and uses
separate training and personal-exploration settings. See the
[Chinese reproduction guide](../online_mab/04_REPRODUCE_AND_ARTIFACTS_zh.md).

## 6. Offline tests

Install all component requirements to run the complete suites. Optional torch or
S-QSTN dependencies otherwise cause documented skips.

```bash
python -B -m unittest discover -s tests/mock_tools -v
python -B -m unittest bandit_experiment.test_stated_policy_bandit online_bandit_experiment.test_wp_fts -v
python -B -m unittest in_context_learning.test_run_ic_four_label in_context_learning.test_current_sqstn in_context_learning.multi_model_screening.test_screen_models -v
cd rl_agent_structure
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s rl_testing/tests -v
cd ../s-qstn
python -B -m unittest discover -s tests -v
```

Five DDQN optimizer tests in `rl_testing/tests` additionally require
`RL_TESTING_ALLOW_TORCH_UPDATES=1`; they run short CPU diagnostics. Set this with
`$env:RL_TESTING_ALLOW_TORCH_UPDATES='1'` in PowerShell or
`export RL_TESTING_ALLOW_TORCH_UPDATES=1` in bash. Eight optional fixed-history
tests need an excluded historical report and skip in a clean checkout.

Test commands use `-B` because the agent checks that its S-QSTN and mock-tool
dependencies remain unchanged. Do not run concurrent jobs into the same output
directory or share one user's learning state between runs.
