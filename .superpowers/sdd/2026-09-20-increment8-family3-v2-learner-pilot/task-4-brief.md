# Task 4 implementation brief — authoritative

**Status:** Approved for Task 4 implementation by the controller on
2026-09-20 after independent contract review and fix round 1. This brief
resolves the approved plan's Task 4 ellipses without changing a scientific
threshold, method, seed, split, budget, or result category.

## Authority, correction, and dispatch gate

The authorities, in descending order, are:

1. the approved English and Chinese learner-pilot specifications;
2. Task 4 and the Global Constraints in the approved implementation plan;
3. `task-4-preflight.md`;
4. the frozen formal config; and
5. this brief for the previously unspecified Task 4 Python interface only.

Discarded provenance: the controller confirmed that an earlier request's
“5 validation cells and 15 test cells” wording was erroneous and has no
aggregate meaning. The approved contract remains exactly **4 validation
graph-condition cells per seed** (2 graphs x 2 conditions), **6 test
graph-condition cells per seed** (3 graphs x 2 conditions), and 50 episodes
per cell. Nothing in this brief uses 5/15 or changes the approved thresholds.

Task 4 may start only after all of the following are true:

- Task 3 has a passing controller review/closeout.
- The controller promotes this draft, or an approved revision of it, to
  `task-4-brief.md`.
- The two Task 4 targets still match the Task 1 boundary exactly:

  | Target | Bytes | SHA-256 |
  |---|---:|---|
  | `rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py` | 8,984 | `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` |
  | `rl_personal_assistant/tests/test_family3_v2_learner_pilot.py` | 6,332 | `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` |

Any mismatch is **BLOCKING**. Do not merge around it, regenerate a base, or
start RED.

## Authorized scope

Modify only:

- `rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py`
- `rl_personal_assistant/tests/test_family3_v2_learner_pilot.py`

The Task 1 `Family3V2PilotConfig`, `CertifiedDependencyVerification`,
`load_family3_v2_pilot_config`, and
`verify_certified_dependency_baseline` behavior is an immutable compatibility
boundary. Append Task 4 behavior; do not refactor, relax, replace, or change the
serialization/hash checks that the existing Task 1 test exercises.

Do not edit the config, baseline, specs, Task 3 files, any certified source or
artifact, any runner/checkpoint module, or any project result root. Do not run
an environment, learner, exact solver, training, evaluation, smoke, broad test
suite, or formal experiment in Task 4.

## Exact public interface

Use these exact field names, annotations, declaration order, frozen/slots
settings, and keyword-only classifier state. No broad `Mapping[str, object]`
substitute is allowed for any of these result schemas.

