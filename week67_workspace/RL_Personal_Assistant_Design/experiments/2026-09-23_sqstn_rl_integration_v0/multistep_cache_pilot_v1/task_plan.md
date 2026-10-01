# Multi-step S-QSTN cache pilot v1 — task plan

2026-09-23 user request: extend real synthetic responses into a small pre-fixed
multi-step cache including denial and permission changes, then compare DDQN, MAB
and a fixed rule under a common explicit protocol. New API budget: USD4 total.
No large online training. Prior instruction waives repeated step approvals.

## Phases

- [x] Inspect history-sensitive cache/authority/feature boundaries and define a
  finite legal controller protocol that can be cached without substituting answers.
- [x] Freeze bilingual data, call budget, coverage gates and comparison specification
  before any paid request. Save implementation steps and self-review decisions.
- [x] Minimal isolated implementation and bounded offline checks; preserve all v0 files.
- [ ] One bounded API collection, no retries; audit and freeze the resulting cache.
- [ ] Only if cache coverage is complete, prepare/run the fixed cache-only comparison
  on an available server GPU; no local neural training or online API during learning.
- [x] Archive the stopped run's available evidence, limitations and continuation beside prior records; no completed comparison exists.

## Hard constraints

- Use existing o4-mini local credential configuration, credentials in memory only.
- New campaign USD4 maximum, explicit call cap to be frozen before collection.
- No overwriting old data/source/defaults, old held-out test opening, tuning or seed search.
- First actual runtime/API failure: stop and preserve evidence; no auto recovery/retry.
- Real model answers are not forced, rewritten, resampled to reach desired label counts,
  or substituted between different histories. Missing denial/permission-change coverage
  blocks the intended comparison rather than producing a false completed dataset.
- Scientific claim: small synthetic cached-environment pilot, not human realism,
  generalization or proof of DDQN superiority. Learned-reward objectives differ.

## Current checkpoint

2026-09-23 17:33 UTC: STOPPED_NO_RETRY. Sole collection17:30:01–17:31:12UTC,exit1;
9validAPIanswers,USD0.0259314estimated,2completegraphs,thirdgraphpartial,training0.
Actual fourth request history exceeded the incorrect per-graph bound3 BEFORE SEND.
No API/network failure; reproduce original guard offline with the same3recorded
responses and matching semantic keys. IntegrityPASS does not imply coveragePASS.
See BLOCKER_zh.md/BLOCKER_en.md and interruption_verification.json.
Do not fix/relaunch/resample/increase caps/prepare GPU package automatically.
Await discussion on a revised branch-count budget; preserve9answers andUSD4total.
The frozen specs and collection evidence remain immutable. Old run unchanged.
