# Statistical appendix

| Method | Seed1301 | Seed1601 | Mean ± sample SD | Requests /16 episodes |
|---|---:|---:|---:|---:|
| DDQN B | 0.500 | 0.000 | 0.250 ± 0.354 | 23 |
| WP-FTS transfer | 0.500 | 0.500 | 0.500 ± 0.000 | 22 |
| Fixed rule | 0.500 | 0.500 | 0.500 ± 0.000 | 22 |

All values are completion fractions across the same8fixed synthetic cases. Sample
SD describes only variation between the two training seeds; zero MAB/rule SD is
not evidence of population stability. DDQN range[0,.5]; MAB/rule range[.5,.5].
Paired DDQN-minus-MAB and DDQN-minus-rule differences are[0,-.5], mean-.25
(-25percentage points). MAB-minus-rule difference is0for both seeds.

No confidence interval or significance test is reported: n2cannot support a useful
normality check, fixtures were engineered rather than randomly sampled, and the
budget targets plumbing rather than performance inference. No multiple-comparison
claim is made; correction is therefore not applicable. Do not treat16episodes per
method or48rows as independent binomial draws. No bootstrap illusion or best-seed selection.

MAB label feedback is a separate online-training statistic:214/545and208/544correct
actual-request predictions (about39.27%and38.24%). It cannot be compared with old
51.083%survey performance or with task completion. No feedback when no question.

No old0.05regret gate is passed or redefined. Original five-seed B result stays
mean.545,near-optimal0/5; this separate integration has no DP/regret certificate.
