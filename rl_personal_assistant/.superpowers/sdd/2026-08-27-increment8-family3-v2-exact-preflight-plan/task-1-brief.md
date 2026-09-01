### Task 1: Freeze the v0/v1 baseline before v2 source exists

**Files:**

- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/frozen_v0_v1_baseline.json`
- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json`
- Create:
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/progress.jsonl`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**

- Produces an immutable baseline containing exactly 14 source entries and 72
  result entries.
- Produces Gate-0 state
  `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.
- No implementation task is allowed to rebaseline these paths.

- [ ] **Step 1: Confirm the output root and every v2 source path are absent**

Run:

```powershell
$out = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
if (Test-Path -LiteralPath $out) { throw "output root already exists: $out" }
$v2 = @(Get-ChildItem -LiteralPath 'src\pa_rl' -Filter 'family3_v2_*.py' -ErrorAction SilentlyContinue)
if ($v2.Count -ne 0) { throw "family3_v2 source exists before baseline freeze" }
```

Expected: exit `0`, no output.

- [ ] **Step 2: Emit the exact baseline mapping to stdout without writing it**

Run this from the project root:

```powershell
$project = (Resolve-Path '.').Path
$source = @(
  Get-ChildItem -LiteralPath 'src\pa_rl' -Filter 'increment8_*.py' -File
  Get-Item -LiteralPath 'src\pa_rl\authorization.py'
  Get-Item -LiteralPath 'src\pa_rl\contracts.py'
  Get-Item -LiteralPath 'src\pa_rl\effects.py'
  Get-Item -LiteralPath 'src\pa_rl\scope_matching.py'
) | Sort-Object FullName -Unique
$roots = @(
  'results\increment8_v1_fixed_formula_preflight',
  'results\increment8_v1_s3_v9_calibration',
  'results\increment8_v1_s3_v9_target6_exposure24_calibration',
  'results\increment8_v1_terminal_cache_bypass_diagnostic'
)
$result = foreach ($root in $roots) {
  if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "missing root: $root" }
  Get-ChildItem -LiteralPath $root -File -Recurse
}
if ($source.Count -ne 14) { throw "expected 14 source files, got $($source.Count)" }
if (@($result).Count -ne 72) { throw "expected 72 result files, got $(@($result).Count)" }
function Entry($file) {
  $relative = [IO.Path]::GetRelativePath($project, $file.FullName).Replace('\','/')
  [ordered]@{ relative_path=$relative; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant() }
}
[ordered]@{
  schema_version='family3_v2_frozen_baseline_v0'
  source_files=@($source | ForEach-Object { Entry $_ })
  result_roots=@($roots | ForEach-Object { $_.Replace('\','/') })
  result_files=@($result | Sort-Object FullName | ForEach-Object { Entry $_ })
} | ConvertTo-Json -Depth 6
```

Expected: one JSON mapping with 14 `source_files` and 72 `result_files`.

- [ ] **Step 3: Atomically create the baseline and Gate-0 files**

Create only the already-fixed output directory (after Step 1 proved it was
absent):

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
New-Item -ItemType Directory -Path $root | Out-Null
```

Use `apply_patch` to create `frozen_v0_v1_baseline.json` from the exact Step 2
stdout. Then run the following read-only formatter to print the complete
checkpoint with its real baseline hash:

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
$baselineHash = (Get-FileHash -Algorithm SHA256 -LiteralPath "$root\frozen_v0_v1_baseline.json").Hash.ToLowerInvariant()
[ordered]@{
  schema_version='family3_v2_preflight_checkpoint_v0'
  status='BASELINE_FROZEN'
  last_completed_gate=0
  next_gate=1
  next_action='Implement Task 2 contracts, suite, and exact mod-5 RNG'
  baseline_relative_path='frozen_v0_v1_baseline.json'
  baseline_sha256=$baselineHash
} | ConvertTo-Json
```

Use `apply_patch` to create `continuation_checkpoint.json` from that exact
stdout. Create `progress.jsonl` with the same state as one compact JSON line and
`flush/fsync` it during later programmatic updates.

- [ ] **Step 4: Verify the frozen baseline**

Run:

```powershell
$root = 'results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight'
$b = Get-Content -Raw -LiteralPath "$root\frozen_v0_v1_baseline.json" | ConvertFrom-Json
$c = Get-Content -Raw -LiteralPath "$root\continuation_checkpoint.json" | ConvertFrom-Json
if ($b.source_files.Count -ne 14 -or $b.result_files.Count -ne 72) { throw 'baseline cardinality mismatch' }
if ($c.status -ne 'BASELINE_FROZEN' -or $c.next_gate -ne 1) { throw 'checkpoint mismatch' }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath "$root\frozen_v0_v1_baseline.json").Hash.ToLowerInvariant()
if ($hash -ne $c.baseline_sha256) { throw 'baseline hash mismatch' }
```

Expected: exit `0`, no output. Update `docs/CONTINUATION_CHECKPOINT.md` with
the baseline hash, cardinalities, stable state, and exact Task 2 next action.

