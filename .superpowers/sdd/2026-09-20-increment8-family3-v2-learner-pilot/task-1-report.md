# Task 1 — Dependency freeze and strict config boundary

Status: DONE.

## Verification inputs and results

- Approved English/Chinese spec SHA-256 and sizes matched the checkpoint: `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` / 38,149 and `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20` / 35,818 bytes.
- The shared normative JSON parsed identically; canonical SHA-256: `27ecd5b5614c1542a971265b8f3ca657a82c434cdcd3fd5e17df9a1c0c07596d`.
- `final_verdict.json` was `CERTIFIED_PASS`; its run-config and frozen-baseline hashes matched. The suite hash was `98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
- All 20 certified source fingerprints, 24 committed gate files, 20 certificate paths, and 20 cache paths verified. `ddqn.py` and `baselines.py` matched their recorded manifest hashes. The formal learner result root was absent.

## TDD record

RED command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

RED result: `ModuleNotFoundError: No module named 'pa_rl.family3_v2_pilot_criteria'`; `Ran 1 test in 0.000s`, `FAILED (errors=1)`. No other failure appeared.

GREEN command: same command.

GREEN result: `Ran 1 test in 0.084s` — `OK`.

## Created files

- `configs/evaluation/family3_v2_learner_pilot_v0.json`: 8,377 bytes, `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`.
- `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`: 6,846 bytes, `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`.
- `src/pa_rl/family3_v2_pilot_criteria.py`: 6,040 bytes, `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`.
- `tests/test_family3_v2_learner_pilot.py`: 3,880 bytes, `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e`.

## Self-review and concerns

The loader freezes the exact canonical approved JSON, rejects unknown/missing/noncanonical values (including booleans substituted for integer fields), and exposes immutable mappings. The verifier compares literal paths, sizes, and hashes without rewriting the baseline; the focused test proves a tampered learner dependency fails. No certified artifact, `ddqn.py`, or `baselines.py` was changed, and no exact-DP/twelve-gate run occurred. Only the approved focused RED/GREEN command was run. Concern: none.

## Checkpoint supplement

The required continuation checkpoint was updated after the normal patch helper encountered its Windows ACL lock. Its final SHA-256 is `45fdb03f541a58c108d9fb313f2fa8b5a9810d0c7d7d19ea7f056f9a5d5ff131` (65,135 bytes). Final Task 1 hashes remain: config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`; baseline `41aeb93fe4b77bf7c989db6e5640353c884f0c95f6ee2676ffb5f110a9bfed4e`; criteria `11abe65fd023614635def7133721861edaa9fbdf4b7a1b6afaf7c7c61ee5f5b7`; test `b80025966f8178737d04ad948b095a577d16854d81e50bf0286b5a13cb64573e`. The checkpoint records Task 1 review as the next step. No test was rerun.

## Fix round 1/5

RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v`.

RED result: `KeyError: 'certificate_entries'` at the new literal certificate-inventory assertion; `Ran 1 test in 0.010s`, `FAILED (errors=1)`. This demonstrated the reviewed path-only integrity gap.

GREEN command: identical focused command. GREEN result: `Ran 1 test in 0.314s` — `OK`.

The baseline now records all 20 certificates and 20 SQLite caches as literal `{relative_path, sha256, byte_size}` entries. The verifier rejects unknown/missing schema fields, noncanonical approved-spec/result-root/suite/inventories, duplicate entries, and escaped paths, while verifying every recorded hash and size. Current hashes/sizes: baseline `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` / 11,338; criteria `dea81534fd46cf5de1789c2628723dfa0e889513418e728204eb7a9c98f2a5a3` / 7,769; test `1f14128d6664362c94c1df90d008d0c307196f391f538f1ad755be99d1776617` / 5,904; checkpoint `dfad2c59eef557a9dc0efe91d5e993445c87f037a5d01a176aeaf79c2fa9ff8f` / 65,061. No test beyond the authorized focused RED/GREEN was run. Current next action: Task 1 review.

## Fix round 2/5

RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v`.

RED result: an assertion that `ValueError` must be raised for a substituted remaining inventory failed: `AssertionError: ValueError not raised`; `Ran 1 test in 0.395s`, `FAILED (failures=1)`. The final focused GREEN used the identical command and passed: `Ran 1 test in 0.453s` — `OK`.

The verifier now binds `certified_source_files`, `additional_learner_dependencies`, `pilot_config`, and preflight artifacts to fixed canonical digests in addition to exact per-entry schema and physical hash/size checks; reorder, duplicate, path, or expected-value substitution fails closed. The current checkpoint exact-next-action block now states Task 1 fix round 2/re-review and prohibits Task 2 until spec and quality approval. Final hashes/sizes: criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` / 8,984; test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` / 6,332; checkpoint `5ead68f023ee85613c6f0a5fe6a9a91d21217d02fc0273531ae53bf710ff9613` / 64,948; baseline unchanged `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` / 11,338.

## Fix round 3/5 — documentation closeout

No production or test file changed and no test was rerun. The continuation checkpoint now points to the final baseline at `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`, SHA-256 `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`, 11,338 bytes, and records the final config `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`, criteria `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143`, and test `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` hashes. Current status is independently APPROVED/complete; the next allowed work is Task 2 public 43/7/7 surface, with smoke/training/validation/test still forbidden. Final checkpoint SHA-256: `998a3550332038d167653ef75361ab4946f65bfafb5f6336d0786bec51750537` (65,367 bytes).
