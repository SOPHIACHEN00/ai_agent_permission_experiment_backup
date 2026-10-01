# Notes: Twin-2K-500 Paper Appraisal

## Source under review

- Local PDF: `C:/Users/Sophi/Downloads/2505.17479v1.pdf`
- Paper: *Twin-2K-500: A Dataset for Building Digital Twins of Over 2,000 People
  Based on Their Answers to Over 500 Questions* (arXiv:2505.17479v1).

## Publication status

- The supplied file is arXiv v1 (23 May 2025, 41 pages). The work was later
  published online on 20 August 2025 in *Marketing Science* as a Database Report,
  DOI `10.1287/mksc.2025.0262`, accepted through the journal's Database Submission
  review process. Cite this final record rather than calling it an unreviewed
  preprint.

## Paper's actual research gap

- The work addresses a **benchmark/data gap**, not the absence of a new LLM
  architecture: public sources lacked the combination of rich individual persona
  information, behavioural outcomes, and a repeat-measure benchmark; richer
  studies were not public.
- Its strongest claim is therefore that Twin-2K-500 permits transparent,
  reproducible construction and evaluation of persona-conditioned LLM simulations.
  It does not establish a universal model of all future human decisions.

## Design and contribution evidence from the PDF

- Final analytic panel: 2,058 U.S. Prolific four-wave completers, initially
  targeted by age, sex, and ethnicity; mean total time 145.47 minutes. The study
  contains >500 questions over demographics, 19 personality tests, cognitive and
  economic-preference measures, classic behavioural experiments, and a pricing
  study.
- A key methodological contribution is the modular split: persona JSON includes
  non-holdout wave 1--3 responses; separate evaluation blocks contain holdout
  answers; wave 4 repeats the holdouts for a human test--retest comparator.
- The individual metric is exact-match for binary outcomes and `1 - normalized
  absolute error` for numerical outcomes, averaged by task. Thus its 71.72% is
  not a four-option classification accuracy. Human test--retest is 81.72%; the
  reported best text-persona baseline is 71.72%, and summary-persona baseline is
  68.02%.
- Aggregate validation is materially weaker: twins reproduce 6/10 effects that
  replicated in both human waves, and only 2/5 within-subject effects. The paper
  reports a reversed sunk-cost effect, all twins choosing the normative option in
  probability matching, and 4% twin versus roughly 45% human refusal in a vaccine
  omission-bias scenario.
- Baseline simulations use temperature 0 (with a separate 0.7 ablation) and one
  shared system prompt. The table does not report a matched no-persona or
  demographics-only LLM baseline.

## Most important reviewer vulnerabilities

1. **Transfer validity:** evaluation is held-out items from the same broad survey
   instrument, not a new privacy/permission domain. The rich persona input may be
   predictive there but has no matched data-permission ground truth.
2. **Normative LLM collapse:** the paper itself shows large failures precisely in
   non-normative, medical, and polarised/political behaviour. Permission choices
   can share these contextual/normative properties.
3. **Metric interpretation:** 71.72% is task-averaged normalized closeness, and
   the random baseline is 59.17%; it must not be retold as 72% correct consent
   decisions.
4. **Benchmark ablations:** no clear no-persona/simple-demographics comparator
   quantifies how much individual fidelity comes from personal history rather than
   question-level LLM priors. Prompt/order robustness and uncertainty are limited.
5. **Population scope:** U.S. Prolific quota targeting is not a probability sample;
   the final four-wave-completer panel may differ after attrition. It cannot justify
   Canadian or global claims without a transportability argument.
6. **Interaction and ethics:** it models one-shot questionnaire answers, not trust,
   fatigue, revocation, or sequential learning. The public high-dimensional record
   includes sensitive measures, so external API transfer needs a data-handling note.

## Implication for QSTN permission study

- Strong use: cite/use Twin as a published external persona bank and a general
  digital-twin benchmark; feed `persona_summary` into a separate QSTN robustness
  lane.
- Insufficient use: use it as the main evidence that generated permission labels
  represent humans, or claim that its reported 71.72% carries over to data access
  decisions.
- Reviewer-defensible main claim: target-domain permission data calibrates QSTN;
  Twin adds out-of-domain profile heterogeneity after the main policy/prompt is
  frozen. Its outputs are stress-test outcomes, not human privacy ground truth.
