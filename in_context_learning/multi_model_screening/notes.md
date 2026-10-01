# Screening research notes (2026-09-25)

## Existing local baseline

- `../run_ic_four_label.py` defines 5 query-grouped folds within each of 201 participants, the four-label prompt, strict parser, and classifier-compatible metrics. One job predicts all permission rows in one held-out query fold.
- Existing code hard-codes OpenAI models and a USD 4 cap from the earlier task. Keep that historical runner intact; implement this screen separately with a USD 10 alert and USD 24 stop.
- One earlier `o3-mini` job used 2,463 prompt tokens and 2,227 completion tokens. Cross-model output lengths, reasoning usage, and provider routing can differ, so this is only a rough sizing example.

## Current model IDs and public prices

| Route | Exact ID | Published standard/list price per 1M input/output tokens | Source |
|---|---|---:|---|
| OpenRouter | `openai/gpt-6-luna` | USD 0.10 / 0.50 | https://openrouter.ai/openai/gpt-6-luna |
| OpenRouter | `deepseek/deepseek-v4-flash-0731` | OpenRouter model page shows a lowest visible endpoint USD 0.03 / 0.32; provider prices vary | https://openrouter.ai/deepseek/deepseek-v4-flash-0731 |
| OpenRouter | `google/gemini-3.8-flash` | USD 0.75 / 3.75 standard promotional rate through 2026-12-31 | https://openrouter.ai/google/gemini-3.8-flash and https://ai.google.dev/gemini-api/docs/latest-model |

The user said “DeepSeek V4 Flash” without a snapshot. The 0731 slug is the newer GA revision; the unsuffixed OpenRouter slug points to the older 0423 page. Record this choice in the run config.

## Gateway and budget controls

- OpenRouter supports the OpenAI Python client with `base_url="https://openrouter.ai/api/v1"`: https://openrouter.ai/docs/quickstart
- Its `provider.max_price` can reject routes above an input/output price ceiling; `sort: price` prefers cheaper providers: https://openrouter.ai/docs/guides/routing/provider-selection
- Include usage in each response (`usage: {include: true}`) and read `usage.cost` when returned. Token counts and any reported reasoning tokens should also be recorded: https://openrouter.ai/blog/announcements/smarter-charts-inline-svg-and-live-usage-accounting/
- A global local cap must reserve the maximum permitted input/output price before each request and track all three models together under one OpenRouter key. It cannot cover purchases or other applications using the same keys.

## Interpretation

- One fixed fold per sampled participant gives a paired, inexpensive screen. It is not a full 5-fold performance estimate. Select finalists using macro-F1 together with over-sharing and persistent over-allow, coverage/parse failures, cost, and per-user uncertainty.
- The shared four-label prompt and holdout rows are essential; no test labels should enter model prompts.
- OpenRouter metadata lists `low` as supported by all three. DeepSeek defaulted to `high` and used all 8,000 output tokens on P009 for reasoning, producing no visible answer. A low-effort diagnostic on the same job parsed 17 answers at 3,970 output tokens. The clean formal screen pins `reasoning.effort=low` for all three and counts USD 0.0284769655 of prior attempts toward the cumulative cap.