```python
ROOT_ACTION_MISSING = "__missing_root_action__"
ROOT_ACTION_MULTIPLE = "__multiple_root_actions__"


@dataclass(frozen=True, slots=True)
class HardIntegrityCounts:
    invalid_action_attempts: int
    policy_mask_violations: int
    unauthorized_committed_effects: int
    monitor_blocked_attempts: int
    monitor_bypass_effects: int
    environment_invalid_runs: int
    scope_binding_integrity_failures: int
    authorization_binding_failures: int
    semantic_conformance_failures: int
    effect_integrity_failures: int
    adapter_contract_failures: int
    candidate_id_resolution_failures: int
    oracle_feature_leaks: int
    split_leakage_events: int
    test_access_before_unlock: int
    evaluation_state_mutations: int
    source_freeze_mismatches: int
    config_freeze_mismatches: int
    certified_dependency_hash_mismatches: int
    artifact_hash_mismatches: int
    checkpoint_policy_violations: int
    common_random_coordinate_mismatches: int
    duplicate_result_rows: int
    unexpected_result_rows: int
    missing_expected_result_rows: int
    nonfinite_events: int


@dataclass(frozen=True, slots=True)
class EvaluationEpisodeRow:
    phase: str
    method_id: str
    evaluation_seed: int
    graph_id: str
    condition: str
    episode_ordinal: int
    root_seed: int
    root_semantic_candidate_id: str
    terminal_success: int
    termination_kind: str
    decision_count: int
    prompt_count: int
    hard_counts: HardIntegrityCounts


@dataclass(frozen=True, slots=True)
class EvaluationCellResult:
    phase: str
    method_id: str
    evaluation_seed: int
    graph_id: str
    condition: str
    episode_count: int
    terminal_success_count: int
    first_request_match_count: int
    forecast_rule_terminal_match_count: int
    hard_counts: HardIntegrityCounts


@dataclass(frozen=True, slots=True)
class ValidationGateResult:
    phase_complete: bool
    status: str | None
    qualifying_seed_ids: tuple[int, ...]
    observed_row_count: int
    hard_counts: HardIntegrityCounts
    cell_results: tuple[EvaluationCellResult, ...]


@dataclass(frozen=True, slots=True)
class TestClassificationResult:
    phase_complete: bool
    test_opened: bool
    classification: str | None
    validation_qualified_seed_ids: tuple[int, ...]
    rule_parity_seed_ids: tuple[int, ...]
    credit_signal_seed_ids: tuple[int, ...]
    observed_row_count: int
    hard_counts: HardIntegrityCounts
    cell_results: tuple[EvaluationCellResult, ...]


def evaluate_validation_gate(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    phase_complete: bool,
) -> ValidationGateResult: ...


def classify_test_result(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    validation_gate: ValidationGateResult,
    permitted_seed_ids: tuple[int, ...],
    test_opened: bool,
    phase_complete: bool,
) -> TestClassificationResult: ...
```

Classifier containers are also exact: `rows` and `permitted_seed_ids` must
be tuples (not lists/generators), every member must have the declared exact
type, and `phase_complete`/`test_opened` must satisfy `type(value) is bool`.
A wrong Python/schema type, missing/extra serialized field, or incoherent
manually constructed result raises `ValueError`. Once inputs are
well-typed, evidence-integrity failures (wrong coordinates, duplicates,
unexpected rows, bad root seeds, root-cardinality markers, or completed-phase
missing rows) are represented by the applicable hard count and returned as
`INVALID_RUN`; they are never converted into performance values.

The two root-action marker constants are artifact-only integrity markers, not
candidate IDs, policy actions, labels, or new outcomes. They preserve the
plan's existing singular `root_semantic_candidate_id: str` field while making
the two forbidden collection states observable:

- no initial committed semantic action -> `ROOT_ACTION_MISSING`;
- more than one initial committed semantic action ->
  `ROOT_ACTION_MULTIPLE`.

The evaluator must never choose one observed action from a multiple-root case
and must never invent a semantic ID for a missing-root case. Either marker adds
one derived `semantic_conformance_failures` event and forces `INVALID_RUN`
before performance aggregation. A single valid non-request ID such as `deny`
or `escalate` remains a performance mismatch, exactly as approved; it is not a
root-cardinality failure.

## Exact dataclass validation

### `HardIntegrityCounts`

- Its 26 fields above are exactly the config's `hard_zero_counts`, in that
  order. There is no 27th catch-all field and none may be omitted or renamed.
- Every value must satisfy `type(value) is int and value >= 0`; `bool`, float,
  numeric strings, NaN, and infinity are rejected with `ValueError`.
- Any mapping-to-dataclass boundary must require exactly those 26 keys and
  reject missing/extra keys before construction. Mapping serialization uses
  declaration/config order.
- Fieldwise aggregation uses exact integer addition in declaration order.
- `missing_expected_result_rows` is classifier-owned and must be zero in each
  episode row. It is synthesized only when `phase_complete is True`.

### `EvaluationEpisodeRow`

The declared fields remain exactly those in the approved plan. Intrinsic
validation is:

- `phase`, `method_id`, `graph_id`, `condition`,
  `root_semantic_candidate_id`, and `termination_kind` have exact type `str`;
  no subclass/coercion is accepted.
