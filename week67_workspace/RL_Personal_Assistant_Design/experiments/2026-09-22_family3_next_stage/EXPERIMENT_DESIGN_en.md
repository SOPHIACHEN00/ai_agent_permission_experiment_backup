# Increment 8 follow-up: shared-budget permission recourse

Date: 2026-09-22. Version: `budget_recourse_design_v0`.
Status: DESIGN COMPLETE; NOT IMPLEMENTED OR RUN. The detailed Chinese design and `next_experiment_plan.json` define this proposal. Existing Family-3 v2 remains immutable.

## Motivation and scope

The sealed v2 pilot achieved its intended mechanism-level result: gamma=1 DDQN learned forecast-conditioned initial authorization and matched the known optimal ForecastRule. Both obtained 737/900 held-out successes. The classifier reports rule parity with precedence over the credit signal, not absence of learning.

The next question is whether policies can trade off authorization scope, exposure, and a scarce opportunity to ask again across two tasks. We do not increase old training budgets, reopen old test data for selection, or design a benchmark requiring DDQN to defeat an optimal planner. This remains an Increment 8 mechanism follow-up, not completed human-interaction RL or a claim of general RL necessity.

## Minimal candidate environment

Two sequential tasks each require a common protected effect followed by an exact/broader continuation effect. Each stage has distinct scopes and its grant expires at the stage boundary. A narrow grant can execute the common effect; only then is its continuation branch revealed. If broader coverage is needed, the agent may explicitly request a new broader authorization. Deterministic user consent replaces the narrow grant; there is no automatic escalation and no scope expansion through refresh.

Stage t has narrow cost n_t and broader cost 2*n_t. Grant issuance and each effect incur one scope-cost charge. Thus narrow/exact uses 3*n_t and one prompt; broader-first uses 6*n_t and one prompt; narrow followed by explicitly authorized recourse uses 6*n_t and two prompts. The two tasks share exposure budget B and prompt budget P. Masks enforce immediate legal feasibility, not oracle future feasibility. No unconsented effect is allowed.

The initial observation includes p1, costs, resources, and the distribution of the later forecast. The second-stage forecast p2 is disclosed only at that stage; p2 is 4/5 with probability r and 1/5 otherwise. Branches are sampled independently conditional on their disclosed forecasts. Future realizations, graph/split IDs, RNG state and DP labels are hidden from the learner. The complete public resource/progress state must be Markov.

Reward remains terminal binary success: all four effects completed within budgets. Intermediate rewards are zero. Horizon is 12; normal successful paths require at most seven decisions. Deny/escalate safely terminate with zero reward. Disabling revokes authority but creates no new request eligibility. Refresh has no valid use in this pilot; we do not claim nontrivial strategic use of all six action categories.

An analytical witness, not an executed result: with n1=n2=1, B=9, p1=1/5 and r=1/2, the optimal root values for narrow/broader are (1/5,1/2) at P=2 and (3/5,1/2) at P=3. Identical forecast, different prompt budget, opposite optimal initial action. Exact enumeration and environment conformance must still confirm this derivation.

## Comparators and fixed suite

The JSON manifest fixes ten candidate graph rows with a 5/2/3 train/validation/test split. Each row has original and prompt-toggle conditions; the entire intervention group stays within one split. Train uses only original conditions. This measures held-out parameter combinations within one mechanism, not ten independent real-world tasks or broad OOD generalization.

Compare six policies: DDQN gamma=1; matched gamma=0; a forecast-majority transfer rule with explicit legal recourse/fallback; an exact current-task rule that ignores the next task; a stronger rule that reserves one prompt and the minimum 3*n2 exposure for task two; and random-valid. Current-task/reservation ties prefer lower expected exposure, then fewer expected prompts, then semantic ID. Include public-information exact DP as a planning comparator and ceiling, not a clairvoyant oracle.

Freeze all baseline definitions before suite-wide certification. If the reservation rule is already optimal, report that result. Cheap exact planning is a legitimate practical alternative to learning.

## Execution stages

Stage A is the immediate next implementation: a separate minimal transition kernel, rational exact DP, rules and environment adapter. Verify analytical costs, both witnesses, two-stage causal resource dependence, nonzero feasibility, follow-up information use, and safety/observation separation. Require a strict current-task versus full-horizon value gap on train/validation before a learning pilot. Stop on the first genuine failure; do not search parameters or enlarge resource caps. Proposed DP caps: 100,000 nonterminal states, 60 seconds and 512 MiB RSS.

Stage B is proposed, not launched: two DDQN arms × three fresh seeds (101,211,307) × 12,000 transitions = 72,000 transitions and six final checkpoints. Use 2,400 transitions per training graph. Preserve the tested CUDA network body and optimizer settings, documenting any necessary input-encoding change. Learning rate=0.001, batch=64, replay=20,000, warmup=256, optimize every four transitions, target update every 250 optimizer steps, clip=5; epsilon decreases from 1 to 0.05 over 9,600 transitions and then stays fixed.

Six evaluated policies × three seeds × two conditions × 50 episodes give 3,600 validation rows on two graphs and 5,400 test rows on three graphs. Use final checkpoints and every seed, not best-run selection. Shared exogenous random numbers are indexed by semantic event; exploration and tie streams are separate. Validation performance does not filter seeds from test: completion/integrity and frozen analysis are the unlock criteria. Test remains single-use.

Proposed resource: one server RTX 3090, physical GPU 1 only; GPU 2 remains unused. Environment/exact computations naturally require host execution, but no CPU-only RL experiment is proposed. No OpenAI API or LLM training is needed. Runtime and memory require measurement after implementation.

## Analysis and decision boundaries

Report per-seed, per-graph/condition success, exact regret, optimal-action-set agreement, resource use, termination causes and computational cost. Prefer exact evaluation of the frozen greedy neural policy on the finite tree; integrate any frozen stochastic tie distribution. If only Monte Carlo evaluation is available, label uncertainty and do not treat sample success above V* as a theoretical improvement.

Proposed versioned thresholds: zero hard safety/integrity counts; mean exact regret <=0.05 for every seed for a near-optimality engineering signal; gamma=1 exceeding gamma=0 and the current-task rule on all seeds for a learning signal; and at least 0.05 paired improvement over the reservation rule on every seed for a strong-rule advantage pilot signal. The 0.05 choices are proposed practical thresholds, not a significance test. Preserve negative/mixed/parity outcomes. No post-test threshold changes; old v1/v2 thresholds remain untouched.

Three training seeds support only a pilot. Episodes and paired interventions are not independent training replicates. Preserve all seed results; a larger confirmatory study requires a separately frozen budget.

## Archival and recovery

Preserve source/config/criteria/checkpoint hashes, exact certificates, raw training records, per-step public actions and budgets, terminal outcomes and all failures. Private simulator truth/DP labels belong in evaluator-only sidecars. Persist timestamps, last durable coordinate, exit status and the recovery decision. Disconnection is not training failure; do not automatically retry, resume, change parameters or launch another writer.

Current delivery includes design, raw-evidence indexing and derived v2 data only. No new certificate or learning result exists.

## Methodological sources

The matched Double DQN update follows the action-selection/target-evaluation separation of [van Hasselt et al.](https://arxiv.org/abs/1509.06461). Small-run uncertainty and cautious interpretation follow [Agarwal et al.](https://arxiv.org/abs/2108.13264). The proposed environment, numeric manifest and decision thresholds are project-specific design choices, not validated claims from these papers.
