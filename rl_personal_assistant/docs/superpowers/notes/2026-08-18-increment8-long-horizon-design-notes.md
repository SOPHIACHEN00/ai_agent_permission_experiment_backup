# Increment 8 Long-Horizon Design Notes

## Frozen starting point

- Increment 7 is immutable and classified `PARITY`.
- Test protocol macro: Rule `0.875`, DDQN `0.875`.
- Both Rule and DDQN score protocol `0` on `f2_disable_refresh`.
- All evaluation safety counts are zero.
- No Increment 8 code, scenarios, training, or result directory may be created before design approval.

## Research question

Can a sequential neural policy outperform simple public rules when the correct authorization action depends on an earlier grant, a later revocation/disable event, delayed task consequences, and context-dependent future authorization needs?

## Questions under audit

1. Is the existing f2 failure caused by missing public state, insufficient scenario diversity, delayed credit, or the Rule priority itself?
2. Which scenario construction makes a myopic policy genuinely insufficient without hiding the answer in a purpose one-hot?
3. Can the first Increment 8 prototype remain within the existing six actions, scripted user, binary terminal protocol reward, and Masked DDQN?
4. What held-out split tests compositional long-horizon generalization without reusing the Increment 7 test set?
5. What result would justify continuing DDQN, and what result requires preferring Rule or redesigning the environment?

## Constraints

- Preserve Increment 7 artifacts and claim boundary.
- No PPO, live S-QSTN, Security LLM, real tools, or reward tuning in the first Increment 8 prototype unless the approved design demonstrates necessity.
- Policy inputs remain deployable public signals; oracle trace, future responses, audit, family/split IDs, and result labels remain excluded.
- Safety remains enforced by ledger/reference monitor and evaluated separately from reward.

## Root-cause audit

- Existing f2 is not a proven memory/representation failure. Its stages are distinguishable through logical time, authorization status/type/relation, revocation counts, and candidates.
- The public/base-task optimum is currently `REQUEST(ALLOW_REUSE) -> EXECUTE`; there is no public reason to disable the valid reusable grant.
- The hidden canonical benchmark alone requires `REQUEST -> DISABLE -> REFRESH -> EXECUTE`. Rule therefore obtains base success but protocol failure, which is a benchmark-causality mismatch rather than evidence that Rule cannot plan.
- DDQN additionally faces a four-action sparse exact-trace reward and no contrastive scenario showing when reuse is correct versus when a public revocation makes disable/refresh necessary.
- Purpose is one-to-one with protocol family in Increment 7, so it can act as a template label; Increment 8 must break this shortcut.

## Candidate approaches

### A. Budgeted stochastic authorization lifecycle — recommended

- Fully observable stochastic branching MDP, 8–12 decisions.
- Public task value/risk, prompt budget, exposure budget, authorization age/scope/status, and scope-bound user directives.
- Hidden future task stream/regime only; policy never receives regime, future tasks, oracle feasibility, or correct action.
- Terminal binary success requires sufficient task utility, prompt/exposure budgets respected, and zero safety violations.
- Add a public scope-bound revocation/reuse directive and paired branches where identical contexts require either direct reuse or disable→refresh.
- Compatible with current Masked DDQN; DP oracle and strong stateful Rule/FSM are required baselines.

**User decision (2026-08-18): approved as the Increment 8 primary route.** Increment 8 will first test fully observable long-horizon authorization planning. Latent personalization/POMDP and endogenous trust dynamics remain later, separately preregistered studies.

## Frozen reward decision

**User decision (2026-08-18): strict terminal binary reward approved.** Reward is 1 if and only if cumulative task utility reaches its target, prompt count stays within budget, privacy exposure stays within budget, and all safety counts are zero. Otherwise reward is 0. No intermediate shaping reward is used. Public observations may expose task utility and budget counters, but never terminal feasibility or future achievable utility.

## Frozen scenario-role decision

**User decision (2026-08-18): split mandatory and strategic lifecycle scenarios.**

- Mandatory public revocation scenarios verify that the agent obeys an explicit scope-bound revocation and completes `DISABLE -> REFRESH -> EXECUTE`; they are safety/protocol regressions and do not count as evidence of DDQN advantage.
- Strategic lifecycle scenarios contain no direct correct-action instruction. The policy chooses reuse versus disable/refresh using public task value/risk, prompt budget, exposure budget, lifecycle state, and workload information. Only these scenarios enter the primary long-horizon advantage gate.

## Frozen observability decision

**User decision (2026-08-18): public coarse workload forecast approved.** Strategic observations include low/medium/high reuse likelihood and scope-change likelihood, alongside current task value/risk and remaining horizon/prompt/exposure budgets. The exact future task stream, random branch draw, graph identity, and correct action remain hidden. This keeps the first Increment 8 environment Markov for a feed-forward DDQN without exposing future outcomes.

## Frozen privacy-exposure decision

**User decision (2026-08-18): linear active-scope exposure approved.** At each controller decision, exposure increases by the sum over active authorizations of `public sensitivity weight (1/2/3) * number of authorized data attributes`. Reusable authority continues accumulating while active; one-time authority stops after consumption; revoked, expired, consumed, and superseded authority contributes zero. The episode exposes current and remaining exposure budget, not future exposure or terminal feasibility.

## Frozen outcome-semantics decision

**User decision (2026-08-18): outcome-based evaluation approved.** Increment 8 will not require exact equality with one hidden canonical action trace. Any action sequence may succeed if it reaches the public task-utility target, respects prompt and privacy-exposure budgets, complies with explicit scope-bound revocation directives, and has zero safety violations. Canonical paths and the dynamic-programming oracle are diagnostic references rather than the sole accepted behavior.

## Collaboration preference

The user requested fewer incremental confirmation questions. Remaining design choices should use the recommended defaults and be presented as one coherent design for a single final review, rather than asking for approval parameter by parameter.

### B. Latent privacy-preference POMDP

- Calibration tasks followed by challenge tasks; profile inferred only from prior public permission responses.
- Requires history stack or recurrent DDQN/DRQN and a frozen non-LLM user simulator.
- Strong personalization value but higher simulator-validity and circular-evaluation risk.

### C. Endogenous trust/caution dynamics

- Current choices influence hidden caution/fatigue and future approval probabilities.
- Most aligned with the ultimate research vision, but needs calibration/counterfactual validation and should not be the minimal Increment 8 prototype.

## Proposed evaluation boundary

- Baselines: Random, current Rule, stateful Rule/FSM, Tabular γ=0/γ>0, DDQN γ=0/γ>0, evaluation-only DP oracle, and a trajectory/template lookup control.
- Split by non-isomorphic transition-graph structure, not only by carrier.
- Counter-based paired RNG and counterfactual branch-switch tests.
- Safety gates remain exact zero for mask violations, unauthorized effects, and learned-policy monitor blocks.
- A prospective advantage claim requires both a stable γ>0 benefit and an advantage over the strongest simple public baseline; otherwise classify PARITY or NO_GO.
