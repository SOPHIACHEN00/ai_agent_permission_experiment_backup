# Increment 6 Task 1 Report — Public Observation v1

## Status

**Task 1 complete.** This boundary adds a policy-only, full-catalog decision
projection. It is not a protocol-outcome wrapper, training runner, criterion,
or pilot result.

## Delivered interface

`src/pa_rl/multiscenario_policy.py` exports:

- `MULTISCENARIO_FEATURE_VERSION = "public_multiscenario_features_v1"`;
- `STATE_DIM_V1 = 75`, `CANDIDATE_DIM_V1 = 36`, and
  `MAX_CANDIDATES_V1 = 16`;
- `PublicScenarioContext.from_public_projection(...)`;
- `MultiScenarioFeatureEncoder.encode(context, observation)`;
- `PolicyDecisionV1.resolve_slot(semantic_candidate_id)`.

The context accepts only the projection produced by
`project_public_observation`. It retains public request/task text and public
task scopes for matching `task_view.next_required_step_id`, but deliberately
does not retain or emit the projected scenario ID. The encoder appends the
frozen 52-value public scope layout to the existing 23 public dynamic values.
Unknown categorical scope values map to explicit `other` buckets.

Every row in the live environment catalog is represented by a 36-value public
candidate feature vector. Candidate semantic IDs are hashes of abstract public
action, binding, reason/target, authorization-status, grant, scope-relation,
remaining-use, and expiry categories. They do not include catalog slots,
authorization IDs, task-step IDs, or source identifier/hash digits. The action
mask is copied exactly from the environment; no second mask or trace-based
filter is applied. Decision tensors are detached, cloned CPU snapshots.

`tests/test_increment6_pilot.py` contains exactly the first focused Increment 6
test method. It resets all ten fixtures, checks full-catalog shapes, exact mask
fidelity, semantic-ID uniqueness and reversible slot resolution, absence of
forbidden metadata, and the presence of a reset with more than two valid
actions.

## TDD evidence

RED command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_public_v1_full_mask_and_firewall -v
```

Result: expected `ModuleNotFoundError: No module named
'pa_rl.multiscenario_policy'`.

GREEN command: the same command completed with `Ran 1 test ... OK`.

Targeted compilation:

```powershell
python -m compileall -q src\pa_rl\multiscenario_policy.py tests\test_increment6_pilot.py
```

Result: exit code 0.

## Scope boundary and next task

No authority, execution, environment, evaluator, replay, policy-interface,
scenario, or fixture code changed. No protocol-oracle data, audit data, or
future scripted permission responses enters the policy decision.

Next: Task 2 may add the trusted, benchmark-only canonical protocol outcome
tracker and the second focused test method. It must keep its expected trace
private and separate from this public policy interface.
