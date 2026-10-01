# Task plan — S-QSTN / RL minimal integration v0

## Goal and authorization

2026-09-23: the user requested all three proposed work packages: freeze DDQN B,
connect the minimal S-QSTN public-user interface, and add a same-environment MAB
comparison. Any server GPU is now permitted, subject to fresh resource checks.
Ask the user before live S-QSTN API use. Never persist connection coordinates,
passwords, API keys or private credentials. Keep all experiment records locally.

## Scope and preservation

- New integration version; preserve Family-3 v2 and Budget-Recourse source/results.
- B is a working hyperparameter candidate, not a global optimum or a successful
  near-optimality claim. No parameter/seed search or default-source promotion.
- Existing held-out tests remain locked. Engineering fixtures are not test data.
- No old checkpoint is automatically compatible with a changed observation/action
  schema. API wiring, matched learning, and scientific conclusions are separate.
- First real execution failure: retain evidence, stop, discuss; no automatic retry.

## Phases

- [x] 1. Pin B configuration and evidence provenance; retain every seed and failure.
- [x] 2. Inspect existing public-user, S-QSTN v2, and MAB boundaries; write a concise
  bilingual integration specification and self-review it.
- [x] 3. Obtain written-spec approval, then write/review the implementation plan.
- [x] 4. Implement the public adapter, four-response lifecycle and deterministic
  fixture/cache path; add bounded safety and reproducibility checks.
- [x] 5. Add the genuine MAB control adapter and matched evaluation harness.
- [x] 6. Run the approved bounded offline/GPU pilot, archive results, and request
  API access/model/budget before any live S-QSTN call.

## Process boundary

The user approved the written specification and waived all further step-by-step
confirmations. Execute IMPLEMENTATION_PLAN.md sequentially, with one final
independent read-only review. Stop at a real post-implementation failure or missing
API authority; expected missing-feature RED checks are not runtime failures.

## Errors encountered

- Windows sandbox helper lock failed on local read-only commands. Retried scoped
  reads through approved escalation; unrelated to the server or training.
- Week67 is not a Git root. The actual repository is ai_agent_permission_experiment.
- Repository status under the escalated identity reported dubious ownership. Use
  per-command safe.directory for read-only Git inspection, not a global change.
- Initial MAB search assumed online_mab/src and online_mab/scripts, which do not
  exist; discover the actual implementation before naming an adapter dependency.
- Documentation apply_patch attempts were blocked by the Windows sandbox helper.
  The batch launcher also lost multiline argument boundaries; use the launcher
  executable directly under approved permissions. No product/server failure.

## Current status

COMPLETE_OFFLINE_INTEGRATION_FIXTURE_COMPARISON_AND_LIVE_API_SMOKE.
B freeze unchanged. New fixture/cache bridge, public31/candidate16 features and
genuine WP-FTS transfer implemented.11interface/1receipt/1CUDA checks pass.
One GPU0 run:4800steps,48dev rows,4learned checkpoints,exit0,45.32seconds process.
DDQN seeds1301/1601=4/8,0/8;MAB and rule=4/8each seed. No seed excluded/retrained.
Full archive6100955bytes downloaded; source/config/checkpoint and2451chain-pair
postflight verification PASS. Safety/fault counts0; test closed; local torch not
imported. See full dated report, analysis-output and postflight_verification.json.
Server GPU released and hidden controller89672 closed exit0; no active experiment
or monitoring remains. Do not reconnect/relaunch/redownload this completed run.
Live API authorization subsequently supplied: existing local.env/o4-mini, USD4,
at most4answers. Separate live_api_smoke_v1 completed once atUTC16:59:19–16:59:49,
exit0:4valid answers,2allow_reuse/2allow_once,USD0.0116292 estimated,zero safety/faults.
Four cache-only replays and postflight verification PASS; frozen46local files unchanged.
No training, server access, old test or extra calls. Read live_api_smoke_v1/REPORT_zh.md.
Do not relaunch the completed run; the four-call authorization is consumed.

## Continuation

Read this file, notes.md and REPORT_zh.md before resuming. Preserve all prior
experiment evidence. Network interruption must not cause training to be restarted.
