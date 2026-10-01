# Task Plan: four-label ICL model screening

## Goal
Run a reproducible three-model screen on four-label within-user folds, alert at cumulative USD 10, and stop new calls before USD 24.

## Phases
- [x] Inspect the existing ICL runner and confirm model IDs, providers, and current prices.
- [x] Fix a small participant sample and shared evaluation jobs; record offline budget estimates.
- [x] Implement a resumable one-key OpenRouter runner with one cap across all three models.
- [x] Verify sample integrity, parsing, budget behavior, and offline reporting.
- [x] Document key setup, exact run commands, interpretation, and remaining limitations.
- [x] Complete 120 calls, audit coverage and budget, and compare models with participant-paired bootstrap intervals.

## Decisions
- Reuse the existing four-label prompt, strict response parser, and 5-fold query-level manifest.
- Screen one preselected fold per sampled participant for each model, using exactly the same jobs.
- Use OpenRouter for `openai/gpt-6-luna`, `deepseek/deepseek-v4-flash-0731`, and `google/gemini-3.8-flash`.
- The user supplied `OPENROUTER_API_KEY`; pin `reasoning.effort=low` for all three after an 8K-token zero-content DeepSeek result at its default high effort.

## Status
The clean 8K-token, low-reasoning screen is complete: 40 participants, 599 held-out rows, and 120 successful calls. Cumulative tracked spend is USD 0.296232641 including USD 0.0284769655 of prior attempts and conservative reserves for two retried DeepSeek failures. The USD 10 warning threshold was not reached. Gemini and Luna are the recommended finalists; details are in `screening_results.md`. Six offline runner tests passed.
