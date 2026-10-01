# Privacy and Security Rule Skill v2.0

## Purpose

This file is the complete English evidence-derived rule catalog for the S-QSTN respondent layer. It preserves the concrete rule descriptions collected in the project evidence registry and explains how they are bounded for an LLM respondent. The v1.0 and v1.1 catalog content is inherited unchanged; this version adds a bounded-memory and verified-event boundary.

This catalog is not a probability model, a safety gate, a tool policy, a reinforcement-learning reward, or a hidden chain-of-thought request. It is a semantic reference layer. The executable subset is defined by `config/v2.0/security_behavior_rules.json`.

## Runtime use

Use the catalog according to the selected skill mode:

- `active_excerpt`: inject only the active qualitative RulePack context for the current questionnaire item. The full catalog remains available as a versioned audit asset but is not placed in the respondent prompt.
- `full_catalog_with_active_excerpt`: inject this complete catalog together with the active qualitative RulePack context. Apply only inherited grouped rules activated by the JSON RulePack for the explicit current context. Apply v2 state rules only through the verified event/state boundary. Treat `deferred_longitudinal`, `candidate_future`, `evidence_only`, and `catalog_only_boundary` entries as documentation and constraints, not as active instructions.

The catalog must not be used to infer missing context. It must not turn evidence boundaries into numeric weights. It must not convert a normal respondent denial into an agent violation. It must not make a safety decision or execute a tool.

## v2.0 operational layer

The v2.0 JSON RulePack preserves the v1.1 grouped behavioral and audit rules and adds explicit state rules for verified negative events, bounded repair recovery, prompt-burden history, trust-dimension separation, and recency metadata.

The default behavior mode is `stateful_audit_compatible`. In this mode, current-turn context and deterministic reason codes are recorded, while verified events may update bounded categorical state through explicit transitions. State is not a probability, confidence score, safety decision, or calibrated answer weight.

The optional `synthetic_exploratory` mode may expose bounded memory fixtures for transition tests. It must be recorded separately from the default mode and must not be presented as a calibrated human memory or behavior model.

`uncertainty_bucket` describes explicit information completeness, not LLM confidence. Missing fields remain `unknown`; the wrapper must not infer purpose, expectedness, scope, duration, transparency, control, burden, or requester identity from question prose, labels, text length, denial, or row count.

`prompt_burden_bucket` may include a bounded event history in v2.0, but it never maps mechanically to allow or deny, and it never suppresses mandatory consent refresh. Single-item presentation remains `not_applicable_single_item` unless an explicit fixture or annotation supplies history.

The structured reason codes summarize source fields and activation boundaries. They are audit facts rather than hidden reasoning. Human `label_id`, `label_text`, and observed Task 3 outcomes remain outside the skill context and every respondent prompt.

## v2.0 memory and event boundary

The respondent does not receive a full transcript. The wrapper maintains a private structured event ledger and compiles a bounded `memory_view` and categorical `state_snapshot` for the current prompt. Only externally verified events may update trust or violation state. Ordinary respondent denial is never an agent violation.

Use event order and explicit retention classes to represent limited recall. A recent-only event may expire from the memory view, while a verified boundary event may remain as a caution summary. v2.0 does not select human-calibrated time windows, decay coefficients, trust-loss magnitudes, recovery durations, or probabilities. Those belong to a later calibration layer.

## v2.0 principle coverage

| Principle | Name | v2.0 status | Interpretation |
| --- | --- | --- | --- |
| P1 | Trust Loss Asymmetry | partial_stateful | Verified negative events may create categorical caution; trust-loss magnitude is not calibrated. |
| P2 | Trust Recovery Lag | partial_stateful | Verified repair enters bounded recovery; recovery duration is not calibrated. |
| P3 | Recency Dominance | uncovered | No current runtime rule. Do not invent a recency decay. |
| P4 | Expectation Violation Effect | active_grouped | Explicit mismatch increases caution and clarification preference. |
| P5 | Perceived Control | active_grouped | Explicit scope, duration, review, or revocation supports controllable options without forcing consent. |
| P6 | Transparency Calibration | active_grouped | Explanation and provenance calibrate understanding; transparency is not an allow command. |
| P7 | Permission Fatigue | partial_stateful | Bounded prompt/interruption history is recorded; fatigue-to-choice effects are not calibrated. |
| P8 | Severity Dominance | safety_boundary_only | Objective severity belongs to an independent safety oracle, not to the respondent simulator. |
| P9 | Privacy Calculus | partial_active | Current necessity and scoped sharing are active; no numeric benefit-minus-cost calculation is active. |
| P10 | Stable Privacy Trait | active_grouped | The empirical profile is a soft prior, not a hard policy. |
| P11 | Context Dependency | active_grouped | Judge the exact item, requester, tool, purpose, and scope together. |
| P12 | Trust Calibration | partial_stateful | Trust dimensions are separated in state; their answer mapping is not calibrated. |

