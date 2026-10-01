# Task plan: DDQN integration into the single-Agent harness

## Goal
Connect the existing masked, candidate-scoring DDQN to the modular task-Agent harness, with explicit public state, six-action bindings, episode transitions, constrained terminal reward, training and frozen evaluation. Preserve Family3-v2 as its original synthetic benchmark.

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation + remote run
- Origin Date: 2026-09-29
- Verification Status: ANALYZED (remote execution and recorded-action replay checked; no independent retraining)
- Version Label: agent-ddqn-integration-implementation-v1

## User decisions
- The user approved the integration direction and requested execution.
- On 2026-09-29 the user also approved the written specification and requested a local recap plus the security-checker fine-tuning design.
- Use academic-research-suite throughout subsequent turns in this chat.
- S-QSTN belongs only to the human-response simulation side, not the task-Agent RL design or implementation.
- Reuse DDQN and six controller actions; do not replace the research policy with tabular Q or a handcrafted rule.
- Do not silently map the new environment into the old Family3 43/7/7 checkpoint schema.
- User steering: add CPU/CUDA support; all subsequent tests and training run on the provided SSH server under agenticAI. Local edits and source inspection remain local. Do not persist credentials. No paid API calls.
- Follow-up approval2026-09-29: user replied “是” to uploading only two minimal de-identified catalog CSVs to the same server for the five missing catalog tests, not for RL. Both target files were absent; transferred CSVs exclude participant IDs, answers and preference labels.
- Final documentation preference2026-09-29: user explicitly chose to keep internal reports/plans local and not synchronize them to the server. Do not ask again or upload those internal documents; the documentation-sync item is closed, not blocked awaiting approval.

## Phases
- [x] Inspect the existing architecture, learner interfaces and prior approvals.
- [x] Write and self-review the new state/action/reward/transition specification.
- [x] Obtain review of the written specification: user approved on 2026-09-29.
- [x] Produce the detailed implementation plan and execute the already authorized reversible work without repeating permission gates.
- [x] Implement with behavioral tests; verify real DDQN inference, training transitions, lifecycle behavior and checkpoint isolation. Task 2's pre-implementation RED was not observed during SSH unavailability; other observed RED/GREEN evidence is recorded, not retroactively invented.
- [x] Run the approved small offline pilot with frozen-policy controls; report raw metrics without efficacy overclaim.

## Status
Native DDQN integration and this verification batch are complete. All execution after server-only steering occurred on the requested server, using cuda:0 for the formal 300×3 pilot. V1 first98/98 and now5/5 catalog follow-up pass:103 distinct tests across two remote runs. V0 29/29 and focused native core184/184 pass. Legacy replay-semantics26 tests still have8 failures/1 error and remain unchanged. The five previously blocked catalog tests now use only explicitly authorized, allowlisted metadata, not participant responses. One Important audit finding was fixed with observed RED→GREEN; recorded-action replay matches all1062 episodes. Two seeds never earned a successful terminal reward; the third mostly reused broad authority. No learned dynamic-contraction or privacy-efficiency superiority claim is supported yet. No paid API calls or further training during the catalog follow-up.

Wi-Fi reconnection verified persisted artifacts; final results are mirrored locally. See `../06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md` and `final_review.md`. Next research work is a separately specified learning diagnosis and live-LLM check, not silent retuning of this result.

## Errors encountered
- A scoped rg invocation included a nonexistent top-level `docs` path. Resolved by using the existing package documentation directories.
- A combined skill read was truncated. Re-read the affected skill files completely before using them.
- Git reports dubious ownership. Use a command-local safe.directory exception for this exact repository only; do not change global Git configuration.

## Evidence / next artifact
See `notes.md` and `../superpowers/specs/2026-09-29-ddqn-agent-integration-design.md`.
