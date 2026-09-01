### Task 3: Replaceable held-out gate

**Files:**
- Create: `configs/evaluation/heldout_context_v0.json`
- Create: `src/pa_rl/heldout_criteria.py`
- Modify: `tests/test_increment7_pilot.py`

**Interfaces:**
- Produces:
  - `SafetyCounts(mask_violations, unauthorized_effects, monitor_blocked_attempts)`
  - `HeldoutCriteria`
  - `HeldoutGate(profile, best_simple_method, checks, classification)`
  - `load_heldout_criteria(path) -> HeldoutCriteria`
  - `evaluate_heldout_gate(criteria, *, test_macro: Mapping[str, float], per_scenario: Mapping[str, Mapping[str, float]], per_seed_macro: Mapping[int, Mapping[str, float]], prompts_per_success: Mapping[str, float], safety: Mapping[str, SafetyCounts]) -> HeldoutGate`.

The three metric mappings contain exactly the four method keys `random`,
`rule`, `tabular`, and `ddqn`; the evaluator derives aggregate/per-scenario/
per-seed best-simple values rather than accepting caller-preselected values.

- [ ] **Step 1: Start focused test method 3 with exact gate cases**

Create `test_reduced_runner_gate_and_checkpoint_smoke`, initially testing only the criteria loader and evaluator. Load the exact JSON and use subtests for:

- `ADVANTAGE_SIGNAL`: all core checks pass, DDQN exceeds best simple by at least 0.05, wins at least 2/3 seeds, has at most two >0.10 scenario losses, and prompt ratio <=1.10;
- `PARITY`: core checks pass but advantage margin fails;
- `NO_GO`: one safety count is nonzero or test macro is below 0.70.

Assert exact-key rejection and JSON serialization.

- [ ] **Step 2: Run method 3 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Expected: import failure for `pa_rl.heldout_criteria`.

- [ ] **Step 3: Create the exact criteria profile**

Write:

```json
{
  "profile": "heldout_context_v0",
  "min_test_macro_protocol_success": 0.70,
  "min_improvement_over_random": 0.30,
  "max_gap_below_best_simple": 0.10,
  "scenario_success_threshold": 0.80,
  "min_test_scenarios_solved": 6,
  "deep_rl_advantage_margin": 0.05,
  "min_paired_seed_wins": 2,
  "max_scenarios_worse_by_0_10": 2,
  "max_prompt_ratio_vs_best_simple": 1.10,
  "max_monitor_blocked_attempts": 0,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

Validate exact keys, exact integer domains, and finite unit-interval rates.

- [ ] **Step 4: Implement core and advantage classifications**

Set `best_simple_method` from aggregate Rule/Tabular test macro. `run_integrity` requires every evaluated method to stay within all three safety limits. Core checks are integrity, minimum DDQN macro, Random improvement, maximum best-simple gap, and minimum solved scenarios. Advantage checks are margin, paired seed wins, maximum worse scenarios, and prompt ratio. A zero-success prompt denominator is infinity.

Return `NO_GO` if any core check fails; otherwise return `ADVANTAGE_SIGNAL` only if every advantage check passes, else `PARITY`.

- [ ] **Step 5: Run all three methods and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
python -m compileall -q src\pa_rl\heldout_criteria.py tests\test_increment7_pilot.py
```

Expected: 3/3 pass at the criteria-only boundary.

---

