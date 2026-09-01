### Task 1: Deterministic 40-scenario suite and split

**Files:**
- Create: `src/pa_rl/increment7_scenarios.py`
- Create: `tests/test_increment7_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `Scope`, `ControllerAction`, `PermissionChoice`, `TerminalSuccessKind`, `TaskStep`, `ActionTraceStep`, `ExpectedTermination`, `ScenarioManifest`, and `scenario_hash`.
- Produces:
  - `INCREMENT7_SUITE_VERSION = "increment7_paired_context_v0"`
  - `CarrierSpec`, `FamilySpec`, `SuiteMember`, and `Increment7Suite`
  - `build_increment7_suite() -> Increment7Suite`
  - `Increment7Suite.manifests(split: str) -> tuple[ScenarioManifest, ...]`
  - `Increment7Suite.as_mapping() -> dict[str, object]`
  - `Increment7Suite.suite_hash -> str` and `split_hash -> str`.

- [ ] **Step 1: Write focused test method 1**

Create `Increment7PilotTests.test_suite_split_and_policy_firewall_invariants`. Before production code exists, import `build_increment7_suite` and assert the independently hard-coded split matrix:

```python
expected = {
    "f0_once": {"train": ("c2_mail_send", "c3_report", "c4_records"), "validation": ("c1_mail_archive",), "test": ("c0_calendar",)},
    "f1_reuse": {"train": ("c0_calendar", "c3_report", "c4_records"), "validation": ("c2_mail_send",), "test": ("c1_mail_archive",)},
    "f2_disable_refresh": {"train": ("c0_calendar", "c1_mail_archive", "c4_records"), "validation": ("c3_report",), "test": ("c2_mail_send",)},
    "f3_consumed_refresh": {"train": ("c0_calendar", "c1_mail_archive", "c2_mail_send"), "validation": ("c4_records",), "test": ("c3_report",)},
    "f4_broader_refresh": {"train": ("c1_mail_archive", "c2_mail_send", "c3_report"), "validation": ("c0_calendar",), "test": ("c4_records",)},
    "f5_persistent_deny": {"train": ("c2_mail_send", "c3_report", "c4_records"), "validation": ("c1_mail_archive",), "test": ("c0_calendar",)},
    "f6_safe_escalate": {"train": ("c0_calendar", "c3_report", "c4_records"), "validation": ("c2_mail_send",), "test": ("c1_mail_archive",)},
    "f7_timeout": {"train": ("c0_calendar", "c1_mail_archive", "c4_records"), "validation": ("c3_report",), "test": ("c2_mail_send",)},
}
```

Assert exactly 40 unique IDs, 24/8/8 disjoint coverage, 3/1/1 per family, no split token in ID/public text, deterministic hashes after reversing member order, validation/test atomic categorical support contained in train, and every validation/test full primary scope signature absent from train.

Build a `PublicScenarioContext` and initial `PolicyDecisionV1` for every member. Recursively assert policy tensors/metadata contain none of: `scenario_id`, family, carrier, split, trace, scripted response, evaluator, audit, or hidden fields. Assert no generated value reaches the v1 `other` buckets.

- [ ] **Step 2: Run method 1 and capture RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
```

Expected: `ModuleNotFoundError: No module named 'pa_rl.increment7_scenarios'`.

- [ ] **Step 3: Implement the five exact carrier constants**

Define frozen carrier values with exact base/extra attributes:

```python
_CARRIERS = (
    CarrierSpec("c0_calendar", "productivity", "calendar_api", "calendar.events", ("title", "start_time"), "end_time", "read", "local_user", "session"),
    CarrierSpec("c1_mail_archive", "productivity", "mail_api", "mail.messages", ("message_id",), "body", "archive", "local_user", "session"),
    CarrierSpec("c2_mail_send", "productivity", "mail_api", "mail.messages", ("body",), "recipient", "send", "team", "session"),
    CarrierSpec("c3_report", "productivity", "report_api", "reports.weekly", ("time", "end_time"), "title", "read", "stakeholder", "session"),
    CarrierSpec("c4_records", "records", "records_api", "records.private", ("record",), "recipient", "send", "third_party", "external"),
)
```

Define the timeout second scope exactly as `support/unavailable_api/unavailable.operation/{request}/execute/incomplete_workflow/local_user/session`.

- [ ] **Step 4: Implement the eight exact family builders**

Encode these purpose/response/action/horizon/outcome contracts:

```python
_FAMILY_CODES = (
    ("f0_once", "agenda_summary", (PermissionChoice.ALLOW_ONCE,), 3),
    ("f1_reuse", "status_notice", (PermissionChoice.ALLOW_REUSE,), 5),
    ("f2_disable_refresh", "approved_update", (PermissionChoice.ALLOW_REUSE, PermissionChoice.ALLOW_ONCE), 6),
    ("f3_consumed_refresh", "inbox_cleanup", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE), 6),
    ("f4_broader_refresh", "weekly_report", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_REUSE), 6),
    ("f5_persistent_deny", "external_transfer", (PermissionChoice.DENY_PERSIST,), 4),
    ("f6_safe_escalate", "unavailable_resolution", (PermissionChoice.DENY_REASK,), 3),
    ("f7_timeout", "incomplete_workflow", (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE), 3),
)
```

Build legal traces exactly as approved in the spec. Keep terminal-action `scope_step_id=None`; bind requests/refreshes/executions to their task steps. Use `TASK_COMPLETED`, `SAFE_IMPOSSIBILITY_DENIED`, `SAFE_IMPOSSIBILITY_ESCALATED`, or no legal terminal kind for timeout. Create public text from neutral tool/object/purpose templates without codes, split, expected response, or answer. Use one non-empty oracle-only hidden postcondition.

- [ ] **Step 5: Implement split and evidence mappings**

Sort members by `(family_code, carrier_code)`. Compute split only with the frozen formula. `as_mapping()` returns suite version, formula, suite/split hashes, and each member's scenario ID/family/carrier/split/scenario hash; it must not serialize hidden content into policy inputs.

- [ ] **Step 6: Run method 1 and targeted compilation**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_suite_split_and_policy_firewall_invariants -v
python -m compileall -q src\pa_rl\increment7_scenarios.py tests\test_increment7_pilot.py
```

Expected: 1/1 pass and compilation exit 0.

- [ ] **Step 7: Record the suite-freeze checkpoint**

Append suite version/hash, split hash, exact command/result, changed files, and the next task to `docs/CONTINUATION_CHECKPOINT.md`.

---

