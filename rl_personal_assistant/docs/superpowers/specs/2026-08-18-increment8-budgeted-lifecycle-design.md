# Increment 8: Budgeted Long-Horizon Authorization Lifecycle

## 1. Objective and decision boundary

Increment 8 tests whether a public-observation policy can make useful long-horizon authorization decisions when keeping an authorization saves future prompts but accumulates privacy exposure. The primary question is whether candidate-scoring Masked Double DQN with `gamma > 0` can outperform myopic learning and strong simple public baselines on structurally held-out stochastic decision graphs.

This is a synthetic, fully observable, finite-horizon Markov decision process. It is not a claim about real users, natural-language understanding, live S-QSTN behavior, production deployment, or hardened replay. PPO, recurrent policies, Security LLMs, Constitutional AI, real tools, and cross-session personalization remain out of scope.

Increment 7 remains immutable. Its `PARITY` result is not replaced or rerun. Increment 8 is a new preregistered experiment with a new suite, observation version, criteria profile, and result directory.

## 2. Why a new benchmark is required

Increment 7's `f2_disable_refresh` protocol required:

```text
REQUEST(reusable) -> DISABLE -> REFRESH(one-time) -> EXECUTE
```

but the public state gave no causal reason to disable a valid reusable grant. The public/base-task optimum was therefore `REQUEST -> EXECUTE`, which the Rule correctly selected. Requiring equality with a hidden canonical trace made protocol failure ambiguous: it did not prove a memory or long-term-planning failure.

Increment 8 removes that mismatch:

- success is determined by public outcome constraints, not equality with one hidden action sequence;
- strategic scenarios expose the variables that make reuse or retirement rational;
- explicit revocation scenarios carry a public scope-bound directive;
- purpose, scenario, family, carrier, graph, and split identifiers cannot act as policy labels;
- stochastic branches and 8--12 decisions create genuine delayed consequences.

## 3. Environment architecture

The suite version is:

```text
increment8_budgeted_lifecycle_v0
```

Increment 8 adds a research-only lifecycle layer around the approved authority components. It reuses the six controller actions, authorization ledger, reference monitor, mock tool, and mediated effect path. It does not weaken or bypass them.

The new subsystem is split into five isolated units:

1. **Typed lifecycle graph generator**: owns graph topology, public parameters, stochastic transition distributions, and the frozen train/validation/test split.
2. **Budgeted lifecycle environment**: composes the existing ledger/monitor/tool path with task utility, prompt budget, exposure accounting, public directives, and graph transitions.
3. **Outcome evaluator**: computes strict terminal binary success from final constraints and never checks equality with a canonical trace.
4. **Public observation and encoder v2**: exposes sufficient Markov state and dynamic candidates while enforcing the public/private/oracle firewall.
5. **Experiment runner**: trains and evaluates frozen baselines with paired counter-based randomness, checkpoints, immutable evaluation, and a replaceable criteria profile.

No graph implementation may import a learned policy. No policy or encoder may import the graph registry, outcome evaluator, audit view, or DP oracle.

## 4. Markov transition contract

Each episode has a public horizon of 8--12 controller decisions. The transition distribution depends only on the current public state, selected action, and a counter-based random draw. There is no hidden persistent regime. Exact future tasks and random outcomes are not exposed, but the public state is a sufficient statistic for their distribution.

The public user-response kernel follows the same rule: it is a deterministic or publicly parameterized function of the current public state and request action. If a response is stochastic, its probability is part of the public state and the realized draw is counter-based. No hidden persistent user type is introduced.

Each decision follows this order:

```text
validated public observation o_t
-> select one mask-valid semantic candidate
-> dispatch through the existing authority/monitor path
-> update prompt count and committed task utility
-> accrue one interval of exposure from authorizations active after the action
-> evaluate irreversible failures and natural-completion conditions
-> if a task effect committed and the episode is still open, draw the next task/branch
-> otherwise retain the same pending task and consume no workload-branch draw
-> emit o_(t+1)
```

This timing means an immediate `DISABLE_LOCAL_AUTHORIZATION` prevents the disabled grant from accruing exposure for the next interval. A reusable grant that remains active continues to accrue. A one-time grant consumed by a committed effect does not accrue after consumption.

Only a committed task effect advances the workload kernel. `REQUEST_AUTHORIZATION`, `REQUEST_REFRESH`, and `DISABLE_LOCAL_AUTHORIZATION` consume a controller decision and accrue exposure but leave the current required task pending and do not address `scope_relation` randomness. `DENY_WITH_REASON` and `ESCALATE` close immediately. This rule applies identically to strategic and mandatory graphs.

The existing terminal `DENY_WITH_REASON` and `ESCALATE` semantics remain terminal. There is no new WAIT action and no change to the frozen six-action catalog.

The episode closes successfully only through the natural-completion predicate in Section 4.1 or a constraint-valid horizon/graph exhaustion accepted by Section 7. Merely reaching the numeric utility target is insufficient while a required task remains pending. An irreversible constraint/safety failure closes immediately with reward 0; prompt/exposure overrun and directive violation are monotonic failures.

### 4.1 Frozen global workload kernel

There are no graph-private transition rules. Every strategic graph is an initial public-state vector passed to one global kernel. After a committed task effect:

```text
P(EXACT next scope)    = p_reuse
P(BROADER next scope)  = (1 - p_reuse) * p_scope_change
P(DISJOINT next scope) = (1 - p_reuse) * (1 - p_scope_change)
```

