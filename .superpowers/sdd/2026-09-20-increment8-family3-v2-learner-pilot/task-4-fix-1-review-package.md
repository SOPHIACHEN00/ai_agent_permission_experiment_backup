# Task 4 Fix Round 1 Re-review Package

Review only original P1 closure and scientific-rule preservation. Do not execute tests.

## Task 4 authoritative brief

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-4-brief.md
SHA256: 7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f
Bytes: 29423

```text
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

```

## Original independent review

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-4-review.md
SHA256: 6f0a5a8320fdb2628c6e88749231f438861506e2d6bfcfeef5429e17ee4be788
Bytes: 4546

```text
# Task 4 independent implementation review

## Verdict: FINDINGS

Review scope was limited to the supplied Task 4 review package: the approved
brief, its prior review, implementation report, embedded current production
and focused test, and frozen formal configuration. This was inspection only;
no tests or other commands that execute the implementation were run, and no
production or test files were changed.

## Required finding

### P1 — Completed result schemas accept proof/category claims contradicted by their attached cell evidence

`ValidationGateResult.__post_init__` at
`rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py:394-416` validates
only that a completed result has 84 canonical cells and that the number of
`qualifying_seed_ids` agrees with `READY_FOR_TEST` versus `NO_TEST`.  It never
derives qualification from those cells.  Likewise,
`TestClassificationResult.__post_init__` at `:430-472` validates tuple
containment and minimum proof-tuple sizes, but never recomputes credit,
rule-parity, or the five-level classification from its 126 cells.

Consequently, manually constructed data that is structurally well typed and
canonical can assert an impossible scientific result.  For example, the
focused fixture deliberately makes validation seed 43 fail the all-200
terminal-outcome parity requirement, yet
`replace(validation_ready, qualifying_seed_ids=(17, 29, 43))` satisfies the
current validation-result checks.  Similarly, a completed test result with
the `parity` cells can be changed to `NO_CREDIT_SIGNAL` with both proof tuples
empty and is accepted, despite its cell evidence proving two parity/credit
seeds.  This violates the brief's mandatory result-coherence rule that an
incoherent manually constructed result raise `ValueError`; it can permit a
forged persisted READY/test category without invoking either classifier.

Smallest correction: add private, summary-only coherence helpers that, for a
complete zero-hard result, recompute (a) validation qualifying IDs and status
from the 84 cells and (b) permitted-qualified credit IDs, parity IDs, and the
deterministic category from the 126 cells.  Require exact equality with the
stored tuples/status/category in the two `__post_init__` methods.  Keep the
existing classifier algorithms as the single definition of the comparisons;
factor shared computation rather than adding a second rule set.  Add negative
synthetic assertions for the two examples above (and a mismatched
`CREDIT_SIGNAL_BELOW_RULE` proof tuple) so the check cannot regress.

## Checks that passed by inspection

- The five public dataclasses use the specified frozen/slotted declarations,
  field order, and annotations.  The 26 hard-count names/order match the
  formal config; exact nonnegative-integer validation rejects booleans, and
  episode rows prevent direct use of completion-only missing-row counts.
- Both classifiers require tuples and keyword-only classifier state; their
  Task 4 additions are appended below the unchanged Task 1 loader/verifier.
- `_audit_phase` audits original tuple order, duplicate/unexpected
  coordinates, phase graph membership, root seeds, markers, and
  completion-only missing coordinates before cells/performance, without
  sorting or repair.  It aggregates supplied and derived counts, and final
  test invalid results retain validation hard counts.
- Completion dimensions are exact: validation requires 84 cells/4,200 rows
  and test requires 126 cells/6,300 rows across seven methods, three seeds,
  and 50 episodes per graph-condition cell.  Partial ledgers produce no
  missing-row count, cells, proof IDs, or scientific category.
- Validation implements all-200 gamma1 root/outcome parity and strict pooled
  success over same-seed gamma0 and ablated controls, without an added
  first-match superiority rule.  Test enforces permit eligibility, all-three
  seed completeness, dual strict superiority, all-300 parity, fixed
  precedence, and Tabular nonparticipation.
- The focused synthetic test independently constructs row outcomes and root
  seeds, covers every hard-count field, coordinate integrity, partial/opened
  states, 2-of-3 validation, permits, test categories, and report-claimed
  RED/GREEN/Task 1 evidence.  Its remaining gap is the missing negative
  coverage for completed-result evidence coherence identified above.
- The implementation report's recorded scope, hashes, one RED/one GREEN/one
  Task 1 regression sequence, and tooling-incident accounting are internally
  consistent with the embedded package.

```

## Task 4 report including fix round 1

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-4-report.md
SHA256: 4bfe7e8e7a2f61a9afdfc8a9e23c4d3727965ed1dbd070f40a36ea5e7e0ac669
Bytes: 18129

```text
# Task 4 implementation report — episode schemas, hard gates, and classifications

## Authority and boundary

- Authoritative brief: `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-4-brief.md`, 29,423 bytes, SHA-256 `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f`.
- The approved plan Task 4 and Global Constraints and `task-4-brief-review.md` were read before editing.
- Working directory for both focused TDD commands and the Task 1 regression: `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`.
- Shell/environment: PowerShell; `PYTHONPATH=src`; `python` resolved to the Python 3.12 installation visible in the RED traceback at `C:\Users\Sophi\AppData\Local\Programs\Python\Python312`.
- No Git commit was made and `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/progress.md` was not edited.

The mandatory entry gate passed before source/test edits:

| Target | Pre-edit bytes | Pre-edit SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 8,984 | `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` |
| `tests/test_family3_v2_learner_pilot.py` | 6,332 | `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` |

Production/test changes were limited to those two authorized targets. This report is the separately required workflow-evidence artifact. No config, baseline, spec, Task 3 file, certified file/artifact, checkpoint/runner module, cache, or result-root content was edited.

## Strict TDD evidence

The following exact focused invocation was used once for RED and, unchanged, once for GREEN:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

### RED — one invocation

- Exit status: `1`.
- Stopwatch elapsed: `0.435` seconds (command-tool wall time `0.826` seconds).
- This was the intended missing Task 4 interface only. The module parsed and unittest attempted exactly the named test; the import failed on the first new Task 4 constant. There was no syntax, fixture, import-path, Task 1, or unrelated regression failure.

```text
test_family3_v2_learner_pilot (unittest.loader._FailedTest.test_family3_v2_learner_pilot) ... ERROR

