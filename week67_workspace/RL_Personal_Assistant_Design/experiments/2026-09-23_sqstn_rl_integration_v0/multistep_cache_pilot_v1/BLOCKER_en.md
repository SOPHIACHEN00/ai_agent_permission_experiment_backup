# Multi-step cache v1: stopped collection / 2026-09-23

The dataset and comparison are incomplete. The sole collection exited1 at
17:31:12UTC after9 valid API answers,2 complete train graphs and16 additional
saved prefixes in the third graph. No server contact, training or evaluation.

Usage estimate: USD0.0259314 of the new USD4 budget; input15342(cached8832),
output3714(reasoning3456). Labels:5allow_reuse,3allow_once,1deny_persist.
No API/network failure, retry, resampling, label editing, tuning or old test access.

The pre-fixed per-graph bound of3 distinct request histories was incorrect.
Optional local disable combined with scope expansion produced a fourth valid
history. The guard stopped before sending that request. The kernel wrapped
per_graph_request_history_bound as adapter_protocol_failure. This is our bounded
enumeration/budget-design defect, not evidence about DDQN learning or API denial.

Read-only verification matched all9 request/response receipts and costs,80 saved
public/execution audit-chain pairs, and2 exact cache-only graph replays. Replaying
the third graph's same3 recorded responses in RAM reproduced the original guard;
regenerated semantic cache keys matched. Added API calls0. Integrity PASS does
not mean dataset coverage PASS. The frozen bilingual specs remain unchanged.

Before any continuation: correct offline branch counting and the explicit call
cap while retaining the USD4 total budget, preserve these9 answers without
resampling, and specify verified full-context reuse across versioned artifacts.
Do not auto-resume. Only complete covered data may unlock the fixed comparison.
No algorithm superiority, significance, human-validity or generalization claim.

Evidence: collection/status.json,campaign_journal.json,private/cache.json,
private/branch_audits.jsonl,and interruption_verification.json. Local project
progress/continuation records updated; no external sharing attempted.
