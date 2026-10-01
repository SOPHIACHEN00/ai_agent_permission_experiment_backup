# S-QSTN multi-step cached pilot v1

Frozen before paid collection, 2026-09-23. Chinese SPEC_zh.md controls semantics.
The user authorized a new USD4 campaign and waived repeated step confirmations.

Eight synthetic two-protected-read, horizon6 scenarios: continuous, once,
scope_denial and disable_refresh, one train/work-calendar and one dev/personal-calendar
variant each. Dataset seeds31001–31004/41001–41004 remain fixed across visits/methods;
learner seeds1301/1601 affect learning only. Public synthetic preferences describe
session reuse, one-use access, or unwillingness to disclose private_notes. They are
not forced model output labels or empirical human profiles.

Use the original authority kernel, six action families, public31/candidate16 features
and v2 respondent prompt/memory. Add a shared bounded action envelope: at most two
permission questions per episode, no redundant question while execution is authorized,
and prefer refresh over a simultaneously valid fresh request. Execution, voluntary
disable and safe exit remain available. In disable_refresh, after the first committed
effect, an active grant is disabled through the real environment action as a logged
protocol intervention. Count controller transitions and environment micro-steps separately.

Exhaustively enumerate legal action prefixes. Cache each actual history, not answer
ordinal; bind protocol/model/transport versions. At most three distinct question histories
per graph, hence at most24 API attempts. Freeze the sampled response at each history;
do not resample, alter labels or replace refusals. No broad full-action claim.

Model o4-mini, medium reasoning, strict one-field JSON, max4096 completion tokens,
standard tier, no retries. New aggregate capUSD4/24attempts. ReserveUSD0.2380224 before
each request (full200000 input context plus output cap); reconcile returned usage at
USD1.10/.275/4.40 per million input/cached/output tokens. If insufficient reservation,
stop with incomplete coverage. Unknown billing remains reserved. Credentials in memory
only, fixed official endpoint, one-shot directories and durable intent.
Pricing source: https://developers.openai.com/api/docs/models/o4-mini (2026-09-23).

Before learning, require eight closed exhaustive graphs, exact cache-only replay,
zero invalid/unauthorized/adapter faults and valid public/execution chains. Each split
must contain allow_once, allow_reuse, denial, an actually successful multi-step path,
allow-then-deny in scope_denial, and actual intervention-disable followed by refresh
in disable_refresh. Missing coverage stops the comparison without changing gates.

Only after all gates pass: new DDQN and genuine WP-FTS-transfer MAB, seeds1301/1601,
2400controller transitions each method/seed,9600total. Fixed B: gamma1,lr.0003,batch64,
replay20000,warmup256,optimize_every4,target_update_every250optimizer updates,clip5.
Expected537DDQNupdates/two target syncs per seed; epsilon1→.1 over1920steps. Existing
MAB global600/personal1800, kappa.01, exploration2/.5, selected observed-label feedback
only. Four model save/reloads and24dev terminal rows (3methods×2seeds×4graphs), frozen
evaluation. Task success remains original0/1; also report prompts, post-denial questions,
fallback, safety and interventions. Never treat24cells as independent statistical units.

Server executes public frozen transition graphs only; policies receive current public
frames, not future edges/private cache. No API during learning, old test remains locked.
Use one freshly checked idle GPU and current memory headroom>=4GiB; no local neural
training, tuning, seed selection or automated rerun. First actual runtime/API error stops.

Limitations: small synthetic conditional response sample, restricted action envelope,
not human validity or DDQN superiority. Text preferences are not encoded in public31;
no language understanding is claimed. Initial once/reuse action collapse and differing
MAB-label versus DDQN-task objectives remain explicit. Preserve old source/data and
record artifacts/hashes/cost/checkpoints beside the prior local experiment logs.
