# Task 3A Brief — Public Interaction and Policy Interface Kernel

## Entry gate and source of truth

Task 0–2B are independently approved. Read `task-3-brief.md` completely; it is binding. Task 3A implements only the deterministic public-side primitives needed before environment assembly:

1. `ScriptedUserAdapter`;
2. verified/hash-chained public-event records;
3. resolved candidate catalog and public-only mask;
4. the exact allowlisted immutable `EnvironmentObservation` builder;
5. the explicitly authorized fixture-10 migration and its contract regression.

Do not implement `PermissionEnvironment.reset/step`, evaluator dispatch, episode replay, baselines, or RL in this subtask.

## Required compatibility

- Preserve the Task-0 `PermissionUserAdapter` signatures: `observe_event(PublicEvent)` and `answer_permission(..., Sequence[PublicEvent])`.
- Preserve the Task-0 `ActionCandidate` base ID and the Task-2A monitor candidate check. Use a separate frozen `ResolvedCandidate` binding wrapper.
- Six existing controller action types only; no `CLARIFY`/`PROPOSE_NARROW_SCOPE` slot or alias.
- Standard library and `unittest` only.
- Public mask/observation builders accept explicit public projections plus already-resolved authoritative IDs; they may not introspect whole manifest/ledger/audit objects or future scripted responses.

## Deliverables

- Focused modules such as `scripted_user.py`, `public_events.py`, and `policy_interface.py`.
- Tests such as `test_scripted_user.py` and `test_policy_interface.py` covering the Task-3 brief sections 1–5 and leakage/mask/candidate invariants that do not require a live environment.
- Correct fixture 10 to the three-decision path:
  `REQUEST_AUTHORIZATION(first_step, allow_once) -> EXECUTE_WITH_AUTHORIZATION(first_step) -> REQUEST_AUTHORIZATION(second_step, allow_once)`, with two scripted `allow_once` responses.
- Update existing fixture contract tests so the migration is explicit and no other canonical fixture semantics change.
- Report `docs/implementation_reports/task-3a-report.md` with genuine RED/GREEN evidence, exact schemas/allowlists, fixture before/after, commands/counts, deviations, and concerns.

## Mandatory behavioral gates

- Adapter reset/FIFO/exhaustion/public-only validation; `observe_event` never consumes an answer; no remaining-script exposure.
- Public-event chain deterministic and independently rejects mutation, deletion, reorder, duplicate, and rehash with invalid sequence/semantics. State clearly that it is not origin authentication.
- Public-event chain exposes a pure two-phase `preview/build_next` then `commit(prebuilt_record)` contract. This lets Task 3B bind the previewed permission-request `event_id` into `AuthorizationService.start_request/start_refresh` before the record is committed. Commit must fail if sequence/head/state changed after preview.
- Resolved slots deterministically bind base candidate, task step, selected/prior authorization, and allowlisted reason/target; stable order/hash; unique; at most 16; overflow fails rather than truncates.
- An execute-shaped resolved slot may carry `authorization_id=None`; it is kept masked in normal policy use but permits a forced mask-bypass test to reach the reference monitor. Constructor validity must not silently turn missing authority into a grant or remove the execute slot.
- Mask is derived only from an explicit public state input and never a permission answer/tool/evaluator/oracle. Deny/escalate keep a valid safe option. Scope/request/refresh/disable/execute bindings obey `task-3-brief.md`.
- Observation top-level fields exactly match the Task-3 allowlist; history is `K=4`, alpha=`1.0`; returned values are deeply immutable. Recursive canary tests must prove private/future/oracle values stay out.
- No code in this subtask may call a tool, mutate an authorization ledger, compute reward, or claim an episode terminal/truncated.

## TDD and verification

Write observable tests first and capture a real missing-behavior RED. Then run the new scoped tests, the full suite, and `python -m compileall -q src`. Do not mark Task 3 complete; it still requires Task 3B environment/replay and independent review.