## Rule status vocabulary

- `active_grouped`: the source rule is represented by a current directional JSON rule and may influence the active excerpt when its explicit trigger matches.
- `partial_stateful`: the v2.0 wrapper records a bounded categorical state or event boundary, but the human-calibrated effect remains deferred.
- `deferred_longitudinal`: the rule requires state or calibration that v2.0 does not claim to provide.
- `candidate_future`: the rule is a useful future context or ledger feature but is not currently executable.
- `evidence_only`: the rule provides an evidence-derived semantic constraint but is not mapped to a v2.0 trigger.
- `catalog_only_boundary`: the rule is a safety, system-strategy, evaluation, or migration boundary. It must not be used as a respondent preference rule.

## Concrete rule catalog

### Cao-R1 - Context rule

- Principle: P11
- Source sheet: `Cao_Rules`
- Evidence rating: Partial direct support
- Runtime status: `active_grouped`
- Rule description: The answer must depend on the current task and request context rather than on a global persona alone.
- Behavioral interpretation: Combine the profile with runtime expectation, current function, request explanation, data type, and scope. Context should condition the profile, not replace it.
- Evidence boundary: The evidence supports bringing context into the model. It does not support ignoring individual differences and looking only at the current task.

### Cao-R2 - Expectation rule

- Principle: P4
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Unexpected or unanticipated permission requests are more likely to be rejected or to prompt a request for explanation.
- Behavioral interpretation: When the request is explicitly unexpected, increase caution and prefer clarification; avoid treating an unexpected request as an automatic safety violation.
- Evidence boundary: The result comes from Android runtime permissions. It transfers to an agent only as a qualitative direction, not as a numeric effect.

### Cao-R3 - Functionality and utility rule

- Principle: P9
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support at the reason layer
- Runtime status: `active_grouped`
- Rule description: Data that is genuinely needed for the current function is more likely to be permitted.
- Behavioral interpretation: Use current utility or feature necessity as a soft reason supporting a scoped, current-task share. Do not treat it as a deterministic causal rule.
- Evidence boundary: The evidence is a user-reported reason distribution, not a randomized causal coefficient for functional necessity.

### Cao-R4 - Least-privilege rule

- Principle: P9
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support at the reason layer
- Runtime status: `active_grouped`
- Rule description: A permission connected to an unused feature is more likely to be rejected; users judge whether the application truly needs the permission.
- Behavioral interpretation: If the feature is not used or necessity does not match, increase denial or narrower-scope preference and preserve a separate denial reason.
- Evidence boundary: Lack of immediate utility and perceived impropriety must remain separate denial reasons so that a denial does not incorrectly update trust or caution.

### Cao-R5 - Explanation rule

- Principle: P6
- Source sheet: `Cao_Rules`
- Evidence rating: Requires rewriting for transfer
- Runtime status: `active_grouped`
- Rule description: A concrete, relevant, and credible explanation can increase willingness to permit access.
- Behavioral interpretation: Explanation presence can soften uncertainty and improve understanding. Explanation quality, relevance, and truthfulness require separate evidence or an independent oracle.
- Evidence boundary: The stronger claim about concrete, relevant, and credible explanations is not attributable to Cao alone; other studies must support it.

### Cao-R6 - Temporal and temporary-grant rule

- Principle: P5 / P9
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support
- Runtime status: `candidate_future`
- Rule description: When users are uncomfortable with permanent authorization, they prefer a temporary or one-time grant.
- Behavioral interpretation: If persistent consent conflicts with the profile or explicit comfort information, a temporary option may be preferred and reluctant consent may be recorded when it is unavailable.
- Evidence boundary: The study did not directly measure uncertainty about future use. Do not treat future uncertainty as an already validated variable.

### Cao-R7 - Reversibility rule

- Principle: P5
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support with decomposition
- Runtime status: `active_grouped`
- Rule description: When users know that a decision can be changed, they may defer or deny now; a historical grant must support later revocation.
- Behavioral interpretation: Explicit reversibility can support defer-or-deny-now without implying permanent rejection. A ledger must distinguish later grant and revoke events.
- Evidence boundary: Reversibility supports deferral, denial now, and revocation. It does not automatically prove that a temporary allow should be selected.

### Cao-R8 - Attitude and behavior separation rule

