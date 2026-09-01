### Task 3: Implement the pure outcome and finite-horizon model

**Files:**

- Create: `src/pa_rl/family3_v2_outcome.py`
- Create: `src/pa_rl/family3_v2_model.py`
- Create: `tests/test_family3_v2_model_outcome.py`

**Interfaces:**

- `evaluate_family3_v2_outcome(evidence) -> Family3V2OutcomeResult`
- `Family3V2Model.initial_state(kernel) -> Family3V2State`
- `Family3V2Model.candidates(state) -> tuple[Family3V2Candidate, ...]`
- `Family3V2Model.transition_distribution(state, semantic_candidate_id) ->
  tuple[Family3V2Transition, ...]`
- `Family3V2Model.transition_from_residue(state, semantic_candidate_id,
  residue) -> Family3V2Transition`
- `Family3V2Model.is_success(state) -> bool`

- [ ] **Step 1: Write the focused model/outcome RED tests**

Include one helper that requests a chosen role, selects a specified exact or
broader transition after the first execute, then repeatedly selects
`execute_covering` until terminal. Assert all four witness cells:

```python
self.assertTrue(run_witness(graph, "request_narrow", "exact").success)
self.assertEqual(run_witness(graph, "request_narrow", "broader").failure_reason, "irreversible_no_coverage")
self.assertEqual(run_witness(graph, "request_broader", "exact").failure_reason, "exposure_budget_exceeded")
self.assertTrue(run_witness(graph, "request_broader", "broader").success)
```

Also assert:

- reset has exactly seven rows and only the two requests, deny, and escalate are
  mask-valid;
- queued future tasks are empty and continuation is `UNREALIZED` before the
  first committed effect;
- grant verification closes the window;
- request/refresh remain `offer_window_closed` thereafter;
- valid disable never reopens the window and immediately reaches the
  nonemitted no-coverage guard;
- exposure failure beats natural completion;
- valid natural completion on the last decision beats horizon exhaustion;
- only `NATURAL_COMPLETION` can yield reward one.

- [ ] **Step 2: Run the focused test for the expected missing-model RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_model_outcome -v
```

Expected: import failure for `pa_rl.family3_v2_model`.

- [ ] **Step 3: Implement the state and seven-row catalog**

Use frozen dataclasses for task, authorization, candidate, state, and transition.
The internal candidate may carry `operational_scope`; no policy type may. Every
normal action increments zero-based `decision_index` exactly once. Terminal
states return an empty catalog; every emitted nonterminal state returns the
seven roles in `FAMILY3_V2_CANDIDATE_ORDER`.

The terminal transition signature also uses the unique empty-mask sentinel
`next_mask=()`. It never fabricates seven false candidates. Every nonterminal
successor instead carries its authoritative seven-entry mask. Model,
observation, solver, and audits must use this same convention.

Reason precedence is implemented before action-specific dispatch:

```python
if state.terminated:
    return "terminal_state"
if action is ControllerAction.REQUEST_AUTHORIZATION and scope not in offered_scopes:
    return "scope_not_offered"
if state.offer.offer_window is OfferWindowV2.CLOSED and action in {
    ControllerAction.REQUEST_AUTHORIZATION,
    ControllerAction.REQUEST_REFRESH,
}:
    return "offer_window_closed"
```

Then apply `no_refreshable_authorization`, `no_covering_authorization`, or
`no_active_authorization`. Masked rows remain in the catalog with neutral
bindings.

- [ ] **Step 4: Implement transition timing and outcome precedence**

For a valid action: apply the action, take the post-action active-grant exposure
snapshot, check integrity/prompt/exposure failure, realize a branch only after
the first committed execute, install its task queue, check irreversible
no-coverage, then natural completion, then horizon exhaustion. A successful
exact path consumes `(e+2)n`; a successful broader path consumes `(d+2)b`.

Forced invalid action must terminate reward zero without changing prompt,
exposure, authority, effect index, or branch state. Store the seven-row
would-be catalog with `emitted=False` before automatic no-coverage termination.

- [ ] **Step 5: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all model/outcome methods PASS. Save hashes,
counts, and the Task 4 next action in both checkpoints.

