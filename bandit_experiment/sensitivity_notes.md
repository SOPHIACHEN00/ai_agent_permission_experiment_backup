# Notes: Reward-weight sensitivity analysis

## Protocol

Pending.

## Verification

- Syntax compilation passed.
- Smoke-tested Access and Persistence learning on 1,000/200-row subsets.
- Verified all requested reward tables normalize to [-1, 1].
- Verified all rate metrics remain in [0, 1].
- High unnecessary-access weights can intentionally make the reward oracle prefer deny over a participant's allow label for explicitly unnecessary data; this is the safety-preference tradeoff under study, not a mapping error.

## Findings

- All 12 pre-specified contrasts changed in the same direction for all 10 common seeds: raw two-sided Wilcoxon p=0.001953, global Holm p=0.023438, matched rank-biserial magnitude 1.0.
- Task utility 0.0→0.5 increased necessary-data allow by 1.48–2.60 percentage points depending on algorithm.
- Unnecessary-access penalty 0.5→2.0 reduced unnecessary access by 33.01–35.59 points.
- Interruption cost 0.05→0.25 reduced ask actions by 14.37–15.28 points.
- Over-persistence cost 0.5→2.0 reduced persistent over-allow by 23.34–23.94 points.
- UCB candidate `task=0.1, unnecessary=2.0` retained 99.90% necessary allow while reducing unnecessary access to 13.34%, but over-sharing remained 72.16%.
- The more conservative UCB `task=0, unnecessary=2.0` reduced unnecessary access to 4.64% and over-sharing to 66.88%, with 98.13% necessary allow.
- Access tuning separates task necessity from preference mismatch: it can suppress explicitly unnecessary data but cannot by itself solve deny preferences on necessary data.
- Persistence has no single dominant point: UCB `(0.05, 2.0)` gives 1.95% persistent over-allow but 98.03% ask rate; `(0.25, 0.5)` gives 51.13% ask rate but 35.59% persistent over-allow.
- Statistical inference is limited to order/exploration variability on one participant split; population generalization requires repeated participant splits.