- Principle: P10
- Source sheet: `Cao_Rules`
- Evidence rating: Direct support with terminology correction
- Runtime status: `active_grouped`
- Rule description: Privacy attitude, expectation accuracy or context understanding, and observed grant or denial behavior should be modeled separately.
- Behavioral interpretation: Keep privacy attitude, expectation accuracy, and observed decision history as separate concepts. Do not derive behavior from privacy attitude alone.
- Evidence boundary: The source did not independently measure a general knowledge level. Use expectation accuracy or context understanding instead of a broad knowledge label.

### Wij2017-R1 - Context-change and no-blind-reuse rule

- Principle: P11
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: A historical allow must not automatically carry over to a different future context; context change requires renewed evaluation.
- Behavioral interpretation: Store an explicit context signature with each authorization. If the current context is not sufficiently similar, do not reuse the old decision blindly and prefer re-evaluation or asking.
- Evidence boundary: The source supports no-blind-reuse, but it does not prove that every agent field independently changes a decision. The final context schema needs additional evidence.

### Wij2017-R2 - Observable runtime-context rule

- Principle: P11 / P4
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Observable request context must enter the decision, especially requester visibility and the foreground task or application being used.
- Behavioral interpretation: Represent requester visibility, foreground task, permission or data type, and request time as explicit features. Treat their effects as profile-conditioned, not universal switches.
- Evidence boundary: Visibility and foreground application are Android proxy variables. An assistant mapping should use task stage, active tool, or user-visible action without copying feature importance.

### Wij2017-R3 - Profile heterogeneity rule

- Principle: P10
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Users are not one average privacy decision maker. Some show stable default allow or deny tendencies, while others make more contextual judgments.
- Behavioral interpretation: Preserve a profile-level default tendency and context sensitivity. Do not simulate every profile as equally contextual.
- Evidence boundary: The reported subgroup proportion is descriptive for one Android sample and threshold; it is not a fixed S-QSTN population prior.

### Wij2017-R4 - Similar-history ledger rule

- Principle: P11
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Similar historical grants and denials are more useful for a later decision than a global allow rate.
- Behavioral interpretation: Index history by request and context signatures and use similar outcomes as soft features. A new high-risk or explicitly inappropriate signal must not be overridden by history.
- Evidence boundary: This is predictive association rather than a causal law, and history is not equivalent to permanent consent. A future ledger must also include purpose, recipient, scope, expiry, and revoke.

### Wij2017-R5 - Cold-start and elicitation rule

- Principle: P10 / P11
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support as system strategy
- Runtime status: `catalog_only_boundary`
- Rule description: A new user cannot be reliably inferred only from other users, especially when the user is contextual; bounded structured elicitation is needed early.
- Behavioral interpretation: During a future bootstrap stage, collect user-specific labels across diverse contexts and keep cold-start uncertainty high until coverage is adequate.
- Evidence boundary: This is a permission-system learning and sampling strategy, not a claim that users must change. Reported trial counts and accuracy do not transfer directly to agent permissions.

### Wij2017-R6 - Low-confidence re-ask rule

- Principle: P10 / P11
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support as system strategy
- Runtime status: `catalog_only_boundary`
- Rule description: When the system cannot reliably predict a preference, it should ask again instead of confidently allowing or denying.
- Behavioral interpretation: A future calibrated policy may map low prediction confidence to clarification and update history only after a response.
- Evidence boundary: Confidence-to-ask is an automation strategy, not a human behavior law. Thresholds and prompt rates must not be hard-coded without calibration.

### Wij2017-R7 - False-allow asymmetry and safety-evaluation rule

- Principle: P8
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Direct support as evaluation design
- Runtime status: `catalog_only_boundary`
- Rule description: False allow and false deny must be measured separately; allowing a request that the user intended to reject can create a privacy violation that is harder to reverse than a later authorization.
- Behavioral interpretation: Keep false-allow privacy violation and false-deny functionality loss as separate evaluation outcomes. High-risk or explicitly inappropriate requests require an independent safety gate.
- Evidence boundary: The source supports asymmetric metrics, not a universal AI-agent reward weight. High-risk classification must come from an independent security or task oracle.

### Wij2017-R8 - Prompt-burden and habituation rule

- Principle: P7
- Source sheet: `Wijesekera_2017_Rules`
- Evidence rating: Partial direct support
- Runtime status: `deferred_longitudinal`
- Rule description: Frequent low-necessity permission prompts create burden and may habituate users to later important prompts; too few prompts can also violate user expectations.
- Behavioral interpretation: A future state may track prompt frequency and interruption cost with profile-specific effects and selective re-asking.
- Evidence boundary: The source motivates a burden variable but does not provide direct longitudinal evidence for a fixed burden-to-allow or burden-to-deny transition.

