# Task 3B2B1 Implementation Report — Static Trusted Context and Independent Semantics

## Status and scope

Task 3B2B1 is locally implemented and verified. It is **not yet independently approved**. This report does not mark Task 3B2, Task 3, or G1 complete, and Task 3B2B2 has not started.

This increment adds only:

- schema-first semantic verification of an already sealed `EpisodeTrace`;
- canonical trusted manifest/fixture/config/evaluation-plan binding;
- independent public, authorization, execution, action, observation, catalog, mask, snapshot, and evaluator semantics;
- stable non-sensitive failure codes and a safe verification summary.

It does **not** create a fresh `PermissionEnvironment`, call an adapter factory, call a tool-plan factory, replay actions against tools, implement `verify_and_replay`, write artifacts, add Gymnasium, train a policy, or change any Task 0–3B1 authority/evaluator/environment semantics.

## Files changed

- `src/pa_rl/replay.py`
  - adds `ReplayFailureCode`, `ReplayFailure`, `SemanticVerification`, `SEMANTIC_VERIFIER_VERSION`, private `_PreparedSemanticContext`, and `verify_episode_semantics`;
  - adds pure static reconstruction and cross-chain verification helpers.
- `tests/test_replay_semantics.py`
  - adds 19 focused semantic verification tests with fully rehashed attacks.
- `docs/implementation_reports/task-3b2b1-report.md`
  - this report.

No environment, authorization, execution, evaluator, fixture, adapter, tool, reward, or policy-interface implementation was edited.

## TDD evidence

The new focused test module was created before the production API existed.

Initial genuine RED:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_replay_semantics -v
```

Observed result: exit `1`; `Ran 1 test in 0.000s`; loader error:

```text
ImportError: cannot import name 'ReplayFailure' from 'pa_rl.replay'
```

This was the intended missing-production-API failure.

After the first minimal implementation, the original 12 focused tests ran with two failures. Both were meaningful classification/isolation findings:

- the effect-ID attack reached evaluator-result comparison before the independently derived final task snapshot was bound, so it returned `evaluator_result_mismatch`; the verifier order was corrected to bind explicit snapshot/ledger/audit preconditions first;
- the first public-source-link attack changed only the initial authorization record copy, unintentionally making the later lifecycle immutable fields inconsistent. The attack was corrected to rewrite that source consistently through the whole rehashed authorization lifecycle, isolating the intended public-link check.

The expanded 19-test run then had one test-only `StopIteration`: the test looked for final expiry in a consumed one-time grant, which correctly has no active authorization to expire. It was corrected to use the reusable-grant fixture. No production behavior changed for that test-fixture error.

A later narrow TDD cycle found a privacy-boundary defect. Although `ReplayFailure` text contained only its code, an exception raised inside a trusted-registry handler remained reachable through `__context__`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_replay_semantics.SemanticFailureBoundaryTests.test_failure_boundary_never_echoes_private_payload_text -v
```

Observed result: `Ran 1 test` — `FAILED (failures=1)` because `registry_error.__context__` was a private `RuntimeError`. The public API now catches internal failures and raises a fresh code-only `ReplayFailure` outside the handler. The isolated rerun passed and both `__cause__` and `__context__` are `None`.

Final focused GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_replay_semantics -v
```

Result: `Ran 19 tests in 4.885s` — `OK`.

Task-3B2 structural plus semantic focused GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay tests.test_replay_semantics -v
```

Result: `Ran 43 tests in 7.762s` — `OK`.

Fresh full-suite verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Result: `Ran 217 tests in 8.721s` — `OK`.

Compilation verification:

```powershell
python -m compileall -q src tests
```

Result: exit `0`, no output. The implementation remains standard-library-only.

## Public verification API

The new API is:

```python
verify_episode_semantics(trace, *, manifests=None) -> SemanticVerification
```

`SemanticVerification` contains exactly:

- `verified`;
- `verifier_version`;
- `trace_id`;
- `trace_hash`;
- `scenario_id`;
- `transition_count`.

It returns no trace, manifest, registry, evaluation plan, authorization service, audit, factory, environment, tool, adapter, permit, reservation, or other live handle. The private `_PreparedSemanticContext` is used only within one call and is never returned or serialized.

