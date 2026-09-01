# Task 6 brief — capped exact solver, independent reference, and artifact store

Implement Task 6 of the approved Family-3 v2 exact-preflight plan. The Task 5 review must be APPROVE before dispatch; its final hashes will be captured separately in `task-6-base.md`.

## Strict scope

Create only:

- `src/pa_rl/family3_v2_exact_solver.py`
- `src/pa_rl/family3_v2_exact_reference.py`
- `src/pa_rl/family3_v2_artifacts.py`
- `tests/test_family3_v2_exact_solver.py`
- `tests/test_family3_v2_exact_reference.py`
- `tests/test_family3_v2_artifacts.py`

After GREEN, update only the existing implementation checkpoints and write the Task 6 SDD report. Do not modify Tasks 2–5, legacy/frozen sources/results, `__init__.py`, preflight runner, scientific parameters, or actual gate/certificate/cache artifacts. Unit tests use isolated temporary directories. Standard library only; do not import/subclass either legacy solver, old lifecycle classes, Torch, `psutil`, or Task 7.

## Required interfaces

- `Family3V2ValueFirstExactSolver.solve(initial_state, initial_action_ids) -> Family3V2ExactSolveResult`
- `enumerate_terminal_free_reference(model, initial_state, initial_action_ids) -> TerminalFreeReferenceResult`
- `verify_frozen_v0_v1_baseline(project_root, baseline) -> FrozenSetAudit`
- `Family3V2PreflightStore.commit_gate(gate, report, evidence)`
- `Family3V2PreflightStore.mark_interrupted(gate, next_action)`
- `Family3V2PreflightStore.mark_terminal_failure(status, gate, evidence)`
- `Family3V2PreflightStore.finalize(verdict) -> ArtifactRef`

Freeze constants: 250,000 cached nonterminal states per graph; 4,096 memory LRU entries; 512 MiB RSS. These are not constructor/CLI scientific overrides. Allow only private/injected RSS and failure hooks required for deterministic unit tests.

## Frozen interface rulings

These rulings close implementation-only ambiguities without changing a
scientific parameter, gate, or result:

- Construct the solver as
  `Family3V2ValueFirstExactSolver(model, database_path, *, source_fingerprints, config_fingerprint, rss_reader=None, failure_hook=None)`.
  `source_fingerprints` is a canonical `Mapping[str, str]` of POSIX-relative
  source names to lowercase SHA-256 values; `config_fingerprint` is one
  lowercase SHA-256 value. Reject duplicate/non-string paths, noncanonical
  hashes, or later mutation. The three limits are module constants and are not
  constructor arguments. The graph/kernel identity is derived from
  `initial_state` at `solve` and must match the database metadata.
- The SQLite application schema has exactly one singleton `metadata` table and
  one value table named `nonterminal_exact_values`; “one value table” does not
  prohibit the metadata table. The singleton stores canonical JSON plus its
  SHA-256. That JSON binds solver/schema/serializer/key/accounting versions,
  graph/kernel identity, source fingerprints, config fingerprint, and all
  limits. No other application table is permitted.
- `Family3V2ExactSolveResult` is frozen/slotted and contains `graph_id`, exact
  `root_value`, caller-ordered `root_q_values`, and frozen/slotted statistics
  containing the counts named below. `TerminalFreeReferenceResult` is
  frozen/slotted and contains `graph_id`, exact root V/caller-ordered Q rows,
  nonterminal-state/terminal-leaf/action/transition counts, and maximum
  decision depth. `FrozenSetAudit` contains `passed`, expected/actual counts,
  and ordered missing/added/changed path evidence. `ArtifactRef` contains only
  POSIX-relative path, lowercase SHA-256, and byte size. Each exposes a
  canonical JSON evidence mapping; encode every `Fraction` as explicit integer
  numerator/denominator, never float or `repr`.
- Construct the store as
  `Family3V2PreflightStore(project_root, output_root, *, baseline, run_config_relative_path, run_config_sha256)`.
  Task 7 owns creation of canonical `run_config.json` before first store use.
  Task 6 neither creates nor interprets it: it validates exact bytes/hash and
  binds `run_config_relative_path` and `run_config_sha256` in the checkpoint.
  Unit tests create this file under their isolated fixed-relative output root.
  Resume revalidates it before reading any committed gate as PASS.

## Mandatory TDD sequence

1. Write all three focused test modules first.
2. Run exactly:
   `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`
3. RED must be missing `pa_rl.family3_v2_exact_solver`; another cause stops/checkpoints.
4. Implement the smallest complete three modules.
5. Run the same focused command for GREEN. Do not run a real ten-graph solve, real preflight, broad regression, training, or create artifacts under the fixed real result root in Task 6.

## 1. Value-first exact solver

Use exact `Fraction` only. Bellman recurrence:

- terminal: validate exact binary integer reward and return `Fraction(reward)` immediately;
- nonterminal: enumerate only mask-valid candidates, validate each exact positive transition probability and exact sum one, compute `Q(a)=sum(p*V(next))`, then `V=max(Q)`;
- fail on a reachable nonterminal with no valid action, malformed probability, inconsistent terminal reward, or recursion cycle.

The terminal branch must return before any serialization, hashing, memory/SQLite lookup, row count, RSS read, or insertion. Focused poison-terminal tests must raise if any of those operations touch the terminal object.

`solve` validates a unique ordered tuple of requested root action IDs, requires each to be present and mask-valid, returns root V plus Q rows in that exact caller order, and always recomputes those root Q values from successors even if root V is a resumed cache hit.

