# Bounded preflight test record

Date: 2026-09-23. Runtime: existing qstn_simulator/.venv, Python 3.12,
OpenAI SDK 2.45.0. No live API, GPU, torch or model training in these checks.

Command (repository cwd):
`qstn_simulator/.venv/Scripts/python.exe -m unittest discover -s rl_sqstn_integration_v0/tests -p test_live_api.py -v`

Expected RED before implementation: missing `rl_sqstn_integration_v0.live_api`,
exit 1. This missing-feature check is not an experimental runtime failure.

GREEN after implementation: three tests, 9.091 seconds, exit 0.

1. Four calls accepted; fifth blocked before HTTP. Unaffordable first call blocked
   with zero attempts. Reported token-based cost matches hand-derived USD 0.000792.
2. HTTP 429 produces one attempt only; subsequent call blocked. Full conservative
   reservation retained. Sensitive error-message sentinel absent from journal.
3. Actual authority environment accepts allow_once, commits exactly one monitored
   effect, and reproduces identical public frames through cache-only replay with
   zero API calls. Only external HTTP is substituted in this test.

Review pending; real API attempts remain zero at this checkpoint. Frozen offline
files have not been edited; only two new live modules and one test module added.