### Elbitar-R1 - Rationale-presence rule

- Principle: P6
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: An explanation or rationale can affect the current authorization; under the standardized rationale, users may grant more often and feel more informed.
- Behavioral interpretation: When a rationale is present and independently verified as intact, it may improve understanding and informed choice. It must not override high-risk, explicitly inappropriate, or integrity-failure signals.
- Evidence boundary: Only one standardized rationale design was tested. The result does not imply that any explanation quality, relevance, truthfulness, or credibility improves allowing.

### Elbitar-R2 - Timing and rationale interaction rule

- Principle: P6
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Request timing and rationale should be modeled together rather than as identical independent bonuses across every outcome.
- Behavioral interpretation: Keep request timing and rationale presence separate and allow an interaction for subjective outcomes such as informedness, clarity, and satisfaction.
- Evidence boundary: The final grant or deny model reported main effects rather than a timing-by-rationale interaction. Do not generalize the interaction to every output, especially allow.

### Elbitar-R3 - Timing trade-off and no-universal-best rule

- Principle: P6
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `candidate_future`
- Rule description: An in-context request can increase granting, but it is not better on every experience measure; without a rationale it may provide an additional informedness or clarity benefit.
- Behavioral interpretation: Treat timing as a context-dependent trade-off. Do not encode in-context timing as inherently safer, more informed, or universally preferred.
- Evidence boundary: In-context was defined by mobile application state. An assistant mapping should use task stage, active feature, or user-visible action rather than a fixed safety label.

### Elbitar-R4 - Individuality and profile-modulated communication rule

- Principle: P10
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Users genuinely differ in their responses to timing and rationale; no single request strategy fits everyone.
- Behavioral interpretation: Preserve profile variables such as rationale preference, timing preference, and privacy concern. Preserve response variance instead of averaging it into a universal prompt rule.
- Evidence boundary: The study does not provide a reusable persona taxonomy or population proportions. S-QSTN profiles require calibration rather than treating an intraclass correlation as a fixed weight.

### Elbitar-R5 - Attitude, sensitivity, and clarity separation rule

- Principle: P10
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Privacy concern, perceived sensitivity of the request, and initial clarity about the purpose should be represented separately; a single privacy attitude cannot explain grant or deny.
- Behavioral interpretation: Keep privacy concern, perceived sensitivity, and purpose clarity separate. A verified explanation can update clarity, but it does not prove necessity or safety.
- Evidence boundary: These are controlled associations, not causal coefficients for an AI-agent permission decision. Actual sensitivity and necessity require an independent task or security oracle.

### Elbitar-R6 - Decision and evaluation separation rule

- Principle: P5
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support as a counter-claim
- Runtime status: `active_grouped`
- Rule description: Consent action, informedness, satisfaction, and perceived control are different outcomes; explanation or suitable timing does not automatically create a feeling of control.
- Behavioral interpretation: Keep action and structured feedback separate. Do not deterministically increase perceived control merely because an explanation was shown.
- Evidence boundary: This is a one-time subjective evaluation, not a longitudinal autonomy or trust trajectory. It cannot replace evidence about revocation, override, or repeated-error behavior.

### Elbitar-R7 - Explanation attention and provenance rule

- Principle: P6
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Direct support with decomposition
- Runtime status: `active_grouped`
- Rule description: Showing a rationale does not prove that the user read it, understood it, or identified its source correctly; attention and source should be explicit.
- Behavioral interpretation: Track rationale presence, being seen, comprehension, and explanation source separately. Label app- or agent-supplied sources and do not infer comprehension from delivery alone.
- Evidence boundary: Post-experiment recall cannot directly set a conversational attention probability. It is evidence for attention and comprehension uncertainty, not a fixed parameter.

### Elbitar-R8 - Rationale-integrity boundary rule

- Principle: P6 / P8
- Source sheet: `Elbitar_2021_Rules`
- Evidence rating: Requires rewriting for agent safety
- Runtime status: `catalog_only_boundary`
- Rule description: An unverified explanation must not increase allowing merely because a rationale exists; misleading, incorrect, or malicious rationales require independent handling.
- Behavioral interpretation: Apply an explanation-related allow effect only when an independent integrity oracle verifies the rationale. Otherwise surface uncertainty or ask for clarification.
- Evidence boundary: This is an agent-safety inference, not a directly measured user effect. It must remain separate from the respondent simulator and any false-allow hard gate.

### Wij2015-R1 - Perceived necessity and functionality rule