- `evaluation_seed`, `episode_ordinal`, `root_seed`, `terminal_success`,
  `decision_count`, and `prompt_count` have exact type `int`; Boolean is
  rejected everywhere an integer is expected.
- `root_seed` is in `[0, 2**64)`, `terminal_success` is exactly 0 or 1,
  `decision_count >= 0`, and `prompt_count >= 0`.
- `hard_counts` is exactly `HardIntegrityCounts`, and its
  `missing_expected_result_rows` is zero.
- `termination_kind` is exactly one of the frozen terminal values
  `natural_completion`, `horizon_exhaustion`, `deny_with_reason`, `escalate`,
  or `irreversible_failure`; `in_progress` is not a terminal episode row.
- `root_semantic_candidate_id` is one of the seven frozen candidate IDs
  (`request_narrow`, `request_broader`, `execute_covering`, `refresh_closed`,
  `disable_active`, `deny`, `escalate`) or one of the two reserved integrity
  markers above. An unknown string is malformed.

Phase/method/seed/graph/condition membership, graph-phase compatibility,
ordinal range, the root-seed formula, duplicate coordinates, and canonical
ordering are phase-level evidence checks. They are audited by the classifiers
before any performance calculation, so a well-typed wrong coordinate produces
an `INVALID_RUN` result rather than being normalized or silently dropped.

### `EvaluationCellResult`

- All five coordinate strings/integers follow the exact row type rules and
  identify one method x evaluation seed x graph x condition cell.
- `episode_count`, `terminal_success_count`, `first_request_match_count`, and
  `forecast_rule_terminal_match_count` are exact nonnegative integers, never
  Boolean. A complete cell has `episode_count == 50`; each other count is in
  `[0, episode_count]`.
- `first_request_match_count` counts rows whose single root semantic ID equals
  the `forecast_rule` row at the identical
  `(evaluation_seed, graph_id, condition, episode_ordinal)` coordinate.
- `forecast_rule_terminal_match_count` counts rows whose
  `terminal_success` equals that paired `forecast_rule` row. It is not an
  unpaired rate comparison.
- `hard_counts` is the fieldwise sum for that cell after derived coordinate
  checks. Cell summaries are emitted only for a complete, structurally valid,
  hard-zero phase, so result-contained cell counts are all zero. The field is
  retained to make that fact explicit and serializable.
- Raw root IDs, terminal outcomes, termination kinds, prompt/decision counts,
  and ordinals remain in the durable episode-row ledger; this summary does not
  replace them.

### `ValidationGateResult`

- `phase_complete` has exact type `bool`; integer 0/1 is rejected.
- `status` is exactly `None`, `INVALID_RUN`, `NO_TEST`, or
  `READY_FOR_TEST`.
- `qualifying_seed_ids` is an exact tuple, contains no duplicate, and is a
  subsequence of `(17, 29, 43)` in that fixed order. Every element is an exact
  integer, not Boolean.
- `observed_row_count` is the exact nonnegative integer `len(rows)` before any
  rejection; duplicates and unexpected rows are included.
- `hard_counts` is the phase aggregate after derived structural counts.
- `cell_results` is an exact tuple in canonical cell order.
- Coherence is mandatory:
  - clean partial: `phase_complete=False`, `status=None`, empty qualifying IDs,
    empty cells, and all applicable hard counts zero;
  - invalid partial or completed phase: `status=INVALID_RUN`, empty qualifying
    IDs and cells, and at least one hard/structural count nonzero;
  - valid completed phase: exactly 4,200 rows and 84 cells, zero hard counts,
    and status `NO_TEST` for 0/1 qualifying seeds or `READY_FOR_TEST` for 2/3.

### `TestClassificationResult`

- `phase_complete` and `test_opened` are exact Booleans.
- `classification` is exactly `None` or one of the fixed precedence values
  `INVALID_RUN`, `NO_TEST`, `RULE_PARITY_SIGNAL`,
  `CREDIT_SIGNAL_BELOW_RULE`, `NO_CREDIT_SIGNAL`.
