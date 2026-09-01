# One Online MAB Design: Warm-started Personalized Factored Thompson Sampling

## Decision in one sentence

Implement **one** online baseline: a **warm-started personalized Factored Thompson Sampling contextual bandit** (WP-FTS), evaluated as a **randomized online-feedback replay simulation** using the original human questionnaire labels.  It keeps the current four permission-policy actions, feature schema, and **unweighted joint exact-match reward**.  Its only new capability is to update a separate posterior from each user's *past, verified* feedback.

This is deliberately a Step-2 MAB baseline, not a preliminary CMDP.

---

## 1. Research question and boundary

### Research question

> For a previously unseen user, can verified feedback from earlier permission requests improve prediction of that user's later four-way stated permission policy relative to the same frozen offline MAB?

This is a question about **stated-policy personalization**, not a claim that the system has measured privacy harm, task success, or long-run user burden.

### What this study is and is not

| In scope: online MAB | Explicitly out of scope: future CMDP / agent work |
|---|---|
| One-step contextual decision; new feedback changes only the current user's posterior. | A saved rule changes a later state; prompt frequency, trust, revocation, and reuse affect future decisions. |
| The policy proposes one of four questionnaire permission policies. | The policy actually discloses sensitive data or permanently grants/revokes a rule. |
| `persist` means the user's one-step *stated preference* to remember the decision. | `persist` is executed and therefore reduces later prompts or causes an erroneous reuse. |
| Reward is agreement with verified user feedback. | Privacy--utility--interruption trade-off is optimized through reward weights or learned preference weights. |

Once an action writes a persistent rule, affects future prompts, or causes a transition in user trust/memory, the problem is sequential and belongs to the later CMDP/RL stage.  This separation follows the project roadmap and prevents the MAB from competing with the main safety contribution.

---

## 2. The one method to implement

### Name

**WP-FTS — Warm-started Personalized Factored Thompson Sampling.**

