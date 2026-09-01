# Task 3B1 Brief â€” Deterministic Environment Kernel

## Gate and scope

Begin only after Task 3A receives `Spec PASS / Quality APPROVED`. Read `task-3-brief.md` and `task-3b-brief.md` completely; both remain binding. Implement only the environment kernel and canonical trajectory tests. Do not implement sealed replay, baselines, Gymnasium, NumPy/Torch, live S-QSTN, or Deep RL.

Allowed production surface:

- `src/pa_rl/environment.py`;
- a narrowly separated private tool-plan helper only if needed;
- `tests/test_environment.py` and focused regression tests;
- `docs/implementation_reports/task-3b1-report.md`.

Do not change approved Task 0â€“3A APIs or canonical fixtures unless composition is genuinely impossible and the blocker is reported before editing.

## Required implementation

1. `PermissionEnvironment` has dependency-free Gymnasium-style signatures:
   - `reset(seed=None, options=None) -> (EnvironmentObservation, info)`;
   - `step(action_index) -> (EnvironmentObservation, int_reward, terminated, truncated, info)`.
2. Construction freezes a trusted canonical manifest/registry, adapter factory, and private tool-plan factory. `reset` accepts only `{}` or `{scenario_id}`; `seed=None` becomes `0`; Boolean/non-integer seeds fail before state creation.
3. Every reset constructs fresh adapter, `AuthorizationService(manifest.scenario_id, H+1)`, `TaskEngine`, `MockTool`, `ReferenceMonitor`, `EvaluationPlan.from_manifest`, public chain, maps, counters, and evidence buffers.
4. Build the current public state and at most six resolved candidates exactly as frozen in Task 3B. Candidate binding and masks use only manifest-public facts, TaskSnapshot public projection, ledger-record public projection, public events, and public summary preferences.
5. Implement all six exact dispatch paths. Only request/refresh call `answer_permission`. Execute calls only `ReferenceMonitor.execute`; masked execute still reaches the monitor. Other masked actions and adapter/protocol failures become verified environment faults with reward 0 and no unauthorized effect.
6. Use the two-phase permission-request event binding and the strict adapter request matrix. Deliver committed records to `observe_event` as `PublicEvent`, never as records.
7. Evaluate from internally owned trusted evidence only. Evaluator termination takes precedence over horizon truncation. Finalize every terminal/truncated episode at `H+1` by calling the approved `AuthorizationService.expire_eligible(H+1)` exactly once and preserving the service's deterministic ledger/audit-event order. Sort the records returned by that call by authorization ID only for public `authorization_expired` publication/delivery, then re-evaluate with the same terminal action and return the exact closed Task-3A observation. Task 3B2 must bind the authorization-event chain in service order and the separately ordered public-event chain without treating one as the other's ordering oracle.
8. Return deeply frozen `{public, audit}` info. The public branch contains only allowlisted hashes/IDs/reasons; the audit branch contains frozen evidence and no live handles. Neither public-state construction nor mask construction may read the audit branch.
9. The default private tool plan commits each typed task step on its first attempt. Missing plan entries produce the existing monitor unknown path. Bind version/hash only in audit metadata.
10. Expose enough typed, immutable transition evidence for Task 3B2, but do not claim sealed trace verification in this increment.

## Mandatory TDD gate

- Real RED evidence before production behavior.
- Reset isolation, exact options/seed/lifecycle, H+1 endpoint, and step-before-reset/after-close errors.
- Request/refresh answer-count matrix; all other actions consume zero answers.
- Exact two-phase source event ID and strict public-history timing.
- Correct trajectories for all ten fixtures, selected by semantic binding rather than hard-coded slot.
- Fixture 2 reusable grant; fixtures 4/5/6 refresh-as-new-record; fixture 7 no-reask; fixtures 8/9 correct versus swapped terminal action; fixture 10 exact truncation and legacy-answer exhaustion fault.
- Forced masked execute with missing/stale/revoked/wrong/superseded authority: monitor block, reward 0, no committed effect. Other masked actions fault before ledger/tool/adapter mutation.
- Terminal/truncation precedence and final expiry/digest recomputation.
- Default committed tool plan versus missing-plan unknown terminal 0.
- Same scenario/seed/action indices give identical semantic outputs across fresh environments despite random private permit secrets.
- Recursive canaries from oracle/private/tool-plan/evaluator/audit never enter observation, mask, public info, or public events.
- Full prior suite and `compileall` remain green.

## Handoff

Write `task-3b1-report.md` with exact RED/GREEN commands and counts, action dispatch table, candidate ranking, public projection schemas, fault handling, finalization order, tool-plan version/hash, deviations, and limitations. Do not mark Task 3 or G1 complete before independent review and Task 3B2 replay.
