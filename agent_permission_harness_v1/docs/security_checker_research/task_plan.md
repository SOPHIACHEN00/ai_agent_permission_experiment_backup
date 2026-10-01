# Task plan: security-checker design and approved DDQN recap

## Material Passport

- Origin Skill: academic-research-suite
- Origin Mode: experiment planning with targeted primary-source verification
- Date: 2026-09-29
- Status: design artifacts saved and self-reviewed; not an executed fine-tuning experiment

## User intent

Preserve the approved DDQN specification locally for recap, and design the previously proposed fine-tuned LLM security checker: where it belongs in the single-Agent architecture, what it learns, how to construct training data, and how to evaluate its contribution. S-QSTN remains human-side simulation only. No paid fine-tuning, model download, or training launch is requested by this design question.

## Work

- [x] Record approval of the existing DDQN specification without changing its technical contract.
- [x] Read the original proposal's RQ7 / section 4.7 / O6 and current harness limitations.
- [x] Verify targeted primary papers and official model / training documentation.
- [x] Save a concise recap and concrete security-checker interface / threat-model design.
- [x] Save the fine-tuning data recipe, model configuration, evaluation and ablation protocol.
- [x] Review internal consistency, source links and evidence boundaries; file locations are ready for the user recap.

## Decisions

- Keep the primary task executor single; implement the checker as a tool-free inference component with no ledger-write capability.
- First integration keeps the approved DDQN feature schema and uses a separate restrictive security mask / release gate.
- Preserve independent business/security evaluation. A trained checker's own PASS verdict is not the ground-truth reward.
- Start from a small open-weight post-trained model with LoRA SFT; exact GPU viability requires a preflight.
- Current shell did not resolve nvidia-smi; this does not prove there is no GPU. An optional resource question is pending.
- Do not describe ordinary SFT plus DDQN as a reproduction of Constitutional AI's original RLAIF procedure.

## Self-review

- Added the recap/design links to the harness README and removed the stale DDQN approval gate in source notes.
- Verified the existing DDQN API has both policy_mask and next_policy_mask; the new security integration is still only designed.
- Kept guard-only holdouts distinct from whole-system holdouts, and required split-use records for all learned components.
- Kept synthetic privacy proxies, semantic security outcomes, task success and interruptions separate; no result is inferred from this design.

## Evidence and artifacts

`notes.md`, `../03_APPROVED_DDQN_RECAP_zh.md`, `../04_SECURITY_CHECKER_DESIGN_zh.md`, `../05_SECURITY_CHECKER_FINETUNING_AND_ABLATIONS_zh.md`.
