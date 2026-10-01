# Statistical record

Unit: a trained seed evaluated on the same four fixed dev graphs; seeds1301/1601.
The24rows are3methods×2seeds×4graphs, not24independent samples or participants.
Fixed rule is deterministic; its duplicate seed rows are alignment, not repetitions
that add evidence.26cached answers are history-specific samples from one synthetic
respondent setup;24distinctprompts, no empirical subject-level independence.

Task completion is binary, higher is better; every method has6/8pooled rows,
per-seedmean.75 and sampleSD0. Seed observed range[.75,.75] describes these two runs
only; it is NOT a95%confidenceinterval. DDQN-MAB,DDQN-rule,MAB-rule paired raw
differences are0percentagepoints in each seed and in the mean.

No inferential tests, normality tests, populationCI or equivalence tests were run.
Two seeds cannot support a normality assessment; deterministic duplicated controls
and purpose-selected graphs do not justify treating rows as an independent cohort.
No p-values or multiple-testing correction apply because no significance family
was tested. Standardized effect sizes with zero SD are undefined; raw differences
are reported instead. Zero observed SD is not proof of robustness.

Per-seed each method asks7questions, has1fallback and1protocol-injecteddisable;
post-denialquestions0. Hardinvalid/unauthorized/adapterfault0. These safety counts
include enforcement by the shared kernel; they do not establish learned safety.

DDQN1301has one extra voluntaryDISABLE in refusal scenario; success-rate tie does
not establish equal efficiency or trajectory equality. The terminal reason there
isincorrect_terminal_action under a manifest allowing onlyTASK_COMPLETEDsuccess;
do not turn absence of unauthorized effects into proof of optimal refusal wording.

No seed exclusions, resampling, failed-run replacement or hyperparameter search.
r1collectionboundfailure retained. r2authorization changes only operational caps;
9originalresponses preserved byte-for-byte,17missinghistories collected once.
All metrics are dev/pilot metrics; old held-outtest remains closed.
