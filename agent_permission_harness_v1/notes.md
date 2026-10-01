# Implementation notes

- User chose RL interface/integration tests, not training.
- Existing six-action enum: REQUEST_AUTHORIZATION, REQUEST_REFRESH, DISABLE_LOCAL_AUTHORIZATION, EXECUTE_WITH_AUTHORIZATION, DENY_WITH_REASON, ESCALATE.
- Core scope matcher supports subset fields, resource-prefix grants, and shorter retention while tool/operation/purpose/recipient must match.
- v0 TaskEngine requires exact manifest scope. New adapter will explicitly allow predeclared execution projections without changing the old core.
- v0 mock catalog covers 28 raw external labels. Internal mira requires its own protected read path.
- Single-threaded synthetic effects and ledger settlement retain the local harness crash-consistency limitation.
- Original static questionnaire contains 65 queries/373 contexts; frozen pilot contains 56 queries/250 contexts and excludes query22.

## Progress / test evidence
Implementation evidence will be appended per module. Tests must exercise real ledger/monitor/store effects; only the external LLM and human endpoint are injected.

- Initial main tests RED: missing candidates/compiler/runner/transport. Added modules, then GREEN.
- Debugged persistent DENY_PERSIST bypass via requesting a broader grant for the same denied pending need; now all such requests masked. Changed future needs evaluated independently.
- Corrected test's ledger insertion-order assumption: core records() sorts by ID. Scope lifecycle assertions follow request-created IDs.
- Human replay hardening: per-channel unique message IDs and once consumption.
- Prepared-effect hardening: immutable nested state, genuine issued-object identity, stale/foreign rejection.
- Independent reviewer found missing search resource silently expanding to whole-tool collection. Reproduced RED, fixed explicit collection aliases, GREEN; reviewer confirmed monitored missing-resource effect absent, zero exposure, grant preserved.
- Reviewed boundaries: local Python harness trusted, no OS sandbox or semantic free-text DLP claim. API session budget/no-retry and CLI existing-output guard reviewed.
- Full v1 suite72 tests GREEN; old v0 suite29 GREEN; original authorization27 + execution25 GREEN. Entire old long RL training suite intentionally not run; no extrapolated full-core claim.
- Offline six-action episode:5 planner turns,8 controller steps,3 permission prompts,1 escalation,2 read effects,oracle/audit success. Fixed hand-authored policy, not trained RL.
- Offline q22:4 turns,6 controller steps,3 prompts,search/read/local-send actual effects,zero excess fields,oracle/audit success.
- Live q22 new v1 session completed:7 model responses,3 compiler-rejected intents,3 actual effects,oracle/audit success. API estimate USD0.0134926; previous smoke cumulative USD0.0148082, no automatic transport retries. Rejected-proposal full parameters not preserved; future trace improvement, not reconstructed claims.
