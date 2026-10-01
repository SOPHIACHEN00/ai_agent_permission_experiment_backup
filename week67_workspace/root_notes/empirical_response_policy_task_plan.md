# Task Plan: Empirical Permission-Response Policy

## Goal

Replace the unvalidated prompt-only QSTN response generator with a leakage-aware,
empirically calibrated permission-response policy, and use Twin-2K only after the
target-domain policy passes its quality gate.

## Phases

- [x] Phase 1: Freeze V1/V2 QSTN diagnostics and record their provenance.
- [x] Phase 2: Audit discovery/held-out splits, available features, and valid
  participant-level evaluation units.
- [x] Phase 3: Specify and implement preregistered four-label empirical-policy
  baselines: profile-majority, context-only, and profile-by-context; document
  why the source-paper CF/ICL is a separate endpoint-only comparator.
- [x] Phase 4: Run held-out policy evaluation and apply the go/no-go quality gate.
- [ ] Phase 4b: Only after a future candidate passes its primary gate, run the
  source-paper endpoint-only reproduction and a clearly labelled four-label
  CF/ICL adaptation as reporting comparators.
- [ ] Phase 5: Integrate the accepted policy into the RL environment.
- [ ] Phase 6: Add Twin-2K as a separately labelled persona-heterogeneity
  robustness arm, only after Phase 4 passes.

## Locked Decisions

- QSTN V1 and V2 prompt cards and their completed held-out evaluations are frozen.
  No V3 prompt wording is to be selected using V1/V2 held-out labels or metrics.
- The primary simulator target is the four-option permission decision, not a
  general narrative persona.
- Main evidence must use target-domain observed labels. Twin-2K is not a source
  of permission ground truth.

## Quality Gate

- Primary evaluation: five-fold participant-held-out evaluation. In each fold,
  all fitted policy count tables are estimated only from discovery rows of the
  other participants. A held-out participant's own discovery responses may be
  used only to infer its profile, modelling a warm-start permission assistant;
  its held-out labels remain unseen.
- The primary policy must exceed the preregistered profile-majority baseline on
  four-label macro-F1. The lower endpoint of a paired, participant-bootstrap
  95% confidence interval for the difference must be strictly above zero.
- The primary policy must not worsen both over-sharing and under-sharing relative
  to the profile-majority baseline. Both rates and their paired bootstrap
  differences will be reported, irrespective of the gate result.
- An exact request-context policy, profile-majority policy, and profile-by-context
  policy must all output a four-label probability distribution. MAP predictions
  are used for accuracy/F1; the accepted simulator will sample from the same
  distribution for RL, with an explicit seed.
- The source-paper CF/ICL implementation is reported in a separate endpoint-only
  (labels 0 versus 3) reproduction because its released code drops both
  "ask-next-time" labels and uses an interaction-level random split. A new
  four-label, same-split adaptation is a comparator, not a claim of exact
  reproduction.

## Errors Encountered

- The raw four-label dataset has no `response_row_id`; an initial audit attempted
  an invalid merge on that derived identifier. The split artifact itself contains
  all modelling fields, so subsequent split analysis reads it directly.
- The first audit looked for `outputs/empirical_response_splits.csv` under the
  project root. The actual canonical artifact is
  `qstn_simulator/outputs/empirical_response_splits.csv`; no data were changed.

## Status

**Phase 4 decision: no-go.** The fixed profile-by-context policy failed to
exceed profile-majority on participant-held-out macro-F1 (paired bootstrap CI
crosses zero) and significantly increased over-sharing. Phases 5 and 6 must not
start from this policy. Phase 4b is intentionally not run: the source endpoint-
only CF/ICL reproduction is a contextual comparator, not a route around the
four-label no-go gate.
