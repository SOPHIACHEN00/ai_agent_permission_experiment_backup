# Task 0 Independent Review — Increment 0 Contracts and Canonical Fixtures

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

The repository contains the requested standard-library package, configuration defaults, six-member enum, protocol, JSON fixtures, and a recorded RED/GREEN run.  The core contract is not yet sufficiently closed or enforceable for later increments: unsupported controller actions can still be represented as candidates, visibility is an unattached convention rather than a firewall, and the fixtures encode the distinguishing authority behaviour only as prose.  The test suite also contains a prohibited tautological hash assertion and does not test those omissions.

Review method: read-only inspection of the brief, implementation report, `pyproject.toml`, all `src/pa_rl/*.py`, `tests/test_contracts.py`, and all ten fixtures.  Per review scope, no tests were rerun.  The report records the author's GREEN evidence as `13` passing `unittest` tests and a successful `compileall` run ([task-0-report.md](../implementation_reports/task-0-report.md:48)).

## What is sound

- The declared enum itself has exactly the specified six values ([contracts.py](../../src/pa_rl/contracts.py:12)), and deferred names fail enum parsing under the included observable test ([test_contracts.py](../../tests/test_contracts.py:41)).
- `PermissionUserAdapter` has all three requested methods and its permission answer is typed as `PermissionChoice` ([contracts.py](../../src/pa_rl/contracts.py:161)).
- The v0 default values match the brief and runtime imports are all from the standard library; `pyproject.toml` declares no runtime dependencies ([config.py](../../src/pa_rl/config.py:6), [pyproject.toml](../../pyproject.toml:5)).
- Canonical serialization sorts mapping keys and candidate generation sorts both scopes and enabled action values before generating SHA-256-derived identifiers ([contracts.py](../../src/pa_rl/contracts.py:101), [contracts.py](../../src/pa_rl/contracts.py:207)).
- Each fixture includes the eight explicitly required top-level fields and has a horizon in the required range.  The ten filenames and narrative scenarios are distinct.

## Findings

### Critical

None.

### Important

1. **The six-action restriction is not enforced at the action-candidate boundary.**  `ActionCandidate` is publicly constructible with any runtime value, despite its annotation, and `build_action_candidates` validates neither `actions` nor each resulting candidate action ([contracts.py](../../src/pa_rl/contracts.py:94), [contracts.py](../../src/pa_rl/contracts.py:101)).  Consequently a caller can construct a candidate whose action is `"CLARIFY"`, or supply a different `str`-backed enum with an undeclared action.  This contradicts the brief's requirement that deferred actions have no candidate slot, and leaves a widening route for later modules.  Require `ControllerAction` at construction/build time (and reject every other value with `ValueError`), ideally deriving candidate identifiers inside the factory only.

2. **The public/private/oracle model is not an enforceable firewall.**  `VisibilityRegistry` is an optional, empty registry that is never populated for `ScenarioManifest` fields or consulted by `project_public_observation` ([contracts.py](../../src/pa_rl/contracts.py:171), [scenarios.py](../../src/pa_rl/scenarios.py:75)).  It also does not validate that `visibility` is a `FieldVisibility`, so a caller can register an arbitrary classification.  The projection currently excludes two hand-selected fields, but that is not a contract-level proof that the required private/oracle categories (e.g. future response, rule IDs, evaluator labels) cannot enter observations.  Define and bind a complete schema/registry for manifest and observation paths; make projection operate from it and validate visibility inputs.

3. **Fixtures cannot structurally express or validate the required authority scenarios.**  `ScenarioManifest` carries only free-text `expected_legal_path`/`prohibited_path`; it contains no typed requested/operation scopes, action trace, protected-step count, or expected response-to-request mapping ([scenarios.py](../../src/pa_rl/scenarios.py:20)).  Thus the reusable-two-step, disable/revocation, consumed-grant refresh, and broader-scope cases are distinguishable only by prose.  Most notably, the broader-scope fixture does not contain either the original or broadened `Scope` ([06_broader_scope_refresh.json](../../fixtures/scenarios/06_broader_scope_refresh.json:1)).  This is insufficient for later authority/environment modules to consume the fixtures as canonical executable contracts and makes the advertised ten-scenario coverage non-substantive.  Add typed scopes and a concise declarative legal/prohibited action trace (or equivalent assertions) to the manifest, then validate each scenario's distinct required property.