- The three seed-ID fields are duplicate-free exact tuples and fixed-order
  subsequences of `(17, 29, 43)`. `validation_qualified_seed_ids` equals
  `validation_gate.qualifying_seed_ids`. For READY, the separately supplied,
  hash-verified `permitted_seed_ids` must equal that same tuple; for partial,
  INVALID, or NO_TEST validation it must be empty. `rule_parity_seed_ids` and
  `credit_signal_seed_ids` are subsets of the qualified tuple. Parity IDs are
  also credit IDs.
- `observed_row_count`, `hard_counts`, and `cell_results` have the same exact
  type/order rules as the validation result.
- Coherence is mandatory:
  - validation still partial, or READY but test unopened: classification
    `None`, phase incomplete, zero rows/cells, and no signal IDs;
  - valid `NO_TEST`: test unopened, phase incomplete, zero rows/cells, no
    signal IDs, and classification `NO_TEST`;
  - clean opened partial test: classification `None`, phase incomplete, no
    cell summaries or signal IDs, and no synthetic missing-row failure;
  - invalid at any applicable boundary: classification `INVALID_RUN`, empty
    cells/signal IDs, and a nonzero hard/structural count;
  - valid completed opened test: exactly 6,300 rows and 126 cells, zero hard
    counts, and one of the three post-test categories. The category must equal
    the deterministic precedence calculation below.

## Coordinate universe and deterministic ordering

The classifier must verify the supplied `Family3V2PilotConfig` is the frozen
Task 1 type and contains the already-approved exact values. It must not reload,
rewrite, or weaken the Task 1 loader.

Canonical orders are:

```text
methods:
  random_valid
  forecast_ablated_rule
  forecast_rule
  tabular_q_gamma0
  tabular_q_gamma1
  masked_ddqn_gamma0
  masked_ddqn_gamma1

evaluation seeds: 17, 29, 43
conditions: original, forecast_counterfactual
validation graphs: i8_f3v2_v5, i8_f3v2_v6
test graphs: i8_f3v2_v7, i8_f3v2_v8, i8_f3v2_v9
episode ordinals: 0..49
```

Rows are ordered lexicographically by the ranks of
`(method_id, evaluation_seed, graph_id, condition, episode_ordinal)`, with the
orders above. Cell summaries use the same order without episode ordinal.
Seed-proof tuples use `(17, 29, 43)` order. Do not sort strings, iterate sets,
or preserve accidental insertion order.

A clean partial tuple may be any strictly increasing subsequence of canonical
row order. It need not be a prefix because resume is missing-coordinate-only.
The classifier never sorts or repairs input. Noncanonical order is an integrity
failure before performance; each row whose canonical rank is not strictly
greater than its predecessor contributes one derived `unexpected_result_rows`
event (and an identical coordinate also contributes the duplicate count).

Expected complete coordinate sizes are:

| Phase | Graph-condition cells per method/seed | All method-seed cells | Rows |
|---|---:|---:|---:|
| validation | 4 | 7 x 3 x 4 = 84 | 84 x 50 = 4,200 |
| test | 6 | 7 x 3 x 6 = 126 | 126 x 50 = 6,300 |

For every row, recompute the approved environment root seed exactly as:

```text
u64be(first8(SHA256(canonical_json([
  "family3_v2_eval_coord_v0",
  "increment8_family3_v2_learner_pilot_v0",
  "environment",
  evaluation_seed,
  graph_id,
  episode_ordinal
]))))
```

Method and condition remain excluded. A mismatch adds one
`common_random_coordinate_mismatches` event. Equality across methods and the
original/counterfactual condition is therefore checked, not assumed.

## Phase audit before performance

The classifiers first perform a structural pass over the original tuple and
derive counts without repairing evidence:

- each occurrence after the first of an identical full row coordinate adds one
  `duplicate_result_rows`;
- every row outside the expected phase/method/seed/graph/condition/ordinal
  universe adds one `unexpected_result_rows`;
- each root-seed mismatch adds one
  `common_random_coordinate_mismatches`;
