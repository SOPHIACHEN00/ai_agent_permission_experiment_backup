# S-QSTN 20-user ICL pilot

## Goal

Complete the approved synthetic 20-persona experiment using configured OpenAI o4-mini as S-QSTN respondent and google/gemini-3.8-flash as 0-shot / 4-shot predictor.

## Fixed design

- Select 20 from the prior 40-person 4-shot manifest: broad restrictors 3, persistent granters 7, reconsent seekers 10. RNG 20260926; sort profile keys and candidate IDs before sampling.
- Reuse each person's four complete history queries and four fold-0 test queries; fold seed 42, original shot seed 20260925.
- Use empirical profile cards v2 and RulePack v2 with fresh empty state for each permission item. No violation fixture or cross-question evolution.
- Freeze all o4-mini labels before Gemini inference. Predictor receives the original allowed public profile fields and synthetic history only; no private cards, rule explanations, or test labels.
- Gemini 0-shot and 4-shot use identical test rows and original model settings (low reasoning, 8000 output-token limit).
- Checkpoint every call, record prompt/source hashes and estimated/reported costs. Budget admission before every request; no automatic retries or model substitution.
- Descriptive synthetic predictability pilot, not independent human-likeness evaluation or chronological forecasting.

## Phases

- [x] Confirm models, scope, and source protocol.
- [x] Implement isolated generator/predictor runner and offline preflight.
- [x] Independently inspect selected users, prompt boundaries, provenance, and budget.
- [x] Generate and freeze synthetic answers with o4-mini.
- [x] Complete paired Gemini 0-shot and 4-shot inference.
- [x] Summarize metrics, costs, limitations, and deliver artifacts.

## Status

Complete. All 624 synthetic labels and 40 Gemini calls are saved in artifacts/pilot20_seed20260926_o4mini_gemini_fold0_schema_v1. Each condition contains 274 matched test records for all 20 users. Independent final audit passed. Total tracked cost USD 1.17105605 including the initial format-error cost; no in-flight calls remain. Results are in REPORT_zh.md.

## Operational notes

- Initial json_object-only request returned a valid label under permission instead of answer. It was rejected and preserved, costing USD 0.0026048; no answer from it is reused.
- Corrected to installed QSTN 0.5.1's native JSONSingleResponseGenerationMethod schema and started a separate revision directory. The old failed ledger entry was copied verbatim with provenance so the cost is counted once.
- No model, participant, question, profile, rule, or split changed.
