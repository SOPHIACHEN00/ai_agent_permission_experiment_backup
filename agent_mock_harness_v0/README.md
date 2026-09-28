# Local mock-tool and mechanism harness (v0)

Chinese design/recap notes: [start here](docs/00_RECAP_zh.md), then [mock internals](docs/01_MOCK_TOOLS_DESIGN_zh.md), [mechanism tests](docs/02_MECHANISM_TESTS_AND_NEXT_EXPERIMENT_zh.md), [minimal-Agent design](docs/03_MINIMAL_AGENT_EXPERIMENT_DESIGN_zh.md), and [implementation plan](docs/04_MINIMAL_AGENT_IMPLEMENTATION_PLAN_zh.md).

This is a small, deterministic test fixture for the permission project. It does **not** connect to real email, banking, shopping, home devices, or cloud storage. The source task is the released `external/ai-agent-permissions/queries.json`; all records, recipients, messages, and effects here are synthetic.

## Research question and coverage

Can the existing permission ledger and reference monitor enforce per-step access while a multi-turn task actually interacts with tools? The raw JSON contains 65 queries and 28 distinct `tool1`/`tool2` labels. The paper's 21-tool summary is a different, curated counting convention. This harness provides one local fixture for each **raw label**, and smoke-tests every advertised `(tool, operation)` pair through a common `search/read/create/update/send/book/control` engine. It is shallow tool coverage, not 65 complete task worlds or vendor API emulation.

The mechanism probes are:

1. Wu query ID 22, expanded into `Cloud Drive.search → Cloud Drive.read → Email.send`. It checks exact authorization, resource/field scope, local-only send, and a state-based completion oracle.
2. A purpose-built three-round file-read task. It checks one-use consumption, reusable grants, revocation, and fresh authorization.

The existing `pa_rl.authorization.AuthorizationService` and `pa_rl.execution.ReferenceMonitor` are used unchanged. The adapter only turns monitor-issued, validated permits into stateful synthetic tool calls. The trusted harness owns the in-memory registry; an arbitrary Python program with direct access to that registry is outside this v0 threat model. The adapter is single-threaded and does not model crash recovery or distributed transactions.

## Run

From `ai_agent_permission_experiment` in PowerShell, with Python 3.12:

```powershell
$env:PYTHONPATH='.;rl_personal_assistant_cuda_v1/src'
python -m unittest discover -s agent_mock_harness_v0/tests -v
```

No service credentials or network access are used. `catalog.py` holds synthetic state and the generic operation semantics; `monitored.py` connects it to the existing permit boundary; `scenarios.py` defines the two multi-turn probes. Tests assert both successful task effects and blocked/zero-effect attempts, and verify the ledger replay and monitor audit chain.

## Minimal task-Agent vertical slice

`agent_protocol.py` validates narrow-domain model decisions. `agent_runner.py` loops over public tool observations while a separate `PermissionPolicy` chooses whether to reuse a valid grant, ask for exact scope, or stop. The existing ledger and reference monitor remain the only authorization and effect boundary. The deterministic planner in the tests is an **offline double**, not an LLM or an RL policy.

The optional one-shot online smoke uses `agent_openai.py` and only the synthetic query-22 report-sharing scenario. It requires `OPENAI_API_KEY`; from the repository root:

```powershell
$env:PYTHONPATH='.;rl_personal_assistant_cuda_v1/src'
python -m agent_mock_harness_v0.run_agent_smoke --output agent_mock_harness_v0/results/query22_live_001
```

The output directory must be new. The command writes `summary.json`, `public_trace.json`, `budget.json`, and `attempts.jsonl`. It makes at most eight `o4-mini` requests, reserves USD $0.40 before each request (at most $3.20 reserved under the $4 user cap), limits the prompt and completion length, sets `store=false`, and never retries a failed request. Request hashes and token usage are logged; API keys and raw provider error bodies are not. It never sends real email: `Email.send` writes only to the local synthetic outbox. A nonzero exit or failed oracle is a recorded unsuccessful smoke, not evidence of task completion.

This vertical slice establishes an Agent/tool/permission integration path. It does **not** connect the existing RL checkpoint, train a new RL controller, compare policy arms, or demonstrate an efficiency–privacy improvement. Those are separate next-stage experiments.

## Interpretation limits / next experiment

Passing these tests establishes local **mechanism feasibility**, not an RL efficiency–privacy improvement. They use scripted authorization choices, not a learned policy or LLM planner. For the proposed trade-off study, freeze the task/planner traces and mock state, then compare policy arms on task success, user prompts, unnecessary authorized/read/sent fields or records, blocked violations, and runtime. A monitor-off or ledger-off arm must be isolated to this synthetic environment and cannot be treated as safe for real tools. Task-specific fixtures and success oracles still need to be authored for the other 64 queries before claiming full benchmark coverage.
