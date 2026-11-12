# S-QSTN permission-response simulator

S-QSTN represents the human side of permission interactions. Given a task,
tool and data item, it compiles a calibrated prompt using retrieved reference
answers, a synthetic persona, behavioral rules and permitted interaction memory.
The provider returns one of four permission responses:

| Response | Agent-side meaning |
| --- | --- |
| No, never share | Persistent refusal for the declared scope and validity period |
| No, but ask me next time | Refusal for the current request |
| Yes, but ask me next time | Allow this request once |
| Yes, always share | Reusable consent for the declared scope and validity period |

These are human-response labels, not the Agent's REQUEST/EXECUTE/RELEASE/END actions.
S-QSTN does not issue execution permits or enforce the agent's ledger.

## Offline use

From the repository root:

```bash
python -m pip install -r s-qstn/requirements.txt
python -B s-qstn/run.py --list-items
python -B s-qstn/run.py --profile persistent_granters --sample-id demo --output s-qstn/outputs/prompt_demo.json
```

Profiles are `persistent_granters`, `reconsent_seekers` and `broad_restrictors`.
Omitting `--profile` uses the frozen mixture and a stable `--sample-id`. These are
synthetic behavioral profiles, not three actual people or a maximum of three
possible trajectories. The frozen mixture is 49.9%, 5.0%, and 45.1%, respectively.

The runtime reference corpus has 13,089 survey-answer rows. The 3,272 held-out
rows are not runtime retrieval inputs. The [evaluation note](docs/evaluation.md)
describes the 216-call, single-turn distribution comparison and its limitations.

## Integration with the Agent

The Agent's `interaction/sqstn_bridge.py` compiles a request with the current
scope, persistence period and that user's previously observed answers.
`SQSTNResponder` accepts an injected transport and validates the reply. The
dispatcher records an accepted answer in the actual consent ledger. Unknown,
malformed or missing replies do not authorize execution. Authored Q54 content and
Q63/Q64 setup items require explicit handling because they are not original
questionnaire items.

The adapter compiles prompts without loading `.env` or invoking the provider.
Its private simulator audit, including persona information, is not a DDQN input.
The Agent's opt-in [`run_online.py`](../rl_agent_structure/run_online.py) supplies
the real provider transport and shares this package's cumulative budget ledger.

## Optional paid response mode

`run.py --send` explicitly sends one OpenRouter request. It needs
`OPENROUTER_API_KEY` from the environment or `s-qstn/.env` based on
[.env.example](.env.example), and an existing cumulative `state/budget.json`.
The environment takes precedence. Placeholder keys are rejected before network
access. Runtime state and credentials are excluded from Git.

From the repository root, first install the requirements shown above. PowerShell:

```powershell
if (-not (Test-Path s-qstn/.env)) { Copy-Item s-qstn/.env.example s-qstn/.env }
```

Replace the placeholder with your OpenRouter API key. For a **new** campaign only:

```bash
python s-qstn/run.py --init-budget
python s-qstn/run.py --profile persistent_granters --sample-id demo --send
```

`--init-budget` creates the initial USD 5 ledger without a network request and
refuses to overwrite an existing file. Preview and `--send` never create a ledger
automatically. Preserve an existing ledger when resuming. The current
provider enforces the configured snapshot, a USD 5 cumulative ceiling, an exclusive
process lock, reservations and no automatic paid retries. The ceiling is an
implementation constraint, not authorization to spend it. Provider availability
and metadata are checked at execution time.

The provider is configured in `sqstn/provider.py` for `openai/o4-mini`, verified
against the `openai/o4-mini-2025-04-16` snapshot. This is the repository's existing
configuration, not a claim that the provider is currently available. There are
no model/base-URL environment overrides. Authentication uses a Bearer token;
permissions use a strict four-answer JSON schema, and the Agent planner uses JSON
object mode followed by local contract validation. See the official
[OpenRouter authentication](https://openrouter.ai/docs/api_reference/authentication)
and [structured-output documentation](https://openrouter.ai/docs/guides/features/structured-outputs).

The combined Agent reads `rl_agent_structure/.env` by default and passes that key
explicitly to both roles. Standalone S-QSTN reads `s-qstn/.env`; a shared process
environment variable works for either entry. Neither key is needed for offline
prompt previews, local mock tools or DDQN itself.

## Package map and tests

- `sqstn/retrieval/`: corpus, retrieval, profile assignment and calibration.
- `sqstn/core/`, `sqstn/engine/`: public memory, context and behavioral rules.
- `sqstn/agent_runtime.py`: Agent-facing simulator runtime.
- `sqstn/client.py`, `sqstn/provider.py`: explicit provider call and cost accounting.
- `config/`, `data/`: frozen configuration and attributed reference inputs.
- `tests/fixtures/prompts.json`: prompt fingerprints for offline regression checks.

```bash
cd s-qstn
python -B -m unittest discover -s tests -v
```

Tests mock external calls. This package is self-contained relative to its own
data/config; it does not need the removed simulator archives.
