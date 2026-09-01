### Task 2: Canonical replay, negative controls, and named public Rule

**Files:**
- Create: `src/pa_rl/public_rule.py`
- Modify: `src/pa_rl/multiscenario_policy.py`
- Modify: `tests/test_increment7_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `Increment7Suite`, `PermissionEnvironment(manifests=...)`, `CanonicalProtocolTracker`, `MultiScenarioFeatureEncoder`, `PolicyDecisionV1`.
- Produces:
  - `PUBLIC_STATE_INDEX_V1: Mapping[str, int]`
  - `PUBLIC_CANDIDATE_INDEX_V1: Mapping[str, int]`
  - `choose_public_rule(decision: PolicyDecisionV1) -> str`.

- [ ] **Step 1: Add focused test method 2**

Create `test_all_protocols_replay_negative_controls_and_named_rule`. Add helpers that instantiate:

```python
PermissionEnvironment(manifests=(manifest,), default_scenario_id=manifest.scenario_id)
```

Resolve actions from the live public catalog by action/task binding, step the unmodified environment, and pass selected rows plus trusted post-step audit only to `CanonicalProtocolTracker.observe`.

Assert all 40 legal traces close as declared with protocol reward 1, zero mask violations, zero unauthorized committed effects, and zero monitor-blocked attempts. Assert representative deviations for each family return protocol reward 0. Assert f1/f3 scope relation exact, f4 narrow-to-broad relation broader, and f7 phase scopes disjoint.

Construct denied states for purposes `unavailable_resolution` and `unavailable_task`; assert the named Rule returns ESCALATE for the former and DENY for the latter. Assert `PUBLIC_STATE_INDEX_V1["purpose_unavailable_resolution"] == 61` without using 61 in Rule implementation.

- [ ] **Step 2: Run method 2 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
```

Expected: import failure for `pa_rl.public_rule` or missing named layout exports.

- [ ] **Step 3: Export named layout positions without changing features**

In `multiscenario_policy.py`, add immutable mappings that reflect the existing order:

```python
PUBLIC_STATE_INDEX_V1 = MappingProxyType({
    "public_denial_count": 15,
    "purpose_unavailable_resolution": 61,
    "purpose_unavailable_task": 62,
})
PUBLIC_CANDIDATE_INDEX_V1 = MappingProxyType({
    "authorization_status_active": 16,
    "scope_relation_exact": 27,
    "scope_relation_narrower": 28,
    "remaining_uses_zero": 32,
    "expiry_future": 35,
})
```

Add import-time assertions derived from `_PURPOSES` and layout sizes so a vocabulary reorder fails unless `MULTISCENARIO_FEATURE_VERSION` is intentionally changed. Do not change tensor values, order, shapes, or version.

- [ ] **Step 4: Implement the frozen generic Rule**

Move no Increment-6 code. Create a reusable Rule with identical priority:

1. valid EXECUTE with active, future, covering authority and nonzero/unbounded uses;
2. valid REFRESH;
3. after a public denial, ESCALATE only for `unavailable_resolution`, otherwise DENY;
4. valid REQUEST;
5. deterministic first remaining valid semantic ID.

Use only `decision.state`, `candidate_features`, `actions`, `semantic_candidate_ids`, and `mask`. Never call `policy_metadata()` or read scenario/text/audit/reward.

- [ ] **Step 5: Run methods 1--2 and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\multiscenario_policy.py src\pa_rl\public_rule.py tests\test_increment7_pilot.py
```

Expected: 2/2 pass and compilation exit 0.

- [ ] **Step 6: Record the protocol checkpoint**

Append all-40 legal replay status, shortcut-control status, and feature-layout version/hash to the continuation checkpoint.

---

