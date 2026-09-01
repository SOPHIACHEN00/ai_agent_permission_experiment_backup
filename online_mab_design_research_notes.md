# Research Notes: Single Online MAB Design

## Scope anchor

- Professor roadmap: Step 2 is naive MAB with epsilon-greedy/UCB/Thompson sampling; Step 3 is interactive RL; Steps 4--5 concern an LLM security-check sub-agent and constitutional-AI fine-tuning plus RL.
- Therefore the online MAB must be a compact interactive Step-2 bridge, not a competing safety/RL system.

## Working design question

What one-step online contextual-bandit protocol can learn from verified permission feedback, preserve a fair comparison with the current offline MAB, and provide clean transition data for future CMDP work?

## Findings

### Local prerequisites

- `qstn_simulator/` already provides a questionnaire-response layer, 201 calibration personas, three empirical permission-response prototypes, prompt audits, and cached held-out calibration outputs.
- The simulator explicitly distinguishes stable profile-grounded persona conditioning from the future changing `memory_state`; this supports using it as a **stationary one-step** environment for the MAB and reserving memory dynamics for CMDP.
- The current QSTN v2 held-out calibration is not a sufficient human-behaviour oracle for a deployment claim: 90 held-out rows / 30 participants, accuracy 0.3222, macro-F1 0.2838, and over-sharing 0.3429. Any online result produced now must remain a simulator stress test, not evidence of human online performance.
- A mandatory Gate 0 is therefore needed: freeze a simulator version only after an independently held-out calibration protocol and then never tune it using online-MAB test trajectories.

### Existing offline benchmark boundary

- Canonical baseline: frozen participant-held-out, fully labelled stated-policy contextual-bandit simulation; train 120 participants, validation 40, test 41.
- Best reported MAB is factored Thompson sampling at 43.78% joint exact match, but it predicts allow for every true deny on that split. The online study must keep false-allow a primary safety diagnostic and cannot claim safety from a higher exact-match score alone.

### Verified methodological sources

- Agrawal & Goyal (ICML 2013): contextual Thompson sampling has a rigorous linear-payoff contextual-bandit formulation. https://proceedings.mlr.press/v28/agrawal13.html
- Hong et al. (AISTATS 2022): hierarchical Thompson sampling uses a shared prior plus task-specific information and benefits from informative priors; relevant to sparse per-person feedback. https://proceedings.mlr.press/v151/hong22c.html
- Kazerouni et al. (NeurIPS 2017): conservative contextual bandits can require performance relative to a baseline at every time. https://proceedings.neurips.cc/paper_files/paper/2017/hash/bdc4626aa1d1df8e14d80d345b2a442d-Abstract.html
- Li et al. (2012) and Wang et al. (ICML 2017): simulator and logged contextual-bandit evaluation have modelling/propensity caveats; action propensities must be logged for later IPS/DR evaluation. https://proceedings.mlr.press/v26/li12a.html ; https://proceedings.mlr.press/v70/wang17a.html
- Tsai et al. (SOUPS 2017): automated contextual privacy decisions require user mechanisms to audit and correct errors. https://www.usenix.org/conference/soups2017/technical-sessions/presentation/tsai
- Liu et al. (SOUPS 2016): a small number of user interactions can support personalized permission recommendations. https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu

### Final design decision

- Implement one `WP-FTS` online baseline, not a sweep of online algorithms: preserve the factored four-policy action space, the existing runtime feature schema, and `r_joint = 1[predicted action == stated action]`.
- Train a global Factored Thompson posterior on train participants; initialize each held-out user with a tempered copy of that posterior, then update only that user's selected action with the binary joint reward. No test user updates the global posterior.
- Use atomic `(participant_id, query_id)` bundles and reveal feedback only after all decisions in a bundle. Call the experiment a randomized sequential online-feedback replay simulation, because the source has no real chronology.
- Compare against a frozen global Factored Thompson policy on identical contexts/orders. Pre-register validation selection, participant-cluster bootstrap, false-allow diagnostics, and a dual success condition: post-adaptation exact-match gain plus false-allow reduction.
