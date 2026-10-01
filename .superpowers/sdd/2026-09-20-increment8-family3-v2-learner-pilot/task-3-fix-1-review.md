# Task 3 Fix Round 1 Independent Re-review

## Verdict: FINDINGS

Reviewed the exact supplied Task-3 fix-round package and the cited source/test
surfaces. No production or test files were modified, and no tests were run.
The report's recorded RED/GREEN evidence is internally consistent with the
source: RED failed at the expected missing `select_candidate` integrity check,
and the recorded focused and module GREEN runs passed after the boundary fix.

The production fix addresses the original P1:

- `Family3V2MaskedDoubleDQN.select_candidate` requires a
  `Family3V2LearnerDecision`, invokes `_require_integrity()` before generic
  selection, still requires an exact external `random.Random`, and delegates to
  the unchanged generic policy-mask validation.
- `Family3V2MaskedDoubleDQN.observe` retains the generic call shape and
  terminal-`None` behavior, checks the current decision and every non-null
  successor before its sole delegation, and therefore before generic replay,
  model, or replay-RNG work.
- The matched initialization and replay-sampling path remains unchanged:
  `_optimize` reseeds the existing private replay RNG from the zero-based
  `optimizer_steps` coordinate immediately before the generic optimization.
- The focused test does synchronously forge both mask and candidate feature
  bit for a current decision and a successor, and asserts rejection at selection
  plus both observe boundaries.

### P2 — failed-observe test does not prove model or optimizer immutability

`test_rng_namespaces_matched_initialization_and_replay_sampling` snapshots and
compares replay contents/cursor/RNG plus `environment_steps`, `optimizer_steps`,
and `last_loss` at
[test_family3_v2_learning.py:235](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:235)
through
[test_family3_v2_learning.py:297](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:297).
It does not snapshot or compare the online-network state, target-network state,
or optimizer state. The source ordering at
[family3_v2_learning.py:196](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:196)
through
[family3_v2_learning.py:211](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:211)
currently prevents those mutations, but the regression test does not itself
prove the report's claim that failed `observe` leaves replay, model, optimizer,
RNG, and counters unchanged.

Smallest fix: extend `replay_before` and every post-rejection comparison with
deterministic digests of `online_network.state_dict()` and
`target_network.state_dict()` (the existing `_tensor_state_digest` helper is
available), plus a deterministic recursive digest of
`integrity_arm._optimizer.state_dict()` that includes nested tensors. This keeps
the test focused while covering all claimed mutable learner state.