- each missing/multiple root marker adds one
  `semantic_conformance_failures`;
- only when `phase_complete=True`, every absent expected unique coordinate
  adds one `missing_expected_result_rows`.

These derived counts are added fieldwise to the supplied episode hard counts.
They are not substitutions for runtime audit counts. A duplicate unexpected
row may therefore contribute to both applicable fields. Any nonzero one of the
26 final counts forces `INVALID_RUN` before cell or performance aggregation.
`TestClassificationResult.hard_counts` is the fieldwise sum of the validated
validation-gate hard counts and the test-phase aggregate, so an earlier invalid
phase cannot disappear at final classification. The evaluator must not also
pre-count either reserved root marker as a semantic-conformance failure; that
one increment is classifier-owned, while independent semantic failures remain
ordinary supplied counts.

For a clean `phase_complete=False` input, missing coordinates do not increment
`missing_expected_result_rows`, `cell_results` stays empty, and no qualifying
or signal seed is calculated. This is the only valid partial-data behavior.
`None` means “no scientific verdict yet”; it is not a new result category and
must never be persisted as READY, NO_TEST, or a post-test signal.

For `phase_complete=True`, the complete coordinate audit is mandatory even if
`len(rows)` happens to equal 4,200/6,300. Duplicates cannot cover missing rows,
and unexpected rows cannot be discarded to manufacture completeness.

## Validation gate algorithm

After, and only after, a complete validation phase has exact coordinates and
all 26 counts are zero, build all 84 cell summaries. All three fixed seeds and
all seven methods are required. Tabular and random rows are completeness and
integrity evidence but have no gate effect.

For each seed in `(17, 29, 43)`, pool the same 200 coordinates from its four
validation cells. The seed qualifies exactly when all are true:

1. `masked_ddqn_gamma1` has `first_request_match_count == 50` in every cell
   (pooled 200), relative to the same-seed `forecast_rule` rows;
2. it has `forecast_rule_terminal_match_count == 50` in every cell (pooled
   200);
3. its pooled terminal-success count is strictly greater than the same seed's
   `masked_ddqn_gamma0` count; and
4. its pooled terminal-success count is strictly greater than the same seed's
   `forecast_ablated_rule` count.

The paired ForecastRule root must itself be one of `request_narrow` or
`request_broader`; otherwise the completed phase is structurally invalid.
Validation deliberately has **no** separate first-request-match-count
superiority comparison. All comparisons are exact integer `>` comparisons;
there is no tolerance, rate rounding, tie pass, or replacement seed.

Return qualifying IDs in fixed seed order. Two or three yield
`READY_FOR_TEST`; zero or one yield `NO_TEST`. A nonzero hard count always
yields `INVALID_RUN` first.

## Test classification algorithm and precedence

`classify_test_result` must validate `validation_gate` before reading test
performance:

1. A validation `INVALID_RUN` yields `INVALID_RUN`.
2. A clean partial validation permits no opened test, rows, or permit IDs and
   yields `classification=None`. Any attempted access is `INVALID_RUN` with
   `test_access_before_unlock` incremented.
3. A validation `NO_TEST` requires `test_opened=False`, empty
   `permitted_seed_ids`, and zero test rows; it yields `NO_TEST`. Any opened
   test or test row instead yields `INVALID_RUN`.
4. For `READY_FOR_TEST`, `permitted_seed_ids` must exactly equal the gate's
   duplicate-free, fixed-order `qualifying_seed_ids` and contain at least two
   seeds. A mismatch is an `artifact_hash_mismatches` integrity failure. Only
   those persisted IDs may contribute to a positive category; noneligible
   seeds can never replace them after test is seen.
5. READY does not itself open test. Before `test_opened=True`, test rows or a
   completed-test claim are invalid. A clean unopened READY state has no final
   classification.