`p_reuse` and `p_scope_change` are the public `low/medium/high` values. EXACT retains the scope, utility, and sensitivity. BROADER adds the carrier's frozen broader-only attribute and sets next utility/sensitivity to `min(3, current + 1)`. DISJOINT moves to the next carrier in the frozen carrier ring and uses that carrier's public sensitivity plus utility `1 + ((current_utility + logical_step) mod 3)`. Here `logical_step` is the one-based controller-decision index of the action whose committed effect triggered this workload draw; request/refresh/disable decisions therefore advance public logical time even though they do not themselves draw a branch.

Forecast categories update by one global rule: EXACT moves reuse one level up and scope-change one level down; BROADER moves reuse one level down and scope-change one level up; DISJOINT sets reuse=`medium`, scope-change=`high`. Category indices are clipped to `low..high`.

The current public scope deterministically defines the strategic permission offer: sensitivity 1 or 2 offers `allow_reuse`, while sensitivity 3 offers `allow_once`. Mandatory graphs expose `authorization_objective=reusable_then_one_time_replacement` from reset: their initial request offers `allow_reuse`, and the bound replacement refresh after verified disable offers `allow_once`, regardless of carrier sensitivity. The objective/offer mode is a public kernel parameter, not a hidden response or a post-grant discriminator. Thus every v0 response is deterministic and public-state-derived. Adding stochastic or latent user preference requires a new spec/version.

Natural completion is emitted automatically after an effect leaves no pending required task and the utility target is met, or at horizon/graph exhaustion when those conditions hold. Reaching the numeric utility target while a required task remains pending does not close successfully.

### 4.2 Dynamic authorization candidates

At most three authorizations may be active simultaneously. A fourth authority-creating request is mask-invalid until an active grant is retired or superseded. Observation v2 may expose up to 16 candidates:

- one request for the current task;
- up to three executions, one per covering active authorization;
- up to three refreshes, one per related refresh-eligible authorization;
- up to three disables, one per active authorization;
- one deny and one escalate candidate.

When more than three related refresh-eligible priors exist, a prior bound by an active `replacement_mode=refresh_required` is selected first, followed by the lowest public authorization ordinal ranks until exactly three are selected. Nonselected priors remain visible in the public lifecycle summary but are not actionable in that decision. The same deterministic selection is used by the environment, Markov audit, DP oracle, and every policy view.

Each verified request-created event assigns a public, monotonically increasing `issuance_ordinal` that is unique within the episode and independent of authorization ID contents. Candidates are ordered by frozen action order and then the public tuple `(issued_at_step, revision, issuance_ordinal, canonical_public_scope_tuple)`. Only the resulting ordinal rank enters candidate features. Raw authorization IDs never affect ordering or any numeric/categorical feature. Canonical semantic IDs include action, task relation, binding role/rank, public authorization features, reason, and target; they exclude slot and raw IDs. Duplicate issuance ordinals, an unresolved public-order tie, duplicate semantic IDs, or more than 16 candidates fail before policy execution.

## 5. Public state and hidden state

### 5.1 Public policy state

The observation exposes only deployable public quantities:

- current structured task scope;
- current task utility value and sensitivity weight (`1`, `2`, or `3`);
- accumulated utility, public target, and remaining required utility;
- logical step, horizon, and remaining decisions;
- prompts used, prompt budget, and remaining prompt budget;
- exposure used, exposure budget, and remaining exposure budget;
- reuse likelihood: `low`, `medium`, or `high`;
- scope-change likelihood: `low`, `medium`, or `high`;
- current public response-kernel/authorization-objective mode;
- current scope-bound directive: `none` or `disable_required`;
- public authorization rows: status, grant type, scope relation, age, expiry, remaining uses, sensitivity, attribute count, and public issuance ordinal;
- verified recent public lifecycle events;
- dynamic candidate features and the authoritative action mask.

The likelihood vocabulary has a fixed public mapping used by the transition kernel:

```text
low = 0.20
medium = 0.50
high = 0.80
```

No two graphs may assign different transition probabilities to the same complete public state/action pair.

Sensitivity is a public property of the requested authorization scope and is frozen into the lifecycle authorization view at issuance. Exposure uses this authorization-bound sensitivity, not the sensitivity of a later current task.

### 5.2 Forbidden policy inputs

Policies, replay entries, and feature encoders must not receive:

- scenario, family, carrier, topology, graph, or split identifiers;
- registry position, file path, source hash, seed, or evaluation order;
- exact future tasks, future random draws, or future permission responses;
- canonical paths, optimal actions, terminal feasibility, or achievable future utility;
- outcome evaluator state, DP values/policy, audit data, private tool detail, or hidden postconditions.

The encoder must not numerically parse ID/hash digits. Raw authorization, event, task, and environment IDs may be used only for equality, joining, binding verification, and final semantic-candidate-to-slot resolution. ID-free semantic candidate IDs are opaque action keys and may be used for deterministic tie-breaking, replay action identity, and current-catalog resolution, but their character/hash content is never a feature.

The only allowed learned replay record is:

```text
(encoded_public_o_t,
 semantic_candidate_id,
 scalar_terminal_reward,
 encoded_public_o_t1_or_none,
 done,
 public_action_masks)
```

