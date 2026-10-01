# Evidence notes — 2026-09-26

- Older `proposal/01_research_canon.md` reports stated-policy replay gains; those are not current end-to-end safety or human behavior evidence.
- `RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`: 2026-09-23 r2 pilot has DDQN/MAB/fixed rule all 3/4 dev success across two seeds, at the fixed cache task-completion ceiling; no incremental DDQN advantage.
- Distinguish DDQN controller training from LLM weight fine-tuning. Current RL results cannot answer the value of LLM RL fine-tuning.
- User asked about architecture vs preference experiments and metrics, targeting ICDE 2027 Nov11. Security implementation status is being clarified asynchronously.
- Official venue and primary prior-work checks are in progress. Main recommendation remains provisional until latest ICL evidence is inspected.

## Final findings

- User confirmed security work has not started. Keep it to permission-specific runtime robustness and, only with an actual language/tool pipeline, a bounded injection evaluation.
- Latest human ICL: 201 users, fold 0, accuracy 62.82%, macro-F1 0.5451, false allow 274/645=42.48%, persistent overallow 282/1898=14.86%. Root read the full result report. 40 participants overlapped model screening; no paired human 0-shot yet.
- Root read S-QSTN comparison: 0/4-shot accuracy improves but false allow stays 15/41. Static empty-state synthetic judgments are not longitudinal human evidence.
- Two independent specialist reviews agree: preference-aware permission management is a plausible focus, but combination of ICL, monitor, cache is not by itself novel. Strong scoped-cache/revocation baseline is essential; keep RL off the deadline critical path.
- Official ICDE dates verified: 2026-11-11 17:00 Pacific, Toronto 20:00. Correct CFP path: https://icde2027.github.io/cf-research-papers.html .
- Primary prior work: Wu arXiv HTML 2511.17959v1; ARIEL PoPETs2026-0087 full PDF read by literature agent; CaMeL 2503.18813v1; AgentDojo 2406.13352v3. Detailed allowed conclusions and links are in research-question-card.md.
- Metric review: separate preference false allow, conditional auto-allow risk, hard authorization violation, and attack success; distinguish actual prompts from ask-next-time labels; respect requested re-asking; distinguish legitimate completion from correct refusal.
- Recommendation delivered as a research direction card and two-week falsification plan. No model training, paid API requests, production changes, or original-result modifications.
