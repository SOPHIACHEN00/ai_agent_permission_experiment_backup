### Task 1: Freeze dependencies and implement the strict config boundary

**Files:**

- Create: `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`
- Create: `configs/evaluation/family3_v2_learner_pilot_v0.json`
- Create: `src/pa_rl/family3_v2_pilot_criteria.py`
- Create: `tests/test_family3_v2_learner_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig: ...

def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig: ...

def verify_certified_dependency_baseline(
    baseline_path: str | Path,
) -> CertifiedDependencyVerification: ...
```

- [ ] **Step 1: Verify the approved inputs before any production edit**

From the project root, read and verify both approved spec hashes, exact-preflight
`run_config.json`, `final_verdict.json`, the suite hash, source fingerprints,
certificate/cache paths, `ddqn.py`, and `baselines.py`.

Expected: final verdict is `CERTIFIED_PASS`; every recorded hash matches; the
formal learner result root is absent. Any mismatch stops the plan.

- [ ] **Step 2: Create the immutable source-baseline JSON**

Write the complete allowlisted paths, hashes, sizes, suite hash, approved spec
hashes, schema version, and timestamp. Do not use a broad glob as the runtime
freeze authority. Update the continuation checkpoint to point to its hash.

- [ ] **Step 3: Copy the approved normative JSON into the formal config**

The config must be substantively identical to the shared JSON block in both
specs. Record its canonical file hash in the immutable baseline and run
boundary after serialization; do not embed a self-referential hash in the
config. Descriptive additions must not change methods, seeds, budgets, RNG
formulas, gates, or recovery rules.

- [ ] **Step 4: Write the config/baseline tests and witness RED**

Add one focused method covering exact seven-method order, 5/2/3 split,
17/29/43 seeds, 12,000/2,400/50 budgets, 43/7/7 dimensions, suite hash, spec
hashes, strict unknown/missing-field rejection, and a tampered dependency hash.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

Expected RED: missing `pa_rl.family3_v2_pilot_criteria`, and nothing else.

- [ ] **Step 5: Implement the minimal frozen dataclasses/loader/verifier**

Use exact types, reject `bool` for integer fields, reject noncanonical method or
graph order, and compare paths/hashes without rewriting the baseline.

- [ ] **Step 6: Run the same focused command once for GREEN**

Expected: one method passes. Record source/config/baseline hashes. If it fails,
stop; do not begin Task 2.
