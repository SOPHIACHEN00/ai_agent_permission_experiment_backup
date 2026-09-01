# Task 2 Review

**Spec Compliance: ❌**  
**Task quality: Needs fixes**

## Strengths

- The suite/schema constants and seven-role candidate order are exact; the five carrier literals and all ten frozen rows match the brief (`src/pa_rl/family3_v2_contracts.py:12-37`, `src/pa_rl/family3_v2_suite.py:47-67`).
- `Family3V2GraphSpec` checks canonical literal membership and recomputes scope costs, target, exposure, horizon, profiles, and the 21-field mapping without trusting a hash (`src/pa_rl/family3_v2_suite.py:115-158`). The suite also enforces the canonical ten-ID order (`src/pa_rl/family3_v2_suite.py:227-233`).
- The counterfactual is implemented as an immutable replacement of only the probability pair, preserving the source graph and coupling UID (`src/pa_rl/family3_v2_suite.py:324-332`).
- RNG construction follows the frozen canonical JSON-list payload, SHA-256, big-endian first eight bytes, and unbiased mod-5 rejection, with exact non-Boolean checks on seed, ordinal, draws, and residue (`src/pa_rl/family3_v2_rng.py:41-109`).
- The required literal projection, rejection-boundary checks, both thresholds, and hand-derived payload/byte-order evidence are present (`tests/test_family3_v2_suite_rng.py:18-85`). Reported hashes match the current four files; the frozen baseline remains `d8b8ff...cca055`, and the result checkpoint remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.

## Critical findings

None.

## Important findings

### I1 — The mandated existing coverage/relation matcher is not reused

`family3_v2_suite.py` imports only `Scope` and `canonical_hash` from the unchanged contract boundary (`src/pa_rl/family3_v2_suite.py:8`). Its scope validation reconstructs two expected scopes and compares them for equality (`src/pa_rl/family3_v2_suite.py:121-130`), but never calls the existing `scope_matching.covers`/`relation` implementation. This misses the binding requirement to reuse and validate the canonical coverage relation: narrow covers narrow, broader covers narrow, and narrow does not cover broader. Exact reconstruction is useful but is not a substitute for exercising the matcher on which the later authority/model theorem depends.

Required fix: validate those three relations through the unchanged matcher in `Family3V2GraphSpec.__post_init__` (and cover them in the focused test), while retaining the stronger literal-scope equality checks.

### I2 — The typed graph/kernel contract admits non-exact or internally inconsistent values

The graph check `self.prompt_budget != 1` is Boolean-permissive because `True == 1` in Python (`src/pa_rl/family3_v2_suite.py:137-138`). A focused read-only probe confirmed `replace(valid_graph, prompt_budget=True)` succeeds and serializes `"prompt_budget": true`, violating the exact integer/schema contract. The kernel validator repeats the same permissive comparison and does not validate `e > d`, exposure/horizon algebra, or even that its 64-character coupling UID is hexadecimal (`src/pa_rl/family3_v2_suite.py:280-294`). Thus public immutable contract instances can be constructed that are not valid Family-3 v2 kernels.

Required fix: use exact `type(value) is int` validation for every integer contract field, including `prompt_budget`, and make `Family3V2KernelInput.__post_init__` enforce its derived invariants and lowercase SHA-256 UID syntax (or make unchecked direct construction impossible).

## Minor findings

### M1 — Negative schema/rejection behavior is untested

The focused module proves the positive ten-row suite and valid RNG behavior but contains no assertions for wrong split, duplicate/nonliteral suite rows, Boolean/out-of-range integers, invalid UIDs, or exhausted rejection sources (`tests/test_family3_v2_suite_rng.py:32-85`). These are explicit fail-closed requirements and the two Important gaps passed because no adversarial construction was exercised.

Suggested fix: add compact table-driven rejection cases, including `prompt_budget=True` and the three existing-matcher coverage relations.

## Verdict

**Needs fixes.** The core literals, algebra, counterfactual, RNG algorithm, RED/GREEN record, hashes, and pre-gate checkpoint handling are strong, but Task 2 is not spec-complete until the existing coverage matcher is actually reused and exact typed-contract validation rejects Boolean/inconsistent constructions.