- Principle: P9
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: When users perceive a request as unrelated to the current function they are more likely to reject or ask why; perceived necessity supports allowing.
- Behavioral interpretation: Keep perceived necessity separate from objective necessity. Low perceived necessity increases denial or clarification preference, but an asserted purpose is not proof of necessity or safety.
- Evidence boundary: This is subjective perceived necessity from retrospective interviews, not technical objective necessity and not a direct causal effect of an explanation.

### Wij2015-R2 - Expectation and contextual-integrity rule

- Principle: P4 / P11
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Access that violates expectations for the current context should increase the tendency to deny, ask for explanation, or ask again.
- Behavioral interpretation: Derive a qualitative expectation-mismatch feature from the active task, recent user action, requester identity, data and scope, and contextual cues.
- Evidence boundary: The evidence comes from a one-week screenshot-recall study and is associative. Do not use its coefficient as a reusable transition probability.

### Wij2015-R3 - Visibility and active-use rule

- Principle: P11
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: A visible requester, active use, and contextual cues make access more expected; background or invisible access increases rejection.
- Behavioral interpretation: Represent agent visibility, user active task, and contextual cues explicitly. An agent acting outside the visible task context should favor explanation or a refresh question.
- Evidence boundary: The source variables are Android foreground and background visibility. An assistant should map them to visible task stage and explicit notification, not equate them with an open chat window.

### Wij2015-R4 - Individual-history calibration rule

- Principle: P10
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Users show stable but different reactions to the same request; calibration should use that user's decision history rather than a global average.
- Behavioral interpretation: Keep user-specific decision state and update it from observed consent action and structured feedback. Treat population estimates as priors only.
- Evidence boundary: The small one-week Android study does not provide a reusable persona taxonomy, population ratio, or long-term trust parameter. Its AUC is not an S-QSTN fidelity target.

### Wij2015-R5 - Context-scoped authorization ledger rule

- Principle: P11
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `candidate_future`
- Rule description: A single authorization should not be permanently reused by requester and permission alone; history must be bound to resource and context.
- Behavioral interpretation: A future ledger may key consent by agent, data or scope, purpose, recipient, action, and visibility. Reuse an old decision only when the key matches.
- Evidence boundary: The source triplet does not include agent purpose, recipient, duration, retention, revoke, or scope editing. The S-QSTN ledger must extend it rather than reuse a global allow rate.

### Wij2015-R6 - Context-over-data-type rule

- Principle: P9 / P11
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Data type or permission type alone is insufficient; requester identity, activity, visibility, and context also matter.
- Behavioral interpretation: Treat data sensitivity as one input and combine it with requester, activity, visibility, scope, necessity, and profile history. Do not let a generic data type decide the answer alone.
- Evidence boundary: The study covered selected sensitive Android resources. It cannot lower a high-risk or explicitly inappropriate safety boundary and cannot generalize a screen-state result to every background agent.

### Wij2015-R7 - Prompt-burden and selective-prompting rule

- Principle: P7
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Partial direct support
- Runtime status: `deferred_longitudinal`
- Rule description: The system should not ask about every sensitive access; frequent prompts create burden and habituation risk, so burden should be represented dynamically.
- Behavioral interpretation: A future state may include recent prompt count, interruption cost, and unresolved requests and may prefer selective prompting for uncertain or expectation-violating requests.
- Evidence boundary: The evidence concerns prompt frequency and design feasibility, not a universal longitudinal transition to greater caution, trust, or allowing.

### Wij2015-R8 - Static privacy-attitude insufficiency rule

- Principle: P10
- Source sheet: `Wijesekera_2015_Rules`
- Evidence rating: Direct support as a counter-claim
- Runtime status: `active_grouped`
- Rule description: A single static privacy-concern score or cautious persona cannot by itself predict rejection; context and personal history are needed.
- Behavioral interpretation: Treat static privacy attitude as a weak prior at most. Update behavior from contextual decisions, feedback, and permission history when those signals are available.
- Evidence boundary: This does not mean privacy concern is irrelevant. It rejects treating one questionnaire score as a sufficient predictor, while safety boundaries remain independent.

### Malkin-R1 - Scoped disclosure and requester-identity rule

- Principle: P11
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support as system design
- Runtime status: `candidate_future`
- Rule description: Authorization should not cover everything an assistant hears; it should bind a requester to the needed data or content scope and disclose who will access it.
- Behavioral interpretation: A future ledger should include agent or app identity, data entity or type, purpose, recipient or network release, scope, and duration. Show identity and log automated decisions.
- Evidence boundary: This is a threat-model and design premise, not a deployment causal measurement. Displaying identity does not prove that the user understood it.

### Malkin-R2 - Denial-reason separation rule

