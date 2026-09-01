# WP-FTS Online MAB Implementation Report

## Status

**Complete.** The final implementation is the single online MAB baseline
**WP-FTS** (warm-started personalized factored Thompson sampling), evaluated
under the canonical-comparable v2 protocol.

It is a **randomized sequential online-feedback replay simulation using human
stated-policy labels**. It is not a live deployment, a QSTN-validity result,
a measurement of realized disclosure harm, or a CMDP result.

## Final protocol

- The four factored actions, governed features, and selected-action reward are
  unchanged from the canonical offline MAB:
  \(r_t=\mathbb{1}[a_t=y_t]\).
- The global Factored-TS prior is trained using the canonical offline setting,
  Thompson exploration \(=2.0\). Personal online Thompson sampling is tuned
  separately.
- Each held-out user starts from an independent tempered state,
  \(\Lambda_{u,0}=I+\kappa(\Lambda_0-I)\), \(b_{u,0}=\kappa b_0\), and can
  update only from that user's own previously revealed selected-action binary
  feedback.
- `(participant_id, query_id)` is atomic: all rows receive actions before a
  bundle's labels are revealed and updates occur.
- Three aligned test roles are emitted: WP-FTS, a matched stochastic frozen
  control, and a canonical global-greedy offline reference.
- The static reference reproduces the prior offline Factored-TS result exactly
  for its shared seed-101 regression check.

## Frozen configuration and checks

| Item | Result |
|---|---:|
| Validation-selected \(\kappa\) | 0.01 |
| Validation-selected personal TS exploration | 0.5 |
| Canonical global training exploration | 2.0 |
| Held-out users / rows per stream | 41 / 3,323 |
| Paired replay streams | 20 |
| Bootstrap replicates | 5,000 participant clusters |
| Unit tests | 14 / 14 passed |
| Canonical seed-101 regression | passed |
| Split/feature/bundle/update leakage guards | all passed |

## Headline result

Against the matched frozen control, WP-FTS improves pooled stated-policy JEM
by **8.872 pp** (95% participant-cluster CI **[4.595, 13.830] pp**). Against
the canonical frozen-greedy offline baseline, it improves JEM by **7.173 pp**
(CI **[2.789, 12.162] pp**) and has a lower observed survey-derived false
allow rate (100.0% to 98.538%; difference **-1.462 pp**, CI **[-2.980,
-0.281] pp**). This second comparison is not mechanism-matched, so it does
not isolate the effect of online updates on false allow.

The false-allow result remains far too high for a safety claim. It is a
stated-preference violation diagnostic, not a measurement of real privacy
harm, and the result does not establish safe autonomous permission revocation.

For the full Chinese interpretation, including the distinction between the
matched mechanism control and the canonical offline baseline comparison, see
`RESULTS_COMPARISON_zh.md`. Machine-readable artifacts are in
`results/participant_heldout_wp_fts_v2/`.