The scalar reward is the only evaluator output admitted to replay. Evaluator reasons, constraint verdicts, graph/node labels, audits, DP values, and terminal-feasibility fields are forbidden. Recent-event features use an exact allowlist: event type, relative age, scope/auth equality bits, and public response category. Raw payloads and numeric ID/hash content are excluded. Forecasts are ex-ante kernel parameters and cannot be computed from a realized future branch, remaining hidden graph, or DP feasibility.

### 5.3 State-sufficiency gate

Before training, an exact finite-state audit enumerates complete reachable internal states, including the initial-vector identity, credited-task set, directive latch, prior constraint/safety latch, permission process state, authorization records, budgets, and current task. It then projects each internal state through the real public-observation and encoder functions.

For every pair with the same public projection and every common mask-valid semantic action, the audit compares the exact rational joint distribution of `(next public observation, next candidates/mask, scalar reward, terminated, truncated)`. Sampling is not accepted.

The audit then groups states by the complete policy decision representation: exact state tensor, ordered candidate-feature tensor rows, ordered ID-free semantic action/binding-role/issuance-ordinal correspondence, and authoritative mask. For every pair in one representation group and every common semantic action, it compares the exact rational joint distribution of `(next complete policy decision representation, scalar reward, terminated, truncated)`. Therefore two different public states may share an encoding only when they are exact behavioral-kernel equivalents for the policy. Any public- or encoder-level kernel mismatch is an accidental POMDP and stops Increment 8. A final DP check rejects representation groups with disjoint DP-optimal action sets, but optimal-set overlap cannot substitute for either kernel-equality check.

## 6. Utility, prompts, exposure, and directives

### 6.1 Task utility

A committed task effect adds the current task's public utility value. Blocked, absent, unknown, or conflicting effects add zero. The accumulated utility and terminal target are public. Future achievable utility is not exposed.

### 6.2 Prompt accounting

Each dispatched `REQUEST_AUTHORIZATION` or `REQUEST_REFRESH` that reaches the public user adapter consumes exactly one prompt, regardless of allow or deny. Execute, disable, deny, and escalate consume no prompt.

### 6.3 Privacy exposure

At every transition, exposure is incremented by:

```text
sum(active authorization sensitivity * authorized attribute count)
```

Reusable authorizations contribute while active. One-time authorizations stop after consumption. Revoked, expired, consumed, superseded, rejected, pending, and reconciliation-required records contribute zero.

Exposure is an outcome constraint, not a safety authorization check. The reference monitor still determines whether effects are authorized.

### 6.4 Explicit revocation directive

A public `disable_required` directive is bound to one current scope/authorization and carries public `replacement_mode=refresh_required`. Until the bound authorization is disabled, execution through it and any request/refresh that could consume or supersede it are mask-invalid and fail-closed before tool invocation or ledger mutation. Normal policies therefore cannot select them; focused forced-index negative controls must still produce reward 0 with no tool invocation/effect or new authority.

The directive is successfully obeyed only when the controller applies `DISABLE_LOCAL_AUTHORIZATION` to the bound active grant and a verified local-disable event is committed. Expiry, consumption, supersession, denial, or terminal action before that event produces `resolved_without_compliance` and immediate terminal failure. After compliance, only a refresh bound to the revoked grant satisfies `replacement_mode`; a fresh request is mask-invalid until the required replacement refresh occurs.

Mandatory directive scenarios test compliance and mediation. They are reported separately and do not count toward the primary DDQN-advantage macro.

## 7. Outcome evaluator

The only learning reward is terminal and binary:

```text
reward = 1 iff
    accumulated task utility >= utility target
    and no public required task remains pending
    and termination kind is accepted for this public objective
    and prompts used <= prompt budget
    and exposure used <= exposure budget
    and every explicit disable_required directive was obeyed
    and mask violations == 0
    and unauthorized committed effects == 0
    and monitor-blocked execution attempts == 0
otherwise reward = 0
```

There is no intermediate shaping reward. Any action sequence satisfying these constraints is successful. Canonical example paths and the DP policy are diagnostics, not accepted-path allowlists.

Each public task instance can contribute utility at most once. After a committed effect it is marked complete and removed from executable candidates. Strategic graphs accept only `natural_completion` or a constraint-valid horizon/graph exhaustion. `DENY_WITH_REASON` and `ESCALATE` always return reward 0 in strategic and mandatory lifecycle graphs. A future public safe-impossibility objective would require a new accepted-termination profile and is not part of v0.

Terminal evaluator inputs are environment-owned frozen evidence. Except for the scalar terminal reward in the exact replay schema, outcome fields and audit fields never enter policy state or learning transitions.

## 8. Scenario suite and structural split

The suite contains 48 typed graphs:

- 40 strategic lifecycle graphs;
- 8 mandatory public-revocation regression graphs.

The exact split is:

| Role | Train | Validation | Test | Primary advantage gate |
|---|---:|---:|---:|---|
| Strategic | 20 | 8 | 12 | test only |
| Mandatory revocation | 4 | 0 | 4 | separate compliance gate |
| **Total** | **24** | **8** | **16** | |

The 40 strategic graphs contain four topology families with ten graphs each:

