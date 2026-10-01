# Test-once terminal notes

- Three launcher wrappers before the successful launch omitted the CUDA environment from their own current process. They stopped before opening test with `frozen artifact changed: boundary.json`; no test writer or test artifacts were created by those attempts.
- A byte-level comparison under the fixed CUDA environment confirmed `boundary.json` was unchanged. The corrected wrapper set the CUDA environment in both the preflight process and detached child.
- The sole test-once process then ran to 6,300 rows and exit code 0. Those preflight launcher errors are operational notes, not experiment failures.
- Credentials and connection coordinates are intentionally absent from all local records.
