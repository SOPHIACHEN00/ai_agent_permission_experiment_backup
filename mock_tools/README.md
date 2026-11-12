# Stateful mock tools

Minimal executable read/write environments for all 65 Wu tasks. Field values are
synthetic. The tools keep local resource state and return a result, execution
receipt and field-flow evidence. They do not contact actual services.

| File | Responsibility |
| --- | --- |
| `sources.py` | Read the attributed original task definitions |
| `tasks.py` | Build executable task steps, scopes and declared assumptions |
| `runtime.py` | Apply reads/writes and retain local tool state |
| `contracts.py` | Tool-side data structures |
| `oracle.py` | Evaluate minimal dataflow completion and privacy proxies |
| `run.py` | Standalone deterministic functionality harness |

The agent sends an exact call after its reference monitor permits execution.
Tool results return to the planner; receipts support reconciliation and reward
accounting. Oracle task requirements are evaluator-side information, not DDQN
features. The evaluator and reference monitor have different responsibilities.

```bash
python -m pip install -r requirements-agent.txt
python -B -m mock_tools.run --all --output outputs/mock_demo
python -B -m unittest discover -s tests/mock_tools -v
```

Run these commands from the repository root. Output must be outside this source
directory. Success means declared local read/write flow completed, not that an
external business service produced a correct real-world answer. See
[execution assumptions](../docs/METHOD.md#8-tools-simulator-and-authored-assumptions).