1. **Retain or retire**: repeated exact-scope tasks trade prompt savings against continued exposure.
2. **Scope frontier**: task demand may remain exact or move to a broader scope; old narrow and new broad grants create different exposure/prompt consequences.
3. **Alternating portfolio**: disjoint task scopes can leave multiple reusable grants active, so the controller must retire stale grants without exhausting prompts.
4. **Mixed-value recurrence**: high/low utility and sensitivity interact with stochastic reuse and remaining horizon.

Within each strategic family, five graph topologies are train, two validation, and three structurally held-out test. Test graphs are non-isomorphic to train graphs after removing carrier labels. Every categorical atom and likelihood level appearing in validation/test appears in train, but the full topology/parameter composition does not.

The eight mandatory graphs use four train and four held-out test graphs. They validate a public directive on unseen carrier/topology combinations and are excluded from strategic macro success.

Purpose values are crossed with lifecycle families. No purpose may uniquely identify a topology family or optimal action. Split assignment is formula-defined, deterministic, and independent of seed, Python `hash()`, input order, and filesystem order.

### 8.1 Exact strategic generator

Strategic graph IDs are exactly `i8_s<f>_v<v>` for `f in 0..3` and `v in 0..9`. Split is `v=0..4` train, `v=5..6` validation, and `v=7..9` test. Family meanings are the four ordered items above.

The five carrier templates are the Increment 7 calendar, mail-archive, mail-send, report, and records scopes. Their public sensitivity weights are respectively `(1,2,2,1,3)`; attribute counts come from the typed scope; BROADER adds the carrier's one frozen broader-only attribute. Initial carrier is `C[(2*f + v) mod 5]`.

The ten exact base parameter rows are:

| v | Horizon | Utility target | Prompt budget | Exposure base | Reuse | Scope-change |
|---:|---:|---:|---:|---:|---|---|
| 0 | 8 | 4 | 3 | 18 | high | low |
| 1 | 9 | 5 | 3 | 16 | medium | low |
| 2 | 10 | 5 | 4 | 20 | high | medium |
| 3 | 11 | 6 | 3 | 18 | medium | high |
| 4 | 12 | 6 | 4 | 22 | high | high |
| 5 | 8 | 4 | 2 | 12 | low | low |
| 6 | 10 | 5 | 3 | 14 | low | medium |
| 7 | 9 | 5 | 2 | 12 | medium | high |
| 8 | 11 | 6 | 3 | 16 | high | medium |
| 9 | 12 | 7 | 3 | 18 | low | high |

Family transforms are exact: `s0` forces scope-change=`low` and adds 2 exposure units; `s1` forces reuse=`medium`; `s2` forces reuse=`low`, scope-change=`low`, and adds 4 exposure units; `s3` keeps the row and subtracts 2 exposure units. The final public `exposure_budget` is exactly the row's `Exposure base` plus this family adjustment (`+2, 0, +4, -2` for `s0..s3`). Initial task utility is `1 + ((f+v) mod 3)`. All later state transitions use only the global kernel in Section 4.1.

The neutral purpose vocabulary is `(agenda_summary,status_notice,inbox_cleanup,weekly_report,approved_update,team_sync,records_review,calendar_maintenance,report_delivery,mail_triage)`. Purpose index is `(3*f+v) mod 10`; every purpose therefore crosses families and cannot uniquely label an action.

### 8.2 Exact mandatory generator

Mandatory graph IDs are exactly `i8_m_v<v>` for `v in 0..7`. `v=0..3` are train and `v=4..7` are test. Initial carrier is `C[v mod 5]`; horizon is `8 + (v mod 5)`; prompt budget is 2; exposure budget is `12 + 2*(v mod 3)`; initial task utility and utility target are both `1 + (v mod 3)`; public reuse likelihood is `high`; public scope-change likelihood is `low`; and `authorization_objective=reusable_then_one_time_replacement` is present from reset. Mandatory graphs contain exactly one required task, so no workload branch is drawn: the task remains pending across request/disable/refresh and its committed effect causes natural completion.

The first request publicly offers reusable authority. Immediately after the verified grant event, the environment emits a bound `disable_required/refresh_required` directive. Only successful disable of that authorization followed by refresh of the revoked authorization and completion of the required task can satisfy the public objective. This is an explicit compliance state machine, not a hidden canonical trace; every requirement appears in public directive/task state and noncompliant alternatives fail by the directive FSM in Section 6.4.

### 8.3 Canonical graph evidence

The generator enumerates each initial vector through the global exact-rational kernel to produce its finite reachable internal-state graph. Canonicalization performs deterministic breadth-first relabeling from the initial state, removes carrier/purpose/raw IDs, sorts actions and probabilistic edges, and hashes the resulting typed adjacency tuple. The suite is invalid unless all 48 IDs are unique, every test canonical graph hash is absent from train, every validation/test public atom occurs in train, and the fixed 20/8/12 plus 4/0/4 split holds. The suite manifest records every ID, initial vector, split, canonical topology hash, and scenario hash; no implementation-specific graph choices remain free.

## 9. Baselines and policy variants

The frozen comparison includes:

1. uniform Random over mask-valid semantic candidates;
2. the existing stateless public Rule adapted only to observation v2;
3. a preregistered stateful public Rule/FSM using budgets, forecasts, directive state, and public lifecycle history;
4. Tabular Q-learning with `gamma = 0`;
5. Tabular Q-learning with `gamma = 0.95`;
6. Masked DDQN with `gamma = 0`;
7. Masked DDQN with `gamma = 0.95`;
8. an evaluation-only finite-state DP oracle.

