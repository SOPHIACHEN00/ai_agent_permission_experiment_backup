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

## Optional paid response mode

`run.py --send` explicitly sends one OpenRouter request. It needs
`OPENROUTER_API_KEY` from the environment or a local `.env` based on `.env.example`,
and an existing cumulative `state/budget.json`. No ledger is created automatically
by the CLI. Runtime state and credentials are excluded from Git.

For a separately authorized **new** campaign, the current client expects a ledger
with `{"limit_usd":"5.00","jobs":{}}`. Only initialize an empty ledger for a genuinely
new campaign; preserve and reconcile an existing ledger when resuming. The current
provider enforces the configured snapshot, a USD 5 cumulative ceiling, an exclusive
process lock, reservations and no automatic paid retries. The ceiling is an
implementation constraint, not authorization to spend it. Provider availability
and metadata are checked at execution time.

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
