# Increment 7 Task 5 Frozen-Results Independent Review

## Verdict

- **Run integrity: PASS**
- **Result interpretation: APPROVED**

The frozen artifacts support the saved `PARITY` classification and the stated
stop-rule decision to prefer Rule on this deterministic suite. No Task 5
finding remains. This review was read-only: it did not run the pilot, train a
learner, regenerate an artifact, or modify source/configuration.

## Reviewed evidence

I read the approved Increment 7 spec and plan, Task 5 brief, Task 4 final
approved review, Task 5 review package, the complete implementation report,
all four raw JSON artifacts, the complete descriptive analysis bundle and
figure builder/catalog, and both frozen PDFs. I also parsed every raw result
row, loaded each evaluation checkpoint read-only, and visually inspected a
render of each PDF.

All SHA-256 values in `task-5-review-package.md` match the reviewed bytes,
including the four JSON artifacts, three checkpoints, implementation report,
continuation checkpoint, three analysis Markdown files, and two PDFs. The run
manifest's seven source hashes match the current frozen sources. Its result,
suite-manifest, scenario, checkpoint, selected-after-validation, canonical
config/criteria, criteria-file, and feature-layout bindings also match.

The durable record reports one exact default invocation, exit `0`, empty
stderr, complete one-line stdout, `1081.5 s` orchestration time and
`1078.4561935000238 s` runner time, with no interruption, restart, recovery,
reseed, tuning, or rerun. Final progress is exactly
`COMPLETE/artifacts_complete/error=null`.

## Raw denominators and aggregate recomputation

The raw evaluation grid is exact and unique:

```text
3 seeds x 2 splits x 4 methods x 8 scenarios = 192 rows
```

Every row contains exactly 50 episodes. Thus each seed/split/method aggregate
contains eight scenario rows and 400 episodes; each method/split contains 24
rows and 1,200 episodes; and each test family/method contains three seed rows
and 150 episodes. There are no missing, duplicate, or unexpected coordinates.

For every row, protocol/base rates equal their success counts divided by 50,
action counts sum to decisions, permission-request plus refresh counts equal
prompts, outcome counts sum to episodes, and the protocol-success outcome count
matches protocol successes. Family, carrier, scenario and split identities
match the suite manifest. All 24 saved per-seed/split/method aggregates exactly
match recomputation for protocol/base macro, episodes, prompts, decisions,
truncation and safety.

The suite contains 40 unique family/carrier pairs and exact disjoint 24/8/8
registries. Regenerating the typed suite reproduces the saved suite and split
hashes. Each of three seeds has exactly two 24-scenario learner quota maps, and
every quota is 500, giving 12,000 transitions per learner and seed.

Independent test-row recomputation gives:

| Method | Protocol macro | Base macro | Prompts/success |
|---|---:|---:|---:|
| Random | 0.0525 | 0.1375 | 8.7301587302 |
| Rule | 0.8750 | 0.8750 | 1.5714285714 |
| Tabular-Q | 0.0533333333 | 0.1241666667 | 9.6718750000 |
| DDQN | 0.8750 | 0.7916666667 | 1.7142857143 |

DDQN and Rule have identical protocol success on every held-out family: `1.0`
on F0, F1 and F3--F7, and `0.0` on F2. DDQN therefore solves 7/8 scenarios,
has zero paired seed wins over the per-seed best simple method, is worse by
more than 0.10 on zero scenarios, and has a DDQN/Rule prompts-per-success ratio
of `1.0909090909`.

## Gate and safety

All validation and test rows contain zero mask violations, unauthorized
committed effects and monitor-blocked attempts for every method. The saved and
independently recomputed gate checks are identical:

- core checks: all pass;
- Deep-RL advantage margin: fail (`0.875 - 0.875 = 0.000 < 0.05`);
- paired seed wins: fail (`0 < 2`);
- scenario-loss bound: pass (`0 <= 2`);
- prompt-ratio bound: pass (`1.0909090909 <= 1.10`).

The exact classification is therefore `PARITY`, not `ADVANTAGE_SIGNAL` or
`NO_GO`.

## Checkpoint and evaluation immutability evidence

Read-only loading of seeds 17, 29 and 43 reproduces each checkpoint byte hash,
seed identity, DDQN fingerprint, Tabular-Q fingerprint, 12,000 environment
steps and 2,937 optimizer steps. File hash, size and modification time remain
unchanged by inspection. For each seed, the saved `checkpoint`,
`before_validation`, `after_validation`, `before_test` and `after_test` learner
digests are identical, and the independently loaded evaluation fingerprint
matches that shared digest. Checkpoint hashes also equal the
`selected_after_validation` hashes.

## Analysis and figure evidence

The descriptive tables reproduce the raw macro, per-seed and per-family
values. The method figure uses the unweighted eight-scenario macro within each
seed, then shows the mean, sample SD and all three seed points. The family
figure uses the three seed rows for each held-out family/method and shows their
mean and sample SD. Both PDFs are single-page grayscale vector PDF 1.4 files
with a full `[0,1]` y-axis, readable labels and legends, correct hatches/error
bars, and no clipping or misleading scale. Their plotted Rule/DDQN tie and
shared F2 failure agree with the raw rows and catalog captions.

The analysis correctly treats three seeds and eight fixed held-out scenarios
as the descriptive units. It does not treat the 50 repeated episodes as users
or independent experimental replications, and it makes no p-value,
confidence-interval or statistical-significance claim.

## Approved claim boundary

Allowed: this one frozen deterministic 40-context suite produced an
exploratory held-out `PARITY` result; DDQN matched Rule on protocol macro,
numerically exceeded Random under the frozen metrics, and recorded zero saved
safety events.

Not supported: a Deep-RL advantage, statistical significance, generalization
to users or unseen protocols/vocabulary, robustness beyond the eight test
scenarios, deployment readiness, or resolution of deferred B2B1/B2B2
hardening. Any later study must remain a new preregistered experiment rather
than a replacement or tuned rerun of this artifact.
