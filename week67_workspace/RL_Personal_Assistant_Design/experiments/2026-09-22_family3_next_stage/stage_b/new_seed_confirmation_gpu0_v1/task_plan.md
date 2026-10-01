# Fixed-candidate new-seed confirmation on GPU0

## Authorization and frozen question

User approved immediate small new-seed confirmation, not expanded tuning. Run exactly6fresh sequential workers on physicalGPU0: baselineA learning_rate.001 versus preselectedB.0003, bothoptimize_every4, pairedseeds401/503/607 fixed before outcomes. These seeds are disjoint from tuning101/211/307. Preserve the old evidence and main defaults.

Eachgroup12000environment transitions(5train graphs×2400),2937optimizerupdates; total72000transitions,17622updates,6final checkpoints,24exactvalidation cells(br05/br06×original/prompt_toggle). Fixedgamma1,batch64,replay20000,warmup256,targetsync250optimizerupdates,clip5,original network/encoder/reward/legality/RNG scheme/exploration schedule. Only newseed coordinates and the A/B learningrate differ. Same-seed initial weights must match between A/B. No extra trajectories/checkpoints chosen after seeing outcomes.

Primary outcome: the three-seed mean paired differenceB-A in exactvalidationvalue, plus allindividual differences, worstseed and unchanged nearoptimalmeanregret<=.05 counts. B is fixed before this run; do not reselect hyperparameters from these results, pool old tuning seeds into an alleged independent confirmation, or claim held-outgraph/test generalization. Testremainsclosed. No new significance/pass threshold invented.

Useexisting frozen parent41files and minimal copies of proven worker/transport. Remove legacy restriction that a fresh seed must have an oldformal checkpoint: record A's initialfingerprint before training and compareB against it. Preserve learned behavior and optimizer unchanged. Reuse bounded intergroup idle waiting; never run two workers concurrently, kill foreign processes, use otherGPUs, automatically retry failed training, or change parameters on failure.

Resource preflight: physicalGPU0UUID and idle confirmed, effectivehost/cgroup headroom>=4GiB before eachworker and>=2GiB duringtraining; one numericalCPUthread. Connection failure is not training failure. Credentials in hiddeninput/memory only, no coordinates/passwords in scripts/config/logs. Evidence stays remotely under/output/agenticAI and is downloaded locally.

## Phases

- [x] Freeze scope, seeds, comparison, budgets and stop rules.
- [x] Prepare minimal runner/transport and syntax/budget verification(no localtraining).
- [x] Resource/source preflight, bounded upload and single launch.
- [x] Monitor sixgroups; preserve first realfailure rather than changing experiment.
- [x] Download and verify complete model/log/config/safety evidence.
- [x] Report allpaired results and update main progress/continuation records.

## Status

COMPLETE_FIXED_CANDIDATE_MEAN_GAIN_NOT_NEAR_OPTIMAL_TEST_LOCKED. Single master 249782/start_ticks 67957654 ran 2026-09-23T03:06:19 to 03:21:38 UTC at /output/agenticAI/budget_recourse_new_seed_confirmation_gpu0_v1; exit 0. All six groups completed exactly once: 72000 transitions, 17622 optimizer updates, six checkpoints and 24 exact validation cells. No runtime failure or read-only monitoring error. Master/worker exited, GPU0 released, hidden authentication helper session 9580 closed (exit 0); no active monitoring remains. Do not reconnect, relaunch, retrain or redownload this completed run.

Offline postflight PASS: all checkpoint byte hashes, 30 record chains, paired initializations, evaluation fingerprint stability, fixed-candidate provenance and closed test verified. All five hard counters zero. Full 24243407-byte archive retained locally; SHA256 8d0e1293544811eb39b21f0980a5642d01fed3065141d938ed90752f0624f061. See REPORT_zh.md, per_seed_results.csv, exact_values.csv and analysis-output/.

Seed values A/B: 401 .6125/.6000; 503 .5000/.5000; 607 .0000/.5750. Means .370833/.558333, paired mean gain .1875; one improvement, one tie, one decrease. Both configurations remain 0/3 near-optimal. Keep B as the previously selected working candidate without changing defaults; no further experiment started. Suggest inspecting existing failure branches before authorizing additional training. Main progress and continuation records updated.

## Errors

No training/runtime or read-only monitoring errors observed in this run. Do not conflate planned new-seed metadata adaptation with a learner bug. Performance shortfall is a scientific result, not a failed execution.