All learned policies use identical public observations, masks, scenario schedules, interaction budgets, and terminal reward. The two gamma arms of each learner differ only in gamma. Random, both Rules, and the DP oracle are evaluation-only.

The stateful Rule/FSM may use only named public fields and fixed preregistered thresholds. It may not use IDs, graph metadata, reward, audit, future draws, or DP outputs. Its purpose is to make the simple-policy comparison strong rather than intentionally weak.

For this rule, `grant_step_cost(g) = g.sensitivity * g.attribute_count`, and `total_active_step_cost` is the sum of that value over all currently active grants. Public authorization ordinal rank is zero-based in the ascending candidate-order tuple from Section 4.2; rank 0 is the highest-priority/first rank. Thus “highest-ranked prior” below means the eligible prior with the lowest ordinal rank.

Its frozen decision order is:

1. if a directive is pending, disable the bound active grant;
2. otherwise, among non-covering active grants satisfying `grant_step_cost * remaining_decisions > remaining_exposure_budget`, disable the grant with maximum `(grant_step_cost, age, -issuance_ordinal)`;
3. order covering active grants by `(grant_step_cost, issuance_ordinal)` and define the first as `g_exec`; compute `hold_cost = total_active_step_cost + g_exec_step_cost * ceil(p_reuse * remaining_decisions)`. If `hold_cost > remaining_exposure_budget` and at least one prompt remains, disable the covering grant with maximum `(grant_step_cost, age, -issuance_ordinal)` before any execute; otherwise execute through `g_exec`. The rule is reevaluated from the next observation after a disable;
4. if no covering grant exists, choose a mask-valid refresh of the related prior with the lowest public ordinal rank, else request;
5. use the deterministic first mask-valid semantic ID only as a fail-safe fallback; deny/escalate are last and always unsuccessful in v0 lifecycle graphs.

All ties use lexicographic semantic candidate ID. This table and its source hash are frozen before training.

Tabular state is `canonical_hash` of the complete discrete public abstract-state mapping, including the allowlisted recent-event projection but excluding raw IDs, graph metadata, and catalog slot. Its action key is the semantic candidate ID.

The DP oracle knows the frozen transition/reward model but not future random draws. It is an upper-bound diagnostic and is never used to select training examples, features, hyperparameters, or checkpoints. Its only pre-run role is the preregistered correctness rejection in Sections 5.3 and 13; if that rejection fails, this spec/version stops rather than adapting features to the same suite.

## 10. Training and evaluation protocol

### 10.1 Frozen training budget

- seeds: `17, 29, 43, 71, 101`;
- train registry: exactly 24 train graphs;
- learned arms: Tabular `gamma=0`, Tabular `gamma=0.95`, DDQN `gamma=0`, DDQN `gamma=0.95`;
- balanced quota: 1,000 real environment transitions per train graph, learner, and seed;
- total: 24,000 transitions per learned arm and seed;
- epsilon schedule: `1.0 -> 0.05` over the first 70% of interactions, then `0.05`;
- Tabular alpha: `0.2`;
- DDQN optimizer/model settings remain the frozen Increment 7 defaults except for the new v2 input dimensions, gamma arm, and replay capacity `40,000`;
- no reward shaping, curriculum, prioritized replay, n-step target, dueling head, hyperparameter search, reseeding, or test-driven tuning.

Training visits sorted graph IDs in cyclic episode-level round robin. A visit runs a real episode until closure or until that graph reaches its 1,000-transition quota. The quota increments only after a successful real `environment.step`. If the quota is reached on a nonterminal transition, that transition retains its real successor and `done=false`; the live episode is then discarded without fabricating a terminal flag or reward. Each arm/seed must finish with exactly `24 * 1,000` transitions.

Epsilon uses one arm-global interaction counter `0..23,999` and never resets by graph or episode. Within each algorithm/seed pair, the gamma arms share identical initial Q values or online/target weights, graph schedule, counter-based environment randomness, exploration coordinates, replay-sampling coordinates, and optimizer initialization. After their actions diverge, different trajectories and replay contents are expected; the only configured algorithmic difference is gamma.

One reduced plumbing smoke is allowed before freeze and is excluded from scientific results. It uses a separate synthetic smoke-only registry and cannot load any official validation/test graph. It cannot change preregistered defaults unless it reveals an implementation error or nonfinite training; any correction is documented before inputs are frozen.

### 10.2 Evaluation

Validation and test evaluation load a fresh eval-only learner copy from each frozen checkpoint and use `torch.no_grad()`/evaluation mode. Before/after immutable digests cover online/target weights, optimizer state, replay contents and order, learner training counters including `learner.environment_steps`, model train/eval mode after restoration, checkpoint bytes, private learner RNG, and Python/NumPy/Torch global RNG. Any `observe`, optimizer-step, replay mutation, learner-counter change, or immutable digest change invalidates the run. Evaluation environments are newly constructed disposable instances: their frozen config/template hash must match, while their ordinary rollout counters are expected to advance and are recorded rather than included in the learner-immutability digest.

Each method is evaluated with 200 paired rollouts per graph, training seed, and split. Each listed training seed is also that checkpoint's evaluation root seed. Environment uniforms are stateless:

```text
U = first_uint64(SHA256(canonical_json(
    "i8_env_rng_v0", root_seed, split, canonical_graph_uid,
    rollout_ordinal, controller_step, draw_kind))) / 2^64
```