4. **A required reproducibility test explicitly violates the brief's anti-tautology rule.**  `test_scenario_and_configuration_hashes_are_reproducible` asserts `scenario_hash(manifest) == scenario_hash(manifest)` ([test_contracts.py](../../tests/test_contracts.py:132)).  This is a helper compared to itself, prohibited by the brief, and it does not establish reproducibility across independently loaded/reordered equivalent fixtures.  Replace it with hashes of two independent equivalent manifest mappings that differ in key insertion order, plus a known SHA-256 test vector or fixed expected digest.  Test candidate/action rejection and visibility-driven projection as observable behaviours at the same time.

5. **“Frozen public contracts” are only shallowly frozen.**  Multiple frozen dataclasses expose mutable mappings: `PublicEvent.payload`, `PublicObservation.request_context`, and both manifest context/postcondition fields ([contracts.py](../../src/pa_rl/contracts.py:123), [contracts.py](../../src/pa_rl/contracts.py:143), [scenarios.py](../../src/pa_rl/scenarios.py:20)).  `scenario_from_mapping` creates ordinary dictionaries, so callers can mutate an already-created manifest ([scenarios.py](../../src/pa_rl/scenarios.py:55)).  This undermines stable hashes, deterministic observations, and the stated frozen-contract guarantee.  Normalize recursively to immutable values (e.g. `MappingProxyType`/tuples or immutable contract dataclasses) before storage, and test mutation cannot change a constructed contract.

### Minor

1. **Scope is underspecified for the supplied scenarios.**  `Scope` has only `resource` and `operation` ([contracts.py](../../src/pa_rl/contracts.py:78)).  That can distinguish broad operation classes, but cannot encode bounded authority such as a selected message, recipient, date range, or other qualifiers without overloading strings.  At minimum, document the intended scope grammar; preferably add a canonical immutable qualifier/target field if future scope matching needs least-privilege granularity.  This should be resolved together with the fixture trace change above.

2. **`PermissionUserAdapter` has no direct contract test.**  Its method signatures look compliant, but the test suite has no concrete adapter implementation/call site exercising `reset`, verified public events, or the history passed to `answer_permission` ([contracts.py](../../src/pa_rl/contracts.py:161), [test_contracts.py](../../tests/test_contracts.py:1)).  A small fake adapter test would prevent accidental signature drift.

3. **Canonical JSON should reject non-finite floats if it is an interchange-format contract.**  `json.dumps` is called with its default `allow_nan=True` ([contracts.py](../../src/pa_rl/contracts.py:207)), which can emit `NaN`/`Infinity` rather than valid JSON.  Reject non-finite floats or use `allow_nan=False` for fully portable canonical artifacts.

## Required resolution before approval

1. Close candidate construction to the exact `ControllerAction` enum and add an observable negative test for each deferred action.
2. Bind a validated visibility schema to manifest ingestion and public observation projection.
3. Make scopes and scenario paths declarative/typed enough to express all ten cases, particularly broader scope and multi-step/refresh/revocation behaviour; add semantic fixture tests.
4. Replace the self-comparison hash test with independent-equivalence and known-digest evidence.
5. Make contract values deeply immutable, or narrow the word “frozen” in the design/brief and document the mutation model.

After those changes, the standard-library-only approach, enum declaration, adapter signature, and deterministic sort/hash foundation are reasonable for Increment 0.

## Fix round 1 re-review

### Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope of this re-review: the appended fix report, the changed Task 0 package/tests, and all ten current fixtures.  No tests were rerun.  The implementation report records `19` passing tests for both the task and project suites ([task-0-report.md](../implementation_reports/task-0-report.md:124)); that is evidence supplied by the implementation, not independently re-executed here.

### Prior findings

