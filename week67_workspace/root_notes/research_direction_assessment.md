# Research-Direction Assessment: Janus vs. the active proposal

## Bottom line

**The direction has not been completed by Janus, so it remains worth pursuing.** However, Janus eliminates the possibility of claiming a generic "agentic permission-management framework" or a first exploration of the security/usability trade-off. The current proposal is publishable only if it is repositioned as a rigorous, personalized sequential policy-learning contribution that is evaluated in a realistic agentic environment and satisfies explicit safety constraints.

The more immediate novelty debt is the local predecessor, *Towards Automating Data Access Permissions in AI Agents* (Wu et al., 2511.17959v1). It already introduced automated permission prediction for AI agents using the same four user choices and a 205-participant vignette study. It then reduced the learning target to persistent allow versus persistent deny and evaluated LLM in-context learning plus collaborative filtering. The present proposal must be written as an extension of that paper, not as a new permission-prediction problem.

## What Janus actually contributes

Janus is a modular runtime system and automated test harness. Its policy manager enforces deterministic policies; a permission-assistant plug-in can allow, deny, escalate, or alter persistent rules. It studies six manually specified designs across simulated email, calendar, and file tasks, using attack and user-intent variants plus synthetic responders. Its conclusion is a systems/HCI result: no single design dominates the security, task-completion, and user-interruption trade-off.

It does **not** learn a participant-specific bandit policy from sequential feedback, estimate the causal value of updates with a frozen control, model a factorized access/persistence action explicitly, optimize a constrained sequential objective, or produce a trained security sub-agent/constitutional-RL policy.

## Claim-by-claim comparison

| Proposal element | Status after Janus and Wu et al. | Assessment |
|---|---|---|
| Agentic data-permission problem and four response choices | Already present in Wu et al.; Janus independently treats runtime permission designs and persistent policies. | Not novel as a problem formulation or UI/action menu. |
| Generic permission-controller architecture | Janus already provides a broader agent + policy-manager + permission-assistant architecture. | Do not claim an architecture/framework contribution unless adding a substantively new, reusable learning interface and evaluation asset. |
| Static prediction from contextual survey inputs | Wu et al. already learns personalized permission decisions from the same style of study data. | A new classifier or another offline MAB alone is unlikely to be a strong contribution. |
| Full factorization: access × persistence | Wu et al. collected four choices but reports a binary persistent allow/deny learning task; Janus has persistence policies but no learned factorized policy. | Potentially novel, but only if factorization yields a demonstrated safety/burden/adaptation advantage. |
| Sequential personalized updating (WP-FTS) | Neither paper evaluates a per-user Bayesian contextual-bandit learner with the proposal's matched frozen control. | A real opportunity, but replay from a one-shot survey demonstrates only stated-policy adaptation, not live behavior. |
| Security–utility–interruption constraints | Janus measures a related empirical frontier but does not formulate or learn a CMDP; the proposal only specifies this future phase. | Strongest future research opportunity, contingent on new outcomes and a trustworthy risk oracle. |
| Security sub-agent / constitutional alignment | Neither Janus nor the current completed proposal evidence establishes this component. | Open, but it is a separate contribution and needs its own data, independent safety audit, and ablations. |

## Reviewer-style assessment

### Reviewer 1 — technical soundness emphasis

The proposed offline and replay protocol is unusually careful about participant-held-out splits, bundle leakage, and separating a frozen control from online updates. That is a real methodological strength. But the current result is not a security result: the stated false-allow rate is approximately 98.5%, and the reward is agreement with stated labels rather than observed privacy harm, task utility, or interruption cost. Sequentially revealing fixed survey answers also cannot establish preference drift, revocation, fatigue, selective feedback, or consequences of an unsafe tool call. A publishable system claim requires a live or behaviorally calibrated evaluation protocol, conservative risk gating, and results on high-risk false negatives.

### Reviewer 2 — originality and significance emphasis