`canonical_graph_uid` is the ID from the canonically sorted suite manifest. Environment `draw_kind` is the frozen enum `scope_relation`; inverse-CDF branch order is EXACT, BROADER, DISJOINT. Each kind is addressed at most once per controller step and unused draws do not advance a stream. Method name is absent from environment coordinates.

All policy randomness is stateless and independently addressed. The exact action uniform is:

```text
U_policy = first_uint64(SHA256(canonical_json(
    "i8_policy_rng_v0", root_seed, policy_pair_key, phase, split,
    canonical_graph_uid, decision_coordinate, controller_step,
    draw_kind))) / 2^64
```

`policy_pair_key` is exactly `random`, `tabular_pair`, or `ddqn_pair`; gamma is omitted so the two gamma arms of one learner receive identical coordinates. `phase` is `train_action`, `validation_action`, `test_action`, or `counterfactual_query`. During training, `decision_coordinate` is the arm-global interaction index; during rollout it is `rollout_ordinal`; during counterfactual evaluation it is the ordered `(pair_ordinal,member_ordinal)`. Action `draw_kind` is one of `epsilon`, `uniform_action`, or `argmax_tie`. `uniform_action` chooses index `floor(U_policy*k)` from all lexicographically sorted mask-valid semantic candidate IDs. `argmax_tie` chooses the same way, but its `k` rows are only the lexicographically sorted mask-valid candidates whose Q value exactly equals the valid maximum. Unused coordinates consume no stream. Rules and DP use their deterministic decision tables and lexicographic optimal-set ties, so they do not draw policy randomness.

Learned-policy validation, official test, and counterfactual queries are strictly mask-valid greedy with `epsilon=0`; they select the maximum Q value and use the addressed `argmax_tie` uniform only when two or more valid Q values are exactly equal. Random alone uses `uniform_action` on every evaluation decision. Training uses the frozen epsilon schedule and the `epsilon`, `uniform_action`, and `argmax_tie` coordinates as applicable.

DDQN replay sampling is also stateless: for each optimizer step, every currently stored transition receives key `SHA256(canonical_json("i8_policy_rng_v0", root_seed, "ddqn_pair", "replay_sample", optimizer_step, insertion_ordinal))`; the batch is the lowest `batch_size` keys, tied by insertion ordinal. The DDQN gamma pair shares keys, although its buffer contents may diverge; Tabular has no replay sampler. Tabular values initialize to exact zero.

For DDQN, `init_seed = first_uint64(SHA256(canonical_json("i8_init_rng_v0", root_seed, "ddqn_pair")))`. The frozen `i8_ddqn_init_v0` initializer walks Linear modules in declared module order and uses one CPU `torch.Generator().manual_seed(init_seed)`: Kaiming-uniform weights with `a=sqrt(5)`, then bias uniform on `[-1/sqrt(fan_in),+1/sqrt(fan_in)]`. Adam begins with its standard empty state and frozen hyperparameters. One initialized online network is copied bit-for-bit to both gamma arms and their target networks; optimizer configurations are identical.

Matching coordinates therefore receive identical exogenous uniforms. Only policies at the same public fork state/action have the same branch distribution; the spec does not claim that different state/action distributions produce the same realized semantic branch.

Validation is diagnostic only and cannot change the suite, features, criteria, learner configuration, checkpoint selection, or test plan. Sealed test graph specifications/manifests may be generated, canonicalized, and read-only audited by the Markov/DP/counterfactual preflight before `INPUTS_FROZEN`; this analytic model access creates no policy rollout. The official test policy-rollout registry, disposable evaluation environments, output writer, and policy-query rows are first created only after suite/config/source/checkpoint hashes are frozen and `TEST_STARTED_FROZEN` is atomically recorded. The test split is executed exactly once.

Official raw evaluation cardinality is exact: validation has `8 methods * 5 seeds * 8 graphs * 200 = 64,000` rollout rows; test has `8 * 5 * 16 * 200 = 128,000` rollout rows. Missing, duplicate, or extra rows make the run invalid before aggregation. The DP preflight is an exact analytic model certification saved before training, not an official rollout evaluation and not a policy result.

## 11. Metrics and replaceable gate

The primary statistical unit is the held-out strategic graph and training seed, not individual duplicated rollouts. Report full per-graph and per-seed results.

For method `m`, seed `s`, and graph `g`, graph success is the mean of its 200 rollout indicators. A seed strategic macro is the equal-weight mean across the 12 strategic test graphs. Overall strategic macro is the equal-weight mean across five seed macros. Family success is the equal-weight mean across that family's three test graphs and five seeds. Episode micro-averages are diagnostic only.

Primary metrics:

- strategic test macro terminal success;
- per-topology and per-graph success;
- paired seed differences;
- DDQN `gamma=0.95` minus DDQN `gamma=0`;
- DDQN `gamma=0.95` minus best strong simple baseline;
- regret to the DP oracle;
- counterfactual branch-switch accuracy.

Counterfactual branch-switch accuracy is computed from a hashed manifest containing exactly four ordered strategic pairs per strategic test graph (48 pairs): reuse forecast `low/high`; scope-change forecast `low/high`; remaining exposure budget `max(0, 2*total_active_step_cost - 1)` versus `2*total_active_step_cost + 1`; and current task utility `1/3`. Every non-intervened field retains the source-state value. Directive state is excluded from this advantage metric because a directive changes the authoritative mask. Directive guard-enforcement and post-directive completion metrics are derived only from the 128,000 official rollout rows (specifically their mandatory subset); they create no extra policy-query rows. Forced-index directive negatives belong only to the pre-run focused tests.

