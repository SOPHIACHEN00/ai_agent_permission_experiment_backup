# GPU0 DDQN 2×2 tuning pilot

## Authorization and goal

User authorized running the previously proposed learning-rate × update-frequency comparison on physical GPU0 and recording the experiment locally. This supersedes the previous diagnostic-only stop boundary. Only physical GPU0 is authorized.

## Frozen comparison

- Gamma=1, seeds101/211/307, 12,000 environment transitions per config/seed, same five train graphs and original environment/exploration schedule.
- Four configs: lr0.001/every4 (baseline), lr0.0003/every4, lr0.001/every2, lr0.0003/every2. Train all twelve groups from the same seed-matched initialization, sequentially on GPU0.
- Total144,000 transitions; optimizer updates2,937 per every4 group and5,873 per every2 group (52,860 total); twelve final reloadable checkpoints.
- Other parameters: batch64, replay20,000, warmup256, target sync250 optimizer updates, gradient clip5. Same gamma, reward, encoder, legal-action mask, task and network.
- Final-only exact validation: br05/br06 × original/prompt_toggle per group,48 exact rows. Primary selection: lowest mean exact regret over all three seeds; report each seed, worst seed, and near-optimal<=0.05 count. Tie: fewer optimizer updates, then configuration ID. No best-intermediate-checkpoint selection.
- Retain safety counts, source/config/checkpoint fingerprints, measured memory and runtime. This is validation-based tuning, not held-out confirmation. Test stays closed; gamma0 and rules are not rerun or used as a newly matched causal comparison.
- GPU preflight must confirm physical0 UUID, no other GPU0 compute process, and >=4GiB effective host/cgroup memory headroom. One sequential learner only; constrain numerical CPU threads. Stop on real error, preserve all evidence; connection failure is not evidence of training failure.

## Phases

- [x] Record scope, fixed matrix, metrics, device and stop conditions.
- [x] Read frozen runner/checkpoint interfaces and make a minimal standalone adapter.
- [x] Syntax/configuration check; GPU0/resource/source preflight; upload only required new files.
- [x] Run the twelve groups and monitor durable progress.
- [x] Download all results/logs/models; verify coverage, hashes and safety.
- [x] Record Chinese report, main progress log and continuation checkpoint.

## Status

COMPLETE_TUNING_IMPROVEMENT_NOT_NEAR_OPTIMAL_TEST_LOCKED. All12groups completed by2026-09-23T02:44:13UTC; final resume_exit_receipt exit0. Best validation configuration B=.0003/every4: mean.59 versus baseline.383333, but0/3seeds pass mean regret<=.05. Full48,898,563-byte archive downloaded; postflight PASS verified12checkpoints,144000steps,52860updates,48exactrows,60recordchains,matched initialization and unchanged evaluation fingerprints. All hard counters0; testclosed. Master/workers exited and GPU0released; authentication helper29665 closed(exit0). Do not restart or keep monitoring this completed run. REPORT_zh.md, analysis-output/, main progress log and continuation checkpoint updated. Proposed new-seed confirmation/trace diagnosis has not been started; no default parameter promotion.

## Errors

Windows sandbox lock helper intermittently failed while reading/updating local files; authorized elevated read/apply_patch commands worked. No learner/test was run locally. Syntax and budget checks passed once. No training error observed at launch.

2026-09-23T01:47:15UTC: original master stopped at gpu_idle() between group0and1,after group0 completed. Error GPU0occupied; no fallback. Follow-up snapshot showed1MiB/0utilization; no second learner had started. Exact triggering occupancy component was not recorded in original guard,so transient release/utilization is plausible,not proven. Bounded supervisor fix waits for two consecutive identical idle predicates,logs readings,and stops if not clear within60seconds. It verifies/adopts group0 by checkpoint hash,then launches only unstarted groups. This is an explicit scheduler continuation within authorized work,not automatic training retry or parameter modification.

During c_lr1e3_every2_seed101, one read-only monitoring call returned CONNECTION_OR_REMOTE_COMMAND_FAILED. Following polls reconnected and verified the same master/worker identities with progress9088then10752steps. Later a TimeoutExpired ended the local watch loop; a read-only poll recovered and found training already advanced, then watch resumed without launching a worker. Connection versus remote read-command cause was not distinguished; no training failure or restart inferred. Raw timestamped snapshots and helper error receipt preserved. Watch ended at final exit0; helper nowclosed.

Local plotting packages were unavailable in both Python runtimes; used dependency-free SVG generation instead of installation. Two SVG/XML outputs and descriptive-statistics generation passed. No model inference/training or experiment change in this archival step.