Janus makes the broad framework and trade-off motivation non-novel. Wu et al. is still closer: it has the same four user response choices, user-study basis, and a personalized prediction objective. The viable contribution is therefore narrow but meaningful: demonstrate that modelling access and persistence jointly, then updating a user-specific policy online, improves the *safety–interruption–task-success frontier* over both Wu et al.'s static predictor and Janus's fixed permission assistants. It must not be framed as "we use MAB for permissions"; that would read as an incremental algorithm substitution.

### Reviewer 3 — broad interest and usability emphasis

The work can interest usable-security, privacy, and agent-systems audiences because it directly operationalizes a growing deployment problem: when should an agent decide, remember, or return control? Its broad-interest case depends on an end-to-end demonstration in an actual agent loop, not a survey-only accuracy gain. Janus is a natural benchmark substrate. The proposal should show how user-specific history affects the choice to prompt or persist without enabling unsafe persistent grants, and should make its user-facing policy scope intelligible.

## Cross-review synthesis

All three assessments agree on a **conditional continue**, not a stop. The current MAB work is valuable as a diagnostic baseline and as preparation for the research question that Janus itself leaves open. It is not sufficient as the final paper. The decisive condition is a shift from a leaderboard claim (higher JEM/macro-F1) to a systems claim (safer delegation under a bounded prompt budget, personalized from sequential feedback).

## Recommended research positioning

Use this as the contribution sentence after empirical validation:

> We study personalized, factorized runtime delegation: from sequential user feedback, a permission assistant decides both whether a proposed data/tool action may proceed and whether that decision should persist, while high-risk actions remain subject to explicit safety constraints.

This creates a clean division of labor:

```text
Janus: agent runtime + scenario/harness + fixed permission-assistant baselines
                  ↓
Your contribution: learned user-specific access/persistence policy
                  ↓
Risk gate / audit: blocks or escalates high-risk actions independently of preference prediction
                  ↓
Evaluation: safety violation, task success, prompt burden, persistence error, adaptation over time
```

## Minimum credible next study

1. **Use Janus as a benchmark, not as a competitor to ignore.** Implement global static, WP-FTS, WP-FTS plus risk gate, and an oracle upper bound as Janus plug-ins; compare against its six supplied assistants.
2. **Establish baselines fairly.** Reproduce or directly compare with Wu et al.'s LLM in-context, collaborative-filtering, and hybrid predictors on the appropriate binary subset; report the four-class extension separately.
3. **Make the primary endpoint a constrained frontier.** Report attack/out-of-alignment false-accept rate, task success/desired calls, user prompts or time, persistence-scope errors, and adaptation curves. Compare methods at matched prompt budgets and matched safety thresholds.
4. **Do not treat Janus's alignment-aware responder as a discovery result.** It receives scenario ground truth and is an oracle-style evaluation component. Use it only as an upper bound; validate the learned policy with real users or a behavioral simulator calibrated independently from held-out human data.
5. **Collect the missing signals before claiming CMDP/RL.** At minimum: confirmation, override/revoke, task completion, data exposure/audit event, prompt burden, and risk labels. Pre-register which become reward terms and which are hard constraints.

## Go / no-go recommendation

- **Go:** build the personalized permission-assistant plug-in and evaluation protocol above. This has a defensible research gap and lets the project turn Janus from a novelty threat into experimental infrastructure.
- **No-go for a standalone final paper:** simply adding more offline or replay MAB variants to the present survey data. It would remain too close to Wu et al., while its near-100% false-allow rate prevents a credible security claim.
- **Phased thesis path:** retain the current MAB result as Paper/Chapter A (bounded stated-policy adaptation); make the end-to-end constrained agent evaluation the main Paper/Chapter B; treat constitutional alignment as a separate follow-on only after a security dataset and audit protocol exist.

## Assessment boundary

The evaluation is grounded in the supplied Janus PDF, the active local proposal, the locally stored Wu et al. predecessor, and a focused current literature check. It does not inspect Janus source code, run the framework, or verify performance claims beyond the papers' reported evidence. The PDF rendering utility was unavailable; the content assessment used complete text extraction rather than visual page review.