Once test is opened, partial-data rules remain in force until
`phase_complete=True`. A completed opened test must have the exact 6,300 rows,
126 cells, and zero hard counts before performance is evaluated. Rows for all
three seeds and all seven methods remain mandatory even though only permit IDs
can support a positive signal. Tabular rows have no classification effect.

For each permitted seed, pool the same 300 coordinates from its six test
cells. Define:

- a **credit seed** as one whose `masked_ddqn_gamma1` pooled terminal-success
  count is strictly greater than both same-seed `masked_ddqn_gamma0` and
  `forecast_ablated_rule`, and whose first-request-match count to ForecastRule
  is also strictly greater than both controls;
- a **rule-parity seed** as a credit seed that additionally has root match to
  ForecastRule in all six cells/all 300 episodes and paired terminal-outcome
  match to ForecastRule in all six cells/all 300 episodes.

Return both proof tuples in permitted-seed order; parity IDs are a subset of
credit IDs. Apply the exact precedence:

1. any hard/structural failure -> `INVALID_RUN`;
2. valid validation without READY and no test -> `NO_TEST`;
3. at least two rule-parity IDs -> `RULE_PARITY_SIGNAL`;
4. otherwise at least two credit IDs -> `CREDIT_SIGNAL_BELOW_RULE`;
5. otherwise -> `NO_CREDIT_SIGNAL`.

There is no tolerance, post-test seed substitution, threshold override,
checkpoint selection, or use of Tabular results.

## Frozen dependencies and no-edit boundary

The approved plan is 30,311 bytes, SHA-256
`d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`.
The following named roots/files are frozen and read-only in Task 4:

- English spec: 38,149 bytes,
  `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`.
- Chinese spec: 35,818 bytes,
  `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`.
- Formal config: 8,377 bytes,
  `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`.
- Source baseline: 11,338 bytes,
  `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`.
- Certified suite hash:
  `98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
- Exact-preflight `run_config.json`: 3,090 bytes,
  `b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb`.
- Exact-preflight `final_verdict.json`: 329 bytes,
  `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`
  and verdict `CERTIFIED_PASS`.
- `src/pa_rl/ddqn.py`: 18,033 bytes,
  `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1`.
- `src/pa_rl/baselines.py`: 4,350 bytes,
  `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69`.
- The entire
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/`
  root, including its frozen baseline/suite manifests, all 20 certificates,
  and all 20 SQLite caches.

The immutable baseline binds the complete certified source fingerprint set,
not merely the thirteen convenient `family3_v2_*` modules:

```text
src/pa_rl/authorization.py
src/pa_rl/config.py
src/pa_rl/contracts.py
src/pa_rl/effects.py
src/pa_rl/execution.py
src/pa_rl/family3_v2_artifacts.py
src/pa_rl/family3_v2_audit.py
src/pa_rl/family3_v2_authority.py
src/pa_rl/family3_v2_contracts.py
src/pa_rl/family3_v2_environment.py
src/pa_rl/family3_v2_exact_reference.py
src/pa_rl/family3_v2_exact_solver.py
src/pa_rl/family3_v2_model.py
src/pa_rl/family3_v2_outcome.py
src/pa_rl/family3_v2_policy.py
src/pa_rl/family3_v2_preflight.py
src/pa_rl/family3_v2_rng.py
src/pa_rl/family3_v2_suite.py
src/pa_rl/scenarios.py
src/pa_rl/scope_matching.py
```

Task 3 lane outputs (`src/pa_rl/family3_v2_learning.py` and
`tests/test_family3_v2_learning.py`) are out of Task 4 scope. At dispatch, bind
their exact final hashes from the passing Task 3 controller closeout. Because
Task 3 review/fix work is still the explicit dispatch predecessor, no
intermediate Task 3 hash is promoted into this Task 4 authority. Task 4 must
not edit either file.

The formal learner result root and non-evidence smoke root were absent at
preflight and Task 4 must not create either.

## Focused RED requirements

Add only
`Family3V2PilotContractTests.test_validation_and_test_classification_contract`.
It must use synthetic rows—no environment, learner, checkpoint, filesystem
result root, or neural model.

