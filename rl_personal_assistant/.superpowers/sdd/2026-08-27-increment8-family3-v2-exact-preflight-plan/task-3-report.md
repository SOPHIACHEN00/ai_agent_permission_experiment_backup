# Task 3 — Pure Outcome and Finite-Horizon Model

## Status

DONE. The required missing-model RED and the one required focused
GREEN completed exactly. Gate 0 remains `BASELINE_FROZEN`, with
`last_completed_gate=0` and `next_gate=1`; no experiment gate was claimed.
No Git repository or Git hash was used.

## Scoped implementation

Created only the three Task 3 source/test paths:

- `src/pa_rl/family3_v2_outcome.py`: immutable terminal evidence/result
  contract and the terminal binary conjunction.
- `src/pa_rl/family3_v2_model.py`: frozen task, authorization, candidate,
  state, and transition dataclasses; seven-row catalog; exact-rational branch
  kernel; post-action exposure accounting; irreversible guard; and finite
  horizon closure.
- `tests/test_family3_v2_model_outcome.py`: nine behavior methods, including
  a ten-graph sweep of all four hand-derived witness cells and the independent
  open-evidence evaluator regression added in the concern-resolution cycle.

No reviewed Task 2 or legacy source/test file was edited. The model imports no
`AuthorizationService`, `ReferenceMonitor`, `MockTool`, environment, policy,
PyTorch, old lifecycle model/outcome/encoder, or solver.

## Witnessed RED

