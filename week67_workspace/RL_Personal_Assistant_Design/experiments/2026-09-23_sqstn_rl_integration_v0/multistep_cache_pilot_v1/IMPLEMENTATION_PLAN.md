# Multi-step cache pilot Implementation Plan

> For agentic workers: use superpowers:executing-plans inline; no per-step approvals.

Goal: a complete bounded real-response graph and an honest cache-only model comparison.
Architecture: new modules in rl_sqstn_integration_v0 reuse frozen originals; actual
environment enumerates/audits every edge, then a public transition graph drives learning.
Tech: existing Python/OpenAI SDK/numpy/PyTorch CUDA; no dependency installation.
Spec: SPEC_zh.md; English counterpart SPEC_en.md.

Execution checkpoint2026-09-23: implementation/offline checks/single review complete;
one paid collection STOPPED_NO_RETRY after9validanswers,USD0.0259314,2completegraphs.
The specified per-graph bound3 is false for scope_denial. Data not complete;Task3
execution forbidden, no server contact/training. Task4 preserves interruption only.
See BLOCKER_zh.md and interruption_verification.json. Unchecked original plan items
below are not evidence of successful execution. No automatic continuation.

## Global constraints and review focus

USD4/24attempts;8graphs/horizon6/2tasks/2questions. B fixed;seed1301/1601;2400controller
steps each learner/seed;9600total;24dev rows;oneGPU;no old test. Unknown costs reserved,
no retry, no output forcing, no historical file edits. Focus: different histories,
budget exhaustion, incomplete branch coverage, automatic-disable timing, learner leakage.

### Task 1 — finite environment and graph

Files: new multistep_v1.py; tests/test_multistep.py.
Consumes Case/Episode/PolicyFrame/parse_response. Produces cases(split),
BoundedEpisode(case,cache,transport=None), enumerate_graph(case,cache,transport=None),
coverage(graphs,cache) and frame_from_mapping(value).

- [ ] Write bounded tests then run expected missing-feature RED:
  ```python
  cache = {}; graph = enumerate_graph(cases('train')[0], cache, synthetic_call)
  assert len(cache) <= 3
  assert all(n['edges'] for n in graph['nodes'].values() if not n['done'])
  assert enumerate_graph(cases('train')[0], cache) == graph
  ```
- [ ] Implement two-step scopes/public synthetic preferences and envelope; real
  automatic disable after first effect; cache-miss collection only, cache-only otherwise.
  Enumerate every valid prefix, serialize current frames/edges/summary; no model sees graph.
- [ ] Check once consumption, denial, forced disable→refresh, cache-only exact replay,
  missing-cache failure and no extra online call after global cap. Run bounded GREEN.

### Task 2 — bounded paid collection

Files: collect_multistep.py and tests/test_multistep.py.
Consumes enumerate_graph/coverage, v0 LiveTransport; produces collector status,
campaign journal, private per-call receipts/cache/audits, graph+dataset fingerprints.

- [ ] Pin budget arithmetic against an offline HTTP/transport double:
  ```python
  assert campaign.attempts <= 24
  assert campaign.accounted_nusd <= 4_000_000_000
  ```
- [ ] Wrap one existing zero-retry LiveTransport per call with global24/USD4 durable
  pre-send accounting; retain full reservation on unknown result; exclusive output root.
- [ ] Freeze spec/config/source hashes before calls; enumerate train then dev once,
  save each graph/cache immediately; verify full replay and coverage. Gate failure
  records DATA_COVERAGE_INCOMPLETE and prevents training. Never resample to fill gaps.

### Task 3 — cache-only server comparison

Files: run_multistep.py, prepare_multistep.py and a scoped secure server controller.
Consumes frozen public graphs and unchanged CudaLearner/MABPolicy/rule_action.
Produces9600controller rows,fourcheckpoints,24evaluation rows,resource/source receipts.

- [ ] Use typed current frames only; choose action via existing policy APIs; follow
  exactly the selected graph edge and deliver only the new observed public answer.
  ```python
  successor = graph['nodes'][node['edges'][str(index)]]
  policy.observe(decision, reward=successor['reward'], done=successor['done'], ...)
  ```
- [ ] Apply fixed budget/epsilon/MAB schedules; save/reload and fingerprint-check
  learning immutability in dev. Existing CUDA smoke runs once onserver, no localtorch.
- [ ] Bundle allowlisted frozen dependencies,new code,publicgraphs and config only;
  no .env/private prompts. Check idleGPU/currentmemory, uniqueagenticAIroot, launchonce,
  monitor read-only then download full evidence. No auto failure recovery.

### Task 4 — review and evidence

- [ ] One fresh read-only whole-change review before actual paid/server execution;
  bounded pre-execution fixes only. No duplicate review or historical test suite.
- [ ] Verify hashes,journals,cost,closedgraphs,replay,safety,counts and model reload;
  write Chinese report and a descriptive-only analysis when comparison data exists.
- [ ] Update task_plan/notes,main progress log and CONTINUATION_CHECKPOINT.

Pre-flight interfaces: Task1 graph/frame→Tasks2/3;Task2 gate/hash→Task3preflight;
Task3 checkpoints/rows→Task4report. Missing gate prevents3. No unresolved interface.
Self-review: all spec sections covered; no new scientific threshold, old defaults
unchanged. User's no-repeat-confirmation/minimal-testing/keep-records instruction
overrides skill defaults for approval loops,broad suites,Git commits and cleanup.
