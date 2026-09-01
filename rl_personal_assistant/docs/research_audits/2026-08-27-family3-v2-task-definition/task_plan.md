# Task Plan: Family-3 v2 task-definition design

## Goal

Design a separately versioned Family-3 benchmark construct whose success
requires a genuine public-state long-horizon authorization decision and whose
ten graphs are oracle-feasible by construction, without another budget/target
parameter search.

## Frozen boundary

- Preserve Increment 8 v0/v1 source, graphs, certificates, and results.
- Do not train, run learner smoke, run all-forty, or alter the `3/5` floor.
- Treat `s3_v3=13/25` as a task-definition failure and `s3_v4=1` as a resolved
  solver-computation result.
- Design semantics first; exact preflight implementation begins only after the
  required design/spec approval gates.

## Phases

- [x] Phase 1: Establish durable planning and approval boundary.
- [x] Phase 2: Audit current Family-3 generator, lifecycle semantics, and all
  ten v1 graph identities.
- [x] Phase 3: Compare 2–3 construct designs against causal-action necessity,
  observability, oracle feasibility, carrier neutrality, and safety.
- [x] Phase 4: Present one consolidated in-chat design for user approval.
- [x] Phase 5: After approval, write and self-review synchronized English and
  Chinese design specs.
- [x] Phase 6: After written-spec approval, invoke writing-plans and produce
  the minimal exact-preflight implementation plan.

## Key questions

1. Which explicit authorization lifecycle decision must be necessary for
   success, and what counterfactual establishes that necessity?
2. How can every graph be feasible at `3/5` by construction without tuning a
   target or budget against oracle outputs?
3. Which state variables are public and Markov-sufficient for that dependency?
4. How should strategic Family 3 differ from the existing mandatory
   disable→refresh compliance graphs?
5. What exact stop rules prevent another hidden low-ceiling suite?

## Decisions made

- Classify this as architectural research design, not a bounded graph edit.
- Use one consolidated design-approval request rather than stepwise parameter
  approvals.
- Recommend forecast-conditioned scope reservation over stale-grant retirement
  and relation-compliance handoffs because it creates a delayed two-choice
  counterfactual and admits an algebraic `V*=4/5` construction certificate.

## Errors encountered

- Independent proposal review found two Critical contract ambiguities: v1
  sensitivity-3 grants would be one-time, and v1 dispatch ignores a proposed
  broader candidate scope. The design was corrected to define a public
  deterministic reusable response profile and exact candidate-scope binding
  as isolated v2 semantics. A second independent read-only review returned
  `approval-ready` with no remaining Critical or Important findings. No
  implementation or experiment had started.

## Status

**IMPLEMENTATION PLAN COMPLETE / AWAITING EXECUTION CHOICE** — the user
approved the written spec on 2026-08-27. The task-by-task plan is saved at
`docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md`
(SHA-256
`036B9690A06267099C62F78B98C973A9B283037BAB449AF074CB6A878A049658`).
Its final independent audit has zero remaining Critical or Important findings.
No source, focused test, DP run, result directory, or learner work has started.