- Principle: P9
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: A denial may mean that access is inappropriate or simply that the service is not useful now; these reasons should not share one training label.
- Behavioral interpretation: Store denial reason separately from consent action, with categories such as not useful now, perceived overreach, integrity concern, scope confusion, and interruption burden.
- Evidence boundary: The source uses short scripted Wizard-of-Oz interactions. S-QSTN should collect structured reasons rather than assume that an action label carries its own meaning.

### Malkin-R3 - Anomaly attention and false-allow rule

- Principle: P4 / P8
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `candidate_future`
- Rule description: Irrelevant or anomalous permission requests usually create alertness and rejection, but a user may still allow by missing the prompt or through habituation.
- Behavioral interpretation: A future current-turn feature may represent anomaly salience and attention. Anomalies can increase denial or clarification while bounded false allow remains possible.
- Evidence boundary: The anomaly app, topic, and timing were researcher-designed. Human false allow supports an evaluation boundary; it does not make a risky policy better.

### Malkin-R4 - Prompt-burden and interruption rule

- Principle: P7
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `deferred_longitudinal`
- Rule description: Asking every time creates substantial interruption; permission history and selective prompting should aim partly to reduce interruption.
- Behavioral interpretation: A future burden state may use recent prompt frequency, unresolved requests, and interruption cost to choose selective or low-risk timing, without suppressing mandatory safety or consent refresh prompts.
- Evidence boundary: The evidence supports prompt burden, not a fixed long-term transition in trust or strictness after every prompt.

### Malkin-R5 - Persistent-scope comprehension and renewal rule

- Principle: P5 / P11
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `candidate_future`
- Rule description: Always allow and always deny must distinguish requester, data scope, and duration; a long-term rule is not automatically permanent or unambiguous consent.
- Behavioral interpretation: Represent one-time, persistent allow, persistent deny, expiry, scope, and renewal separately. If scope or duration is unclear or changed, ask a refresh question.
- Evidence boundary: The result concerns a specific voice interface and Rules UI. It supports explicit scope, expiry, and refresh fields but does not measure long-term revocation rates or an optimal expiry duration.

### Malkin-R6 - Automation-control heterogeneity rule

- Principle: P5 / P12
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Users differ in their acceptance of automatically learned permissions: some prefer fewer interruptions, while others prefer direct control because they distrust automation.
- Behavioral interpretation: Keep automation trust and control preference as profile-conditioned concepts. Let them modulate acceptance of automation and review requests rather than choosing one universal automation preference.
- Evidence boundary: Learning was an idealized simulation with only one or two requests per app and no real online learner. It does not validate long-term personalized updates.

### Malkin-R7 - Review and audit are not a safety substitute rule

- Principle: P5
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: Retrospective review and audit can provide feedback and correction, but they cannot replace proactive confirmation or blocking for high-risk requests.
- Behavioral interpretation: Keep review availability and engagement separate. Support audit, override, and correction as interaction feedback while keeping hard safety boundaries external.
- Evidence boundary: Short experiments may underestimate long-term review use. User preference for audit must not be interpreted as proof of safety.

### Malkin-R8 - Consequential-action and sensitive-data safety rule

- Principle: P8
- Source sheet: `Malkin_2022_Rules`
- Evidence rating: Requires rewriting as an independent safety boundary
- Runtime status: `catalog_only_boundary`
- Rule description: High-consequence actions should require human confirmation at runtime, and known highly sensitive data should receive stricter protection.
- Behavioral interpretation: An independent security oracle may require confirmation for high-consequence actions or block invalid high-risk scope. These constraints remain outside the respondent simulator and learned allow tendency.
- Evidence boundary: This is a safety design recommendation and researcher inference, not a universal human action policy measured by the source.

### Harborth-R1 - Contextualized-purpose explanation rule

- Principle: P6 / P11
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support
- Runtime status: `active_grouped`
- Rule description: An explanation improves understanding when it clearly links the app, permission, function, and data use.
- Behavioral interpretation: Represent the purpose as a structured link between agent or app, requested resource, concrete task function, and data use. Improve comprehension only when the explanation is contextualized and readable.
- Evidence boundary: The evidence supports short-term understanding in a hypothetical application setting, not long-term trust or a causal increase in allowing.

### Harborth-R2 - Explanation is not an allow-nudge rule

- Principle: P6
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support as a counter-constraint
- Runtime status: `active_grouped`
- Rule description: Better transparency or understanding must not be written as "the better the explanation, the more the user should allow."
- Behavioral interpretation: Keep explanation effects on comprehension separate from action. Let utility, risk, scope, and profile govern the final decision; do not reward persuasive wording.
- Evidence boundary: A correlation between lower privacy concern and higher grant does not authorize persuasive explanations to bypass a safety boundary.

