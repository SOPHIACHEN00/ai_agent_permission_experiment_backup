# Minimal S-QSTN–RL integration and matched MAB pilot v0

Date: 2026-09-23. Status: **USER_APPROVED; further step-by-step confirmation waived. Implementation status: progress.md.**
This is the English counterpart of SPEC_zh.md; the Chinese specification governs
ambiguities. The user approved the three work packages and use of any available
server GPU. Live API access/model/budget still require explicit coordination.

## Scope and selected approach

Freeze DDQN B and all five confirmation seeds; connect the existing S-QSTN v2
prompt/memory pipeline to the general PermissionEnvironment user factory; add a
same-environment DDQN / MAB-transfer / fixed-rule engineering comparison.

Use the existing general environment (horizon 3–8), which already handles four
permission responses. Do not change the frozen Family-3 or Budget-Recourse tasks,
18-dimensional checkpoints, DP certificates, results or held-out tests. Directly
extending the horizon-12 Budget-Recourse model would require wider task/state
changes; immediate large live-API training would precede cache and cost validation.

New code belongs in ai_agent_permission_experiment/rl_sqstn_integration_v0/.
This directory holds local specifications, configuration, receipts and downloaded
evidence. Explicitly select and hash the actual imported pa_rl root; two copies
exist and must not be accidentally interchanged by sys.path ordering.

## Public interface and authority

Reuse reset(public_scenario, seed), observe_event(verified_public_event), and
answer_permission(public_request, public_history). Only request/refresh asks the
respondent; execution, disabling and fallback do not require permission answers.

- deny_persist: rejected authorization plus the existing scoped do-not-reask rule.
- deny_reask: rejected authorization; no immediate repeated-prompt entitlement.
- allow_once: one-use grant consumed only after a committed protected effect.
- allow_reuse: scoped, expiring, revocable reusable authorization.

Only the authorization service and reference monitor create/use authority. A
refusal is valid feedback, not a runtime failure. Malformed output, timeout,
unknown scope and cache misses fail closed and are recorded as adapter faults,
not silently converted into valid scientific episodes or replacement answers.

Resolve opaque scope identities through the episode's public TaskStep/scope map.
Never send full manifests, scripted answers, hidden evaluator conditions or future
branches. Reject unknown/missing context instead of inventing question semantics.
An audited public answer record (request, choice, scope, logical step) is available
to every policy, never exclusively to MAB, without applying authority twice.

## S-QSTN, events and cache

Reuse v2 rulepack/contract/rendering/injection/bounded memory with a synthetic
persona, not human participant records. Accept events only from trusted environment
dispatch; a PublicEvent type alone is not origin authentication. Maintain episode
sequence-based IDs, not content-only deduplication of legitimate repeated requests.
Map request/grant/revoke/refresh explicitly; refusal is not an agent error and a
blocked operation is not automatically a committed scope violation. Unsupported
ordinary events are logged without fabricated caution updates.

Private memory, rule IDs, caution, persona latents, future answers and full prompt/
cache payloads stay outside controller observations and replay. Cache keys bind
versions, semantic request, public history, persona, actual memory view, prompt,
model and sampling configuration; private-derived keys are not policy features.

Modes: fixture (explicit synthetic answers through the real prompt/memory/parser
pipeline), cache_only (exact semantic hit or stop), live (disabled until API
coordination). Strictly parse four labels; no hidden network fallback or reuse of
an answer merely because it is the same question ordinal. Different policy
histories can legitimately require different cache entries. Keep prompt/raw
response artifacts separate from common training logs. Never persist credentials
or server connection coordinates.

## MAB transfer, not historical-model parity

Reuse tempered_factored_copy from online_bandit_experiment/wp_fts.py and
FactoredJointPolicy from bandit_experiment/run_stated_policy_bandit.py. Execute
when valid coverage exists; otherwise deny_persist predicts safe exit, while the
other labels may request permission if permitted by the shared mask. Do not ask
immediately after an actual refusal. Freeze fallback and tie-breaking rules.

The general request catalog has no requested once/reuse argument: both allow
predictions therefore map to the same initial request, and actual response controls
grant lifetime. This v0 limitation is explicit; do not claim the complete proposed
one-time-versus-reusable request strategy has already been implemented.

Use shared public features, not incompatible historical survey weights. Within
each training budget, the first half fits global FTS and the second half adapts an
independent tempered copy. Freeze kappa=.01, global exploration=2.0 and personal
exploration=.5. Update only selected access/persistence components, after a real
public response, with joint label agreement. No request means no counterfactual
label or update. Name the method wp_fts_public_transfer_v0. It is an algorithm
transfer, not a reproduction of the historical 51.083% weights/result. Disclose
its label-feedback objective versus DDQN task reward; this is a system comparison,
not an isolated long-term-credit causal ablation.

## Bounded pilot

DDQN uses the eight frozen B hyperparameters with a newly declared and frozen
public encoder/action schema and fresh initialization; old 18-dimensional weights
are not assumed portable. The fixed rule executes under valid coverage, otherwise
requests, then safely falls back after refusal, without reading fixture answers.

Four synthetic train and eight dev fixtures cover four responses, one-use
consumption, reuse, refusal and disable/refresh. Do not access historical held-out
tests. Fix seeds1301/1601, 1200 interactions per learned method per seed: 4800
total training interactions across DDQN and MAB. MAB splits each budget into600
global and600 personal steps. Use the same predefined fixture schedule/interface,
record actual request/feedback counts, and freeze all learning during evaluation.
Three methods × two seeds × eight dev fixtures produce48 terminal records.

One idle server GPU and at most one training process suffice. Recheck physical
device identity/current memory headroom. All GPUs are permitted, not a reason to
increase the budget. Keep runtime files in a new /output/agenticAI/ subdirectory
and download complete evidence locally. Local work is limited to small interface/
format checks, not model training.

Report task success, prompts, fallback, invalid actions, unauthorized effects and
adapter faults; label agreement is separate. Correct safe fallback does not
retroactively redefine the predeclared task-success condition. These dev fixtures
are engineering evidence, not task generalization or a new near-optimality claim.
The historical regret threshold .05 and failed gate remain unchanged.

## Verification, stopping and deliverables

Bounded checks cover the four responses, lifecycle/masks, bad JSON/unknown scope/
cache miss, actual v2 prompt memory, private-feature exclusion, MAB selected-only
feedback, deterministic replay, evaluation immutability and physical CUDA identity.
Expected missing-feature RED checks are not experimental failures. Real runtime,
NaN, safety or resource failures stop with evidence, without automatic repair/retry.
Low success is a result, not grounds for dropping seeds or increasing budgets.

Coordinate secure API configuration, model and request/cost caps before live
execution; the first live phase has at most four permission answers and remains
separate from the fixture pilot. Missing approval means LIVE_API_NOT_STARTED.

Deliver the freeze/provenance, adapter/cache/event bridge, fixed MAB mapping,
bounded runner and complete local results/checkpoint. Separate FREEZE_COMPLETE,
OFFLINE_INTEGRATION_VERIFIED, FIXTURE_COMPARISON_COMPLETE and live API statuses.
The user approved this spec and waived further step-by-step confirmations. Offline
implementation and the fixture pilot are now complete; see REPORT_zh.md for evidence.
Live API remains separately gated. Technical requirements were not changed by results.

Self-review: no historical overwrite/test opening/threshold relaxation; authority
and private-state boundaries explicit; fixture/live and engineering/science
separated; MAB limitations and DDQN incompatibility stated. This document is outside
the existing Git root; no new repository or unrelated commit is created.