We will *not* add an online epsilon-greedy version, online UCB version, or a second online reward formulation.  Epsilon-greedy/UCB/Thompson have already served their purpose in the offline comparison.  Thompson sampling is selected here because a posterior can naturally be initialized from population evidence and then adapted for one user; it has a standard contextual-bandit formulation [Agrawal & Goyal, 2013](https://proceedings.mlr.press/v28/agrawal13.html).  The shared-prior / local-adaptation idea is also consistent with hierarchical Bayesian bandits [Hong et al., 2022](https://proceedings.mlr.press/v151/hong22c.html).

### Action space: unchanged and factored

\[
\mathcal A=\mathcal A_{\mathrm{access}}\times\mathcal A_{\mathrm{persist}},
\qquad
\mathcal A_{\mathrm{access}}=\{\mathrm{deny},\mathrm{allow}\},
\qquad
\mathcal A_{\mathrm{persist}}=\{\mathrm{ask\ next\ time},\mathrm{persist}\}.
\]

| ID | Four-way stated policy | Access | Persistence |
|---:|---|---|---|
| 0 | No, never share | deny | persist |
| 1 | No, but ask me next time | deny | ask next time |
| 2 | Yes, but ask me next time | allow | ask next time |
| 3 | Yes, always share | allow | persist |

The action is selected access-first, then persistence conditioned on the selected access action, exactly as in the existing `FactoredJointPolicy`.

### Runtime context: unchanged

The primary context is intentionally the current validated offline feature schema:

\[
x_t=\{\text{domain},\ \text{tool},\ \text{raw data type},\ \text{generic data type},\ \text{concern domain},\ \text{privacy importance}\}.
\]

| Allowed at decision time | Why | Not allowed as a feature |
|---|---|---|
| Request/domain/tool/data descriptors and the opt-in privacy fields already used offline | They are available before the permission decision and maintain an apples-to-apples comparison. | `participant_id`, `query_id`, target label, access/persistence target, necessity oracle, demographic fields, query text, future historical rates. |
| Anonymous `user_state_id` | It retrieves a separate posterior; it is **not** one-hot encoded or learned as an identity feature. | Any profile/persona constructed from that user's future answers. |

The user's earlier feedback is represented by the **posterior state**, not by a raw historical-allow-rate feature.  `query_id` is used only to keep related rows together during replay; it never enters the model.

### Reward: unchanged, unweighted, selected-action only

Let \(y_{u,t}\) be the user's hidden, verified four-way response and \(a_{u,t}\) be the policy proposed before observing it.  The only learned reward is

\[
r_{u,t}^{\mathrm{joint}}
=\mathbb{1}\!\left[a_{u,t}=y_{u,t}\right].
\]

In the replay, the evaluator uses the original human questionnaire label to generate this binary feedback.  The learner receives **only** \(r_{u,t}^{\mathrm{joint}}\) for the action it selected; it must not receive the other three counterfactual rewards or the corrected four-way label in `update()`.

This preserves the definition of a contextual bandit—only the selected action's reward is observed—rather than converting the study to online supervised classification [Agarwal et al., 2014](https://proceedings.mlr.press/v32/agarwalb14.html).

There are no manual or adaptive weights such as

\[
w_{\mathrm{privacy}}H+w_{\mathrm{prompt}}B+w_{\mathrm{task}}Q.
\]

The survey does not identify the exchange rate between those outcomes.  `false allow`, `false deny`, and persistence errors remain separate diagnostics, not negative terms secretly added to the reward.

### Personalized posterior

1. Fit a global Factored Thompson posterior on **training participants only**; use validation participants only to choose hyperparameters.
2. Freeze the global posterior before touching test participants.
3. For each unseen test user \(u\), create an independent *tempered* copy of the global posterior.  The tempering prevents thousands of population observations from overwhelming the user's first few verified answers:

\[
\Lambda_{u,0}=\lambda I+\kappa(\Lambda_0-\lambda I),
\qquad
b_{u,0}=\kappa b_0,
\qquad 0<\kappa\leq1.
\]

Here \(\Lambda_0,b_0\) are the action-specific precision/reward statistics of the global policy; \(\lambda I\) is its ridge baseline.  \(\kappa\) is a **prior-strength hyperparameter**, not a reward weight.  It will be selected using only validation participants.

4. At request \(t\), sample/select an access action and then a persistence action from this user's factored Thompson posterior:

\[
a_{u,t}^{A}\sim\mathrm{TS}(x_{u,t};\Lambda^A_{u,t},b^A_{u,t}),
\qquad
a_{u,t}^{P}\sim\mathrm{TS}([x_{u,t},a_{u,t}^{A}];\Lambda^P_{u,t},b^P_{u,t}).
\]

5. After verified binary feedback arrives, update **only the selected access and persistence arms**, using the same joint reward for both, as in the existing offline `FactoredJointPolicy`:

\[
(\Lambda^A_{u,t+1},b^A_{u,t+1},\Lambda^P_{u,t+1},b^P_{u,t+1})
=\operatorname{UpdateSelected}(a^A_{u,t},a^P_{u,t},x_{u,t},r^{\mathrm{joint}}_{u,t}).
\]

The global posterior is never updated with test-user feedback, and feedback from user A can never improve user B's test result.

---

## 3. Feedback protocol and experiment environment

### Primary experiment: human-label online replay

The current dataset has no timestamps, real execution, prompt burden, overrides, or revocations.  Therefore the implementation must be called:

> **randomized sequential online-feedback replay simulation using human stated-policy labels**

It is not a live online-user study and not a deployment evaluation.

For each held-out participant:

1. Keep all rows with the same `(participant_id, query_id)` in one **atomic query bundle**.  A bundle must never be partly in an earlier prefix and partly in a later suffix.
2. Generate a fixed, pre-registered random permutation of that user's query bundles.
3. For a bundle, issue all policy predictions before revealing feedback from that bundle.  This avoids an optimistic within-query leak when a natural-language request contains multiple related data items.
4. The evaluator maps each hidden stated label to the selected-action binary reward; then and only then update that user's posterior.
5. Move to the next bundle.

The learner sees only current context and its own past selected-action feedback:

\[
\mathcal H_{u,t}=\{(x_{u,s},a_{u,s},r_{u,s})\}_{s<t}.
\]

It cannot see a future label, a query bundle's future response, or the full reward vector.

### Why QSTN is not the primary feedback source yet

The current QSTN v1/v2 held-out calibration reports do not validate it as a human-like privacy-feedback oracle (v2: 90 held-out rows, accuracy 0.322, macro-F1 0.284; the project review explicitly says not to use v1/v2 as a validated source for RL).  Thus it must not be used to claim that online MAB improves for real people.

Once it passes an independent, frozen calibration gate, QSTN can implement a `FeedbackSource` adapter for a **separately labelled synthetic stress test**.  That is useful later for CMDP development, but it is not a primary online-MAB result and it must never be mixed with the human-label replay claim.

### Future live feedback rule (not part of current evaluation)

If this bandit is later connected to real users, its action should first be a **proposal in a confirmation-mediated study mode**.  No sensitive data is released merely because Thompson sampling explored an allow action.  A neutral confirmation, a random audit, or an explicit correction can produce feedback; silence must never be treated as approval.  The feedback-acquisition rule is not an extra MAB action and does not enter the reward.

This avoids selective-label bias and prepares the logs needed for future IPS/DR evaluation [Wang, Agarwal & Dudik, 2017](https://proceedings.mlr.press/v70/wang17a.html).  It is a study-safety wrapper, not a claim that this Step-2 model already solves deployment safety.

---

## 4. Fair comparison and validation protocol

### Data split

Reuse the existing participant-held-out split for direct comparability:

| Purpose | Participants | Use |
|---|---:|---|
| Train | 120 | Fit the population posterior. |
| Validation | 40 | Select \(\kappa\), Thompson exploration scale, and any implementation-only settings using the same replay protocol. |
| Test | 41 | One frozen final online replay; no hyperparameter tuning, no global updates. |

All hyperparameter decisions must be logged before the test run.  We will select settings on validation with a lexicographic rule:

1. retain only candidates whose validation false-allow rate does not exceed the frozen Factored-TS comparator;
2. among them, maximize validation prequential joint reward;
3. if none qualify, choose the minimum false-allow candidate, breaking ties by joint reward.

This is a transparent selection rule, not a scalar reward with arbitrary privacy weights.

### The sole efficacy comparator

Run the same contexts and bundle orders through:

| Role | Policy |
|---|---|
| Necessary fixed comparator | **Frozen global Factored Thompson**: same action space, features, and selected-action joint reward, but never updates on test-user feedback. |
| Proposed online baseline | **WP-FTS**: same global initialization, then a separate user posterior updates only from that user’s past selected-action feedback. |

The difference therefore isolates online personalization rather than a change in label, reward, feature set, or action space.  Existing majority and flat-four-arm results can remain in the paper's offline table; they are not additional online-MAB variants.

### Randomness and uncertainty

- Pre-register 20 bundle-order seeds and the Thompson random seeds before the final test.
- Treat them as algorithm/order sensitivity runs, **not** as independent human observations.
- For each participant, average the paired WP-FTS minus frozen-policy result across the pre-registered runs.
- Report 95% confidence intervals from a paired **participant-cluster bootstrap** over the 41 test participants.  Do not use 3,323 rows or five random seeds as the unit of independent human evidence.

---

## 5. Outcomes and success criteria

### Primary outcome

The primary performance outcome is prequential joint exact match, scored before the current feedback is revealed:

\[
\mathrm{PJEM}=\frac{1}{N}\sum_{u,t}\mathbb{1}[a_{u,t}=y_{u,t}].
\]

Report both the all-round score and the learning curve over equal within-user progress bins.  The curve makes it possible to distinguish a genuine online improvement from a cold-start average.

### Required safety and behavior diagnostics

| Metric | Formula / meaning | Why it is required |
|---|---|---|
| False-allow rate | \(P(a^A=\mathrm{allow}\mid y^A=\mathrm{deny})\) | A stated-preference violation: the user would deny but the model allows. |
| False-deny rate | \(P(a^A=\mathrm{deny}\mid y^A=\mathrm{allow})\) | Prevents claiming safety by simply denying everything. |
| Deny recall | \(P(a^A=\mathrm{deny}\mid y^A=\mathrm{deny})\) | Directly exposes whether the model learns restrictive users. |
| Over-/under-persistence | prediction of `persist` when the true label is `ask next time`, and vice versa | Keeps the access/persistence distinction visible. |
| Macro-F1 and access/persistence accuracy | Four-class and component diagnostics | Prevents a majority-class accuracy story. |

These diagnostics do **not** mean observed real-world data leakage or harm; this dataset contains stated preferences, not an executed disclosure outcome.

### Pre-registered acceptance condition

WP-FTS is a successful online baseline only if, on the frozen test protocol:

1. the paired participant-bootstrap 95% CI for the post-adaptation joint-exact-match gain over frozen Factored-TS has a lower bound above zero; **and**
2. false allow is lower than the frozen comparator, without a collapse in macro-F1 or deny recall.

We will not promise in advance that this occurs.  The legitimate reason it may occur is that WP-FTS has each user's previously verified feedback; it is not because it sees future labels, receives a hidden reward weight, or is allowed to exploit the entire full-information reward vector.

The current frozen offline Factored Thompson has a 43.78% joint exact-match score but a 100% false-allow rate on the existing held-out test.  That result makes false allow and deny recall mandatory diagnostics; a higher accuracy alone would not be an acceptable privacy claim.

An exploratory feasibility check found that simple within-user histories contain meaningful personalization signal, but it is **not a result** and will not be reported as one.  The final claim must rest only on the locked protocol above.

---

## 6. Required logging and implementation artifacts

Each replay event must record at least:

\[
(\texttt{run\_id},\texttt{split},\texttt{anon\_user\_id},\texttt{bundle\_id},t,
x\_\texttt{hash},a_t,\hat p_t(a_t\mid x_t),r_t,
\texttt{feedback\_source},\texttt{update\_applied},\texttt{model\_version}).
\]

For the current replay, `feedback_source = human_survey_replay` and `update_applied = true` after each bundle.  The hidden four-way label can appear in a protected evaluation column, but must be absent from the policy-update interface.  Thompson action propensity should be estimated with a fixed number of posterior Monte Carlo draws and logged; this is not required for the direct replay score but makes later logged-bandit analysis possible.

Implementation should be a separate `online_bandit_experiment/` module that reuses the existing sparse context builder, four-action mapping, `DiagonalLinearBandit`, and `FactoredJointPolicy` mechanics.  Required outputs:

- frozen protocol/configuration and split manifest;
- validation search table for \(\kappa\) and Thompson exploration;
- per-event immutable trajectory log;
- per-participant paired metrics;
- participant-bootstrap summary and learning-curve figures;
- leakage checks proving no future label, full reward vector, or test-user global update entered training.

---

## 7. Explicit non-goals and hand-off to CMDP

Do not add the following to this implementation:

- privacy-leakage/task/prompt weighted reward;
- QSTN as a human-valid feedback oracle;
- actual rule persistence, re-use, revocation, trust, fatigue, or prompt-budget dynamics;
- an LLM security guard that generates alternative responses such as “do not provide SSN; use an order number instead”;
- automatic execution of an exploratory allow decision.

Those are the right ingredients for the later main contribution:

\[
\max_\pi J_{\mathrm{user/task}}(\pi)
\quad\text{s.t.}\quad
J_{\mathrm{privacy\ violation}}(\pi)\leq B_P,
\qquad
J_{\mathrm{prompt\ burden}}(\pi)\leq B_I.
\]

At that stage, constraints, memory state, verified task outcomes, user corrections/revocations, an independently calibrated QSTN environment, and potentially a constitutional security sub-agent can be introduced.  A constrained objective is more defensible there than an arbitrary scalar reward weight [Achiam et al., 2017](https://proceedings.mlr.press/v70/achiam17a.html).

---

## 8. Approval checklist before implementation

Please confirm these five design choices:

1. Implement only WP-FTS as the online MAB; no online epsilon/UCB sweep.
2. Keep the current four actions, context features, and unweighted selected-action joint reward.
3. Use original human survey labels in a randomized sequential replay as the primary result; keep QSTN out of the primary online-MAB evaluation.
4. Treat `persist` as a one-step stated-policy label only; no real memory/reuse or long-horizon dynamics.
5. Require both post-adaptation agreement improvement and false-allow improvement before calling the online method successful.
