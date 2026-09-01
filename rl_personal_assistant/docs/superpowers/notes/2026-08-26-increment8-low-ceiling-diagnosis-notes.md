# Increment 8 low-ceiling exact diagnosis notes

## Authorization and boundary

- User authorized a read-only exact failure decomposition after Task 8F triggered the DP stop rule.
- Target graphs: `i8_s0_v9`, `i8_s1_v8`, `i8_s3_v7`, `i8_s3_v9`.
- No graph, probability, budget, outcome, gate, source behavior, or frozen artifact may be changed.
- No policy training, smoke run, validation, or official test may run.
- Stop and discuss if the exact loss cannot be uniquely attributed or if model/graph semantics conflict.

## Questions

1. What exact probability mass reaches success versus each terminal failure class under an optimal policy?
2. Which loss is unavoidable stochasticity after an optimal action, and which is induced by budget/outcome constraints?
3. Are any low ceilings caused by a graph-generator or lifecycle-model defect rather than intended design?
4. What research-definition change, if any, is justified without using learner results?

## Status

**COMPLETE.** Evidence collection was read-only and exact; no benchmark changes or training occurred. Increment 8 remains `INVALID_RUN_BLOCKED` pending a user-approved v1 research decision.

## Methodological finding

- Raw terminal reason is not generally invariant across Bellman-optimal policies. Once a stochastic branch enters a nonterminal state with exact DP value zero, all later zero-return actions can tie, so a lexicographic policy may label the same underlying loss as deny, escalate, prompt failure, exposure failure, or horizon exhaustion.
- Stable attribution therefore uses the first transition from positive DP value to zero DP value, followed by exact resource-feasibility checks. Terminal labels are secondary path diagnostics only.

## `i8_s3_v7`

- Reachable states: 727; exact initial DP success `9/20`; failure `11/20`.
- Initial unique optimum is request authorization, followed by execute. First workload draw: EXACT `1/2` reaches value `9/10`; BROADER `2/5` reaches value zero; DISJOINT `1/10` reaches value zero.
- After the first EXACT branch, the next execute is uniquely optimal. Its BROADER branch (`1/10`, joint mass `1/20`) reaches value zero; EXACT (`4/5`) and DISJOINT (`1/10`) remain successful.
- Stable mutually exclusive root-cause partition: exposure infeasibility `9/20`; prompt-budget × utility-target infeasibility `1/10`; decision-contingent success loss `0`.
- The two BROADER dead states require minimum successful exposure thresholds 16 and 18 against budget 10. The first DISJOINT dead state needs a third prompt to reach target 5, but prompt budget is 2.
- No implementation/spec mismatch was found. The low ceiling follows from the frozen combination of horizon 9, target 5, prompt budget 2, exposure budget 10, medium reuse, and high scope-change.

## `i8_s3_v9`

- Reachable states: 53,370; exact initial DP success `6127/50000`; failure `43873/50000`.
- Initial request and following execute are each uniquely optimal. The first workload draw alone sends BROADER mass `16/25` directly to value zero; EXACT `1/5` retains conditional value `1083/2000`, and DISJOINT `4/25` retains conditional value `89/1000`.
- Stable first-zero frontier over the whole episode: BROADER `197117/250000`, EXACT `32/625`, DISJOINT `1181/31250`; these sum exactly to failure `43873/50000`.
- Exact existential resource relaxation on the 17 first-zero states: exposure-only relaxation restores positive feasibility for mass `7989/10000`; joint prompt+exposure relaxation is required for mass `491/6250`; horizon/target residual is zero.
- Within failure mass, approximately 91.047% is exposure-dominant and 8.953% requires prompt and exposure jointly. Decision-contingent success loss is zero.
- No implementation/spec mismatch was found. The frozen `target=7`, low reuse, high scope-change, prompt budget 3, and family-adjusted exposure budget 16 make the v9/s3 graph structurally low-ceiling.

## `i8_s0_v9`

- Exact initial DP success `8/25`; failure `17/25`.
- Stable first-zero frontier under the frozen optimal-set lexicographic resolution: EXACT `1/5`, BROADER `52/125`, DISJOINT `8/125`; these sum to `17/25`. Oracle residual loss before first-zero entry attributable to a suboptimal action is zero.
- Budget recoverability: increasing prompt budget from 3 to 4 alone restores positive feasibility for mass `53/125`; mass `32/125` requires that prompt increase together with exposure budget 30. Exposure-only restores none.
- The successful oracle path begins `REQUEST → DISABLE → REFRESH → EXECUTE`. These nonexecution actions advance `logical_step`; DISJOINT task utility is defined from that controller step. The oracle therefore pads the clock before executing so that a later disjoint task receives greater utility.
- This clock-padding behavior matches the frozen spec and code, so it is not an implementation mismatch. It is a scientific benchmark-misspecification risk because unrelated authorization churn can manipulate the exogenous workload value being optimized.

## `i8_s1_v8`

- Exact initial DP success `50161/100000`; failure `49839/100000`.
- Stable first-zero frontier: BROADER `45422/100000`, DISJOINT `4417/100000`, EXACT zero; these sum to the full failure mass. Oracle residual loss before first-zero entry attributable to a suboptimal action is zero.
- Budget recoverability: exposure budget 30 alone restores positive feasibility for mass `9491/25000`; mass `19/160` additionally requires prompt budget 4. Prompt-only restores none.
- The first BROADER branch (`1/4`) is immediately irrecoverable. Conditional success after first EXACT is `2596/3125`; after first DISJOINT it is `69/200`.
- No implementation/spec mismatch was found. Exposure is the dominant limiting resource under the frozen parameter composition.

## Synthesis

- The four initial DP success values are `8/25`, `50161/100000`, `9/20`, and `6127/50000`.
- For every target graph, the entire oracle failure mass is first triggered by a workload draw from a positive-value state into a zero-value state; the controller actions before that transition are Bellman-optimal. This is a statement about oracle residual failure, not a claim that arbitrary learned policies cannot make decision errors.
- Resource feasibility, not Markov aliasing or an authority-safety failure, explains the low ceilings. Prompt is primary in `s0_v9`; exposure is primary in `s1_v8`, `s3_v7`, and `s3_v9`; a smaller portion needs joint prompt/exposure relief.
- Code matches the frozen v0 specification. The diagnosed problem is scientific design: the absolute raw-success gate was not calibrated to the stochastic budget distribution, and the controller-time-dependent DISJOINT utility permits clock padding.
- Exact graph probabilities are analytic MDP quantities, not sampled runs or independent subjects. Confidence intervals, significance tests, and winner claims are inapplicable here.
