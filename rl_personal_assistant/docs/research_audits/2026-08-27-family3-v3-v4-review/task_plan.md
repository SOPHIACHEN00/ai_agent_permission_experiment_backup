# Task Plan: Family 3 `s3_v3` / `s3_v4` scientific review

## Goal

Determine why the frozen Family-3 formula fails on `s3_v3` and remains
computationally unresolved on `s3_v4`, then select the smallest scientifically
valid next action without parameter search, floor reduction, or a state-limit
increase.

## Phases

- [x] Phase 1: Create durable plan, notes, and decision-memo boundary.
- [x] Phase 2: Inventory the exact task definitions, transition semantics, and
  certificate/cache evidence for `s3_v3` and `s3_v4`.
- [x] Phase 3: Run independent read-only causal audits for `s3_v3` feasibility
  and `s3_v4` state-space growth.
- [x] Phase 4: Integrate findings, distinguish definition defect from intended
  difficulty, and identify falsifiable next checks.
- [x] Phase 5: Write the decision memo and synchronize recovery/project logs.

## Key Questions

1. Which exact constraints cap `s3_v3` at `13/25`, and is that cap intended?
2. Which state dimensions and branches dominate `s3_v4` growth before the
   initial-state value can be cached?
3. Can either issue be resolved by a semantics-preserving analysis or solver
   change, or is a task-definition revision required?
4. What is the smallest next experiment that can distinguish those hypotheses?

## Decisions Made

- Treat exact DP values as deterministic oracle evidence, not seed-level
  samples; inferential statistics and learner comparisons are out of scope.
- Preserve the frozen formula `exposure+8`, `target=max(4,target-1)`, the `3/5`
  floor, and the 1,000,000-state evidence boundary during diagnosis.
- Do not run all-forty, learner, smoke, training, validation, or official test.

## Errors Encountered

- A parallel audit agent's file-planning setup replaced this shared plan and
  `notes.md` with v4-only placeholders. The collision was detected immediately;
  both agents were restricted to separate audit files and the shared files were
  restored. No source, test, certificate, checkpoint, or SQLite artifact changed.
- The v4 audit's first recursive instruction-file scan crossed an unreadable
  sibling path; it switched to repository-scoped `rg --files`. No applicable
  repository instruction file was missed.
- The first final documentation check used an intentionally strict literal
  status token and found that the decision memo required approval but did not
  explicitly say the solver was unimplemented. Added one status line; no
  scientific claim or experiment artifact changed.
- The second documentation check searched for plain `(N+1)th`, while the audit
  correctly formats `` `(N+1)`th `` with Markdown code delimiters. The check
  was corrected to match the semantic `N+1` token; no document change was
  required.

## Status

**COMPLETE** — both read-only audits, the integrated decision memo, and all
recovery/project logs are synchronized. The proposed diagnostic explicitly
changes the cache-accounting/work domain and awaits user approval; no solver
implementation or new exact run has started.
