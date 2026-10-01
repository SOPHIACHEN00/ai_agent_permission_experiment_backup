# Integration notes

## Confirmed starting point

- Latest five-seed confirmation: B mean exact validation value 0.5450 versus
  A 0.4335, four improvements and one tie, B near-optimal 0/5. Test remained locked.
- Family-3/Budget-Recourse currently uses DeterministicAllowReuseUserV2, so a real
  refusal cannot safely be substituted without changing the environment contract.
- General pa_rl.scripted_user.ScriptedUserAdapter already exposes reset,
  observe_event and answer_permission with public allowlists and four choices.
  Its public scenario validator is horizon 3–8; the Budget-Recourse horizon is 12.
  Reusing it blindly would therefore be incompatible even before denial handling.
- S-QSTN v2 has an existing bounded verified-event memory/rule/prompt pipeline.
  Its one-item smoke is not an RL integration runner and has no reusable RL cache.
- Old MAB label agreement and sequential task success remain distinct endpoints.

## Sources inspected

- ai_agent_permission_experiment/rl_personal_assistant/docs/CONTINUATION_CHECKPOINT.md
- experiments/2026-09-22_family3_next_stage/stage_b/five_seed_confirmation_gpu0_v1/
- ai_agent_permission_experiment/rl_personal_assistant/src/pa_rl/scripted_user.py
- ai_agent_permission_experiment/qstn_simulator/RULEPACK_V2.0_README.md
- ai_agent_permission_experiment/qstn_simulator/scripts/v2/smoke_test_openai_qstn_v2.py

## Resolved boundaries

- PermissionEnvironment already accepts adapter_factory and applies all four
  responses through AuthorizationService; use it for the new short fixtures.
- Request schema has no requested once/reuse mode. The minimal MAB adapter must
  disclose collapsed initial allow predictions, not pretend to provide that control.
- Environment verifies its chain before delivering PublicEvent projections, but
  the projections have no standalone source authentication/logical timestamp.
  Use trusted delivery and episode-local order, not type checks as origin proof.
- WP-FTS lives in online_bandit_experiment/wp_fts.py and its factored bandit in
  bandit_experiment/run_stated_policy_bandit.py. Only selected components receive
  feedback after an actual response; no counterfactual labels for unasked requests.
- New public-feature transfer is not the historical survey checkpoint. Different
  feedback objectives are disclosed; this is not a pure credit-assignment ablation.

## Freeze and review boundary

UTC2026-09-23T15:40:19:30/30 evidence hashes and five B checkpoint receipts/parameters
match. Full original ZIP remains40622664bytes with SHA256
25e97d8cae25599625429fcfe98a036a1d89502621db8699c5a0b656986baec3.
No model run, source/default change, server or API connection. B's near-optimal0/5
remains unchanged. Chinese/English specs self-reviewed, written-spec approval
pending; no new integration code or scientific experiment result exists yet.

## Final update — the above approval boundary is historical

User subsequently approved the spec and waived step confirmations. Offline v0
implemented and one GPU0 fixture pilot completed. See REPORT_zh.md, dated full
report,postflight_verification.json andanalysis-output.4800steps/48rows/4models,
exit0;DDQN4/16(MAB/rule8/16),safety0. Fixed-response engineering, not realAPI nor
convergence evidence. Key limits:DDQN1601immediateexit,1301reaskloops;237updates
below250targetsync;MAB/ruleall16actiontracesequal;disablefixtureisnotforcedintervention.
48source/confighashes,2451audit chain pairs andallcheckpoint/evaluationfingerprints
verified locally, completeZIP preserved. GPU/controller closed; no active run.
Only liveAPI configuration/model/cost coordination remains. Do not rerun v0.
