# Task 5 fix round 1 — fresh re-review package

Review authority:

- Approved plan: `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md`, Task 5.
- Approved bilingual specs: `docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md` and `_zh.md`.
- Original findings: `task-5-review.md` (C1–C3, I1–I4, M1).
- Fix base: `task-5-fix-1-base.md`.
- Implementer evidence: `task-5-report.md`, section “Fix round 1/5”.

## Authorized changed surface

| Path | Base SHA-256 | Review SHA-256 | Bytes |
|---|---|---|---:|
| `src/pa_rl/family3_v2_environment.py` | `764EC0132B09D2FCDCBF6339F2D6B8013E7E06DED05849F4611A2F2D532F9663` | `20FC2B7BDF42382508650FBC3D8E4143F8004CCE4D787D17FEA2B9C7C70F5AB8` | 15,947 |
| `tests/test_family3_v2_authority_environment.py` | `63CE6FD58A6E55B93C4293664F55EC2C73F1BFDDB9CA25CC54D18A5F3DD38EEB` | `DAF5E80AEA4569AC9FE8E007A5CF7A2F2EB680B69F6D28DA78D5A0916DE1D092` | 18,793 |
| `src/pa_rl/family3_v2_audit.py` | `36F590A1804369F05429142479A6D51FA0D9F50A9FFBDC0BA6BB00675ED6CB2C` | `1BA1DC3B660892410BB31BEC9AF3CB1A0D145F479851FFB58EE954EC049B98D5` | 57,282 |
| `tests/test_family3_v2_policy_audit.py` | `A848B77C80F74DA487374EF3C40FE191140CEEBC520CC24746617CCA3C82D77F` | `2ED2837D0E081947643E4DEF4B7893D431FACAA5A631A23EC0F6B19B2FE708D0` | 19,073 |

The Task 4 delta is evidence-only: immutable task snapshot and exact user-dispatch count in environment info plus focused tests. It must not alter the policy observation, encoder, semantic transition kernel, RNG, rewards, masks, scientific parameters, or legacy v0/v1 files.

## TDD/process evidence

- Regression RED: the authorized combined command ran with 18 tests, 6 expected errors, 31.029 seconds.
- Single post-fix GREEN: the identical command ran once, 18 tests passed, 71.949 seconds, exit 0.
- Command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment tests.test_family3_v2_policy_audit -v`.
- No broad suite, DP solver, runner, training, tuning, search, gate, or rebaseline ran.
- The earlier round-0 extra GREEN attempt remains recorded as I4 process history; determine whether the transparent record plus strict single-GREEN fix round resolves it without erasing history.

## Claimed exact evidence to verify independently

- C1: 314 reachable valid no-coverage supports replayed through fresh real environments: 294 disables plus 20 executes; 2,198 ordered nonemitted catalog rows; real task installation/pending evidence for execute; no doomed public observation.
- C2: all 882 forced-invalid rows compare ledger records/events, user dispatch, binding, monitor/tool/effect, prompt/exposure/branch, task snapshot, and stable authorization/task/continuation/effect semantic channels; 882 zero-delta passes; negative mutations traverse the comparator.
- C3: public and encoded successor distributions use separate key builders; duplicated same-key occurrences force invalid-reason, termination-kind, and mask mutations through the real group comparator, not a direct self-reported mismatch.
- I1: semantic-successor canary mutates `info.semantic_state` while leaving observation unchanged.
- I2: exactly 40 cells / 20 success / 10 resource / 10 no-coverage; exact model branch `Fraction`; broader/exact exposure is `(E // b + 1) * b`.
- I3: 480 manifests / 4,800 rows / 4,800 schema / 4,800 algebra / 14,400 leakage checks; full construction theorem, sensitivity/phase structural key, independent analytic-role oracle, and predicate-family negative canaries.
- M1: `no_repair_state_count=294`, `closed_offer_row_check_count=882`, `disable_guard_count=294`, `execute_guard_count=20`, `nonemitted_guard_count=314`, `forced_invalid_count=882`.

Do not accept counts alone. Inspect that real environment replay, independent public/encoded successor construction, group comparison, and each negative hook exercise the intended production predicate. Check all ordered catalog fields against an independent literal theorem rather than only real-vs-pure equality.

## Frozen/checkpoint evidence

- Legacy 14-source/72-result baseline digest remains `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`.
- Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.
- `task-5-report.md`: `6FFA5E8F6B0A40E54698081A88B47AF93D075C48A90F50A4B9E1DD3B8FB275EE`.
- SDD `progress.md`: `0B03D03433C6D9E9FFA11DB6D63A71D40616A14FDDFC6DCC6594E25C5B068913`.
- Project checkpoint: `48D1ACF32EB8CD58AA55D4EABF6000F7EE2E0D2D121C7EA5C731C351BB4E851D`.
- Result checkpoint: `D0924BAE5B899914F153EE494D2585700DAC418BD7DD512393AE74424E0C5C14`.
- Result JSONL: `30F095E00913AB89F550C0A16457DFC8A4690BFBC691A2718E1FE3E38A5DCFC8`.

## Required verdict

Return separate `Spec Compliance` and `Code Quality` verdicts, every original finding as `ADDRESSED` or `OPEN`, any new Critical/Important/Minor finding with exact file/line evidence, the frozen-baseline/checkpoint result, and a final `APPROVE` or `DO NOT APPROVE`. Do not modify files and do not run a broad test. Task 6 remains blocked unless the fresh verdict is APPROVE.
