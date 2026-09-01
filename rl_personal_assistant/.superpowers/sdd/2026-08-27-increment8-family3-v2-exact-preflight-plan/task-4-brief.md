# Task 4 brief — real scope binding, mediated environment, and label-free encoder

Implement Task 4 of `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md` under the approved English/Chinese Family-3 v2 specs.

## Strict scope

Create only:

- `src/pa_rl/family3_v2_authority.py`
- `src/pa_rl/family3_v2_policy.py`
- `src/pa_rl/family3_v2_environment.py`
- `tests/test_family3_v2_authority_environment.py`

You may update only the two existing implementation checkpoints after GREEN:

- `docs/CONTINUATION_CHECKPOINT.md`
- `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json`
- append one compact, flushed JSON line to `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/progress.jsonl`
- write your Task 4 implementation report to `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-4-report.md`

Do not modify Task 2/3 files, any legacy v0/v1 source/result, the frozen baseline, `__init__.py`, or any other file. Standard library plus unchanged project authority/effect components only. Do not import Torch, `increment8_policy`, old lifecycle classes, or old solvers.

## Required interfaces

- `DeterministicAllowReuseUserV2.answer_permission(request) -> Family3V2PermissionResponse`
- `Family3V2AuthorizationBindingGateway.commit_request(selected_candidate_scope, request, response, expires_at_step) -> AuthorizationBindingResultV2`
- `project_family3_v2_observation(state, model) -> Family3V2Observation`
- `Family3V2FeatureEncoder.encode(observation) -> Family3V2EncodedDecision`
- `Family3V2Environment.reset(graph_id, root_seed, episode_ordinal, forecast_counterfactual=False) -> (observation, info)`
- `Family3V2Environment.step(slot_index) -> (observation, reward, terminated, truncated, info)`

Keep new request/response/binding/info dataclasses minimal, typed, frozen/slotted where practical, and explicit enough for later audits. Environment `info` may be a typed object; tests and later audits must be able to inspect binding evidence, ledger records/events, monitor/tool evidence, branch evidence, run-valid status, and semantic conformance evidence.

## Mandatory TDD sequence

1. Create the focused test module first.
2. Run exactly:
   `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment -v`
3. RED must be an import failure for missing `pa_rl.family3_v2_authority`. A different RED cause is a genuine stop: write the report/checkpoint and return `BLOCKED` without implementing.
4. Implement the smallest complete Task 4 surface.
5. Run the same focused command for GREEN.
6. If focused GREEN passes, run Tasks 2–4 together once:
   `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng tests.test_family3_v2_model_outcome tests.test_family3_v2_authority_environment -v`
7. Any GREEN or combined regression failure is a genuine stop: record exact output/checkpoint and return for human review. Do not tune scientific parameters.

## Required binding and environment behavior

Test narrow and broader requests on `i8_f3v2_v4` (sensitivity 3), and require all four complete operational scopes to be equal:

`selected_candidate_scope == dispatched_scope == accepted_scope == recorded_ledger_scope`.

The result must be a reusable active grant with `remaining_uses is None` and `expires_at_step == horizon + 1 == 9`. The deterministic user returns only `PermissionChoice.ALLOW_REUSE`, including sensitivity 3; do not reuse the v1 sensitivity-to-ALLOW_ONCE shortcut.

The fixed gateway transaction is:

`candidate scope -> immutable request -> public user response -> precommit equality -> AuthorizationService.start_request -> AuthorizationService.apply_permission_choice(ALLOW_REUSE) -> reread record -> postcommit equality -> private raw-ID/public issuance-ordinal binding`.

- Precommit mismatch: return before `start_request`; zero ledger events/records, no authority.
- Postcommit mismatch: preserve the append-only ledger evidence, quarantine the raw authorization ID, withhold a public ordinal/usable candidate, terminate `authorization_binding_integrity_failure`, and never invoke monitor/tool.
- Production constructs `AuthorizationService(episode_id, episode_end_step=horizon+1)` and requests `expires_at_step=horizon+1`.
- Only a private environment map may bind public issuance ordinal to raw authorization ID. Raw IDs, hashes, and operational scope labels must not enter policy observations or encoded keys.

Use the unchanged real components:

- `AuthorizationService`
- `ReferenceMonitor`
- `TaskEngine` (a minimal v2 subclass may add a clean, unique continuation task following the existing lifecycle-engine pattern; do not modify the base)
- `MockTool`
- `covers` and `relation`