| Prior finding | Status | Evidence |
| --- | --- | --- |
| Six-action restriction was not enforced at candidate construction | **ADDRESSED** | `ActionCandidate` and `build_action_candidates` reject non-`ControllerAction` values, and the identifier is checked against the canonical action/scope digest ([contracts.py](../../src/pa_rl/contracts.py:123), [contracts.py](../../src/pa_rl/contracts.py:138)). The negative candidate test covers both deferred names and a foreign enum ([test_contracts.py](../../tests/test_contracts.py:69)). |
| Visibility was an unattached convention, not a firewall | **ADDRESSED** | A complete top-level manifest schema is registered, frozen, used to reject undeclared fixture keys, and is the sole source for public projection ([scenarios.py](../../src/pa_rl/scenarios.py:29), [scenarios.py](../../src/pa_rl/scenarios.py:190), [scenarios.py](../../src/pa_rl/scenarios.py:236)). The registry now rejects untyped visibility values ([contracts.py](../../src/pa_rl/contracts.py:237)). |
| Fixtures could not structurally express/validate authority scenarios | **NOT_ADDRESSED** | Typed `TaskStep`, eight-field `Scope`, and action traces are a substantial improvement ([scenarios.py](../../src/pa_rl/scenarios.py:64), [scenarios.py](../../src/pa_rl/scenarios.py:78)). However, the current typed traces do not make their declared authorization semantics valid; see new findings 1 and 2 below. |
| Scenario-hash test was a prohibited self-comparison | **ADDRESSED** | The test now constructs two independently ordered mappings and compares their scenario hashes; canonical JSON also has a fixed known digest test ([test_contracts.py](../../tests/test_contracts.py:100), [test_contracts.py](../../tests/test_contracts.py:233)). |
| Frozen contracts exposed mutable nested mappings | **ADDRESSED** | `freeze_value` recursively copies mappings/sequences/sets to immutable containers and the public/manifest contracts call it during initialization ([contracts.py](../../src/pa_rl/contracts.py:164), [contracts.py](../../src/pa_rl/contracts.py:175), [scenarios.py](../../src/pa_rl/scenarios.py:110)). Tests mutate both input and constructed values ([test_contracts.py](../../tests/test_contracts.py:146)). |
| Scope was under-specified | **ADDRESSED** | `Scope` now requires all eight requested structural fields and canonicalizes the non-empty immutable attribute tuple ([contracts.py](../../src/pa_rl/contracts.py:93)). This establishes a usable v0 scope value, though the fixture relations below still need repair. |
| No direct `PermissionUserAdapter` contract exercise | **ADDRESSED** | A fake adapter is exercised through all three protocol methods with a `PublicEvent` and public history ([test_contracts.py](../../tests/test_contracts.py:162)). |
| Canonical JSON accepted non-finite floats | **ADDRESSED** | Non-finite values are rejected both during normalization and JSON serialization, with a negative test ([contracts.py](../../src/pa_rl/contracts.py:259), [test_contracts.py](../../tests/test_contracts.py:116)). |

### Controller-confirmed gaps

- **Eight-field immutable `Scope`: PASS.**  The required `domain`, `tool`, `resource`, `data_attributes`, `operation`, `purpose`, `recipient`, and `retention` fields are mandatory and normalized; fixtures provide all eight ([contracts.py](../../src/pa_rl/contracts.py:97), [01_one_time_grant_success.json](../../fixtures/scenarios/01_one_time_grant_success.json:1)).
- **Complete authorization statuses: PASS.**  The contract declares the reviewed complete lifecycle set—pending, active, reserved, consumed, expired, revoked, superseded, rejected, and reconciliation-required—and tests it exactly ([contracts.py](../../src/pa_rl/contracts.py:58), [test_contracts.py](../../tests/test_contracts.py:87)).
- **Truncation separated from success: PASS.**  `TRUNCATED` was removed from `TerminalSuccessKind`, is represented by `ExpectedTermination`, and the timeout fixture declares no success kind ([contracts.py](../../src/pa_rl/contracts.py:81), [scenarios.py](../../src/pa_rl/scenarios.py:24), [10_timeout_truncation.json](../../fixtures/scenarios/10_timeout_truncation.json:1)).

### New findings

#### Critical

None.

#### Important

1. **The reusable-grant fixture has an internally incompatible typed legal path.**  In fixture 02, `REQUEST_AUTHORIZATION` is tied to `calendar_read` (a `calendar_api`/`calendar.events`/`read` scope), while the second authorized execution is tied to `briefing_send` (a `mail_api`/`mail.messages`/`send` scope), with no refresh or broader declared authorization ([02_reusable_grant_two_steps.json](../../fixtures/scenarios/02_reusable_grant_two_steps.json:1)).  Under the new exact eight-field scope contract, these are distinct scopes.  The fixture calls that trace legal and describes it as reusable authority over both steps, which conflicts with scope-bounded authorization.  Either make both protected steps use the same reusable scope, or represent and request an explicit multi-step/broader scope that covers both before the two executions.