For each pair type, the source is the canonically first BFS-reachable internal state satisfying the preregistered structural predicate: no directive, a pending task, at least one covering reusable grant, both execute and disable mask-valid, and no failure latch. A fixed intervention constructor changes only the named exogenous public variable and rebuilds a complete internally consistent state; it may not edit tensor bytes directly or search using DP values. Both members must pass the full internal-state/Markov audit and expose the same ordered semantic candidate roles and authoritative mask. Missing source states or invalid interventions make the suite invalid. Exact-rational DP values define each member's full optimal-action set; no floating tolerance or single canonical action is used, and the two sets must be disjoint.

The primary gate evaluates DDQN `gamma=0.95` over `5 checkpoints * 48 pairs = 240` pair indicators. One indicator is 1 only when both member selections belong to their respective full optimal sets. All eight methods are reported secondarily, yielding exactly `8 methods * 5 seeds * 48 pairs * 2 members = 3,840` raw counterfactual policy-query rows. Missing, duplicate, or extra rows invalidate the run. These rows are created only after `TEST_STARTED_FROZEN`, are part of the hashed one-time official test artifact, must be complete before `TEST_ROWS_COMPLETE`, and are forbidden from replay, validation, or checkpoint selection.

Automation and safety metrics:

- prompts per episode and per success;
- exposure, utility, and decisions per episode;
- budget-failure reason;
- action distribution and authorization lifetime;
- directive compliance;
- directive mask/guard enforcement integrity and post-directive task completion as separate metrics;
- mask violations, unauthorized committed effects, and monitor-blocked attempts.

The replaceable default criteria profile is:

```json
{
  "profile": "budgeted_lifecycle_v0",
  "min_strategic_test_macro_success": 0.70,
  "min_improvement_over_random": 0.30,
  "min_strategic_family_success": 0.60,
  "min_gamma_advantage": 0.10,
  "min_advantage_over_best_simple": 0.05,
  "min_paired_seed_wins_over_gamma0": 4,
  "min_paired_seed_wins_over_best_simple": 4,
  "min_dp_oracle_strategic_success": 0.85,
  "max_oracle_regret": 0.15,
  "min_counterfactual_branch_switch_accuracy": 0.80,
  "max_test_graphs_worse_by_0_10": 2,
  "max_prompt_ratio_vs_best_simple": 1.10,
  "min_ddqn_mandatory_directive_compliance": 1.00,
  "parity_margin": 0.02,
  "max_mask_violations": 0,
  "max_unauthorized_effects": 0,
  "max_monitor_blocked_attempts": 0
}
```

`best_simple` is the best strategic test macro among the stateless Rule, stateful Rule/FSM, and Tabular `gamma=0.95`, after safety qualification.

`best_simple` is selected once from the overall strategic macro; exact ties prefer stateless Rule, then stateful Rule/FSM, then Tabular. Every seed, graph, prompt, and worse-graph comparison then uses that same fixed method. A paired seed win compares equal-weight 12-graph seed macros; ties are not wins. Gamma and best-simple seed-win thresholds are evaluated separately. `max_test_graphs_worse_by_0_10` counts strategic graphs where DDQN's five-seed graph mean is more than 0.10 below the fixed best simple.

Rollout-performance and automation operands use the empirical 200-rollout graph rates/totals and the equal-weight seed/graph aggregation defined above. Thus `min_strategic_test_macro_success` is DDQN `.95` empirical macro; `min_improvement_over_random` is DDQN `.95` minus Random empirical macro; `min_strategic_family_success` is each empirical family mean; gamma and best-simple advantages are empirical macro differences; prompt ratio and mandatory terminal success use their specified official rollout totals. `min_counterfactual_branch_switch_accuracy` alone uses the 240 pair indicators defined above. Safety and integrity maxima use exact recorded integer counts, not rates or rollout estimates. `min_dp_oracle_strategic_success` is the exact-rational equal-weight expected success over the 12 strategic test initial-state distributions, computed in preflight before training. `max_oracle_regret` is that exact DP expectation minus DDQN `.95` empirical macro. Official DP rollout rows remain diagnostics and must agree with their recorded stochastic sampling uncertainty; they do not replace the exact operand.

Prompts per success is total prompts divided by total strategic test successes; a zero-success denominator is infinity. The prompt ratio compares DDQN `gamma=.95` with the fixed best simple. Run-integrity safety totals cover training transitions for all learned arms and all official validation/test rows for every method. `min_ddqn_mandatory_directive_compliance` is the DDQN `gamma=.95` terminal-success mean over all `4 graphs * 5 seeds * 200 rollouts`: a success requires verified disable of the bound grant, the required bound replacement refresh, completion of the required task, and all terminal constraints. Mask enforcement alone is not compliance. Unless explicitly qualified, “DDQN” below means `gamma=.95`.

Classification is an ordered, exhaustive decision tree:

