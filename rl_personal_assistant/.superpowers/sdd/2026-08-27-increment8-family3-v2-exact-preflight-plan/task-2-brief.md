### Task 2: Add typed contracts, literal suite, and exact branch RNG

**Files:**

- Create: `src/pa_rl/family3_v2_contracts.py`
- Create: `src/pa_rl/family3_v2_suite.py`
- Create: `src/pa_rl/family3_v2_rng.py`
- Create: `tests/test_family3_v2_suite_rng.py`

**Interfaces:**

- `build_family3_v2_suite() -> Family3V2Suite`
- `Family3V2KernelInput.from_graph(graph) -> Family3V2KernelInput`
- `Family3V2KernelInput.forecast_counterfactual() -> Family3V2KernelInput`
- `draw_family3_v2_branch_residue(root_seed, branch_coupling_uid,
  episode_ordinal) -> Family3V2BranchResidue`
- `continuation_from_residue(forecast_exact_probability,
  forecast_broader_probability, residue) -> ContinuationModeV2`

- [ ] **Step 1: Write one focused failing suite/RNG test module**

The test must include these assertions, with all ten rows checked literally:

```python
class Family3V2SuiteRngTests(unittest.TestCase):
    def test_literal_suite_and_counterfactual(self) -> None:
        suite = build_family3_v2_suite()
        self.assertEqual(tuple(g.graph_id for g in suite.graphs), tuple(f"i8_f3v2_v{i}" for i in range(10)))
        self.assertEqual([g.split for g in suite.graphs], ["train"] * 5 + ["validation"] * 2 + ["test"] * 3)
        self.assertEqual([g.exposure_budget for g in suite.graphs], [9, 12, 16, 12, 30, 15, 24, 24, 21, 30])
        self.assertEqual([g.target for g in suite.graphs], [3, 4, 4, 5, 5, 6, 6, 7, 7, 6])
        for graph in suite.graphs:
            other = Family3V2KernelInput.from_graph(graph).forecast_counterfactual()
            self.assertEqual(other.branch_coupling_uid, graph.branch_coupling_uid)
            self.assertEqual(other.forecast_exact_probability, 1 - graph.forecast_exact_probability)

    def test_rejection_sampling_is_exactly_mod_five(self) -> None:
        self.assertEqual(residue_from_uint64s(iter((2**64 - 1, 14))), 4)
        for residue in range(5):
            self.assertEqual(
                continuation_from_residue(Fraction(4, 5), Fraction(1, 5), residue),
                ContinuationModeV2.EXACT if residue < 4 else ContinuationModeV2.BROADER,
            )
            self.assertEqual(
                continuation_from_residue(Fraction(1, 5), Fraction(4, 5), residue),
                ContinuationModeV2.EXACT if residue < 1 else ContinuationModeV2.BROADER,
            )
```

In the first method, also construct one `literal_projection` tuple containing
all fields shown in Step 3—graph ID, split, carrier literal, purpose literal,
forecast numerator, `e`, `d`, target, exposure, and horizon—and compare it in
one `assertEqual` against the complete ten-row `_ROWS` tuple. The subset checks
above are diagnostic duplicates, not a substitute for the literal assertion.

- [ ] **Step 2: Run the focused test and witness the missing-module RED**

Run:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_suite_rng -v
```

Expected: import failure for `pa_rl.family3_v2_contracts` or
`pa_rl.family3_v2_suite`. Any other failure cause stops the task.

- [ ] **Step 3: Implement the immutable contracts and literal suite**

Define the exact profile constants and enums from the spec. The candidate order
must be:

```python
FAMILY3_V2_CANDIDATE_ORDER = (
    CandidateRoleV2.REQUEST_NARROW,
    CandidateRoleV2.REQUEST_BROADER,
    CandidateRoleV2.EXECUTE_COVERING,
    CandidateRoleV2.REFRESH_CLOSED,
    CandidateRoleV2.DISABLE_ACTIVE,
    CandidateRoleV2.DENY,
    CandidateRoleV2.ESCALATE,
)
```

Copy the five carrier literals from `increment8_suite.py`; do not import its
private `_CARRIERS`. Freeze the ten rows as:

```python
_ROWS = (
    ("i8_f3v2_v0", "train", "c0_calendar", "agenda_summary", 4, 2, 1, 3, 9, 8),
    ("i8_f3v2_v1", "train", "c1_mail_archive", "status_notice", 1, 3, 1, 4, 12, 8),
    ("i8_f3v2_v2", "train", "c2_mail_send", "inbox_cleanup", 4, 3, 2, 4, 16, 8),
    ("i8_f3v2_v3", "train", "c3_report", "weekly_report", 1, 4, 2, 5, 12, 8),
    ("i8_f3v2_v4", "train", "c4_records", "approved_update", 4, 4, 3, 5, 30, 8),
    ("i8_f3v2_v5", "validation", "c0_calendar", "inbox_cleanup", 1, 5, 3, 6, 15, 9),
    ("i8_f3v2_v6", "validation", "c1_mail_archive", "weekly_report", 4, 5, 4, 6, 24, 9),
    ("i8_f3v2_v7", "test", "c2_mail_send", "approved_update", 1, 6, 4, 7, 24, 10),
    ("i8_f3v2_v8", "test", "c3_report", "agenda_summary", 4, 6, 5, 7, 21, 10),
    ("i8_f3v2_v9", "test", "c4_records", "status_notice", 1, 5, 3, 6, 30, 9),
)
```

The fifth field is the exact-forecast numerator over denominator five, followed
by `e`, `d`, target, exposure budget, and horizon. `Family3V2GraphSpec` must
recompute `n`, `b`, target, exposure, horizon, profile strings, scope relation,
and the exact 21-field row allowlist in `__post_init__`; it rejects values that
merely happen to hash.

- [ ] **Step 4: Implement unbiased residue generation**

Use the spec's JSON-list payload and big-endian first eight digest bytes. The
testable rejection core is:

```python
def residue_from_uint64s(values: Iterator[int]) -> int:
    limit = 2**64 - (2**64 % 5)
    for value in values:
        if type(value) is not int or not 0 <= value < 2**64:
            raise ValueError("draw must be an exact uint64")
        if value < limit:
            return value % 5
    raise ValueError("draw source ended before an accepted residue")
```

`draw_family3_v2_branch_residue` repeatedly hashes the frozen payload with
counter `j`, returns the accepted residue, attempt number, accepted uint64, and
payload SHA-256, and rejects Boolean/out-of-range seeds.

- [ ] **Step 5: Run focused GREEN and checkpoint**

Run the Step 2 command. Expected: all methods PASS. Record the exact method
count, elapsed time, three new source hashes, test hash, and Task 3 next action
in `docs/CONTINUATION_CHECKPOINT.md` and the result-root checkpoint.