`ReplayFailure` exposes only one typed `ReplayFailureCode`. Its string form is the stable code value. The public wrapper removes nested cause/context objects so private payloads and nested exception text are not reachable through the returned exception boundary.

Current stable codes are:

| Code | Meaning |
|---|---|
| `schema_invalid` | Task-3B2A structural validation failed |
| `trusted_context_invalid` | caller-supplied trusted registry could not be normalized |
| `trusted_binding_mismatch` | trace metadata disagrees with trusted static sources |
| `public_semantics_invalid` | public chain, projection, observation, or public cross-link is invalid |
| `action_semantics_invalid` | selected action, phase, terminal action, flags, or reason is invalid |
| `authorization_semantics_invalid` | authorization lifecycle/replay is invalid |
| `execution_semantics_invalid` | execution chain or monitor/effect semantics is invalid |
| `evaluator_semantics_invalid` | supplied final snapshot fails explicit evaluator preconditions |
| `evaluator_result_mismatch` | independently recomputed evaluator output/digest differs |
| `verifier_internal_error` | unexpected verifier failure, without exposing internal text |

## Schema-first and trusted static binding

`verify_episode_semantics` first calls the approved Task-3B2A `validate_episode_trace`. If that fails, it returns `schema_invalid` without touching the supplied trusted manifest registry. A hostile registry canary proves this order.

Only after structural success does the verifier normalize the complete registry and select the trusted manifest. It independently recomputes and compares:

- scenario hash;
- fixture-set version and canonical sorted fixture-set hash;
- environment configuration hash and environment/contract versions;
- scope-ontology and authorization-policy versions;
- evaluator version;
- trusted endpoint `H+1`;
- `EvaluationPlan.from_manifest(manifest)` and its canonical hash.

For an empty authorization history, the verifier explicitly creates `AuthorizationService(scenario_id, H+1)` instead of using the legacy `AuthorizationService.replay(empty)` default endpoint. The direct one-step safe-denial trace with an empty ledger and horizon 3 therefore verifies at endpoint 4.

Adapter version and tool-plan version/hash are retained as structurally bound trace fields but are deliberately **not** compared to canonical defaults in B2B1. A legal trace may use trusted injected factories, and this API accepts no factories. Task 3B2B2 must bind those dynamic facts to the adapter and normalized tool plan produced by the one permitted fresh reset.

## Independent prefix reconstruction

The verifier never treats stored observations or their hashes as the semantic oracle. At the initial boundary and every transition pre/post boundary it reconstructs from trusted manifest plus cumulative evidence prefixes:

1. the authorization state using `AuthorizationService.replay`, or an explicit trusted-endpoint empty service;
2. the ordered task snapshot from manifest steps and execution dispositions/effect receipts;
3. current task step, phase, remaining count, next step/scope, unknown/completion flags, and last public execution outcome;
4. latest public authority-event bindings, including the cross-chain `permission_requested.event_id == request_created.record.source_public_event_id` relation;
5. exact sorted authorization views, expiry projection, scope relation, and re-ask preference;
6. exact request/nullable execute/deny/escalate candidates plus eligible refresh and disable candidates;
7. canonical catalog ordering and resolved IDs;
8. public-only action mask, including the manifest-declared unprotected execute exception;
9. exact K=4 history, counts, response counts, and smoothed rates from the complete public prefix;
10. the complete `EnvironmentObservation` through the approved strict builder.

The reconstructed observation, typed selected candidate, action index, catalog, and mask must equal the sealed evidence exactly. Fully rehashed attacks that rewrite task view, authorization view, history statistics, catalog/scope, or mask are rejected even when their stored hashes are recomputed.

## Public/action/authorization/execution semantics

The public verifier accepts only event types the current environment can emit. `authorization_revoked` and `execution_blocked` remain valid schemas in the lower public-event module but are rejected here because `PermissionEnvironment` never emits them.

For every transition it checks the selected action against the exact current-step public/auth/execution deltas:

- request: `permission_requested` followed by grant or denial;
- refresh: request followed by denial, or grant plus `authorization_refreshed`;
- disable: one matching local-disable record;
- execute: one matching monitor audit and one matching public execution result;
- deny/escalate: the exact typed public terminal event;
- masked non-execute: only `verified_error(masked_action)`;
- masked execute: still monitor-mediated.

