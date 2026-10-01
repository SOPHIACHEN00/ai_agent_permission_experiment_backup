# Design notes and evidence ledger

Sources inspected: v0 adapter.py/environment.py/features.py/policies.py/learner.py,
run_pilot.py/server_ops.py/prepare_package.py; core environment.py/policy_interface.py;
live_api_smoke_v1/REPORT_zh.md and frozen B. No credential file or human data inspected
during design. OpenAI official model page opened; markdown variant unsupported, normal
page succeeded. No API spent during design.

Key findings: cache includes complete history and episode identities; changing the
environment seed on each learning visit would miss. Original mask permits redundant
requests even with active authority, causing an unnecessarily large response tree.
Original numeric features do not encode free text. MAB transfer switches at600steps.

Ruling: use fixed dataset seeds and complete history-specific response trees, not
ordinal answer tapes — prevents false semantic reuse; cost: freezes one sampled world.
Ruling: shared two-question/no-redundant-question/prefer-refresh envelope — bounded
coverage within24calls; cost: conclusions apply only to this restricted protocol.
Ruling: forced disable after first effect is an explicit environment intervention,
not credited to the policy — ensures lifecycle opportunity; cost: macro/micro counts differ.
Ruling: native inline implementation plus one final read-only review, user-waived
approval pauses, fixed project directories, no commits/worktrees/evidence deletion —
honors minimum-version and durable records instructions over skill defaults.
Ruling: keep public31 and MAB600global boundary — no representation/tuning search;
cost: no text-semantic adaptation claim, MAB global/personal lengths differ.

State: specs frozen in files; API0, training0. Implementation follows fixed gates.

Development RED: new-module import missing as expected. First bounded GREEN attempt
had5/6passing; typed frame deserialization omitted conversion of history.records
from JSON list back to tuple. policy_interface.py:225 requires exactly four tuple
records. Fix only that deserialization boundary, not the kernel or data. This is
preflight development, not a failed paid collection/training retry; no API/GPU used.

Tuple fix GREEN:6/6tests,4.281s. A command initially used Week67 instead of repository
cwd and failed package import; corrected only command cwd, no code/data/API change.
Additional development gate RED: dropping same-path request proofs still passed the
disable→refresh gate because it searched any cache record of that scenario. Bind
the gate to each node's actual request_links, preserving the full semantic cache key.

Development GREEN after proof binding:7/7checks PASS8.234s;6newmodules ASTparse.
Inline implementation complete, single final read-only reviewer dispatched. Current
API0/training0. Source branches and typed publicframes are validated; real label
coverage remains unknown until the one authorized collection. No protocol softened.

2026-09-23 17:29 UTC: final read-only review found no Critical, one Important:
successful cost reconciliation followed by a logging failure reconciled twice.
Offline BrokenPipeError test RED: accounted=-237626400 instead of198000nanodollars.
Added reconciled guard, no other transport change. GREEN8/8checks6.223s,exit0;
the24testcalls use an in-memory HTTP double, real API0. No second review required.
Next: one collection; actual coverage/billing/CUDA behavior not yet claimed.

2026-09-23 17:33UTC actual first-runtime stop: collection session94477 exited1.
9calls allvalid,5reuse/3once/1deny_persist,costUSD0.0259314;2completegraphs plus16
partialthirdgraphprefixes. NoCUDA/server/train/eval. Frozen3historylimit reached;
fourthscope_denialhistory blockedbeforeAPI. Kernelwrappedasadapter_protocol_failure.
Read-only audit PASS:9receipts/cachehash/cost,80auditchainpairs,2exactgraphreplays;
same3savedthirdgraphresponsesreproduceper_graph_request_history_bound withmatching
semanticcachekeys,extraAPI0. No post-freeze source edits. This is a design-bound
error missed by small tests/review, not model failure or incomplete label sampling.
results-analysis read-only mode and results-report hardgate: only blocker summaries,
no invented algorithm results/figures. Await discussion; do not autoadjustcaps/resume.