### Harborth-R3 - Current functional necessity and least-privilege rule

- Principle: P9
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support in a related model
- Runtime status: `active_grouped`
- Rule description: If the user believes the application can complete the current function without the permission, willingness to allow falls; necessity should be judged per function and permission.
- Behavioral interpretation: Compute a qualitative necessity match for the specific requested function. Non-essential access increases denial, narrower-scope, or ask-why preference.
- Evidence boundary: The source used a fictional MAR furniture application and cannot serve as an objective necessity oracle. The environment or security layer must supply objective necessity.

### Harborth-R4 - Perceived privacy-danger rule

- Principle: P9
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support in a related model
- Runtime status: `active_grouped`
- Rule description: When users perceive a permission as more privacy-invasive or risky, willingness to allow decreases; perceived risk is profile by context.
- Behavioral interpretation: Keep perceived privacy danger separate from objective risk. Higher perceived danger can increase denial, explanation, scope restriction, and revocation preference.
- Evidence boundary: The source measures perception, not objective risk. Low concern must not be simulated as low objective risk or automatic allow.

### Harborth-R5 - Risk-perception gap and novel-sensor caution rule

- Principle: P8 / P9
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Partial direct support
- Runtime status: `catalog_only_boundary`
- Rule description: Users may underestimate unfamiliar or unlisted sensor risks; low concern must not be treated as evidence that sharing is safe.
- Behavioral interpretation: Keep objective risk, comprehension, and perceived danger separate. If objective risk is high and comprehension is low, ask for clarification or defer to the independent safety gate.
- Evidence boundary: Blocking high-risk access is an S-QSTN safety design inference, not a measured user behavior effect. External risk evidence must not be mislabeled as this experiment's causal effect.

### Harborth-R6 - Scope, timing, and revocability disclosure rule

- Principle: P5
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support as qualitative finding and design recommendation
- Runtime status: `active_grouped`
- Rule description: Users ask whether an individual permission can be refused or limited, when data is collected, and what refusal does to functionality; these should be visible request and feedback fields.
- Behavioral interpretation: Expose scope, foreground or background timing, required versus optional status, consequence of decline, and restrictability. Missing fields favor explanation or deferral rather than broad persistent consent.
- Evidence boundary: Open responses support information needs and UI fields but do not estimate their causal effect on multi-round trust, revocation, or real choices.

### Harborth-R7 - Readability and progressive-detail rule

- Principle: P6 / P7
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Partial direct support
- Runtime status: `active_grouped`
- Rule description: Explanations should be understandable, concise, and expandable; difficult terminology or excessive length reduces information value and increases burden.
- Behavioral interpretation: Represent readability and detail level qualitatively. Use plain-language base text with optional detail; low readability favors clarification or deferral and reduces comprehension.
- Evidence boundary: Complexity was mainly a design control, not an independently estimated behavioral coefficient. Use it as a quality condition, not a numeric weight.

### Harborth-R8 - Temporal foreground-scope rule

- Principle: P11
- Source sheet: `Harborth_2021_Rules`
- Evidence rating: Direct support as descriptive evidence
- Runtime status: `active_grouped`
- Rule description: Authorization is not one permanent switch: users are generally more willing to authorize foreground use than indefinite or background use, so duration and runtime scope should be separate.
- Behavioral interpretation: Represent foreground-only, one-time, session, persistent, and background access as separate scopes. Ambiguous requests favor a narrower scope or explicit scope question.
- Evidence boundary: The study did not track long-term scope changes or revocation rates, so it cannot set a long-term memory update speed.

### Esterwood-R1 - Repeated verified-violation accumulation rule

- Principle: P1 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Partial direct support across domains
- Runtime status: `deferred_longitudinal`
- Rule description: Repeated observable or explicitly disclosed errors by the same collaborator accumulate and reduce trust; each request should not be treated as an independent questionnaire item.
- Behavioral interpretation: A future state may count only oracle-verified or user-observed agent failures. Each verified failure can raise caution and reduce relevant trust dimensions; ordinary denial is excluded.
- Evidence boundary: The source measured trust in robot collaboration rather than privacy or questionnaire answers. It supports only a directional verified-error prior and no decay rate.

### Esterwood-R2 - No full reset after verbal repair rule

- Principle: P1 / P2 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Partial direct support across domains
- Runtime status: `deferred_longitudinal`
- Rule description: After multiple errors, apology, explanation, or promise cannot restore trust to a never-failed baseline; long-term memory must not be cleared by one repair utterance.
- Behavioral interpretation: Treat repair language as a bounded mitigation signal. Preserve violation history and require later error-free behavior for gradual recovery.
- Evidence boundary: The source did not test a genuine long-term recovery trajectory or continuous correct behavior. Gradual recovery is a cautious S-QSTN design, not an estimated result.

