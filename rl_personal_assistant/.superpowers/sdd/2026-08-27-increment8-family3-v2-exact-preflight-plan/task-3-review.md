# Task 3 Review — Pure Outcome and Finite-Horizon Model

## Verdict

**APPROVE**

### A) Spec Compliance: PASS

The full current contents of the three Task 3 files comply with the approved
brief, implementation plan, and relevant design sections:

- The model remains a pure standard-library/typed-kernel implementation. Its
  imports are limited to dataclasses, `Fraction`, shared contracts, the new v2
  contracts/outcome/RNG/suite, and the unchanged coverage matcher; none of the
  prohibited authority, monitor, tool, environment, policy, PyTorch, legacy
  lifecycle, or solver components appear (`src/pa_rl/family3_v2_model.py:5-22`).
- Exact rational probabilities are retained as `Fraction` values, with the
  first committed execute producing the two frozen branch probabilities and
  every later transition remaining deterministic (`src/pa_rl/family3_v2_model.py:168-185`,
  `src/pa_rl/family3_v2_model.py:471-480`). Branch realization occurs only
  after the first effect and only after the post-action resource checks
  (`src/pa_rl/family3_v2_model.py:370-391`).
- Every reachable nonterminal state exposes the fixed seven-role catalog;
  terminal states expose no catalog. Transition construction derives the
  authoritative seven-entry nonterminal mask and uses only `()` for a terminal
  successor (`src/pa_rl/family3_v2_model.py:235-272`,
  `src/pa_rl/family3_v2_model.py:301-310`).
- Request, execute, disable, deny, and escalate all apply the required
  post-action active-grant exposure rule. Prompt/exposure failures precede
  branch realization, no-coverage, natural completion, and horizon exhaustion;
  natural completion precedes the horizon check
  (`src/pa_rl/family3_v2_model.py:312-317`,
  `src/pa_rl/family3_v2_model.py:348-446`).
- A valid disable removes authority without reopening the offer and immediately
  invokes the no-coverage guard. The guard stores the complete would-be catalog
  with `emitted=False` before terminal closure
  (`src/pa_rl/family3_v2_model.py:319-330`,
  `src/pa_rl/family3_v2_model.py:412-426`).
- Forced invalid actions change decision and invalid-attempt accounting, then
  terminate without changing prompt, exposure, authority, effect, continuation,
  or queued-task state (`src/pa_rl/family3_v2_model.py:449-470`).
- The continuation templates implement the exact and broader constructions,
  and the focused ten-graph sweep proves all four witness cells and both exact
  exposure totals (`src/pa_rl/family3_v2_model.py:332-346`,
  `tests/test_family3_v2_model_outcome.py:85-98`). The construction uses at
  most `e+2` decisions against `max(8, e+4)`, so all successful paths complete
  naturally before the horizon; the last-decision precedence also has a direct
  regression (`tests/test_family3_v2_model_outcome.py:142-160`).
- The outcome evaluator returns reward one only for the complete natural
  terminal conjunction and correctly accepts open/in-progress evidence as a
  nonterminal zero result (`src/pa_rl/family3_v2_outcome.py:111-131`,
  `tests/test_family3_v2_model_outcome.py:162-206`).
- Current Task 3 SHA-256 values exactly match the final review package. All
  four reviewed Task 2 hashes exactly match `task-3-base.md`. A read-only
  verification of all 14 frozen source entries and all 72 frozen result entries
  found zero missing or changed paths; the frozen baseline manifest itself
  remains `d8b8ff2c...cca055`.
- The report contains the required missing-model RED, focused GREEN, and the
  concern-resolution regression cycle. The added open-evidence test first
  reproduced the invariant error and then passed after the one-condition fix
  (`tests/test_family3_v2_model_outcome.py:187-206`).

### B) Code Quality: PASS

The implementation is compact and cohesive, uses frozen slotted dataclasses,
keeps transition construction centralized, applies explicit validation at its
public boundaries, and preserves a single outcome evaluator for reward
derivation. Tests are behavioral, deterministic, and directly trace the
scientifically important construction and precedence obligations.

## Findings

### Critical

None.

### Important

None.

### Minor

None.

## Verification note

Per the review instruction, I did not rerun the focused tests because complete
code inspection raised no concrete doubt requiring execution. I performed only
read-only source inspection, import/name scanning, SHA-256 comparison, and a
full 14-source/72-result frozen-baseline hash verification.
