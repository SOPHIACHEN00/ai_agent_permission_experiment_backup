# New-seed confirmation notes

Predecessor: ../hyperparam_tuning_gpu0_v1/REPORT_zh.md and postflight_verification.json. TuningA/B/C/D means.383333/.59/.575/.578333; Bchosen; allconfigs0/3nearoptimal. Newconfirmation must keep Bfixed, not search again. BaselineA is necessary to distinguish an improvement from simply easier newrandomseeds. Current experiment uses newseeds401/503/607 and no held-outtest access.

All scoped implementations, resource observations, connection failures and scientific findings will be added here or preserved in timestamped monitoring evidence.

UTC2026-09-23T03:06:19 singlelaunch master249782/startticks67957654. StaticcheckPASS:trainingloop/TunedDDQNclassASTidenticalto priorrunner;newpairedinitializationreceipts replace historicalseedlookup; nooptimizerchange. GPU0idle3090,UUIDmatch,41sourcehashes,effectiveheadroom44,456,849,408bytes. Firstsnapshotseed4011920steps,417updates,successfirstat1529,identitiescorrect. No conclusions yet. Hiddenauthsession9580watching;authnotstored. ArchiveuploadSHA256048e2f783c99a462ea83bb7537740b045233130686a7db8056e0c6bdd9e544d7.

UTC 2026-09-23T03:21:38: completion and exit 0. Six groups ran once, 72000 transitions / 17622 updates / six models / 24 exact cells. No runtime or read-only monitoring errors observed. Mean A=.3708333333, B=.5583333333; paired changes [-.0125,0,.575], mean .1875. Both 0/3 near-optimal; gain dominated by seed607 recovery. No new winner selection or production default change. Original-condition gaps remain on br06 for B/503 and B/607; do not assume only prompt_toggle is deficient.

Post-run local archival: all evidence downloaded, archive SHA256 8d0e1293544811eb39b21f0980a5642d01fed3065141d938ed90752f0624f061 (24243407 bytes). postflight.py exit 0 / PASS; six checkpoint hashes, 30 record chains, fixed candidate provenance, paired initial fingerprints and unchanged evaluation fingerprints verified. Five hard counters all zero, test closed. Master/workers exited, GPU0 released; hidden transport 9580 quit with exit 0. No server work remains.

Offline summarize_evidence.py produced paired-seed descriptive statistics and two SVGs; SVG XML parses, but no visual/publication QA claimed. Exploratory sign test on two non-tied pairs gives p=1; not a test of mean gain or equivalence. Full assumptions/limitations in analysis-output/stats-appendix.md. Completed REPORT_zh.md and main progress/checkpoint; next branch-level inspection is a suggestion, not a started experiment.

Local documentation tooling: direct apply_patch update was blocked by Windows sandbox helper lock; used the same apply-patch implementation through the approved command route. This affected documentation only, not server training or evidence.
