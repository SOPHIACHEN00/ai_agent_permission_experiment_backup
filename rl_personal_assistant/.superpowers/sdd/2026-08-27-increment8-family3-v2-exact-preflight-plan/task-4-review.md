# Task 4 independent review

## Verdict

**A) Spec Compliance: FAIL**

**B) Code Quality: FAIL**

Task 4 is not approved. Two Important findings must be fixed before Task 5. No Critical finding was found.

## Review basis

Read completely: the Task 4 brief, base manifest, implementation report, review package, approved plan Task 4, relevant approved English spec Sections 3–6 and 8–12, all four Task 4 source/test files, and the needed Task 2/3 plus existing authorization/monitor/task/tool interfaces.

I did not rerun the focused tests, as requested. The recorded outputs are internally consistent with the tests and implementation. I independently verified all four Task 4 file SHA-256 hashes and sizes, all seven frozen Task 2/3 input hashes and sizes, and the frozen baseline hash; every value matches the base/report/review package. The checkpoint still retains `status=BASELINE_FROZEN`, `last_completed_gate=0`, and `next_gate=1`. No forbidden Torch, legacy-policy, lifecycle, or solver import is present.

## Findings

### Critical

None.

### Important

1. **The returned binding evidence directly exposes the private raw-ID/public-ordinal association.**

   Evidence: `AuthorizationBindingResultV2` contains both `usable_authorization_id` and `public_issuance_ordinal` (`src/pa_rl/family3_v2_authority.py:64-67`). On a successful request, the environment stores the raw ID in its private map but then also copies the public ordinal into that same result and appends it to caller-visible `info.binding_evidence` (`src/pa_rl/family3_v2_environment.py:195-198`; the returned field is declared at `src/pa_rl/family3_v2_environment.py:59-70`). Thus the private map is not the only object binding ordinal 1 to the raw authorization ID. This violates the brief's exact requirement that only a private environment map bind the public issuance ordinal to the raw ID. The observation/encoder itself remains clean, but that narrower property does not cure the binding-boundary violation.

   Required fix: split the private gateway handle from public/audit binding evidence, or sanitize the result before it enters `Family3V2EnvironmentInfo`, so no returned object contains both a raw authorization ID and a public issuance ordinal. Keep the usable raw ID solely in the private map. Add an assertion that walks returned binding evidence and proves the association is absent while preserving the four-scope equality evidence.

2. **Integrity failures bypass `transition_from_residue` and depend on the model's private `_close` helper.**

   Evidence: every gateway, execution, disable, and semantic-conformance integrity failure funnels through `_fail`, which directly calls `self._model._close(...)` (`src/pa_rl/family3_v2_environment.py:150-154`). This is a semantic successor returned by `step`, but it did not come from `Family3V2Model.transition_from_residue`, contrary to the Task 4 requirement that every semantic successor be obtained exclusively through that API. It also makes Task 4 depend on a private Task 3 implementation detail with no compatibility contract. Although `_close` currently centralizes outcome evaluation and therefore is not a duplicated full FSM, the boundary is still noncompliant and unsafe under a Task 3 refactor.

   Required fix: introduce an approved public model API for integrity-failure closure (or revise the approved interface contract explicitly), and route every environment failure through that public model-owned transition. Do not reproduce closure/outcome logic in the environment. Add coverage proving gateway, monitor/tool, revision, and injected conformance failures all use the public model transition and return matching state/reward/termination/truncation evidence.

### Minor

1. **The branch residue is recorded before the pure kernel confirms that resource-failure precedence did not suppress realization.**

   Evidence: after the monitor commits, `_execute` draws and appends residue whenever the pre-transition `effect_index` is zero (`src/pa_rl/family3_v2_environment.py:247-255`), then calls the model. The pure model checks prompt/exposure failure before installing a branch and intentionally returns a singleton successor with continuation still unrealized (`src/pa_rl/family3_v2_model.py:379-384,471-475`). Therefore an injected or future first-effect resource failure would leave branch evidence even though the semantic branch was not realized.

   This is not reachable in the frozen ten-graph suite: after the only legal request and first execute, prompt use is exactly 1 and exposure is at most `2b`, while `E >= (d+2)b >= 3b`. It therefore does not independently fail the current frozen scientific construct.

   Required fix: consult the model-owned transition distribution/branch applicability first and draw only when the pure kernel says a stochastic continuation transition remains after precedence checks. Add a focused regression that proves a first committed effect whose pure successor closes before realization records no branch residue.

## Confirmed compliant behavior

- Both offered scopes, including `i8_f3v2_v4` sensitivity 3, use the deterministic reusable response, produce an active reusable record with `remaining_uses=None`, and expire at horizon plus one (9).
- The gateway checks the complete three-way scope equality before ledger mutation and the recorded scope/status/grant/lifetime after append; precommit mismatch has no ledger evidence and postcommit mismatch quarantines the raw ID with no usable/public ordinal.
- The environment uses the real `AuthorizationService`, `ReferenceMonitor`, `TaskEngine`, and `MockTool`; plans cover task ordinals 1 through `e+1`, first attempts deterministically commit unique effects, and canonical monitor candidate IDs are used.
- Successful request/execute/disable/deny/escalate and forced-mask paths delegate to `transition_from_residue`; masked rows perform no external action. Noncommitted, malformed/unknown, conflict, duplicate-effect, blocked-monitor, and revision-mismatch paths are rejected by the mediation checks.
- The first committed effect installs all remaining semantic tasks in the engine. An immediate no-coverage successor retains the installed current task and the pure model's nonemitted seven-row guard catalog; no doomed nonterminal observation is emitted.
- The policy projection contains no `Scope`, graph/split/carrier/purpose/seed/raw operational label, raw authorization ID, hash, future branch, solver, value, feasibility, or certificate fact. It exposes the required exact fractions, continuation/accounting state, authorization summaries, and seven ordered candidate rows with neutral authorization bindings on masked rows. The encoder stores fractions as exact numerator/denominator integers and does not retain the raw observation.
- The public-field mismatch hook covers state, reward, termination, and truncation rejection. Source/baseline integrity evidence is unchanged.

## Decision

**REQUEST CHANGES.** Fix both Important findings, add their focused regressions, and then perform a fresh read-only fix-round review before Task 5.