Permission request IDs are recomputed from scenario, logical step, resolved candidate ID, request kind, and monotonic request ordinal. Grant/denial/refresh/disable/expiry IDs, request source event, execution outcome/reason/step, and endpoint expiry publication are cross-bound to their respective authority or execution evidence. Authorization expiry remains in service order; public expiry is independently required in sorted authorization-ID order. A one-shot expiry delivery failure may expose only the already committed sorted public prefix followed by `verified_error(adapter_protocol_failure)`.

The suite verifies real legal adapter-fault prefixes for request delivery, refresh delivery, and expiry delivery. Fully rehashed missing-middle and post-error-continuation streams fail. Orphan grant, refresh, expiry, and execution records and a non-emittable public event type also fail.

## Authorization, monitor, and evaluator gates

The full authorization chain is replayed through `AuthorizationService.replay`; the output lifecycle must be valid under the trusted scenario and endpoint. A fully rehashed `allow_reuse` choice attached to a one-time record fails despite valid unkeyed hashes.

`ReferenceMonitor.verify_audit_chain` is required but is not treated as semantic proof. Before any evaluator-result comparison the verifier explicitly requires:

- `PostconditionEvaluator._snapshot_valid` on the supplied final snapshot;
- `PostconditionEvaluator._ledger_valid` on authorization evidence;
- `PostconditionEvaluator._audit_valid` on the snapshot, execution audits, and authorization evidence;
- exact equality between a separately derived ordered task snapshot and the supplied final snapshot.

These gates reject fully rehashed false check vectors, task-revision attacks, changed effect correlations, illegal ordered task progress, and malformed snapshots. Only after all preconditions pass does the verifier call `PostconditionEvaluator.evaluate` and require full `EvaluationResult` equality plus exact digest equality. A structurally valid replacement `evaluator_integrity_failure` result is therefore not accepted as proof that malformed inputs are valid.

Intermediate transition evaluator results are also recomputed against their exact cumulative prefixes and typed terminal action. Reward, terminated/truncated flags, horizon reason, evaluator reason, and verified fault reason must agree. The trace-level terminal action must match the closing selected deny/escalate action and its exact public event; immediate safe terminal action remains legal without a prior permission prompt.

## Test coverage

The focused suite covers:

- all ten canonical legal traces, including terminal and fixture-10 truncation;
- direct one-step safe denial with an empty ledger;
- zero environment/adapter/tool-factory construction in B2B1;
- legal request, refresh, and expiry adapter-fault prefixes;
- schema-first registry canary;
- trusted scenario/fixture/evaluation-plan metadata attacks;
- public request-source link attack;
- illegal authorization lifecycle;
- false monitor check, changed effect correlation, and task-revision attacks;
- snapshot and evaluator-result replacement attacks;
- terminal-action substitution;
- task/auth/history/catalog/mask observation rewrites;
- orphan grant/refresh/expiry/execution records and non-emittable public event;
- missing-middle and after-error continuation;
- failure privacy, including empty cause/context;
- no mutation of the supplied trace.

All semantic mutations are sealed-shape attacks with the affected inner event chain, transition deltas/heads, final head, observations where needed, and outer trace checksum recomputed. They are not stale-hash-only checks.

## Deferred Task 3B2B2 boundary

Still intentionally unfinished:

- trusted runtime adapter version binding;
- trusted normalized runtime tool-plan version/hash binding;
- exactly one fresh `PermissionEnvironment` construction and reset;
- single-use adapter/tool factory call-count proof;
- replay of recorded action indices against fresh runtime state;
- per-transition fresh sealed evidence comparison;
- exact fresh closure and whole-trace equality;
- final `verify_and_replay` / `ReplayVerification` API.

Static evidence cannot prove that an adapter actually threw during delivery because delivery success/failure is not itself audited. B2B1 therefore verifies the only environment-compatible fault-prefix grammar; B2B2 will test whether the trusted fresh runtime reproduces it.

As in Task 3B2A, all hashes remain unkeyed corruption/consistency checks, not origin authentication. A wholly replaced, independently valid, newly sealed history can still pass within this prototype’s trusted in-process artifact model. Deployment protection against hostile wholesale replacement requires a signature, MAC, or trusted external append-only anchor.