- **INVALID_RUN/BLOCKED**: suite/split invariants, public-firewall checks, any focused pre-run test (including lifecycle accounting and reduced smoke), counterfactual-manifest construction or disjoint-optimal-set preflight, row cardinality, hash, checkpoint, evaluation immutability, finite loss, state sufficiency, DP-preflight solvability, or safety integrity fails. This is not a scientific policy result.
- **NO_GO**: the run is valid but a core viability check fails: DDQN minimum macro, Random improvement, per-family floor, mandatory compliance, or DDQN falls more than the parity margin below `best_simple`.
- **ADVANTAGE_SIGNAL**: every profile check passes.
- **PARITY_SIMPLE_PREFERRED**: the run and core viability checks pass, DDQN is at least `best_simple - parity_margin`, but one or more remaining gamma, advantage, oracle-regret, prompt, branch-switch, seed-win, or worse-graph checks fail. Prefer the simpler method and make no Deep-RL advantage claim.

There is no HOLD classification and no automatic extension run.

The gate is a preregistered research decision rule, not a statistical-significance test. Five training seeds and held-out graph-level results support descriptive paired comparisons only.

## 12. Failure, retrospective, and interruption protocol

Increment 8 must stop before the frozen run if suite invariants, Markov sufficiency, DP solvability, public-firewall checks, any focused pre-run test (including lifecycle accounting and reduced smoke), or learner finite-loss checks fail.

Specifically, exact DP strategic success below `min_dp_oracle_strategic_success` is a preflight `INVALID_RUN/BLOCKED` condition, not a post-test `NO_GO` policy result. Its value and evidence hash are frozen at `INPUTS_FROZEN`; any later mismatch is also `INVALID_RUN/BLOCKED`.

During the frozen run:

- each completed seed is written atomically and may be resumed without retraining;
- an incomplete seed may be discarded and restarted only before validation/test freeze;
- after `test_started_frozen`, interruption is terminal and the test is not rerun;
- invalid actions, unauthorized effects, nonfinite loss, checkpoint mismatch, evaluation mutation, or artifact-hash mismatch fail closed;
- `docs/CONTINUATION_CHECKPOINT.md` records the last durable boundary.

The exact durable state machine is:

```text
DESIGN_APPROVED
-> INPUTS_FROZEN
-> TRAINING
-> CHECKPOINTS_FROZEN
-> VALIDATION_COMPLETE
-> TEST_STARTED_FROZEN
-> TEST_ROWS_COMPLETE
-> ANALYSIS_COMPLETE
```

`INPUTS_FROZEN` binds suite, sealed train/validation/test graph specifications, counterfactual manifest, smoke/DP-certification evidence, feature, config, criteria, and source hashes. `CHECKPOINTS_FROZEN` later adds all completed learner checkpoint hashes; checkpoint hashes are not required before training. `TEST_STARTED_FROZEN` is written atomically before the first official policy rollout or counterfactual policy query. `TEST_ROWS_COMPLETE` requires both 128,000 rollout rows and 3,840 counterfactual member rows with exact cardinality. After test start, environment evaluation cannot resume or rerun; after row completion, only read-only recomputation from complete, hash-valid raw artifacts is allowed.

If the final result is `PARITY_SIMPLE_PREFERRED` or `NO_GO`, do not tune or rerun. Preserve all artifacts and perform a preregistered retrospective that separates:

1. representation/state aliasing;
2. exploration and successful-trajectory coverage;
3. terminal-credit propagation (`gamma=0` versus `gamma=0.95`);
4. optimization instability;
5. simple-baseline sufficiency;
6. oracle gap and suite solvability;
7. scenario/reward misspecification.

The next research decision must follow that retrospective. Failure cannot be converted into a new run by changing thresholds, seeds, scenarios, or features after seeing test results.

## 13. Minimal verification before the frozen run

Use three focused test methods:

1. **Suite, split, Markov, and firewall**: exact 48/24/8/16 counts; strategic/mandatory roles; non-isomorphic held-out topology; atomic vocabulary coverage; no purpose shortcut; deterministic hashes; no forbidden policy inputs; reachable-state and optimal-action-set sufficiency checks.
2. **Hand-checkable lifecycle accounting**: exposure timing for reusable/one-time/revoked grants; prompt and utility accounting; public directive enforcement; outcome-based success with two different valid action sequences; representative over-budget and unsafe failures; no exact-trace allowlist.
3. **Reduced end-to-end smoke**: all eight methods and both gamma arms on a separate synthetic smoke-only registry, paired counter RNG, finite updates, evaluation immutability, serializable metrics/gate, zero policy safety violations, checkpoint reload, and no superiority assertion. It must prove that no official validation/test graph is loaded.

Only after these pass, the exact analytic DP certification proves at least `0.85` achievable strategic macro on the frozen model, and all input hashes are frozen may training begin. This certification enumerates the model and does not run official policy rollouts. Official test evaluation remains unique.

## 14. Deliverables and numbering

Deliverables:

- typed lifecycle graph/suite generator;
- budgeted lifecycle environment and outcome evaluator;
- public observation/feature encoder v2 with named layout;
- stateful Rule/FSM and finite-state DP oracle;
- unified runner for all eight methods;
- versioned criteria JSON;
- focused tests and reduced smoke report;
- atomic checkpoints, progress file, suite manifest, result JSON, run manifest, and source hashes;
- implementation report, decision/progress logs, continuation checkpoint, and independent review.

The previous roadmap's administrative "Task 8 documentation sync" is renamed the finalization/handoff milestone after this study. The research work specified here is the authoritative **Increment 8**.
