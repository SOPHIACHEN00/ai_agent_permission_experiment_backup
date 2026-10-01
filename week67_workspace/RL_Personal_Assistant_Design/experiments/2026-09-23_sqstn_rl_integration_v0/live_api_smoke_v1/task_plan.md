# Live S-QSTN API smoke v1

Authorization: 2026-09-23, user approved USD 4; preceding agreement limits this
first live stage to four permission-answer calls, using the existing o4-mini
configuration. No further training, tuning, GPU job, old test or real-person data.

## Fixed execution

- Four new one-protected-step synthetic calendar episodes; existing rule controller
  drives the interface. The live model freely selects one of four permission labels.
  Fixture replies exist only to construct the manifest and are NOT the live answer.
- Existing prompt/memory, strict parser, authorization service and reference monitor.
  No frozen offline file changes. Bind transport options into an instance-specific
  adapter version so live/cache replay also binds reasoning/output/schema settings.
- Official OpenAI Chat Completions; o4-mini, medium reasoning, 4096 maximum completion
  tokens including reasoning, standard service tier, no temperature/seed override.
- SDK retries zero; four global attempts maximum. Durable intent before each call;
  unique run directory blocks a second launch. Stop on the first actual runtime/API
  error. Uncertain calls retain full reserved cost, never automatically resubmit.
- Price checked from official model documentation on 2026-09-23: USD 1.10 input,
  0.275 cached input and 4.40 output per million tokens. Reserve an intentionally
  conservative 200000 input tokens plus 4096 output per call: USD 0.2380224 each,
  USD 0.9520896 for four, below the authorized USD 4. Cost from usage is an estimate,
  not the provider's final invoice. No tools/images/other billable features.
- Read only API key/model from local .env into process memory; fixed official endpoint;
  never print or persist secrets, environment contents, headers or raw exceptions.
- Save private synthetic prompts/responses/cache separately from public traces.
  Replay the four completed episodes cache-only, with no network callback.

Sources: https://developers.openai.com/api/docs/models/o4-mini and
https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

## Checklist

- [x] Minimal transport/budget/error tests: 3/3 PASS, no model training or real API.
- [x] Implementation and one independent read-only final review; no blockers.
- [x] Single live launch: exactly four API requests, exit0, no retry.
- [x] Cache-only replay 4/4; audit/cost/source verification PASS; progress recorded.

## Execution rulings / continuation

Use approved fixed directories and retain all offline evidence. Do not create a
Git worktree, commit unrelated files or broaden the test suite. This is the live
stage already approved by SPEC_zh.md sections 4 and 7, not a new scientific protocol.
No new approval loop. Real labels need not cover all four choices. Four similar
short synthetic episodes cannot establish human realism, long-horizon learning,
cross-turn memory effects, or DDQN superiority.

State: LIVE_API_COMPLETE. Four valid responses, 2 allow_reuse and 2 allow_once;
estimated cost USD0.0116292, safety/fault counts0. Local verification PASS at
UTC2026-09-23T17:01:03.359027. See REPORT_zh.md and verification.json.
The four-call authorization is consumed. Do not relaunch/resume/retry or erase run/.