The single method must cover at least:

- exact dataclass field order, immutability/slots, strict 26-key mapping,
  missing/extra keys, negative values, and Boolean-as-integer rejection;
- intrinsic row validation, both distinct root integrity markers, valid
  `deny`/`escalate` performance mismatch, nonfinite/wrong types, and exact
  terminal-kind domain;
- canonical method/seed/graph/condition/ordinal ordering, root-seed
  recomputation, duplicates, unexpected coordinates, wrong phase/method/seed/
  graph/condition, and completed-phase missing coordinates;
- clean partial validation and opened-test ledgers: no missing-row count, no
  cell summaries, no seed proof, and no scientific verdict;
- exact 4,200/6,300 row and 84/126 cell completion boundaries;
- one subtest for every one of the 26 hard counts. For the completion-only
  missing-row count, remove an expected row and set `phase_complete=True`;
  do not inject that count into an episode row;
- all three validation seeds evaluated, exact 2/3 rule, all-200 root/outcome
  parity, strict pooled-success superiority, no validation first-match-count
  superiority rule, fixed seed-ID persistence, and Tabular irrelevance;
- permit IDs equal validation-qualified IDs, rejection of a nonqualified seed
  substitution, test-unopened/test-once boundary, and all three fixed test
  seeds still present;
- test dual superiority (success and first-request match) for both positive
  categories, all-six-cell/all-300 parity for `RULE_PARITY_SIGNAL`, Tabular
  irrelevance, and the exact five-level precedence.

Run exactly once from `rl_personal_assistant`:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

Expected RED: only the absent Task 4 schema/classifier behavior (normally an
import error for the new names or the focused missing behavior). Syntax,
fixture, collection, import-path, Task 1 regression, or unrelated failures are
not an acceptable RED. Record exact command/output and stop on any other
failure; do not auto-retry or edit production.

## Minimal GREEN implementation

Implement only the dataclasses, exact validation, deterministic aggregation,
two pure classifiers, and small private helpers needed by those classifiers.
Do not add runner, checkpoint, ledger, environment, learner, certificate,
exact-reference, or filesystem logic. Do not import any policy/learner/exact
module to calculate the approved result; the classifiers consume only config
and synthetic/evaluator-produced rows.

Run the identical focused command exactly once for GREEN. Expected: one test
passes. If it fails, record the durable failure and stop without retry.

Then run the unchanged Task 1 regression exactly once:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

Expected: one test passes, proving the loader/verifier boundary did not drift.
Any failure stops Task 4. No full module, adjacent suite, compileall, smoke,
training, validation, test, or formal run is authorized by this task.

## Required Task 4 report

Write the SDD evidence report at
`.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-4-report.md`.
It is workflow evidence, not an additional production deliverable. Record:

- authority and pre-edit base hashes/sizes;
- exact changed-file list (the two authorized targets only);
- exact RED command, exit status, full relevant failure, and confirmation that
  it was the intended missing behavior only;
- exact GREEN and Task 1 regression commands, exit statuses, and test counts;
- the frozen dataclass field/signature contract, 26-key check, 4/6-cell and
  4,200/6,300-row checks, partial/completed behavior, root marker checks,
  qualifying/permitted seed checks, precedence checks, and Tabular
  nonparticipation;
- post-edit SHA-256 and byte size for both changed files;
- confirmation that no other test/run occurred, no frozen dependency changed,
  and neither real result root was created;
- any invalid attempt or unexpected failure verbatim, followed by a stop for
  controller review rather than a retry.

## Ambiguity disposition

There is no remaining scientific ambiguity in Task 4. The controller-resolved
5/15 typo is discarded provenance, and the interface choices above only make
the approved evidence and phase boundaries explicit. If implementation finds
that an approved threshold, comparison, seed eligibility rule, or root-action
state cannot be represented by this exact interface, mark **BLOCKING**, make no
scientific substitution, and return to the controller. Do not invent a
tolerance, new count, new verdict, seed replacement rule, or performance rule.