Exact command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_model_outcome -v
```

Exact result: exit 1, `Ran 1 test in 0.000s`, `FAILED (errors=1)`.
The traceback ended with:

```text
from pa_rl.family3_v2_model import (
ModuleNotFoundError: No module named 'pa_rl.family3_v2_model'
```

Cause: the intended missing Task 3 production model. There was no unrelated
RED cause.

## Witnessed GREEN

The same exact command ran once after the implementation. Exact result:

```text
test_all_four_construction_witnesses_hold_for_every_graph ... ok
test_exposure_failure_beats_same_step_natural_completion ... ok
test_first_execute_is_the_only_stochastic_transition ... ok
test_invalid_action_has_no_authority_resource_effect_or_branch_side_effect ... ok
test_natural_completion_on_last_decision_beats_horizon ... ok
test_only_natural_completion_can_receive_reward_one ... ok
test_reset_catalog_and_branch_are_literal_and_unrealized ... ok
test_verified_grant_closes_offer_and_disable_hits_nonemitted_guard ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.046s

OK
```

Method count: 8. No broad test, DP, training, learner, smoke, validation, or
official experiment command ran.

## Transition and witness evidence

- Reset emits the exact seven roles in `FAMILY3_V2_CANDIDATE_ORDER`, with
  mask `(true,true,false,false,false,true,true)`, an empty future queue,
  `UNREALIZED` continuation, and effect index zero.
- Both request roles install one reusable pure-model authorization, take one
  prompt and one post-action exposure snapshot, and close the offer. Request
  and refresh rows thereafter report `offer_window_closed`.
- The first committed execute alone produces the exact forecast distribution;
  later executes are deterministic `Fraction(1)` transitions. No branch exists
  before that effect.
- Valid disable leaves the offer closed, snapshots zero active exposure, and
  immediately closes through `irreversible_no_coverage`; its stored would-be
  catalog has seven rows, all `emitted=false`.
- Every terminal transition carries `next_mask=()`; every nonterminal
  successor carries the computed seven-entry authoritative mask.
- Forced masked execute increments only decision/invalid-attempt accounting;
  prompt, exposure, authorization, effect index, continuation, and queued
  tasks remain unchanged.
- For all ten frozen graphs, narrow/exact succeeds at exposure `(e+2)n`,
  narrow/broader fails `irreversible_no_coverage`, broader/exact reaches the
  target but fails `exposure_budget_exceeded`, and broader/broader succeeds at
  `(d+2)b`.
- The explicit last-decision fixture terminates as natural completion with
  reward one and `truncated=false`, proving completion precedes horizon.

## SHA-256 evidence

| Path | SHA-256 |
|---|---|
| `src/pa_rl/family3_v2_outcome.py` | `944b8d151ebb4f9b55caaeb9faf14e5d257c5f2b48dc8803d26952dcfaa9e5d1` |
| `src/pa_rl/family3_v2_model.py` | `315a13a37a5d8479ec3185b7082fb45e51e42a62493a374bb205cc6bc45b246a` |
| `tests/test_family3_v2_model_outcome.py` | `2b4e13039dce7c876482d3172ac9652b15e0752212bf5486fc38e36e858bf6b3` |
| frozen baseline (unchanged) | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` |

Reviewed Task 2 inputs stayed at contracts `c6ceb984...e5d1`, suite
`b9def623...e8d54`, RNG `bf0f9cb3...ffc46530`, and focused test
`4755e05d...9283379`, exactly matching the base manifest.

## Checkpoint evidence

- Project checkpoint SHA-256: `6af2cf1d7f9a644f5eebd8cad779fbe50f5077b980f0e49a1c5508d6ec9b547d`.
- Result checkpoint SHA-256: `9f12ebf2da4e2ee59cd4135e8344f5b7ed830f67e4acad48d77dd256cb15329d`.
- Result progress JSONL SHA-256: `456ae40d35d29c330136f05a9165e75ffa1d96b37e5c9ed275fdc8f4fc80b107`.
- All five JSONL lines parsed as JSON. Exactly one initial Task 3
  `implementation_progress` record was appended. Frozen Gate fields and the
  baseline hash were preserved. The exact next action is Task 4: real scope
  binding, mediated environment, and label-free encoder.

## Self-review and concerns

The mutation review checked wrong branch thresholds, early realization,
coverage reversal, missing exposure snapshots, completion/exposure order,
offer reopening, emitted doomed states, invalid partial mutations, and false
terminal masks; each is covered by a literal assertion. Static import scanning
found none of the prohibited runtime components.

The initially reported open-evidence concern was reproduced and resolved by
the TDD fix round below. No Task 3 correctness concern remains.

## Implementer concern resolution

Regression method:
`test_open_outcome_evidence_returns_a_nonterminal_zero_result`. It constructs
independent valid `closed=False` / `IN_PROGRESS` evidence and requires
`terminal=False`, reward `0`, `success=False`, and `failed_constraints=()`.

Exact RED command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_model_outcome -v
```

Exact RED outcome: the eight existing methods remained `ok`; the new method
ended:

```text
test_open_outcome_evidence_returns_a_nonterminal_zero_result ... ERROR
ValueError: success and failed constraints disagree
----------------------------------------------------------------------
Ran 9 tests in 0.055s

FAILED (errors=1)
```

Cause: `Family3V2OutcomeResult.__post_init__` applied the terminal
success-versus-failed-constraints equivalence to a nonterminal result. The
smallest production fix added `self.terminal and` to that single invariant;
the evaluator return path and model semantics were otherwise unchanged.

The same exact command then produced:

```text
test_open_outcome_evidence_returns_a_nonterminal_zero_result ... ok
----------------------------------------------------------------------
Ran 9 tests in 0.053s

OK
```

Final SHA-256 values:

| Path | SHA-256 |
|---|---|
| `src/pa_rl/family3_v2_outcome.py` | `b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6` |
| `src/pa_rl/family3_v2_model.py` | `315a13a37a5d8479ec3185b7082fb45e51e42a62493a374bb205cc6bc45b246a` |
| `tests/test_family3_v2_model_outcome.py` | `e9346686642413c9d90fa679439d76face47c91a61fa6071a07c1890a5d79e21` |
| project checkpoint | `6af2cf1d7f9a644f5eebd8cad779fbe50f5077b980f0e49a1c5508d6ec9b547d` |
| result checkpoint | `9f12ebf2da4e2ee59cd4135e8344f5b7ed830f67e4acad48d77dd256cb15329d` |
| result progress JSONL | `456ae40d35d29c330136f05a9165e75ffa1d96b37e5c9ed275fdc8f4fc80b107` |

Revised concern status: resolved; no remaining concern. Gate 0 is still
`BASELINE_FROZEN / 0 / 1`, and Task 4 remains the exact next action.