Build a frozen deterministic MockTool plan for every possible declared task. Each valid pending task's first attempt must yield exactly one unique `COMMITTED` effect. Every execute goes through `ReferenceMonitor.execute(ExecutionIntent(...))`; the raw execution candidate ID must be the monitor's canonical candidate ID, not the v2 semantic role string. Treat blocked, absent, unknown/malformed, system conflict, missing plan, duplicate commit/effect, unknown effect, task/ledger revision disagreement, or any non-committed result as an integrity failure with `run_valid=False`.

The environment must not implement a second semantic FSM. Mediate and validate side effects, then obtain the semantic successor exclusively from `Family3V2Model.transition_from_residue`. Compare state, reward, terminated, and truncated against the environment's public result and reject any injected/mutated mismatch. Draw the branch residue exactly once, only after the first actual committed effect, using `draw_family3_v2_branch_residue(root_seed, branch_coupling_uid, episode_ordinal)`. If branch installation immediately produces no coverage, install the task in the engine and preserve the nonemitted catalog before terminal return.

- Valid request: user + ledger path, then pure semantic transition.
- Valid execute: monitor/tool path, then pure semantic transition.
- Valid disable: private ordinal lookup + ledger disable, then pure semantic transition.
- Deny/escalate: pure semantic transition and no ledger/tool action.
- Masked/forced action: no user, ledger, monitor, tool, prompt, authority, exposure, effect, or branch side effect; use the pure model's invalid terminal successor.

Create deterministic operational step IDs and a committed plan for all initial/exact/broader tasks. `ExecutionIntent.logical_step` must be a positive valid step; the first execute naturally follows the request at model decision index 1.

## Label-free public observation and encoder

`PolicyScopeRoleViewV2` contains only role, typed relation, attribute count, sensitivity, exposure cost, and optional public issuance ordinal—never `Scope`. The observation exposes the transition-relevant public state listed in approved spec section 8: both offer roles/views; exact forecast fractions; response profile; public continuation templates; offer/continuation state; realized-mode/tail information only after realization; current-task relation/utility; decision/effect/utility/prompt/exposure/target/horizon accounting; active authorization summaries; seven semantic candidates and authoritative mask.

Forbidden in observation/encoder: graph/family/split/carrier/purpose/registry/source/file/seed/order IDs; future branch realization; optimal/Q/V/feasibility/outcome/audit/certificate facts; raw scope label fields; raw authorization IDs or hashes.

Every nonterminal observation contains exactly seven ordered rows. Masked rows remain, with their public invalid reason and neutral binding fields.

Use exactly:

```python
@dataclass(frozen=True, slots=True)
class Family3V2EncodedDecision:
    state_features: tuple[int, ...]
    candidate_features: tuple[tuple[int, ...], ...]
    mask: tuple[bool, ...]
    semantic_candidate_ids: tuple[str, ...]

    def representation_key(self) -> tuple[object, ...]:
        return (self.state_features, self.candidate_features, self.mask, self.semantic_candidate_ids)
```

Encode every `Fraction` as exact numerator/denominator integers. Do not retain the raw observation in `representation_key`.

## Minimum required focused tests

1. Both request roles on `i8_f3v2_v4`: four-way equality, reusable active record, expiry 9, public ordinal bound, no raw ID/scope labels in policy representation.
2. Gateway precommit mismatch and postcommit mismatch/quarantine behavior.
3. Happy mediated execute: one committed effect, monitor evidence, reusable grant remains active, exactly one residue after first execute, exact equality to pure model successor.
4. Integrity table: missing plan, malformed/unknown outcome, conflict, duplicate effect, monitor block, or ledger/model revision disagreement fail closed with `run_valid=False`.
5. Forced masked row changes no external side-effect counts and matches the pure invalid successor.
6. A deliberately mutated mediated/public successor is rejected for mismatch in state, reward, termination, or truncation.
7. Projection/encoder: fixed seven rows, masks/reasons retained, masked bindings neutral, exact fraction encoding, no raw `Scope`, labels, raw ID, or hash in observation/key.

Do not duplicate Task 3 witness mathematics or state-machine tests beyond what is necessary to prove mediation equality.

## Completion/checkpoint contract

On GREEN, record exact RED/GREEN/combined commands and outputs, method counts, elapsed times, new-file SHA-256/size, unchanged Task 2/3 input hashes, and any concerns in `task-4-report.md`. Retain Gate authority exactly as `status=BASELINE_FROZEN`, `last_completed_gate=0`, `next_gate=1`; update only `implementation_progress.task_4` and the exact Task 5 next action. Append one implementation-progress JSONL record. Do not rebaseline.

