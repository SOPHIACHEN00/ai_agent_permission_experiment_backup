# Task Plan: Four-label in-context learning baseline

## Goal
Reproduce the paper's IC-only setup where applicable, extend the prompt and evaluation to all four permission answers, and deliver a runnable baseline aligned with the local classification benchmark.

## Phases
- [x] Create task plan and identify sources
- [x] Audit paper, released IC code, four-label dataset, and local evaluation protocol
- [x] Implement the four-label IC-only runner and documentation
- [x] Verify offline behavior and report limitations
- [ ] Run a budget-safe live baseline and report results

## Key Questions
1. What does the paper's released IC-only code actually include and exclude?
2. Which split is comparable to existing four-label classifiers while retaining a user's own history?
3. How are four labels represented, parsed, and scored?

## Errors Encountered
- System Python lacked scikit-learn; verification used the experiment .venv.
- An initial fold assertion assumed 20 nonempty permission queries for every user; CSV has 18-20 per user, so verification and documentation were corrected.
- The initial shell had no OPENAI_API_KEY or openai package. The user identified an ignored qstn_simulator/.env file; the client was installed and one live o3-mini pilot was completed under the budget cap.

## Status
Live pilot complete and budgeted runner implemented; awaiting model choice for the USD 4 full-run constraint.