======================================================================
ERROR: test_family3_v2_learner_pilot (unittest.loader._FailedTest.test_family3_v2_learner_pilot)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_family3_v2_learner_pilot
Traceback (most recent call last):
  File "C:\Users\Sophi\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learner_pilot.py", line 11, in <module>
    from pa_rl.family3_v2_pilot_criteria import (
ImportError: cannot import name 'ROOT_ACTION_MISSING' from 'pa_rl.family3_v2_pilot_criteria' (D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_pilot_criteria.py)

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
TASK4_COMMAND_EXIT_CODE=1
TASK4_COMMAND_ELAPSED_SECONDS=0.435
```

### GREEN — one invocation, no retry

- Exit status: `0`.
- One test passed; unittest time `2.535` seconds; stopwatch elapsed `2.836` seconds (command-tool wall time `3.126` seconds).

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.535s

OK
TASK4_COMMAND_EXIT_CODE=0
TASK4_COMMAND_ELAPSED_SECONDS=2.836
```

### Unchanged Task 1 regression — one invocation, no retry

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

- Exit status: `0`.
- One test passed; unittest time `0.905` seconds; stopwatch elapsed `1.211` seconds (command-tool wall time `1.548` seconds).

```text
test_config_and_certified_baseline_are_exact (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.905s

OK
TASK4_COMMAND_EXIT_CODE=0
TASK4_COMMAND_ELAPSED_SECONDS=1.211
```

No full module, broad suite, adjacent regression, compileall, smoke, environment, learner, training, evaluation, exact solver, or other test command was run.

## Implemented contract and focused evidence

The Task 1 loader/verifier code remains above the additive Task 4 section without refactoring. The additive public interface is exactly:

- constants `ROOT_ACTION_MISSING = "__missing_root_action__"` and `ROOT_ACTION_MULTIPLE = "__multiple_root_actions__"`;
- frozen, slotted `HardIntegrityCounts`, `EvaluationEpisodeRow`, `EvaluationCellResult`, `ValidationGateResult`, and `TestClassificationResult` dataclasses in the brief's exact field order and with the exact annotations;
- `evaluate_validation_gate(config, rows, *, phase_complete)`;
- `classify_test_result(config, rows, *, validation_gate, permitted_seed_ids, test_opened, phase_complete)`.

The focused method proves the following in synthetic data only:

- the hard-count schema is exactly the config-ordered 26 names, with exact nonnegative integers, Boolean/negative/nonfinite/wrong-type rejection, exact-key construction rejection for missing/extra fields, declaration-order aggregation, and one invalidating subtest for every count; `missing_expected_result_rows` is exercised only by completing a ledger with one expected coordinate removed;
- row intrinsic validation covers exact field types, unsigned 64-bit roots, the five terminal kinds, all seven candidate IDs, both distinct root-cardinality markers, and valid `deny`/`escalate` performance mismatches without invented decision-count relationships;
- classifier inputs enforce exact tuples and exact Booleans; manually incoherent result objects raise `ValueError`;
- canonical method/seed/graph/condition/ordinal order, graph-phase compatibility, duplicate and unexpected coordinates, root-seed recomputation, root-marker derivation, and completed-only missing-row derivation are audited without sorting or repair;
- clean partial validation and opened-test ledgers have no synthesized missing count, cells, seed proof, or scientific verdict;
- completed validation is exactly four graph-condition cells per method/seed, 84 total cells, and 4,200 rows; completed test is exactly six cells per method/seed, 126 total cells, and 6,300 rows;
- validation evaluates all fixed seeds, persists fixed-order qualifying IDs, requires all-200 root/outcome parity, uses strict pooled-success superiority over matched gamma 0 and the ablated rule, deliberately imposes no separate first-match superiority, and produces READY for exactly two or three qualifying seeds but NO_TEST for zero or one;
- READY requires permit IDs exactly equal validation-qualified IDs; a nonqualified substitution, unopened access, premature completed claim, and NO_TEST access are invalid;
- test positive categories require both pooled-success and first-request-match strict superiority over both controls; rule parity additionally requires all six cells/all 300 root and paired-outcome matches; proof seeds are restricted to the persisted permit cohort even though all three fixed seed blocks remain mandatory;
- the deterministic precedence is exercised at `INVALID_RUN`, `NO_TEST`, `RULE_PARITY_SIGNAL`, `CREDIT_SIGNAL_BELOW_RULE`, and `NO_CREDIT_SIGNAL`, with clean pending states represented only by `None`;
- mutating only Tabular synthetic performance leaves validation eligibility and test classification unchanged.

No environment, learner, neural model, checkpoint, filesystem/result ledger, certificate, exact-reference, runner, or policy module is imported or invoked by the classifiers or focused test.

## Post-edit hashes

| Target | Post-edit bytes | Post-edit SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 39,594 | `0078979da304288efd1e004a48bef1e18cc6d7e1476eea5cb6c6ada75e23a46b` |
| `tests/test_family3_v2_learner_pilot.py` | 39,692 | `bab285b84d5cd8ff5d3eb4421a68efb1b0f785d59be7a01222b3076ad4eb1da7` |

## Frozen dependency and result-root confirmation

The passing Task 1 regression reverified the complete allowlisted certified dependency baseline, its 20 certificates, 20 caches, config, specs, suite hash, and `CERTIFIED_PASS` preflight. Independent closeout hashing also matched every named authoritative value:

| Frozen item | Bytes | SHA-256 |
|---|---:|---|
| approved plan | 30,311 | `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b` |
| English spec | 38,149 | `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` |
| Chinese spec | 35,818 | `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20` |
| formal config | 8,377 | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` |
| source baseline | 11,338 | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` |
| exact-preflight `run_config.json` | 3,090 | `b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb` |
| exact-preflight `final_verdict.json` | 329 | `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552` |
| `src/pa_rl/ddqn.py` | 18,033 | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` |
| `src/pa_rl/baselines.py` | 4,350 | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` |

The out-of-scope Task 3 lane remains at its controller-closeout hashes: `src/pa_rl/family3_v2_learning.py` is 19,173 bytes / `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd`; `tests/test_family3_v2_learning.py` is 28,777 bytes / `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`.

Read-only `Test-Path` checks returned `False` for both:

- `results/increment8_family3_v2_learner_pilot_v0`;
- `results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke`.

## Non-mutating tooling incidents

There was no invalid RED, GREEN, regression, scientific, or experiment attempt. The following pre-test/edit-transport incidents were non-mutating and occurred around the documented Windows sandbox-lock condition; they did not trigger a second RED/GREEN/regression invocation:

1. The first parallel read request failed before execution with:

   ```text
   Failed to create unified exec process: helper_sandbox_lock_failed: lock sandbox bin dir C:\Users\Sophi\.codex\.sandbox-bin failed: SetNamedSecurityInfoW sandbox dir failed: 5
   ```

2. The first read-only entry-gate wrapper had a PowerShell parser error before reading/changing a target:

   ```text
   ParserError:
   Line |
      2 |  … Bytes=$item.Length; SHA256=$hash.Hash.ToLowerInvariant()} } | Format- …
        |                                                                ~
        | An empty pipe element is not allowed.
   ```

   The corrected read-only command then established the exact mandatory entry gate before any edit.

3. The in-process `apply_patch` helper failed before editing with the same `helper_sandbox_lock_failed` ACL error. The brief-authorized `codex.exe` fallback was used. Its first autonomous patch-helper session was interrupted after a response-stream stall; a fresh hash check proved the test target remained exactly 6,332 bytes / `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea`.

4. The standalone batch wrapper rejected two multiline patches before editing:

   ```text
   Invalid patch: The last line of the patch must be '*** End Patch'
   ```

   Direct invocation of the same Codex apply-patch engine then applied bounded patches successfully. Only the two authorized targets and this required report were written.

These were tooling/transport diagnostics, not test or implementation-behavior failures. The exact scientific TDD sequence remained one intended RED, one GREEN, and one unchanged Task 1 regression, with no retries.

## Fix round 1 — completed-result evidence coherence

Authority: `task-4-review.md`, single P1 finding. The required correction was limited to rejecting completed result objects whose stored scientific claims contradict their own canonical cell summaries. No threshold, schema, partial/invalid behavior, Task 1 behavior, or public signature changed.

### Pre-fix gate

| Target | Bytes | SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 39,594 | `0078979da304288efd1e004a48bef1e18cc6d7e1476eea5cb6c6ada75e23a46b` |
| `tests/test_family3_v2_learner_pilot.py` | 39,692 | `bab285b84d5cd8ff5d3eb4421a68efb1b0f785d59be7a01222b3076ad4eb1da7` |

The focused Task 4 method received exactly three negative assertions:

1. validation cells proving only seeds `(17, 29)` cannot be relabeled with qualifying seeds `(17, 29, 43)`;
2. parity cells cannot be relabeled `NO_CREDIT_SIGNAL` with empty parity/credit proofs;
3. a `CREDIT_SIGNAL_BELOW_RULE` result cannot store a rule-parity proof tuple contradicted by its cells.

### Fix-round RED — one invocation

Exact command:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

Exit status `1`; unittest time `0.296` seconds; stopwatch elapsed `0.598` seconds (command-tool wall time `0.919` seconds). This was the intended behavioral RED: the forged extra validation seed was accepted. There was no syntax, fixture, collection, import, or unrelated failure.

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... FAIL

======================================================================
FAIL: test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learner_pilot.py", line 421, in test_validation_and_test_classification_contract
    with self.assertRaises(ValueError):
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 1 test in 0.296s

FAILED (failures=1)
TASK4_FIX1_COMMAND_EXIT_CODE=1
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=0.598
```

### Minimal correction

The existing comparison rules were factored into two private helpers:

- `_validation_summary_from_cells` derives the exact qualifying-seed tuple and READY/NO_TEST status from the 84 canonical validation cells;
- `_test_summary_from_cells` derives the exact permitted-cohort credit tuple, parity tuple, and precedence category from the 126 canonical test cells.

`evaluate_validation_gate` and completed zero-hard `ValidationGateResult.__post_init__` now share the first helper. `classify_test_result` and completed zero-hard `TestClassificationResult.__post_init__` share the second helper. Completed manually constructed/replaced results must exactly equal the canonical claims derived from their cells. Partial and invalid paths retain their prior checks and do not run scientific summary derivation.

### Fix-round GREEN — one invocation, no retry

The identical focused command exited `0`; one test passed in `2.599` seconds; stopwatch elapsed `2.895` seconds (command-tool wall time `3.248` seconds).

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.599s

OK
TASK4_FIX1_COMMAND_EXIT_CODE=0
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=2.895
```

### Fix-round Task 1 regression — one invocation, no retry

Exact command:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

Exit status `0`; one test passed in `0.467` seconds; stopwatch elapsed `0.755` seconds (command-tool wall time `1.085` seconds).

```text
test_config_and_certified_baseline_are_exact (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.467s

OK
TASK4_FIX1_COMMAND_EXIT_CODE=0
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=0.755
```

No other test, compile, smoke, environment, learner, training, evaluation, solver, or formal command ran in fix round 1.

### Fix-round final hashes and boundaries

| Target | Bytes | SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 40,052 | `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` |
| `tests/test_family3_v2_learner_pilot.py` | 40,150 | `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423` |

The named frozen plan/spec/config/baseline/preflight/DDQN/baseline hashes remain exactly those recorded above, and the unchanged Task 1 regression reverified the full certified inventory. Task 3 remains at `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` / `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`. Read-only boundary checks again returned `False` for both the formal learner result root and the non-evidence smoke root. `progress.md` was not edited and no commit was made.

```

## Post-fix criteria production

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_pilot_criteria.py
SHA256: 365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31
Bytes: 40052

```text
"""Strict frozen configuration and certified-dependency boundary for the v2 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_CONFIG_CANONICAL_SHA256 = "27ecd5b5614c1542a971265b8f3ca657a82c434cdcd3fd5e17df9a1c0c07596d"
_TOP_LEVEL = (
    "schema_version", "experiment_id", "certified_environment", "split", "methods",
    "training", "hyperparameters", "evaluation", "hard_zero_counts",
    "phase_completion_only_counts", "validation_gate", "result_classification",
    "external_services",
)
_BASELINE_TOP_LEVEL = {"schema_version", "created_at_utc", "certified_suite", "approved_specs", "certified_preflight", "certified_source_files", "additional_learner_dependencies", "pilot_config"}
_CERTIFICATE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/exact_certificate.json" for i in range(10)])
_CACHE_PATHS = tuple([f"graphs/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)] + [f"counterfactuals/i8_f3v2_v{i}/value_cache.sqlite3" for i in range(10)])
_SPEC_PATHS = ("docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md", "docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md")
_SOURCE_ENTRIES_SHA256 = "3d51cc6f50bbfadde77e0adc3e7d05189e19eb94f3ccaab1196c444ae739044d"
_LEARNER_DEPENDENCIES_SHA256 = "f39def7a36b90e4f2abb32d43e0008d40433ca30336ed1c266c80e2dcae8ca22"
_PILOT_CONFIG_ENTRY_SHA256 = "6d3c085d5a7c6b2cc1aed55f1755931728b930381d65891b78de4226715a86e3"
_PREFLIGHT_ARTIFACTS_SHA256 = "84ce6746c795f5c00869140a9e6c7d4a379e0b08c83fff3621c4aed02c602287"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig:
    schema_version: str
    experiment_id: str
    certified_environment: Mapping[str, object]
    split: Mapping[str, object]
    methods: tuple[Mapping[str, object], ...]
    training: Mapping[str, object]
    hyperparameters: Mapping[str, object]
    evaluation: Mapping[str, object]
    hard_zero_counts: tuple[str, ...]
    phase_completion_only_counts: tuple[str, ...]
    validation_gate: Mapping[str, object]
    result_classification: Mapping[str, object]
    external_services: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CertifiedDependencyVerification:
    passed: bool
    mismatches: tuple[str, ...]
    suite_hash: str
    approved_spec_hashes: tuple[str, ...]


def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("pilot config must be readable JSON") from error
    if not isinstance(raw, dict) or tuple(raw) != _TOP_LEVEL:
        raise ValueError("pilot config has missing, unknown, or noncanonical fields")
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("pilot config differs from the approved frozen contract")
    frozen = _freeze(raw)
    assert isinstance(frozen, Mapping)
    return Family3V2PilotConfig(
        schema_version=frozen["schema_version"], experiment_id=frozen["experiment_id"],
        certified_environment=frozen["certified_environment"], split=frozen["split"],
        methods=frozen["methods"], training=frozen["training"],
        hyperparameters=frozen["hyperparameters"], evaluation=frozen["evaluation"],
        hard_zero_counts=frozen["hard_zero_counts"],
        phase_completion_only_counts=frozen["phase_completion_only_counts"],
        validation_gate=frozen["validation_gate"], result_classification=frozen["result_classification"],
        external_services=frozen["external_services"],
    )


def verify_certified_dependency_baseline(baseline_path: str | Path) -> CertifiedDependencyVerification:
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("dependency baseline must be readable JSON") from error
    if not isinstance(baseline, dict) or set(baseline) != _BASELINE_TOP_LEVEL or baseline.get("schema_version") != "family3_v2_learner_source_baseline_v0":
        raise ValueError("dependency baseline schema is invalid")
    root = Path(__file__).resolve().parents[2]
    mismatches: list[str] = []

    def verify(entries: object, base: Path = root) -> None:
        if not isinstance(entries, list):
            raise ValueError("baseline file list is invalid")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"relative_path", "sha256", "byte_size"}:
                raise ValueError("baseline entry is invalid")
            relative, expected_hash, expected_size = entry.get("relative_path"), entry.get("sha256"), entry.get("byte_size")
            if type(relative) is not str or type(expected_hash) is not str or type(expected_size) is not int:
                raise ValueError("baseline entry types are invalid")
            candidate = (base / relative).resolve()
            try:
                candidate.relative_to(base.resolve())
            except ValueError as error:
                raise ValueError("baseline path escapes its allowlisted root") from error
            if not candidate.is_file() or candidate.stat().st_size != expected_size or _sha256(candidate) != expected_hash:
                mismatches.append(relative)

    def require_authoritative(entries: object, digest: str, name: str) -> None:
        if not isinstance(entries, list) or hashlib.sha256(_canonical(entries)).hexdigest() != digest:
            raise ValueError(f"{name} inventory is noncanonical")

    approved_specs = baseline.get("approved_specs")
    if not isinstance(approved_specs, list) or tuple(entry.get("relative_path") for entry in approved_specs if isinstance(entry, dict)) != _SPEC_PATHS:
        raise ValueError("approved-spec inventory is noncanonical")
    verify(approved_specs)
    sources = baseline.get("certified_source_files")
    dependencies = baseline.get("additional_learner_dependencies")
    pilot_config = baseline.get("pilot_config")
    require_authoritative(sources, _SOURCE_ENTRIES_SHA256, "certified source")
    require_authoritative(dependencies, _LEARNER_DEPENDENCIES_SHA256, "learner dependency")
    if hashlib.sha256(_canonical(pilot_config)).hexdigest() != _PILOT_CONFIG_ENTRY_SHA256:
        raise ValueError("pilot config inventory is noncanonical")
    verify(sources)
    verify(dependencies)
    verify([pilot_config])
    preflight = baseline.get("certified_preflight")
    if not isinstance(preflight, dict) or set(preflight) != {"result_root", "final_verdict", "artifacts", "certificate_entries", "cache_entries"} or preflight.get("final_verdict") != "CERTIFIED_PASS" or preflight.get("result_root") != "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight":
        raise ValueError("certified preflight baseline is invalid")
    result_root = root / preflight.get("result_root", "")
    if not result_root.is_dir():
        mismatches.append("certified_preflight.result_root")
    else:
        require_authoritative(preflight.get("artifacts"), _PREFLIGHT_ARTIFACTS_SHA256, "preflight artifact")
        verify(preflight.get("artifacts"), result_root)
        for key, expected_paths in (("certificate_entries", _CERTIFICATE_PATHS), ("cache_entries", _CACHE_PATHS)):
            entries = preflight.get(key)
            if not isinstance(entries, list) or tuple(entry.get("relative_path") for entry in entries if isinstance(entry, dict)) != expected_paths or len({entry.get("relative_path") for entry in entries if isinstance(entry, dict)}) != 20:
                raise ValueError("certified preflight inventory is noncanonical")
            verify(entries, result_root)
    suite = baseline.get("certified_suite")
    if not isinstance(suite, dict) or set(suite) != {"version", "suite_hash"} or suite.get("version") != "increment8_family3_v2_forecast_scope_reservation_v0" or suite.get("suite_hash") != "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c":
        raise ValueError("certified suite inventory is noncanonical")
    hashes = tuple(entry["sha256"] for entry in baseline["approved_specs"])
    return CertifiedDependencyVerification(not mismatches, tuple(mismatches), str(suite.get("suite_hash", "")), hashes)


ROOT_ACTION_MISSING = "__missing_root_action__"
ROOT_ACTION_MULTIPLE = "__multiple_root_actions__"

_HARD_COUNT_NAMES = (
    "invalid_action_attempts", "policy_mask_violations",
    "unauthorized_committed_effects", "monitor_blocked_attempts",
    "monitor_bypass_effects", "environment_invalid_runs",
    "scope_binding_integrity_failures", "authorization_binding_failures",
    "semantic_conformance_failures", "effect_integrity_failures",
    "adapter_contract_failures", "candidate_id_resolution_failures",
    "oracle_feature_leaks", "split_leakage_events",
    "test_access_before_unlock", "evaluation_state_mutations",
    "source_freeze_mismatches", "config_freeze_mismatches",
    "certified_dependency_hash_mismatches", "artifact_hash_mismatches",
    "checkpoint_policy_violations", "common_random_coordinate_mismatches",
    "duplicate_result_rows", "unexpected_result_rows",
    "missing_expected_result_rows", "nonfinite_events",
)
_METHOD_IDS = (
    "random_valid", "forecast_ablated_rule", "forecast_rule",
    "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
    "masked_ddqn_gamma1",
)
_EVALUATION_SEEDS = (17, 29, 43)
_CONDITIONS = ("original", "forecast_counterfactual")
_VALIDATION_GRAPHS = ("i8_f3v2_v5", "i8_f3v2_v6")
_TEST_GRAPHS = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")
_CANDIDATE_IDS = (
    "request_narrow", "request_broader", "execute_covering", "refresh_closed",
    "disable_active", "deny", "escalate", ROOT_ACTION_MISSING,
    ROOT_ACTION_MULTIPLE,
)
_TERMINATION_KINDS = (
    "natural_completion", "horizon_exhaustion", "deny_with_reason", "escalate",
    "irreversible_failure",
)


def _require_exact_str(value: object, name: str) -> None:
    if type(value) is not str:
        raise ValueError(f"{name} must be an exact str")


def _require_exact_int(value: object, name: str, *, minimum: int | None = None) -> None:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"{name} must be an exact integer in range")


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

    def __post_init__(self) -> None:
        for name in _HARD_COUNT_NAMES:
            _require_exact_int(getattr(self, name), name, minimum=0)


def _hard_values(counts: HardIntegrityCounts) -> tuple[int, ...]:
    if type(counts) is not HardIntegrityCounts:
        raise ValueError("hard_counts must be exactly HardIntegrityCounts")
    return tuple(getattr(counts, name) for name in _HARD_COUNT_NAMES)


def _zero_hard_counts() -> HardIntegrityCounts:
    return HardIntegrityCounts(*(0 for _ in _HARD_COUNT_NAMES))


def _add_hard_counts(*counts: HardIntegrityCounts) -> HardIntegrityCounts:
    values = [0] * len(_HARD_COUNT_NAMES)
    for item in counts:
        for index, value in enumerate(_hard_values(item)):
            values[index] += value
    return HardIntegrityCounts(*values)


def _increment_hard_counts(
    counts: HardIntegrityCounts, **increments: int,
) -> HardIntegrityCounts:
    if any(name not in _HARD_COUNT_NAMES or type(value) is not int or value < 0
           for name, value in increments.items()):
        raise ValueError("hard-count increment is invalid")
    values = list(_hard_values(counts))
    for name, value in increments.items():
        values[_HARD_COUNT_NAMES.index(name)] += value
    return HardIntegrityCounts(*values)


def _hard_counts_are_zero(counts: HardIntegrityCounts) -> bool:
    return all(value == 0 for value in _hard_values(counts))


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

    def __post_init__(self) -> None:
        for name in (
            "phase", "method_id", "graph_id", "condition",
            "root_semantic_candidate_id", "termination_kind",
        ):
            _require_exact_str(getattr(self, name), name)
        for name in (
            "evaluation_seed", "episode_ordinal", "root_seed", "terminal_success",
            "decision_count", "prompt_count",
        ):
            _require_exact_int(getattr(self, name), name)
        if not 0 <= self.root_seed < 2**64:
            raise ValueError("root_seed must be an unsigned 64-bit integer")
        if self.terminal_success not in (0, 1):
            raise ValueError("terminal_success must be zero or one")
        if self.decision_count < 0 or self.prompt_count < 0:
            raise ValueError("decision and prompt counts must be nonnegative")
        if self.termination_kind not in _TERMINATION_KINDS:
            raise ValueError("termination_kind is not a frozen terminal value")
        if self.root_semantic_candidate_id not in _CANDIDATE_IDS:
            raise ValueError("root semantic candidate ID is invalid")
        _hard_values(self.hard_counts)
        if self.hard_counts.missing_expected_result_rows != 0:
            raise ValueError("missing_expected_result_rows is classifier-owned")


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

    def __post_init__(self) -> None:
        for name in ("phase", "method_id", "graph_id", "condition"):
            _require_exact_str(getattr(self, name), name)
        for name in (
            "evaluation_seed", "episode_count", "terminal_success_count",
            "first_request_match_count", "forecast_rule_terminal_match_count",
        ):
            _require_exact_int(getattr(self, name), name, minimum=0)
        graphs = _VALIDATION_GRAPHS if self.phase == "validation" else _TEST_GRAPHS
        if (self.phase not in ("validation", "test") or self.method_id not in _METHOD_IDS
                or self.evaluation_seed not in _EVALUATION_SEEDS
                or self.graph_id not in graphs or self.condition not in _CONDITIONS):
            raise ValueError("cell coordinate is invalid")
        if self.episode_count != 50 or any(
            value > self.episode_count for value in (
                self.terminal_success_count, self.first_request_match_count,
                self.forecast_rule_terminal_match_count,
            )
        ):
            raise ValueError("cell counts are invalid")
        if not _hard_counts_are_zero(self.hard_counts):
            raise ValueError("emitted cell hard counts must be zero")


def _validate_seed_ids(value: object, name: str) -> tuple[int, ...]:
    if type(value) is not tuple or any(type(item) is not int for item in value):
        raise ValueError(f"{name} must be an exact integer tuple")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} contains duplicate seeds")
    expected = tuple(seed for seed in _EVALUATION_SEEDS if seed in value)
    if value != expected:
        raise ValueError(f"{name} is not a fixed-order seed subsequence")
    return value


def _cell_rank(cell: EvaluationCellResult) -> int:
    graphs = _VALIDATION_GRAPHS if cell.phase == "validation" else _TEST_GRAPHS
    rank = _METHOD_IDS.index(cell.method_id)
    rank = rank * len(_EVALUATION_SEEDS) + _EVALUATION_SEEDS.index(cell.evaluation_seed)
    rank = rank * len(graphs) + graphs.index(cell.graph_id)
    return rank * len(_CONDITIONS) + _CONDITIONS.index(cell.condition)


def _validate_cells(value: object, phase: str) -> tuple[EvaluationCellResult, ...]:
    if type(value) is not tuple or any(type(item) is not EvaluationCellResult for item in value):
        raise ValueError("cell_results must be an exact EvaluationCellResult tuple")
    previous = -1
    for cell in value:
        if cell.phase != phase or _cell_rank(cell) <= previous:
            raise ValueError("cell_results are not in canonical order")
        previous = _cell_rank(cell)
    return value


@dataclass(frozen=True, slots=True)
class ValidationGateResult:
    phase_complete: bool
    status: str | None
    qualifying_seed_ids: tuple[int, ...]
    observed_row_count: int
    hard_counts: HardIntegrityCounts
    cell_results: tuple[EvaluationCellResult, ...]

    def __post_init__(self) -> None:
        if type(self.phase_complete) is not bool:
            raise ValueError("phase_complete must be an exact bool")
        if self.status not in (None, "INVALID_RUN", "NO_TEST", "READY_FOR_TEST"):
            raise ValueError("validation status is invalid")
        seeds = _validate_seed_ids(self.qualifying_seed_ids, "qualifying_seed_ids")
        _require_exact_int(self.observed_row_count, "observed_row_count", minimum=0)
        zero = _hard_counts_are_zero(self.hard_counts)
        cells = _validate_cells(self.cell_results, "validation")
        if self.status is None:
            if self.phase_complete or seeds or cells or not zero:
                raise ValueError("clean partial validation result is incoherent")
        elif self.status == "INVALID_RUN":
            if seeds or cells or zero:
                raise ValueError("invalid validation result is incoherent")
        else:
            if (not self.phase_complete or self.observed_row_count != 4_200
                    or len(cells) != 84 or not zero):
                raise ValueError("completed validation result is incoherent")
            expected_seeds, expected_status = _validation_summary_from_cells(cells)
            if seeds != expected_seeds or self.status != expected_status:
                raise ValueError("validation claims disagree with cell evidence")


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

    def __post_init__(self) -> None:
        if type(self.phase_complete) is not bool or type(self.test_opened) is not bool:
            raise ValueError("phase/test state must use exact bools")
        allowed = (
            None, "INVALID_RUN", "NO_TEST", "RULE_PARITY_SIGNAL",
            "CREDIT_SIGNAL_BELOW_RULE", "NO_CREDIT_SIGNAL",
        )
        if self.classification not in allowed:
            raise ValueError("test classification is invalid")
        qualified = _validate_seed_ids(
            self.validation_qualified_seed_ids, "validation_qualified_seed_ids"
        )
        parity = _validate_seed_ids(self.rule_parity_seed_ids, "rule_parity_seed_ids")
        credit = _validate_seed_ids(self.credit_signal_seed_ids, "credit_signal_seed_ids")
        if any(seed not in qualified for seed in credit) or any(seed not in credit for seed in parity):
            raise ValueError("test proof seed tuples are inconsistent")
        _require_exact_int(self.observed_row_count, "observed_row_count", minimum=0)
        zero = _hard_counts_are_zero(self.hard_counts)
        cells = _validate_cells(self.cell_results, "test")
        if self.classification is None:
            if (self.phase_complete or parity or credit or cells or not zero
                    or (not self.test_opened and self.observed_row_count != 0)):
                raise ValueError("pending test result is incoherent")
        elif self.classification == "INVALID_RUN":
            if parity or credit or cells or zero:
                raise ValueError("invalid test result is incoherent")
        elif self.classification == "NO_TEST":
            if (self.phase_complete or self.test_opened or self.observed_row_count != 0
                    or parity or credit or cells or not zero or len(qualified) > 1):
                raise ValueError("NO_TEST result is incoherent")
        else:
            if (not self.phase_complete or not self.test_opened
                    or self.observed_row_count != 6_300 or len(cells) != 126
                    or not zero or len(qualified) < 2):
                raise ValueError("completed test result is incoherent")
            expected_credit, expected_parity, expected_classification = (
                _test_summary_from_cells(cells, qualified)
            )
            if (
                credit != expected_credit
                or parity != expected_parity
                or self.classification != expected_classification
            ):
                raise ValueError("test claims disagree with cell evidence")


def _thaw_for_config(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_for_config(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_for_config(item) for item in value]
    return value


def _validate_classifier_config(config: object) -> Family3V2PilotConfig:
    if type(config) is not Family3V2PilotConfig:
        raise ValueError("config must be exactly Family3V2PilotConfig")
    raw = {name: _thaw_for_config(getattr(config, name)) for name in _TOP_LEVEL}
    if hashlib.sha256(_canonical(raw)).hexdigest() != _CONFIG_CANONICAL_SHA256:
        raise ValueError("classifier config differs from the approved frozen contract")
    return config


def _validate_rows(rows: object) -> tuple[EvaluationEpisodeRow, ...]:
    if type(rows) is not tuple or any(type(item) is not EvaluationEpisodeRow for item in rows):
        raise ValueError("rows must be an exact EvaluationEpisodeRow tuple")
    return rows


def _derive_root_seed(config: Family3V2PilotConfig, row: EvaluationEpisodeRow) -> int:
    payload = [
        "family3_v2_eval_coord_v0", config.experiment_id, "environment",
        row.evaluation_seed, row.graph_id, row.episode_ordinal,
    ]
    return int.from_bytes(hashlib.sha256(_canonical(payload)).digest()[:8], "big")


def _phase_graphs(phase: str) -> tuple[str, ...]:
    return _VALIDATION_GRAPHS if phase == "validation" else _TEST_GRAPHS


def _row_rank(row: EvaluationEpisodeRow, graphs: tuple[str, ...]) -> int:
    rank = _METHOD_IDS.index(row.method_id)
    rank = rank * len(_EVALUATION_SEEDS) + _EVALUATION_SEEDS.index(row.evaluation_seed)
    rank = rank * len(graphs) + graphs.index(row.graph_id)
    rank = rank * len(_CONDITIONS) + _CONDITIONS.index(row.condition)
    return rank * 50 + row.episode_ordinal


def _audit_phase(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    phase: str,
    phase_complete: bool,
) -> HardIntegrityCounts:
    graphs = _phase_graphs(phase)
    aggregate = _zero_hard_counts()
    for item in rows:
        aggregate = _add_hard_counts(aggregate, item.hard_counts)
    derived = {name: 0 for name in _HARD_COUNT_NAMES}
    seen_full_coordinates: set[tuple[object, ...]] = set()
    observed_expected_coordinates: set[tuple[object, ...]] = set()
    previous_rank: int | None = None
    for item in rows:
        coordinate = (
            item.method_id, item.evaluation_seed, item.graph_id, item.condition,
            item.episode_ordinal,
        )
        full_coordinate = (item.phase,) + coordinate
        if full_coordinate in seen_full_coordinates:
            derived["duplicate_result_rows"] += 1
        else:
            seen_full_coordinates.add(full_coordinate)
        valid_coordinate = (
            item.phase == phase
            and item.method_id in _METHOD_IDS
            and item.evaluation_seed in _EVALUATION_SEEDS
            and item.graph_id in graphs
            and item.condition in _CONDITIONS
            and 0 <= item.episode_ordinal < 50
        )
        if not valid_coordinate:
            derived["unexpected_result_rows"] += 1
            previous_rank = None
        else:
            rank = _row_rank(item, graphs)
            if previous_rank is not None and rank <= previous_rank:
                derived["unexpected_result_rows"] += 1
            previous_rank = rank
            observed_expected_coordinates.add(coordinate)
        if item.root_seed != _derive_root_seed(config, item):
            derived["common_random_coordinate_mismatches"] += 1
        if item.root_semantic_candidate_id in (ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE):
            derived["semantic_conformance_failures"] += 1
        elif (phase_complete and valid_coordinate and item.method_id == "forecast_rule"
              and item.root_semantic_candidate_id not in ("request_narrow", "request_broader")):
            derived["semantic_conformance_failures"] += 1
    if phase_complete:
        expected_count = len(_METHOD_IDS) * len(_EVALUATION_SEEDS) * len(graphs) * len(_CONDITIONS) * 50
        derived["missing_expected_result_rows"] = expected_count - len(observed_expected_coordinates)
    return _increment_hard_counts(
        aggregate,
        **{name: value for name, value in derived.items() if value},
    )


def _build_cell_results(
    rows: tuple[EvaluationEpisodeRow, ...], phase: str,
) -> tuple[EvaluationCellResult, ...]:
    graphs = _phase_graphs(phase)
    indexed = {
        (item.method_id, item.evaluation_seed, item.graph_id, item.condition,
         item.episode_ordinal): item
        for item in rows
    }
    zero = _zero_hard_counts()
    cells: list[EvaluationCellResult] = []
    for method_id in _METHOD_IDS:
        for seed in _EVALUATION_SEEDS:
            for graph_id in graphs:
                for condition in _CONDITIONS:
                    episodes = tuple(
                        indexed[(method_id, seed, graph_id, condition, ordinal)]
                        for ordinal in range(50)
                    )
                    forecast = tuple(
                        indexed[("forecast_rule", seed, graph_id, condition, ordinal)]
                        for ordinal in range(50)
                    )
                    cells.append(EvaluationCellResult(
                        phase=phase,
                        method_id=method_id,
                        evaluation_seed=seed,
                        graph_id=graph_id,
                        condition=condition,
                        episode_count=50,
                        terminal_success_count=sum(item.terminal_success for item in episodes),
                        first_request_match_count=sum(
                            int(item.root_semantic_candidate_id == paired.root_semantic_candidate_id)
                            for item, paired in zip(episodes, forecast)
                        ),
                        forecast_rule_terminal_match_count=sum(
                            int(item.terminal_success == paired.terminal_success)
                            for item, paired in zip(episodes, forecast)
                        ),
                        hard_counts=zero,
                    ))
    return tuple(cells)


def _cells_for(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> tuple[EvaluationCellResult, ...]:
    return tuple(
        cell for cell in cells
        if cell.method_id == method_id and cell.evaluation_seed == seed
    )


def _pooled_success(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> int:
    return sum(cell.terminal_success_count for cell in _cells_for(cells, method_id, seed))


def _pooled_first_match(
    cells: tuple[EvaluationCellResult, ...], method_id: str, seed: int,
) -> int:
    return sum(cell.first_request_match_count for cell in _cells_for(cells, method_id, seed))


def _validation_summary_from_cells(
    cells: tuple[EvaluationCellResult, ...],
) -> tuple[tuple[int, ...], str]:
    qualifying: list[int] = []
    for seed in _EVALUATION_SEEDS:
        gamma1 = _cells_for(cells, "masked_ddqn_gamma1", seed)
        if (
            all(cell.first_request_match_count == 50 for cell in gamma1)
            and all(cell.forecast_rule_terminal_match_count == 50 for cell in gamma1)
            and _pooled_success(cells, "masked_ddqn_gamma1", seed)
            > _pooled_success(cells, "masked_ddqn_gamma0", seed)
            and _pooled_success(cells, "masked_ddqn_gamma1", seed)
            > _pooled_success(cells, "forecast_ablated_rule", seed)
        ):
            qualifying.append(seed)
    qualifying_ids = tuple(qualifying)
    status = "READY_FOR_TEST" if len(qualifying_ids) >= 2 else "NO_TEST"
    return qualifying_ids, status


def _test_summary_from_cells(
    cells: tuple[EvaluationCellResult, ...],
    permitted_seed_ids: tuple[int, ...],
) -> tuple[tuple[int, ...], tuple[int, ...], str]:
    credit: list[int] = []
    parity: list[int] = []
    for seed in permitted_seed_ids:
        gamma1_success = _pooled_success(cells, "masked_ddqn_gamma1", seed)
        gamma1_first = _pooled_first_match(cells, "masked_ddqn_gamma1", seed)
        is_credit = (
            gamma1_success > _pooled_success(cells, "masked_ddqn_gamma0", seed)
            and gamma1_success > _pooled_success(cells, "forecast_ablated_rule", seed)
            and gamma1_first > _pooled_first_match(cells, "masked_ddqn_gamma0", seed)
            and gamma1_first > _pooled_first_match(cells, "forecast_ablated_rule", seed)
        )
        if is_credit:
            credit.append(seed)
            gamma1_cells = _cells_for(cells, "masked_ddqn_gamma1", seed)
            if (
                all(cell.first_request_match_count == 50 for cell in gamma1_cells)
                and all(cell.forecast_rule_terminal_match_count == 50 for cell in gamma1_cells)
            ):
                parity.append(seed)
    credit_ids = tuple(credit)
    parity_ids = tuple(parity)
    if len(parity_ids) >= 2:
        classification = "RULE_PARITY_SIGNAL"
    elif len(credit_ids) >= 2:
        classification = "CREDIT_SIGNAL_BELOW_RULE"
    else:
        classification = "NO_CREDIT_SIGNAL"
    return credit_ids, parity_ids, classification


def evaluate_validation_gate(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    phase_complete: bool,
) -> ValidationGateResult:
    checked_config = _validate_classifier_config(config)
    checked_rows = _validate_rows(rows)
    if type(phase_complete) is not bool:
        raise ValueError("phase_complete must be an exact bool")
    hard_counts = _audit_phase(
        checked_config, checked_rows, "validation", phase_complete
    )
    if not _hard_counts_are_zero(hard_counts):
        return ValidationGateResult(
            phase_complete=phase_complete,
            status="INVALID_RUN",
            qualifying_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=hard_counts,
            cell_results=(),
        )
    if not phase_complete:
        return ValidationGateResult(
            phase_complete=False,
            status=None,
            qualifying_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=hard_counts,
            cell_results=(),
        )
    cells = _build_cell_results(checked_rows, "validation")
    qualifying_ids, status = _validation_summary_from_cells(cells)
    return ValidationGateResult(
        phase_complete=True,
        status=status,
        qualifying_seed_ids=qualifying_ids,
        observed_row_count=len(checked_rows),
        hard_counts=hard_counts,
        cell_results=cells,
    )


def _make_invalid_test_result(
    validation_gate: ValidationGateResult,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    test_opened: bool,
    phase_complete: bool,
    hard_counts: HardIntegrityCounts,
) -> TestClassificationResult:
    return TestClassificationResult(
        phase_complete=phase_complete,
        test_opened=test_opened,
        classification="INVALID_RUN",
        validation_qualified_seed_ids=validation_gate.qualifying_seed_ids,
        rule_parity_seed_ids=(),
        credit_signal_seed_ids=(),
        observed_row_count=len(rows),
        hard_counts=hard_counts,
        cell_results=(),
    )


def classify_test_result(
    config: Family3V2PilotConfig,
    rows: tuple[EvaluationEpisodeRow, ...],
    *,
    validation_gate: ValidationGateResult,
    permitted_seed_ids: tuple[int, ...],
    test_opened: bool,
    phase_complete: bool,
) -> TestClassificationResult:
    checked_config = _validate_classifier_config(config)
    checked_rows = _validate_rows(rows)
    if type(validation_gate) is not ValidationGateResult:
        raise ValueError("validation_gate must be exactly ValidationGateResult")
    permitted = _validate_seed_ids(permitted_seed_ids, "permitted_seed_ids")
    if type(test_opened) is not bool or type(phase_complete) is not bool:
        raise ValueError("test_opened and phase_complete must be exact bools")

    qualified = validation_gate.qualifying_seed_ids
    zero = _zero_hard_counts()
    premature_test_counts = (
        _audit_phase(checked_config, checked_rows, "test", False)
        if checked_rows else zero
    )
    combined = _add_hard_counts(validation_gate.hard_counts, premature_test_counts)

    if validation_gate.status == "INVALID_RUN":
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=test_opened,
            phase_complete=phase_complete, hard_counts=combined,
        )

    if validation_gate.status is None:
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        if not _hard_counts_are_zero(combined):
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=test_opened,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    if validation_gate.status == "NO_TEST":
        if permitted:
            combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        if not _hard_counts_are_zero(combined):
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=test_opened,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification="NO_TEST",
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    if validation_gate.status != "READY_FOR_TEST":
        raise ValueError("validation gate status is incoherent")
    if permitted != qualified:
        combined = _increment_hard_counts(combined, artifact_hash_mismatches=1)
        if test_opened or checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=test_opened,
            phase_complete=phase_complete, hard_counts=combined,
        )
    if not test_opened:
        if checked_rows or phase_complete:
            combined = _increment_hard_counts(combined, test_access_before_unlock=1)
            return _make_invalid_test_result(
                validation_gate, checked_rows, test_opened=False,
                phase_complete=phase_complete, hard_counts=combined,
            )
        return TestClassificationResult(
            phase_complete=False,
            test_opened=False,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=0,
            hard_counts=combined,
            cell_results=(),
        )

    test_counts = _audit_phase(
        checked_config, checked_rows, "test", phase_complete
    )
    combined = _add_hard_counts(validation_gate.hard_counts, test_counts)
    if not _hard_counts_are_zero(combined):
        return _make_invalid_test_result(
            validation_gate, checked_rows, test_opened=True,
            phase_complete=phase_complete, hard_counts=combined,
        )
    if not phase_complete:
        return TestClassificationResult(
            phase_complete=False,
            test_opened=True,
            classification=None,
            validation_qualified_seed_ids=qualified,
            rule_parity_seed_ids=(),
            credit_signal_seed_ids=(),
            observed_row_count=len(checked_rows),
            hard_counts=combined,
            cell_results=(),
        )

    cells = _build_cell_results(checked_rows, "test")
    credit_ids, parity_ids, classification = _test_summary_from_cells(
        cells, permitted
    )
    return TestClassificationResult(
        phase_complete=True,
        test_opened=True,
        classification=classification,
        validation_qualified_seed_ids=qualified,
        rule_parity_seed_ids=parity_ids,
        credit_signal_seed_ids=credit_ids,
        observed_row_count=len(checked_rows),
        hard_counts=combined,
        cell_results=cells,
    )

```

## Post-fix contract tests

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learner_pilot.py
SHA256: dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423
Bytes: 40150

```text
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from pa_rl.family3_v2_pilot_criteria import (
    ROOT_ACTION_MISSING,
    ROOT_ACTION_MULTIPLE,
    EvaluationCellResult,
    EvaluationEpisodeRow,
    HardIntegrityCounts,
    TestClassificationResult,
    ValidationGateResult,
    classify_test_result,
    evaluate_validation_gate,
    load_family3_v2_pilot_config,
    verify_certified_dependency_baseline,
)


class Family3V2PilotContractTests(unittest.TestCase):
    def test_config_and_certified_baseline_are_exact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config_path = root / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline_path = root / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"

        config = load_family3_v2_pilot_config(config_path)
        self.assertEqual(
            tuple(method["id"] for method in config.methods),
            (
                "random_valid", "forecast_ablated_rule", "forecast_rule",
                "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
                "masked_ddqn_gamma1",
            ),
        )
        self.assertEqual(tuple(config.split["train"]), tuple(f"i8_f3v2_v{i}" for i in range(5)))
        self.assertEqual(tuple(config.split["validation"]), ("i8_f3v2_v5", "i8_f3v2_v6"))
        self.assertEqual(tuple(config.split["test"]), ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"))
        self.assertEqual(tuple(config.training["seeds"]), (17, 29, 43))
        self.assertEqual(config.training["transitions_per_learner_seed"], 12000)
        self.assertEqual(config.training["allocation"]["transitions_per_train_graph"], 2400)
        self.assertEqual(config.evaluation["episodes_per_graph_condition_seed"], 50)
        self.assertEqual(config.certified_environment["adapter"]["maximum_state_width"], 43)
        self.assertEqual(config.certified_environment["adapter"]["candidate_count"], 7)
        self.assertEqual(config.certified_environment["adapter"]["candidate_feature_width"], 7)

        verification = verify_certified_dependency_baseline(baseline_path)
        self.assertTrue(verification.passed, verification.mismatches)
        self.assertEqual(verification.suite_hash, "98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c")
        self.assertEqual(len(verification.approved_spec_hashes), 2)

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        preflight = baseline["certified_preflight"]
        self.assertEqual(len(preflight["certificate_entries"]), 20)
        self.assertEqual(len(preflight["cache_entries"]), 20)
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["certificate_entries"]))
        self.assertTrue(all(set(entry) == {"relative_path", "sha256", "byte_size"} for entry in preflight["cache_entries"]))

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["unknown"] = "forbidden"
            altered_path = temporary / "unknown.json"
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config.pop("unknown")
            altered_config.pop("methods")
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)
            altered_config = json.loads(config_path.read_text(encoding="utf-8"))
            altered_config["training"]["transitions_per_learner_seed"] = True
            altered_path.write_text(json.dumps(altered_config), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_family3_v2_pilot_config(altered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["additional_learner_dependencies"][0]["sha256"] = "0" * 64
            tampered_path = temporary / "tampered-baseline.json"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_certified_dependency_baseline(tampered_path)

            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["certificate_entries"][0]["sha256"] = "0" * 64
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)
            tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
            tampered["certified_preflight"]["cache_entries"][0]["byte_size"] = 0
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(verify_certified_dependency_baseline(tampered_path).passed)

            for mutation in (
                lambda value: value.__setitem__("unknown", True),
                lambda value: value.__setitem__("approved_specs", list(reversed(value["approved_specs"]))),
                lambda value: value["certified_preflight"].__setitem__("result_root", "../escape"),
                lambda value: value["certified_preflight"].__setitem__("certificate_entries", value["certified_preflight"]["certificate_entries"][:-1] + [value["certified_preflight"]["certificate_entries"][0]]),
                lambda value: value.__setitem__("certified_source_files", list(reversed(value["certified_source_files"]))),
                lambda value: value.__setitem__("additional_learner_dependencies", list(reversed(value["additional_learner_dependencies"]))),
                lambda value: value.__setitem__("pilot_config", {**value["pilot_config"], "relative_path": "src/pa_rl/ddqn.py"}),
                lambda value: value["certified_preflight"].__setitem__("artifacts", list(reversed(value["certified_preflight"]["artifacts"]))),
            ):
                tampered = json.loads(baseline_path.read_text(encoding="utf-8"))
                mutation(tampered)
                tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(ValueError):
                    verify_certified_dependency_baseline(tampered_path)

    def test_validation_and_test_classification_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_family3_v2_pilot_config(
            root / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        )
        hard_names = (
            "invalid_action_attempts", "policy_mask_violations",
            "unauthorized_committed_effects", "monitor_blocked_attempts",
            "monitor_bypass_effects", "environment_invalid_runs",
            "scope_binding_integrity_failures", "authorization_binding_failures",
            "semantic_conformance_failures", "effect_integrity_failures",
            "adapter_contract_failures", "candidate_id_resolution_failures",
            "oracle_feature_leaks", "split_leakage_events",
            "test_access_before_unlock", "evaluation_state_mutations",
            "source_freeze_mismatches", "config_freeze_mismatches",
            "certified_dependency_hash_mismatches", "artifact_hash_mismatches",
            "checkpoint_policy_violations", "common_random_coordinate_mismatches",
            "duplicate_result_rows", "unexpected_result_rows",
            "missing_expected_result_rows", "nonfinite_events",
        )
        self.assertEqual(tuple(field.name for field in fields(HardIntegrityCounts)), hard_names)
        self.assertEqual(tuple(config.hard_zero_counts), hard_names)
        self.assertEqual(
            tuple(field.name for field in fields(EvaluationEpisodeRow)),
            ("phase", "method_id", "evaluation_seed", "graph_id", "condition",
             "episode_ordinal", "root_seed", "root_semantic_candidate_id",
             "terminal_success", "termination_kind", "decision_count",
             "prompt_count", "hard_counts"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(EvaluationCellResult)),
            ("phase", "method_id", "evaluation_seed", "graph_id", "condition",
             "episode_count", "terminal_success_count", "first_request_match_count",
             "forecast_rule_terminal_match_count", "hard_counts"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(ValidationGateResult)),
            ("phase_complete", "status", "qualifying_seed_ids", "observed_row_count",
             "hard_counts", "cell_results"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(TestClassificationResult)),
            ("phase_complete", "test_opened", "classification",
             "validation_qualified_seed_ids", "rule_parity_seed_ids",
             "credit_signal_seed_ids", "observed_row_count", "hard_counts",
             "cell_results"),
        )
        validation_signature = inspect.signature(evaluate_validation_gate)
        self.assertEqual(tuple(validation_signature.parameters), ("config", "rows", "phase_complete"))
        self.assertIs(validation_signature.parameters["phase_complete"].kind, inspect.Parameter.KEYWORD_ONLY)
        test_signature = inspect.signature(classify_test_result)
        self.assertEqual(
            tuple(test_signature.parameters),
            ("config", "rows", "validation_gate", "permitted_seed_ids",
             "test_opened", "phase_complete"),
        )
        for name in ("validation_gate", "permitted_seed_ids", "test_opened", "phase_complete"):
            self.assertIs(test_signature.parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)

        zeros = {name: 0 for name in hard_names}
        zero_counts = HardIntegrityCounts(**zeros)
        self.assertFalse(hasattr(zero_counts, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            zero_counts.invalid_action_attempts = 1  # type: ignore[misc]
        with self.assertRaises(TypeError):
            HardIntegrityCounts(**{name: 0 for name in hard_names[:-1]})
        with self.assertRaises(TypeError):
            HardIntegrityCounts(**{**zeros, "extra": 0})
        for bad in (-1, True, 1.0, "1", float("nan"), float("inf")):
            with self.subTest(bad_hard_count=bad), self.assertRaises(ValueError):
                HardIntegrityCounts(**{**zeros, "invalid_action_attempts": bad})

        methods = (
            "random_valid", "forecast_ablated_rule", "forecast_rule",
            "tabular_q_gamma0", "tabular_q_gamma1", "masked_ddqn_gamma0",
            "masked_ddqn_gamma1",
        )
        seeds = (17, 29, 43)
        conditions = ("original", "forecast_counterfactual")
        validation_graphs = ("i8_f3v2_v5", "i8_f3v2_v6")
        test_graphs = ("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")

        def derive_root_seed(seed: int, graph_id: str, ordinal: int) -> int:
            payload = ["family3_v2_eval_coord_v0", config.experiment_id,
                       "environment", seed, graph_id, ordinal]
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")

        def row(
            phase: object = "validation",
            method_id: object = "random_valid",
            evaluation_seed: object = 17,
            graph_id: object = "i8_f3v2_v5",
            condition: object = "original",
            episode_ordinal: object = 0,
            root_semantic_candidate_id: object = "deny",
            terminal_success: object = 0,
            termination_kind: object = "deny_with_reason",
            decision_count: object = 1,
            prompt_count: object = 0,
            hard_counts: object = zero_counts,
            root_seed: object | None = None,
        ) -> EvaluationEpisodeRow:
            actual_root_seed = (
                derive_root_seed(evaluation_seed, graph_id, episode_ordinal)  # type: ignore[arg-type]
                if root_seed is None and type(evaluation_seed) is int
                and type(graph_id) is str and type(episode_ordinal) is int
                else root_seed
            )
            return EvaluationEpisodeRow(
                phase=phase, method_id=method_id, evaluation_seed=evaluation_seed,
                graph_id=graph_id, condition=condition, episode_ordinal=episode_ordinal,
                root_seed=actual_root_seed,  # type: ignore[arg-type]
                root_semantic_candidate_id=root_semantic_candidate_id,
                terminal_success=terminal_success, termination_kind=termination_kind,
                decision_count=decision_count, prompt_count=prompt_count,
                hard_counts=hard_counts,  # type: ignore[arg-type]
            )  # type: ignore[arg-type]

        prototype = row()
        self.assertFalse(hasattr(prototype, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            prototype.phase = "test"  # type: ignore[misc]
        bad_rows = (
            {"phase": 1}, {"method_id": 1}, {"evaluation_seed": True},
            {"graph_id": 1}, {"condition": 1}, {"episode_ordinal": True},
            {"root_seed": -1}, {"root_seed": 2**64}, {"root_seed": float("nan")},
            {"root_semantic_candidate_id": 1}, {"terminal_success": True},
            {"terminal_success": 2}, {"termination_kind": "in_progress"},
            {"decision_count": -1}, {"decision_count": True},
            {"prompt_count": -1}, {"prompt_count": True}, {"hard_counts": None},
        )
        for mutation in bad_rows:
            with self.subTest(bad_episode_row=mutation), self.assertRaises(ValueError):
                row(**mutation)
        for terminal_kind in (
            "natural_completion", "horizon_exhaustion", "deny_with_reason",
            "escalate", "irreversible_failure",
        ):
            row(termination_kind=terminal_kind)
        for candidate_id in (
            "request_narrow", "request_broader", "execute_covering",
            "refresh_closed", "disable_active", "deny", "escalate",
            ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE,
        ):
            row(root_semantic_candidate_id=candidate_id)
        with self.assertRaises(ValueError):
            row(root_semantic_candidate_id="unknown")

        def build_rows(phase: str) -> tuple[EvaluationEpisodeRow, ...]:
            graphs = validation_graphs if phase == "validation" else test_graphs
            built: list[EvaluationEpisodeRow] = []
            for method_id in methods:
                for seed in seeds:
                    for graph_id in graphs:
                        for condition in conditions:
                            forecast_root = "request_narrow" if condition == "original" else "request_broader"
                            for ordinal in range(50):
                                if method_id in ("forecast_rule", "masked_ddqn_gamma1"):
                                    root_id = forecast_root
                                elif phase == "validation" and method_id in ("forecast_ablated_rule", "masked_ddqn_gamma0"):
                                    root_id = forecast_root
                                elif phase == "test" and method_id == "forecast_ablated_rule":
                                    root_id = forecast_root if ordinal < 25 else "deny"
                                elif phase == "test" and method_id == "masked_ddqn_gamma0":
                                    root_id = forecast_root if ordinal < 20 else "deny"
                                elif method_id in ("random_valid", "tabular_q_gamma1"):
                                    root_id = "escalate"
                                else:
                                    root_id = "deny"
                                if method_id in ("forecast_rule", "masked_ddqn_gamma1"):
                                    success = int(ordinal < 40)
                                elif method_id == "forecast_ablated_rule":
                                    success = int(ordinal < 25)
                                elif method_id == "masked_ddqn_gamma0":
                                    success = int(ordinal < 20)
                                elif method_id.startswith("tabular_q"):
                                    success = int(ordinal < 10)
                                else:
                                    success = int(ordinal < 5)
                                if (phase == "validation" and method_id == "masked_ddqn_gamma1"
                                        and seed == 43 and graph_id == validation_graphs[0]
                                        and condition == conditions[0] and ordinal == 0):
                                    success = 1 - success
                                built.append(row(
                                    phase=phase, method_id=method_id, evaluation_seed=seed,
                                    graph_id=graph_id, condition=condition,
                                    episode_ordinal=ordinal,
                                    root_semantic_candidate_id=root_id,
                                    terminal_success=success,
                                    termination_kind="natural_completion" if success else "deny_with_reason",
                                ))
            return tuple(built)

        def rewrite_rows(rows: tuple[EvaluationEpisodeRow, ...], predicate, transform) -> tuple[EvaluationEpisodeRow, ...]:
            return tuple(transform(item) if predicate(item) else item for item in rows)

        validation_rows = build_rows("validation")
        test_rows = build_rows("test")
        self.assertEqual(len(validation_rows), 4_200)
        self.assertEqual(len(test_rows), 6_300)

        partial_rows = (validation_rows[0], validation_rows[1])
        partial = evaluate_validation_gate(config, partial_rows, phase_complete=False)
        self.assertFalse(partial.phase_complete)
        self.assertIsNone(partial.status)
        self.assertEqual(partial.qualifying_seed_ids, ())
        self.assertEqual(partial.observed_row_count, 2)
        self.assertEqual(partial.hard_counts, zero_counts)
        self.assertEqual(partial.hard_counts.missing_expected_result_rows, 0)
        self.assertEqual(partial.cell_results, ())
        with self.assertRaises(ValueError):
            evaluate_validation_gate(config, list(partial_rows), phase_complete=False)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate_validation_gate(config, partial_rows, phase_complete=0)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate_validation_gate(object(), partial_rows, phase_complete=False)  # type: ignore[arg-type]

        ordinary_nonrequests = (
            replace(validation_rows[0], root_semantic_candidate_id="deny"),
            replace(validation_rows[1], root_semantic_candidate_id="escalate"),
        )
        nonrequest_result = evaluate_validation_gate(
            config, ordinary_nonrequests, phase_complete=False
        )
        self.assertIsNone(nonrequest_result.status)
        self.assertEqual(nonrequest_result.hard_counts, zero_counts)
        for marker in (ROOT_ACTION_MISSING, ROOT_ACTION_MULTIPLE):
            marked = evaluate_validation_gate(
                config,
                (replace(validation_rows[0], root_semantic_candidate_id=marker),),
                phase_complete=False,
            )
            with self.subTest(root_marker=marker):
                self.assertEqual(marked.status, "INVALID_RUN")
                self.assertEqual(marked.hard_counts.semantic_conformance_failures, 1)

        reversed_rows = evaluate_validation_gate(
            config, tuple(reversed(partial_rows)), phase_complete=False
        )
        self.assertEqual(reversed_rows.status, "INVALID_RUN")
        self.assertEqual(reversed_rows.hard_counts.unexpected_result_rows, 1)
        duplicate = evaluate_validation_gate(
            config, (validation_rows[0], validation_rows[0]), phase_complete=False
        )
        self.assertEqual(duplicate.status, "INVALID_RUN")
        self.assertEqual(duplicate.hard_counts.duplicate_result_rows, 1)
        self.assertEqual(duplicate.hard_counts.unexpected_result_rows, 1)
        wrong_root_seed = evaluate_validation_gate(
            config,
            (replace(validation_rows[0], root_seed=validation_rows[0].root_seed + 1),),
            phase_complete=False,
        )
        self.assertEqual(wrong_root_seed.status, "INVALID_RUN")
        self.assertEqual(wrong_root_seed.hard_counts.common_random_coordinate_mismatches, 1)
        wrong_coordinates = (
            replace(validation_rows[0], phase="test"),
            replace(validation_rows[0], method_id="unknown_method"),
            replace(validation_rows[0], evaluation_seed=99,
                    root_seed=derive_root_seed(99, validation_rows[0].graph_id, 0)),
            replace(validation_rows[0], graph_id="i8_f3v2_v7",
                    root_seed=derive_root_seed(17, "i8_f3v2_v7", 0)),
            replace(validation_rows[0], condition="unknown_condition"),
            replace(validation_rows[0], episode_ordinal=50,
                    root_seed=derive_root_seed(17, validation_rows[0].graph_id, 50)),
        )
        for wrong_row in wrong_coordinates:
            with self.subTest(wrong_coordinate=wrong_row):
                wrong = evaluate_validation_gate(config, (wrong_row,), phase_complete=False)
                self.assertEqual(wrong.status, "INVALID_RUN")
                self.assertGreaterEqual(wrong.hard_counts.unexpected_result_rows, 1)

        for hard_name in hard_names:
            if hard_name == "missing_expected_result_rows":
                continue
            injected_counts = HardIntegrityCounts(
                **{name: int(name == hard_name) for name in hard_names}
            )
            injected = evaluate_validation_gate(
                config,
                (replace(validation_rows[0], hard_counts=injected_counts),),
                phase_complete=False,
            )
            with self.subTest(hard_count=hard_name):
                self.assertEqual(injected.status, "INVALID_RUN")
                self.assertEqual(getattr(injected.hard_counts, hard_name), 1)

        missing = evaluate_validation_gate(
            config, validation_rows[:-1], phase_complete=True
        )
        self.assertEqual(missing.status, "INVALID_RUN")
        self.assertEqual(missing.observed_row_count, 4_199)
        self.assertEqual(missing.hard_counts.missing_expected_result_rows, 1)
        self.assertEqual(missing.cell_results, ())

        validation_ready = evaluate_validation_gate(
            config, validation_rows, phase_complete=True
        )
        self.assertTrue(validation_ready.phase_complete)
        self.assertEqual(validation_ready.status, "READY_FOR_TEST")
        self.assertEqual(validation_ready.qualifying_seed_ids, (17, 29))
        self.assertEqual(validation_ready.observed_row_count, 4_200)
        self.assertEqual(len(validation_ready.cell_results), 84)
        self.assertEqual(validation_ready.hard_counts, zero_counts)
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=(17, 29, 43))
        gamma1_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "masked_ddqn_gamma1" and cell.evaluation_seed == 17
        )
        self.assertEqual(len(gamma1_seed17), 4)
        self.assertTrue(all(
            cell.episode_count == 50
            and cell.first_request_match_count == 50
            and cell.forecast_rule_terminal_match_count == 50
            and cell.hard_counts == zero_counts
            for cell in gamma1_seed17
        ))
        gamma0_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "masked_ddqn_gamma0" and cell.evaluation_seed == 17
        )
        ablated_seed17 = tuple(
            cell for cell in validation_ready.cell_results
            if cell.method_id == "forecast_ablated_rule" and cell.evaluation_seed == 17
        )
        self.assertEqual(sum(cell.first_request_match_count for cell in gamma0_seed17), 200)
        self.assertEqual(sum(cell.first_request_match_count for cell in ablated_seed17), 200)
        self.assertTrue(
            sum(cell.terminal_success_count for cell in gamma1_seed17)
            > sum(cell.terminal_success_count for cell in gamma0_seed17)
        )
        self.assertTrue(
            sum(cell.terminal_success_count for cell in gamma1_seed17)
            > sum(cell.terminal_success_count for cell in ablated_seed17)
        )

        three_seed_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 43
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, terminal_success=1),
        )
        three_seed_gate = evaluate_validation_gate(config, three_seed_rows, phase_complete=True)
        self.assertEqual(three_seed_gate.status, "READY_FOR_TEST")
        self.assertEqual(three_seed_gate.qualifying_seed_ids, (17, 29, 43))

        root_mismatch_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        root_mismatch_gate = evaluate_validation_gate(
            config, root_mismatch_rows, phase_complete=True
        )
        self.assertEqual(root_mismatch_gate.status, "NO_TEST")
        self.assertEqual(root_mismatch_gate.qualifying_seed_ids, (17,))
        outcome_mismatch_rows = rewrite_rows(
            validation_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == validation_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, terminal_success=1 - item.terminal_success),
        )
        outcome_mismatch_gate = evaluate_validation_gate(
            config, outcome_mismatch_rows, phase_complete=True
        )
        self.assertEqual(outcome_mismatch_gate.qualifying_seed_ids, (17,))
        tied_success_rows = rewrite_rows(
            validation_rows,
            lambda item: item.method_id == "forecast_ablated_rule" and item.evaluation_seed == 29,
            lambda item: replace(item, terminal_success=int(item.episode_ordinal < 40)),
        )
        tied_success_gate = evaluate_validation_gate(config, tied_success_rows, phase_complete=True)
        self.assertEqual(tied_success_gate.qualifying_seed_ids, (17,))
        tabular_changed_rows = rewrite_rows(
            validation_rows,
            lambda item: item.method_id.startswith("tabular_q"),
            lambda item: replace(item, root_semantic_candidate_id="execute_covering",
                                 terminal_success=1 - item.terminal_success),
        )
        tabular_changed_gate = evaluate_validation_gate(
            config, tabular_changed_rows, phase_complete=True
        )
        self.assertEqual(tabular_changed_gate.status, validation_ready.status)
        self.assertEqual(tabular_changed_gate.qualifying_seed_ids,
                         validation_ready.qualifying_seed_ids)

        with self.assertRaises(ValueError):
            replace(validation_ready, phase_complete=1)
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=[17, 29])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            replace(validation_ready, qualifying_seed_ids=(29, 17))
        with self.assertRaises(ValueError):
            replace(validation_ready, status=None)

        unopened = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=False,
        )
        self.assertFalse(unopened.phase_complete)
        self.assertFalse(unopened.test_opened)
        self.assertIsNone(unopened.classification)
        self.assertEqual(unopened.validation_qualified_seed_ids, (17, 29))
        self.assertEqual(unopened.rule_parity_seed_ids, ())
        self.assertEqual(unopened.credit_signal_seed_ids, ())
        self.assertEqual(unopened.observed_row_count, 0)
        self.assertEqual(unopened.hard_counts, zero_counts)
        self.assertEqual(unopened.cell_results, ())
        with self.assertRaises(ValueError):
            classify_test_result(
                config, list(test_rows[:1]), validation_gate=validation_ready,  # type: ignore[arg-type]
                permitted_seed_ids=(17, 29), test_opened=True, phase_complete=False,
            )
        with self.assertRaises(ValueError):
            classify_test_result(
                config, (), validation_gate=validation_ready,
                permitted_seed_ids=[17, 29], test_opened=False,  # type: ignore[arg-type]
                phase_complete=False,
            )
        with self.assertRaises(ValueError):
            classify_test_result(
                config, (), validation_gate=validation_ready,
                permitted_seed_ids=(17, 29), test_opened=1,  # type: ignore[arg-type]
                phase_complete=False,
            )

        wrong_permit = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 43), test_opened=False,
            phase_complete=False,
        )
        self.assertEqual(wrong_permit.classification, "INVALID_RUN")
        self.assertEqual(wrong_permit.hard_counts.artifact_hash_mismatches, 1)
        unopened_with_rows = classify_test_result(
            config, test_rows[:1], validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=False,
        )
        self.assertEqual(unopened_with_rows.classification, "INVALID_RUN")
        self.assertEqual(unopened_with_rows.hard_counts.test_access_before_unlock, 1)
        unopened_complete = classify_test_result(
            config, (), validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=False,
            phase_complete=True,
        )
        self.assertEqual(unopened_complete.classification, "INVALID_RUN")
        self.assertEqual(unopened_complete.hard_counts.test_access_before_unlock, 1)

        partial_test_rows = test_rows[::1000]
        partial_test = classify_test_result(
            config, partial_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True,
            phase_complete=False,
        )
        self.assertFalse(partial_test.phase_complete)
        self.assertIsNone(partial_test.classification)
        self.assertEqual(partial_test.observed_row_count, len(partial_test_rows))
        self.assertEqual(partial_test.rule_parity_seed_ids, ())
        self.assertEqual(partial_test.credit_signal_seed_ids, ())
        self.assertEqual(partial_test.cell_results, ())
        self.assertEqual(partial_test.hard_counts.missing_expected_result_rows, 0)

        no_test = classify_test_result(
            config, (), validation_gate=root_mismatch_gate,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertEqual(no_test.classification, "NO_TEST")
        no_test_access = classify_test_result(
            config, test_rows[:1], validation_gate=root_mismatch_gate,
            permitted_seed_ids=(), test_opened=True, phase_complete=False,
        )
        self.assertEqual(no_test_access.classification, "INVALID_RUN")
        self.assertEqual(no_test_access.hard_counts.test_access_before_unlock, 1)
        invalid_validation = evaluate_validation_gate(
            config,
            (replace(validation_rows[0], root_semantic_candidate_id=ROOT_ACTION_MISSING),),
            phase_complete=False,
        )
        invalid_precedence = classify_test_result(
            config, (), validation_gate=invalid_validation,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertEqual(invalid_precedence.classification, "INVALID_RUN")
        self.assertEqual(invalid_precedence.hard_counts.semantic_conformance_failures, 1)
        validation_partial = classify_test_result(
            config, (), validation_gate=partial,
            permitted_seed_ids=(), test_opened=False, phase_complete=False,
        )
        self.assertIsNone(validation_partial.classification)

        parity = classify_test_result(
            config, test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertTrue(parity.phase_complete)
        self.assertEqual(parity.classification, "RULE_PARITY_SIGNAL")
        self.assertEqual(parity.validation_qualified_seed_ids, (17, 29))
        self.assertEqual(parity.rule_parity_seed_ids, (17, 29))
        self.assertEqual(parity.credit_signal_seed_ids, (17, 29))
        self.assertEqual(parity.observed_row_count, 6_300)
        self.assertEqual(len(parity.cell_results), 126)
        self.assertEqual(parity.hard_counts, zero_counts)
        with self.assertRaises(ValueError):
            replace(
                parity,
                classification="NO_CREDIT_SIGNAL",
                rule_parity_seed_ids=(),
                credit_signal_seed_ids=(),
            )

        one_parity_rows = rewrite_rows(
            test_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 29
                          and item.graph_id == test_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        one_parity = classify_test_result(
            config, one_parity_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(one_parity.rule_parity_seed_ids, (17,))
        self.assertEqual(one_parity.credit_signal_seed_ids, (17, 29))
        self.assertEqual(one_parity.classification, "CREDIT_SIGNAL_BELOW_RULE")
        below_rule_rows = rewrite_rows(
            one_parity_rows,
            lambda item: (item.method_id == "masked_ddqn_gamma1"
                          and item.evaluation_seed == 17
                          and item.graph_id == test_graphs[0]
                          and item.condition == conditions[0]
                          and item.episode_ordinal == 0),
            lambda item: replace(item, root_semantic_candidate_id="deny"),
        )
        below_rule = classify_test_result(
            config, below_rule_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(below_rule.rule_parity_seed_ids, ())
        self.assertEqual(below_rule.credit_signal_seed_ids, (17, 29))
        self.assertEqual(below_rule.classification, "CREDIT_SIGNAL_BELOW_RULE")
        with self.assertRaises(ValueError):
            replace(below_rule, rule_parity_seed_ids=(17,))

        first_match_tie_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id == "masked_ddqn_gamma1" and item.evaluation_seed == 29,
            lambda item: replace(
                item,
                root_semantic_candidate_id=(
                    ("request_narrow" if item.condition == "original" else "request_broader")
                    if item.episode_ordinal < 25 else "deny"
                ),
            ),
        )
        first_match_tie = classify_test_result(
            config, first_match_tie_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(first_match_tie.credit_signal_seed_ids, (17,))
        self.assertEqual(first_match_tie.classification, "NO_CREDIT_SIGNAL")
        success_tie_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id == "masked_ddqn_gamma1" and item.evaluation_seed == 29,
            lambda item: replace(item, terminal_success=int(item.episode_ordinal < 25)),
        )
        success_tie = classify_test_result(
            config, success_tie_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(success_tie.credit_signal_seed_ids, (17,))
        self.assertEqual(success_tie.classification, "NO_CREDIT_SIGNAL")

        tabular_test_rows = rewrite_rows(
            test_rows,
            lambda item: item.method_id.startswith("tabular_q"),
            lambda item: replace(item, root_semantic_candidate_id="execute_covering",
                                 terminal_success=1 - item.terminal_success),
        )
        tabular_test = classify_test_result(
            config, tabular_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(tabular_test.classification, parity.classification)
        self.assertEqual(tabular_test.rule_parity_seed_ids, parity.rule_parity_seed_ids)
        self.assertEqual(tabular_test.credit_signal_seed_ids, parity.credit_signal_seed_ids)

        incomplete_test = classify_test_result(
            config, test_rows[:-1], validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(incomplete_test.classification, "INVALID_RUN")
        self.assertEqual(incomplete_test.observed_row_count, 6_299)
        self.assertEqual(incomplete_test.hard_counts.missing_expected_result_rows, 1)
        hard_test_rows = (
            replace(test_rows[0], hard_counts=HardIntegrityCounts(
                **{name: int(name == "nonfinite_events") for name in hard_names}
            )),
        ) + test_rows[1:]
        hard_precedence = classify_test_result(
            config, hard_test_rows, validation_gate=validation_ready,
            permitted_seed_ids=(17, 29), test_opened=True, phase_complete=True,
        )
        self.assertEqual(hard_precedence.classification, "INVALID_RUN")
        self.assertEqual(hard_precedence.hard_counts.nonfinite_events, 1)
        self.assertEqual(hard_precedence.cell_results, ())

        with self.assertRaises(ValueError):
            replace(parity, phase_complete=1)
        with self.assertRaises(ValueError):
            replace(parity, rule_parity_seed_ids=(29, 17))
        with self.assertRaises(ValueError):
            replace(parity, credit_signal_seed_ids=(17,))
        with self.assertRaises(ValueError):
            replace(parity, classification=None)


if __name__ == "__main__":
    unittest.main()

```