Create a fresh versioned deterministic full-semantic-state serializer/key. Encode every transition-affecting nonterminal field (kernel/offer/scopes/probabilities/window, current/queued tasks, authorization, continuation, counters/indices, termination/failure fields). Encode Fraction numerator/denominator; never `repr`, float, object identity, policy projection, or lossy labels. Use a primary SHA-256 key plus an independent guard digest and verify the guard on every memory/SQLite hit.

SQLite contains metadata plus only one value table, `nonterminal_exact_values`; no terminal table/row. Bind metadata strictly to solver/schema/serializer/key versions, accounting domain `nonterminal_bellman_states`, cache signature, graph/kernel hash, source/config fingerprints, and all three frozen limits. Reject missing/incompatible/unsigned metadata or an existing database over cap. Store exact numerator/denominator losslessly. One solver/database/LRU instance is used per graph.

Before inserting a new distinct nonterminal row:

- current row count must be `< 250000` (never insert row 250001);
- RSS must be `<= 512*1024*1024` bytes;
- at 512 MiB insertion may proceed; at +1 byte raise a dedicated resource-cap error before insertion.

The 4,096-entry memory cache is a true LRU (`OrderedDict`, hit moves to MRU, evict oldest). Expose immutable solve statistics sufficient for certificates: row/new-row counts, value/terminal calls, memory/disk hits, LRU peak, recursion depth, and peak/current RSS.

Default RSS reader:

- Windows: standard-library `ctypes`, `GetCurrentProcess` + `GetProcessMemoryInfo`, `WorkingSetSize`;
- Linux: resident pages from `/proc/self/statm` × `os.sysconf('SC_PAGE_SIZE')`;
- unsupported platform/API/malformed/non-exact/negative result fails closed; no `psutil`.

Focused tests must cover terminal-before-key, exact V and ordered Q, root-Q recomputation after resume, schema/signature mismatch, guard mismatch, malformed/non-unit probability, deliberate cycle, no-valid-action, row cap before 250001, RSS boundary, and LRU bound.

## 2. Independent terminal-free bottom-up reference

Do not import the solver module. Permit only source graph IDs `i8_f3v2_v0` and `i8_f3v2_v1`.

BFS-enumerate reachable nonterminal states only. When a successor is terminal, validate/compress it immediately to a binary reward leaf without hashing, serializing, queueing, or storing the terminal object. Require every nonterminal child `decision_index == parent.decision_index + 1`, exact positive probabilities summing to one, and at least one valid action. Compute exact values/Q in reverse decision-index order. Preserve caller root-action ordering.

Return immutable exact V/Q plus nonterminal-state, terminal-leaf, action/transition, and decision-depth counts. Poison-terminal tests must prove terminal objects never enter state tables; add rejection for v2 graph IDs and non-advancing/cyclic successors.

## 3. Frozen baseline verifier and strict artifact/checkpoint store

`verify_frozen_v0_v1_baseline` validates the Task 1 schema/cardinalities/path syntax/uniqueness/hash syntax, then re-enumerates and compares exact sets and hashes:

- exactly 14 frozen source entries: every current `src/pa_rl/increment8_*.py` plus `authorization.py`, `contracts.py`, `effects.py`, and `scope_matching.py`;
- exactly four frozen result roots and 72 regular files.

Missing, changed, or added paths fail, including a newly added `increment8_*.py` or any extra file under a frozen result root. New `family3_v2_*` files are outside this set. Return immutable expected/actual/missing/added/changed evidence; never freeze/rebaseline.

The store operates only under the resolved fixed project-relative output root and has no freeze/rebaseline API. Reject absolute artifact paths, empty paths, `..`, lexical/resolved escape, and symlink/reparse escape. Store only POSIX-relative references.

Atomic JSON/evidence write sequence: same-directory temp file → flush → `os.fsync` → `os.replace` → hash final bytes. Write/hash all evidence and gate report before atomically advancing the checkpoint; then append exactly one flushed/fsynced JSONL gate record. A partial file without checkpoint advance is never PASS.

Gate order is exactly numeric 1 through 12, contiguous and once only. `commit_gate` accepts only `checkpoint.next_gate` and binds every report/evidence hash. The initial Task-1 `BASELINE_FROZEN/0/1` checkpoint is startable. Only `INTERRUPTED` is resumable after revalidating baseline, immutable run config, contiguous committed reports, and all evidence hashes. `GATE_FAILED` and `RESOURCE_CAP_EXCEEDED` are terminal/non-resumable. `finalize` refuses fewer than 12 committed gates and writes/hashes `final_verdict.json` only after Gate 12.

`mark_interrupted(gate, next_action)` treats `gate` as the current uncommitted/next gate and records last committed `gate-1`, exact next action, and interruption evidence without pretending a gate committed. `mark_terminal_failure` accepts only the two terminal failure statuses and never permits later resume/commit.

Tests use isolated temporary project/output roots and cover: valid/missing/changed/added frozen set; output/artifact escape; out-of-order/repeated gate; write failure leaving checkpoint unadvanced; tampered report/evidence; interrupted-only resume; terminal-status refusal; immutable run-config mismatch; and finalization refusal at eleven gates.

## Completion/checkpoint contract

On GREEN, record RED/GREEN commands and exact method/time counts, six new-file hashes/sizes, resource-cap boundary evidence, schema/signature/reference/artifact test evidence, unchanged Task 2–5 hashes, and concerns in `task-6-report.md`. Retain `BASELINE_FROZEN/0/1`; keep the checkpoint's existing single `implementation_progress` mapping and set its `task` field to `6` (do not introduce a nested `task_6` shape), record the exact Task 7 next action, append one flushed implementation JSONL record, and do not create Gate 1 or any real cache/certificate.
