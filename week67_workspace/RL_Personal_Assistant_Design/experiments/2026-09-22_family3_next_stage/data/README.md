# Archived data dictionary

These are derived summaries of sealed Family-3 v2 results, not new evaluations. The original ZIPs remain authoritative in their existing local directories.

- `provenance_manifest.json`: workspace-relative ZIP paths, fixed archive hashes/sizes, ZIP member paths and row hashes, verified row/source counts, all 12 checkpoint payload hashes and training metadata, analysis-script hash and read-only execution boundary.
- `method_summary.csv`: 14 rows, one per phase/method. Success is the sum of terminal binary success; rate = successes / episodes.
- `per_seed_summary.csv`: 42 rows, one per phase/method/seed. Seed is a training seed for learners and a paired evaluation coordinate for non-learning rules.
- `paired_summary.csv`: two rows, comparing DDQN gamma=1 with ForecastRule at identical (seed, graph, condition, ordinal). A mismatch is a count of unequal recorded fields, not a new experiment. Counterfactual columns refer to paired original/forecast-intervention DDQN decisions.
- `paired_diagnostics.json`: full per-phase comparison counts, branch/forecast formula checks, failure termination counts and all 26 recorded hard counters.

Validation contains 600 rows/method and test 900 rows/method, with 7 methods. The original JSONL rows and trained models are inside the ZIPs identified by the manifest. No original raw row was deleted, modified or substituted. The records do not contain complete per-step trajectories; do not claim that they do.

Reproduction: run the adjacent `analyze_sealed_results.py` with Python `-B`. It prints the derived payload and never writes the frozen evidence, runs an environment, loads a model, or uses the network. Keep the workspace-relative directory structure when moving the archive. The summary timestamp can change on a later read-only audit; the underlying evidence SHA-256 must not change.

`next_experiment_plan.json` is one directory above: it contains planned parameters only, deliberately separate from these observed-result tables.
