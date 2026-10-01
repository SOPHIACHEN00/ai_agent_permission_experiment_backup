# Tuning notes

The prior seed307 fixed-replay continuation improved four-cell exact value from0 to0.55/0.625/0.58 at additional updates1000/2000/2937, with unequal and non-monotonic cell outcomes. This motivates a bounded fresh-training comparison of learning rate and update frequency; it does not prove the cause.

Initial group a_lr1e3_every4_seed101 completed12000steps/2937updates,exact mean41/80(0.5125),regret39/200(0.195),first success71;identical validation result to historical baseline. First master then stopped at the inter-worker GPU0idle guard. No second group started. This outer-control failure is preserved; a separate resume_master.py waits up to60seconds for two idle readings and reuses original worker code/config,adopting the completed group without retraining. New supervisor launched01:53:50UTC,PID245688. Its own logs/status/exit filenames have resume_ prefixes,so original evidence is not overwritten.

The base DDQN dataclass defaults are not the executed configuration. The frozen bridge explicitly uses batch64, replay20,000, warmup256, optimize_every4 and target_update_every250. The new matrix changes only learning rate and optimize_every; GPU0 and thread bounds are execution controls. Keeping target sync measured in optimizer updates means every2 has more syncs per environment-step budget, which must be acknowledged in interpretation.

Single-seed exploratory observations are not independent statistical replication. This pilot retains all three training seeds and all twelve final outputs. Forty-eight validation cells are repeated measurements, not48 independent runs. No significance or test-performance claim from tuning data.

## Intermediate baseline replication

Monitoring on UTC2026-09-23 records all three baseline groups complete: seeds101/211/307 exact validation means41/80,51/80,0 (0.5125,0.6375,0), matching historical values. First successful training transitions71/6861/9242 also match the original run. Three-seed mean23/60=0.383333; mean regret389/1200=0.324167. Semantic checkpoint equality will be verified after full download, not inferred merely from matching metrics. The low-learning-rate groups have started; no parameter-selection conclusion yet.

## Halfway observation: 6/12 groups complete

Low learning rate0.0003/every4 seed means119/200,9/16,49/80 (0.595,0.5625,0.6125); three-seed mean0.59 and mean regret0.1175. Paired changes versus baseline are+0.0825,-0.075,+0.6125; seed307 no longer collapses to zero, but seed211 is worse and near-optimal seeds remain0/3. This is a completed configuration's exploratory validation result, not the full matrix verdict. The every2 configurations are now running. No source/science adjustment or training retry.

## Final verified result — UTC2026-09-23

All12groups complete,exit0. Configuration means A/B/C/D=.383333/.59/.575/.578333. Bselected by fixed validation criterion; everyconfiguration0/3nearoptimal. All three new baseline semantic checkpoints exactlymatch historical same-seed baselines. Bseed307 reaches DP onoriginal br05/br06(.50/.93),butprompt_toggle remains.50/.52vs.60/.80; prioritize existing branch traces rather than claiming overall resolution.

Postflight PASS:144000transitions,52860updates,12byte/hash-verified checkpoints,48exactcells,60verifiedchains,matched initializations,12unchanged evaluation fingerprints,all5hardcounters0,testfalse. CompleteZIP SHA2568298f67c6d694ccb61446d372d1e1b3ad67ecc0ec26caa50aeae78d08d7665ca. Two SVGs and descriptive/statistical appendix generated from verified data only; three paired seeds cannot support general population superiority. All three post-hoc direction-only sign tests and Holm-adjustedpvalues1.0; not evidence of equivalence.

Server master/workers exited;GPU0released. Hidden authentication helper29665quit with exit0. No further training,test,sourcechanges,default promotion orAPIcalls. All supervision/connection errors retained; firstgroupwasadoptedwithoutretraining. REPORT_zh.md is the final narrative; earlier intermediate entries above remain chronology.
