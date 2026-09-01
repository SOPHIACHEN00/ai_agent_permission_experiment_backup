# Task 5 fix round 2 — focused fresh re-review package

Review only the two findings left OPEN by `task-5-fix-1-review.md` and ensure
the previously accepted findings were not regressed. Task 6 remains blocked
until an independent APPROVE.

## Changed surface

| Path | Fix-2 base SHA-256 | Review SHA-256 | Bytes |
|---|---|---|---:|
| `src/pa_rl/family3_v2_audit.py` | `1BA1DC3B660892410BB31BEC9AF3CB1A0D145F479851FFB58EE954EC049B98D5` | `92EF0F7794536581A5FBB51719EA8B4A79436B61B4B0BC61EB3632A020B45921` | 64,280 |
| `tests/test_family3_v2_policy_audit.py` | `2ED2837D0E081947643E4DEF4B7893D431FACAA5A631A23EC0F6B19B2FE708D0` | `DE07886C8609204B0A9539F1A514E85BCFE6E9B69E9FEA10CEFFD845CD37FE48` | 22,466 |

No other production/test file was authorized or changed. In particular:

- environment: `20FC2B7BDF42382508650FBC3D8E4143F8004CCE4D787D17FEA2B9C7C70F5AB8`
- environment test: `DAF5E80AEA4569AC9FE8E007A5CF7A2F2EB680B69F6D28DA78D5A0916DE1D092`
- independently clarified Task 6 brief: `7D57AB70C77BE1FD8ADD1A68F7232C6FD6373FD85A69A14155A707F064F61581`

Task 2/3, authority, policy, legacy files, scientific parameters, fixed output
root, and gate state must remain unchanged.

## Focused TDD evidence

- RED command selected only the two new C1/C2 regression methods.
- RED: 2 tests, 7.078 seconds, exactly two expected missing-report-field errors.
- The identical two-method command ran once after the fix.
- GREEN: 2 tests, 14.976 seconds, `OK`.
- No complete Task 5 suite, broad suite, solver, runner, training, tuning, real
  gate, or rebaseline ran in this round.

## C1 evidence to trace

- Production literal `_EMITTED_POST_GRANT_LITERAL` is independent of model
  output and contains the complete ordered role/action/mask/reason theorem.
- Every one of 294 emitted post-grant states is compared against it and all
  rows are required emitted.
- Production disable-trigger and execute-trigger no-coverage literals each
  contain all seven ordered role/action/mask/reason/emitted fields.
- Every one of 314 pure catalogs and every one of 314 real-environment catalogs
  is separately compared to its independent literal; both comparisons enter
  `verified` and therefore report `passed`.
- The catalog hook mutates comparator input; it does not directly append a
  mismatch. One negative audit must traverse and fail the emitted, pure-guard,
  and real-guard comparators.
- Claimed counts: 294 emitted literal checks, 314 pure guard literal checks,
  314 real guard literal checks, 314 real replays, and 2,198 guard rows.

## C2 evidence to trace

- `_forced_invalid_stable_key` derives fields from the full state dataclass and
  excludes exactly `decision_index`, `invalid_actions`, `termination_kind`,
  `failure_reason`, and `reward`.
- Before/after stable keys are compared independently of the pure successor.
- Closure independently requires decision index +1, invalid actions +1,
  reward zero, irreversible failure, failure reason equal to the selected
  invalid row, and `run_valid=True`.
- The state-input hook feeds a changed state through the real comparator; it
  does not directly append a mismatch. A single negative audit changes offer
  window, accumulated utility, unauthorized committed effects, and monitor
  blocked attempts on four distinct occurrences and must yield four stable-key
  mismatches.
- Claimed counts: 882 stable-key checks and 882 exact closure checks.

## Reports/checkpoints

- `task-5-report.md`: `1BC8CB06F077056F8E3398A74F01C1AE43C42E99CF7DC06DB4359499EFDA5C6E`
- SDD `progress.md`: `085A38567185826E0BE96F4BADC265022716CEA96A8FC3DCAAF090B50852BDA2`
- project checkpoint: `53D5C4FF443C5DE3BD93BCFC9853EB7A898DFC4BD92DF85650C2AA5D2A765BF1`
- result checkpoint: `77645DCF67688CF5EA175321718ABBEB4E2BAAC179F938473ECDB4911772C0C3`
- result JSONL: `D1C59500DBF01294510D29B3D2DAD77FA65568D6256935E49FA1D19830D04BB4`
- baseline digest remains
  `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`.
- gate state must remain `BASELINE_FROZEN / 0 / 1`.

## Required verdict

Do not modify files and do not rerun the complete 72-second audit or broad
suite. Independently trace the two production comparators and their input-level
negative hooks, verify hashes/scope/baseline/checkpoint, then return:

- C1: ADDRESSED or OPEN;
- C2: ADDRESSED or OPEN;
- regression check for already accepted C3/I1/I2/I3/I4/M1;
- separate Spec Compliance and Code Quality verdicts;
- any new Critical/Important/Minor with exact file/line evidence;
- final APPROVE or DO NOT APPROVE.
