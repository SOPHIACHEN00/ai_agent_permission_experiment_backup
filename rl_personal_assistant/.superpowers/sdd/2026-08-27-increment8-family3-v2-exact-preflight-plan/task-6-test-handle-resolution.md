# Task 6 test-handle resolution

## Cause and boundary

The first combined GREEN attempt exited 1 after `Ran 12 tests in 5.311s`, with 11 methods passing and one Windows cleanup error. The guard-mismatch method's scientific assertions completed; `TemporaryDirectory` then raised WinError 32 removing `values.sqlite3`.

The test used `with sqlite3.connect(...) as connection:` for guard tampering. That context manager commits or rolls back but does not close the connection, leaving a Windows handle live during temporary-directory cleanup.

## Authorized, test-only correction

Only `tests/test_family3_v2_exact_solver.py` changed: it imports `contextlib.closing`, and its guard-tamper setup now uses `with closing(sqlite3.connect(...)) as connection:`. This explicitly closes the test-owned connection. No production module, solver semantics, scientific parameter, assertion, result artifact, run config, cache, certificate, or gate changed.

## One authorized rerun

The same prescribed command was rerun once:

`$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`

It exited 0: `Ran 12 tests in 5.260s`; `OK`. All twelve methods passed and no warning was reported. This is focused unit-test evidence only, not a real scientific solve, preflight, cache, certificate, or Gate 1 execution.