2. **“Broader scope” is still not declaratively represented as a widening relation.**  Fixture 06's initial read scope and refreshed send scope differ in domain/tool/resource/operation, so they are disjoint task scopes rather than a typed narrower-to-broader relation ([06_broader_scope_refresh.json](../../fixtures/scenarios/06_broader_scope_refresh.json:1)).  The test only asserts that there are two distinct scopes ([test_contracts.py](../../tests/test_contracts.py:207)); distinctness does not establish broadening.  Preserve a common base scope and declare the added/widened dimension (or add a declarative `broader_than`/coverage relationship) so a later matcher can consume the fixture without interpreting prose.

3. **Trace validation does not require a scope for authorization requests/refreshes.**  `ActionTraceStep` requires a permission response for request/refresh, but permits `scope_step_id=None`; only execution requires a scope reference ([scenarios.py](../../src/pa_rl/scenarios.py:84), [scenarios.py](../../src/pa_rl/scenarios.py:141)).  This permits a future fixture to request authorization without declaring what authority it requests, defeating the new scope contract.  Require `scope_step_id` for `REQUEST_AUTHORIZATION` and `REQUEST_REFRESH`, and add a negative test.

#### Minor

1. The fake-adapter test invokes all methods but does not assert that `reset` retained the seed or that `answer_permission` received the supplied history ([test_contracts.py](../../tests/test_contracts.py:163)).  Add those assertions so it guards the intended call values, not only return type.

### Required resolution before approval

1. Repair fixture 02 so the typed request scope actually covers both legal protected executions.
2. Encode and validate a real narrow-to-broader scope relation in fixture 06.
3. Require and test scope-step references on every authorization request/refresh trace action.

The remediation is otherwise strong: it resolves six-action closure, immutability, bound visibility, canonical JSON validity, hash test quality, the full reviewed status vocabulary, and separate truncation semantics.

## Fix round 2 re-review

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope: inspected only the latest appended implementation report, `src/pa_rl/scenarios.py`, `tests/test_contracts.py`, and fixtures 02/06.  No tests were rerun.  The implementation report records 20 passing task and project tests ([task-0-report.md](../implementation_reports/task-0-report.md:196)); that execution evidence was not independently repeated in this review.

### Previously open findings

| Open finding from round 1 | Status | Evidence |
| --- | --- | --- |
| Fixture 02's reusable grant authorized one scope but executed a different scope | **ADDRESSED** | Both protected steps now have equal complete `Scope` values (`productivity` / `calendar_api` / `calendar.events` / identical attributes / `read` / identical scalar qualifiers), and the one `allow_reuse` request precedes both executions ([02_reusable_grant_two_steps.json](../../fixtures/scenarios/02_reusable_grant_two_steps.json:1)). The test asserts scope equality ([test_contracts.py](../../tests/test_contracts.py:209)). |
| Fixture 06 did not express a real narrow-to-broader relationship | **ADDRESSED** | The narrow and broader steps have identical scalar scope fields; `data_attributes` changes strictly from `{time}` to `{time, title}`, with a refresh tied to the broader step ([06_broader_scope_refresh.json](../../fixtures/scenarios/06_broader_scope_refresh.json:1)). The test asserts scalar equality, strict set inclusion, and the full request/execute/refresh/execute sequence ([test_contracts.py](../../tests/test_contracts.py:215)). |
| Authorization request/refresh trace actions could omit a scope reference | **ADDRESSED** | `ActionTraceStep` rejects a request or refresh without `scope_step_id`, rejects blank values through `_non_empty`, and `ScenarioManifest` rejects references to unknown task IDs ([scenarios.py](../../src/pa_rl/scenarios.py:84), [scenarios.py](../../src/pa_rl/scenarios.py:143)). The direct negative test covers both authorization actions ([test_contracts.py](../../tests/test_contracts.py:239)). |
| Fake-adapter test did not assert actual inputs | **ADDRESSED** | The test now asserts the seed supplied to `reset`, the exact verified-event list received by `observe_event`, and the exact public history received by `answer_permission` ([test_contracts.py](../../tests/test_contracts.py:180)). |

### New breakage

None found in the scoped re-review.  The changed fixture semantics are internally consistent with the eight-field scope model: fixture 02 demonstrates same-scope reuse, while fixture 06 demonstrates an explicit strict attribute widening that requires refresh.
