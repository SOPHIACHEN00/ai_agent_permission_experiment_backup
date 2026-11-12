# Repository refresh validation — 2026-11-11

The checks below validate the packaged current code. They are separate from the
historical research results in [DATA_AND_EVIDENCE.md](DATA_AND_EVIDENCE.md).

## Offline suites

Executed on Windows with Python 3.12, the declared simulator dependencies and
native PyTorch. No provider keys or paid API calls were used.

Key installed versions: PyTorch 2.11.0, jsonschema 4.26.0, qstn 0.5.1,
NumPy 2.5.1, pandas 3.0.3, scikit-learn 1.9.0, SciPy 1.18.0 and OpenAI SDK 2.45.0.

| Suite | Result |
| --- | --- |
| Agent core | 175 collected: 167 passed, 8 optional historical-report tests skipped |
| RL diagnostics, including opted-in CPU update tests | 29 passed |
| Mock tools, including isolated-copy execution | 21 passed |
| S-QSTN | 38 passed |
| Offline and online MAB | 14 passed |
| ICL and current S-QSTN adapter | 16 passed |
| Total | **285 passed, 8 skipped, 0 failures** |

The eight skips require an exact historical 60-task training report, which is not
distributed. PyTorch update tests were enabled explicitly with
`RL_TESTING_ALLOW_TORCH_UPDATES=1`.

## Entry-point checks

- The current four-action `run_noapi.py` completed **65/65 tasks**, with all five
  consent lifecycle checks passing, zero network attempts, zero optimizer steps
  and unchanged mock/S-QSTN dependencies.
- The example CPU `update-check` completed, with **18 optimizer updates**, a
  checkpoint round trip and frozen-evaluation state checks. It used rule-collected
  fixture transitions and does not measure learning gains.
- S-QSTN compiled an explicit-persona prompt offline (`paid_call=false`).
- The four-label dataset rebuilt to 16,361 rows from the packaged upstream inputs,
  byte-identical to the retained CSV.
- All three fixed LR baselines ran on the full participant-held-out split. Their
  accuracy/macro-F1 values matched the retained baseline rows: flat
  0.406560/0.366901, ordinal 0.406560/0.362884, factored 0.405958/0.365880.
- Offline MAB ran with one tuning seed, one test seed and epsilon-greedy at 0.1;
  both flat and factored paths completed.
- WP-FTS ran with one validation/test stream, kappa 0.01, online exploration 0.5
  and 20 bootstrap replicates. This checks the complete runner, not the precision
  or exact values of the retained 20-stream / 5,000-replicate experiment.

## Packaging fixes

- Migrated mock-tool tests from removed six-action calls and the old single-scope
  ledger to the current C/G/bundle protocol. Checks still cover blocked forwarding,
  scope expansion, withdrawal, expiry, one-use consent and exact tool effects.
- Removed the S-QSTN bridge test's dependency on a sibling local virtual environment.
- Created diagnostic output parents within tests, so a clean checkout does not
  require pre-existing run directories.
- Made the ICL test import work from the repository-root command.

Runtime algorithms were copied from the active local implementation, with text
line endings and one trailing blank line normalized. These fixes
change test portability and current-protocol coverage, not the research method.
Generated verification outputs are ignored by Git. The GitHub workflow runs the
offline suites and 65-query functional check in a fresh Linux environment.
