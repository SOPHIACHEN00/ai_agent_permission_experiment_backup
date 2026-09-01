# Task 4 fix round 1 independent re-review

## Verdict

**APPROVE**

I1, I2, and M1 are fully addressed. I found no new in-scope Critical, Important, or Minor breakage.

## Review basis

I read the original Task 4 review, fix-round base, fix-round review package, updated implementation report, Task 4 and Task 3 briefs, and the complete current contents of all six affected source/test files. I reviewed the code independently rather than relying on the recorded test counts.

I did not rerun tests because code reading produced no concrete doubt requiring a rerun. The reported finding-specific RED, 19-test affected GREEN, and 24-test Tasks 2–4 combined GREEN are consistent with the implemented regressions and paths.

## Finding dispositions

### I1 — ADDRESSED

`Family3V2EnvironmentInfo.binding_evidence` is now typed as `PublicAuthorizationBindingEvidenceV2` (`src/pa_rl/family3_v2_environment.py:59-70`). That public evidence type retains the selected, dispatched, accepted, and recorded scopes plus validity/failure and public ordinal, but contains no usable or quarantined raw-ID field (`src/pa_rl/family3_v2_authority.py:71-80`). The environment constructs a fresh sanitized public object before appending evidence (`src/pa_rl/family3_v2_environment.py:158-171`).

The private gateway result still transports the raw usable/quarantined handle internally, but its construction paths never assign a public ordinal (`src/pa_rl/family3_v2_authority.py:57-67,111-136`). On success, the environment puts the usable raw ID into `_raw_authorization_by_ordinal` and independently publishes only the ordinal through the sanitized object (`src/pa_rl/family3_v2_environment.py:209-215`). Therefore no published binding-evidence object co-locates a usable/quarantined raw authorization ID with a public ordinal, and the sole direct ordinal-to-usable-raw-ID binding remains the private environment map.

The focused regression checks both request roles, four-scope equality, the public ordinal, absence of any authorization-ID field/value from the walked binding evidence, and absence of the raw ID from the encoded policy representation (`tests/test_family3_v2_authority_environment.py:55-90`).

### I2 — ADDRESSED

`Family3V2Model.transition_integrity_failure` is a public, model-owned transition API. It rejects a non-`Family3V2State`, a terminal state, and an empty/non-string reason, and delegates irreversible closure and outcome construction to the model's existing `_close`/`_transition` machinery (`src/pa_rl/family3_v2_model.py:500-515`). Consequently its successor is irreversible terminal, reward zero, non-truncated, probability one, and uses the terminal empty-mask sentinel; the direct regression verifies those properties and invalid inputs (`tests/test_family3_v2_model_outcome.py:208-222`).

The environment's single `_fail` funnel marks run evidence invalid and calls only `transition_integrity_failure`; it neither calls `_close` nor reproduces closure/outcome logic (`src/pa_rl/family3_v2_environment.py:151-156`). Every detected request, execution/binding, ledger, mediation, semantic-conformance, and disable anomaly routes through `_fail` (`src/pa_rl/family3_v2_environment.py:193,209-211,218-247,248-261,297,315-325`). The regression spies on the public API across gateway, execution, revision, and conformance anomalies and compares the returned state/reward/termination/truncation to the public model transition (`tests/test_family3_v2_authority_environment.py:264-329`).

### M1 — ADDRESSED

After a real committed first effect is validated, the environment asks the model for the authoritative transition distribution and treats the branch as stochastic only when that distribution has exactly two successors (`src/pa_rl/family3_v2_environment.py:248-270`). It draws and appends residue only in that case, then obtains the selected successor from `transition_from_residue` (`src/pa_rl/family3_v2_environment.py:271-280`). A singleton first-effect closure therefore uses residue zero without branch evidence. The regression forces a resource-precedence singleton closure and verifies an empty branch-evidence tuple (`tests/test_family3_v2_authority_environment.py:331-343`).

## Cross-task boundary

The Task 3 delta is limited to the narrow public integrity-failure transition and its focused regression. Normal candidate transitions remain pure and continue through `transition_distribution` / `transition_from_residue`; the new API reuses the existing model-owned outcome and transition constructors. No Torch, legacy-policy, lifecycle, solver, or other forbidden import was introduced in any affected file.

## Integrity verification

All six affected file hashes and sizes independently match the fix-round review package:

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_model.py` | `F7848D2AC0343D2FFB79B24D584A81DA1FA5DAA51C7F97D35134948D90020F2C` | 23,904 |
| `tests/test_family3_v2_model_outcome.py` | `36A8BF08E5D0DC337FAC80447F5FF8E6BCC95FDE0293BEEBD551433886A9EFC1` | 11,357 |
| `src/pa_rl/family3_v2_authority.py` | `0ACA9E16347A8E0C128B0DCAF632A3223556A6C9D79ADBF4C9FE776FE030588D` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2EBBB936567C0CA65EC616CC91E4E5C708D939394C7F41B31D00C0C8A2F4E0A6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | 15,680 |
| `tests/test_family3_v2_authority_environment.py` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | 17,862 |

The updated report and checkpoint/progress hashes also match the package. The five unchanged frozen Task 2/3 inputs retain their recorded hashes. The frozen baseline independently hashes to `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`, and the result checkpoint retains `status=BASELINE_FROZEN`, `last_completed_gate=0`, and `next_gate=1`.

## New findings

- Critical: none.
- Important: none.
- Minor: none.

## Decision

**APPROVE.** Task 4 fix round 1 resolves I1, I2, and M1 without new in-scope breakage.
