# Five-new-seed fixed-candidate confirmation on GPU0

## Frozen scope

User approved the bounded five-new-seed A/B confirmation. Before any outcomes, fix seeds 701,809,907,1009,1103, disjoint from tuning 101/211/307 and prior confirmation 401/503/607. A learning_rate=.001, B=.0003, optimize_every=4 for both. Gamma=1; batch64, replay20000, warmup256, target sync250 optimizer updates, gradient clip5. Preserve network, encoding, reward, action mask, train order and exploration. Same-seed initial network fingerprints must match. Do not search parameters, select favorable seeds/checkpoints, change defaults, lower thresholds or open test.

Exactly ten sequential workers on physical GPU0 only, each 12000 transitions and 2937 optimizer updates: total120000 transitions,29370 updates,10 final checkpoints,40 exact validation cells (br05/br06 × original/prompt_toggle). No additional runs after this batch, regardless of outcomes. No API calls or local model execution.

Primary outcome: this batch's five-seed mean paired difference B−A; report every pair, mean/SD, zero-valued final-policy counts, win/tie/loss and unchanged per-seed near-optimal mean regret≤.05 count. B was fixed in the previous tuning receipt, not selected here. Report this batch separately. Prior three-seed replication may be described separately or in an explicitly exploratory combined summary, never silently pooled into a fresh confirmatory sample. Same validation graphs remain reused; seed robustness is not held-out graph/test generalization.

Reuse proven runner/transport with minimal metadata/budget adaptations. Preflight frozen 41 source files, prior B selection hash, physical GPU0 identity/idleness and effective host/cgroup headroom≥4GiB. One numerical CPU thread, ≥2GiB headroom during training. Never use GPUs1–3 or stop other jobs. Credentials only in memory/hidden input; no coordinates/secrets in files or replies. New evidence retained under /output/agenticAI and downloaded locally; preserve previous runs.

Network interruption: write sanitized checkpoint and resume read-only inspection, never infer training failure solely from a disconnected client. On real runtime failure preserve evidence and stop to discuss, no automatic training retry or parameter change. Single launch only after safe resource checks.

## Phases

- [x] Freeze authorization, seeds, scope and stopping rule.
- [x] Inspect and minimally adapt existing runner; static/budget verification only.
- [x] Safe resource/source preflight, upload and one launch.
- [x] Monitor ten workers and preserve receipts.
- [x] Download/check all models, logs, counts, source and safety evidence.
- [x] Report all results and update main progress/continuation records.

## Status

COMPLETE_FIVE_SEED_MEAN_GAIN_NOT_NEAR_OPTIMAL_TEST_LOCKED. UTC2026-09-23T03:45:38—04:08:53: ten groups completed exactly once, exit0,120000 transitions/29370 updates/10 checkpoints/40 exact validation cells. Master251310 and workers exited, final GPU0 idle observation; hidden authentication helper74056 quit exit0. No active training/monitoring or pending server operation. Do not reconnect, relaunch, retrain or redownload this completed run.

Offline postflight PASS: ten checkpoint byte hashes,50 record chains,paired initializations,unchanged evaluation fingerprints and frozen B-selection provenance. All five hard counters0, testfalse.47 read-only snapshots, zero monitoring connection errors. Archive40622664bytes, SHA25625e97d8cae25599625429fcfe98a036a1d89502621db8699c5a0b656986baec3 downloaded locally with complete original evidence.

A values0/.5425/.5375/.55/.5375, mean.4335; B .425/.6125/.575/.575/.5375, mean.5450. Paired gain.1115,4 wins/1 tie/0 losses; both0/5 near-optimal. Zero-valued seed means1/5→0/5, but B/701 br05/original remains0. This batch stays separate from prior three-seed confirmation. Main progress/checkpoint updated, CSV/analysis bundle/two SVGs and dated Chinese report saved. Next branch diagnosis is a suggestion only; no extra seed/parameter search, default promotion or test opening.

Static check PASS: training loop and learner class AST unchanged, resource/device/RNG coordinate functions unchanged, exact ten-group budget verified without local model execution. Preflight PASS: idle physicalGPU0 3090/UUID matched,41 frozen source hashes, effective headroom73651916800 bytes (~68.6GiB). Uploaded archive SHA256211e2d6b6f463375d2eed0728924b2c09b75dcc2c78c3a2901072decbcf616a4. Worker/config hashes match static evidence. Credentials only in hidden input/memory.

## Errors

Initial local read command could not start because Windows sandbox helper lock failed (SetNamedSecurityInfoW access denied). Use approved command escalation for scoped project operations; this is not a server/experiment failure.

No training/runtime or read-only monitoring errors observed. Failure to reach near-optimality is a retained scientific outcome, not execution failure.