### Esterwood-R3 - Denial after verifiable error penalty rule

- Principle: P1 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Partial direct support across domains
- Runtime status: `deferred_longitudinal`
- Rule description: If an agent denies responsibility for a verifiable error or boundary crossing, trust loss should exceed silence or honest repair; denial should not be modeled as normal repair.
- Behavioral interpretation: A future verified event may add an integrity penalty and increase evidence-seeking, rejection, revocation, and manual-confirmation preferences. Keep this separate from a truthful uncertainty statement.
- Evidence boundary: The error and attribution must be verifiable. Reasonable disagreement, low-confidence inference, or ordinary user denial must not be encoded as deception.

### Esterwood-R4 - Trust-dimension separation rule

- Principle: P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Direct support for measurement structure across domains
- Runtime status: `deferred_longitudinal`
- Rule description: Long-term evaluation should distinguish competence, integrity, and benevolence rather than use one undifferentiated trust score.
- Behavioral interpretation: A future state may keep competence trust, integrity trust, and benevolence trust separate and map permission mistakes to the relevant dimension.
- Evidence boundary: The scale concerns robots, not privacy assistants. The dimensions are candidate state representations, not a validated privacy persona taxonomy.

### Esterwood-R5 - Integrity is not cheaply repairable rule

- Principle: P1 / P2 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Partial direct support across domains
- Runtime status: `deferred_longitudinal`
- Rule description: After repeated errors, ability and integrity loss cannot be repaired mainly by wording; subsequent behavior matters more than repair text.
- Behavioral interpretation: Bound recovery by later observed compliance. A repair utterance may create a feedback event but cannot erase ledger errors or relax a safety boundary.
- Evidence boundary: The study used a single post-task measurement and does not support equal per-round decrements for ability or integrity.

### Esterwood-R6 - Do not over-rank apology, explanation, and promise rule

- Principle: P1 / P2 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Direct support as a cross-domain counter-constraint
- Runtime status: `deferred_longitudinal`
- Rule description: After repeated errors, do not assume a stable universal ranking of apology, explanation, and promise; prioritize honesty and subsequent behavior over wording optimization.
- Behavioral interpretation: Do not assign a universal ranking or large fixed repair bonus. Treat repair type as contextual and bounded; false denial is the consistently poor strategy in the source experiment.
- Evidence boundary: The rule does not claim that all three repair types are equivalent in every privacy context. It rejects a universal strong repair mechanism.

### Esterwood-R7 - Verified-violation trigger boundary rule

- Principle: P1 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Requires rewriting as an S-QSTN boundary
- Runtime status: `catalog_only_boundary`
- Rule description: Trust penalties must be triggered by verified errors or broken commitments, not by ordinary denial, low utility, or unresolved uncertainty.
- Behavioral interpretation: Keep event types separate: oracle-verified error, explicitly inappropriate request, scope violation, false statement, ordinary denial, low utility denial, and uncertainty. Only verified event classes may update violation history.
- Evidence boundary: This separation is an S-QSTN design safeguard and should not be presented as directly measured by the source paper.

### Esterwood-R8 - No direct privacy-choice calibration rule

- Principle: P1 / P2 / P12
- Source sheet: `Esterwood_2023_Rules`
- Evidence rating: Requires rewriting as a transfer limitation
- Runtime status: `catalog_only_boundary`
- Rule description: The source can constrain trust and caution memory but cannot directly assign probabilities to allow, deny, or revoke privacy choices.
- Behavioral interpretation: Use this source only to constrain the direction of future trust-memory updates. Calibrate consent action from privacy and permission studies and keep hard safety boundaries external.
- Evidence boundary: HRI trust scores or statistics must not be translated directly into privacy questionnaire answer distributions.

## Application boundary

For the current S-QSTN v2.0 run, the JSON RulePack and verified StateStore boundary are authoritative for activation. This skill catalog is authoritative for semantic interpretation and evidence boundaries. When the two layers appear to disagree, do not invent a new effect: record the mismatch, keep the JSON behavior, and create a new version before changing prompts.

In full-catalog mode, do not independently activate a rule from its prose description. The wrapper's active RulePack excerpt and explicit trigger evaluation are the only activation signal for the current question.

The current questionnaire exposes necessity, tool, and data-type fields but does not expose every trigger described above. Missing expectedness, control, transparency, history, burden, severity, and violation fields remain unknown or inactive. The respondent should answer the supplied item using only explicit profile and context information.
