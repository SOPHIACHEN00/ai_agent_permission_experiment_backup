# Task 6 fix round 1/5 base (no Git)

Captured after the fresh independent Task 6 review returned Spec FAIL / Quality
Needs fixes / DO NOT APPROVE. The workspace has no Git repository, so these
hashes are the immutable scoped-review base.

## Review authority

- `task-6-review.md`: `cdac850e9e44adb73a4042784ca659adf48d108040fdee768a1f83a5985be547` / 22,147 bytes
- Open findings: C1; I1, I2, I3, I4, I5, I6; M1.

## Six-file base

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` | 36,031 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` | 11,935 |
| `src/pa_rl/family3_v2_artifacts.py` | `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` | 29,226 |
| `tests/test_family3_v2_exact_solver.py` | `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` | 7,172 |
| `tests/test_family3_v2_exact_reference.py` | `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` | 3,400 |
| `tests/test_family3_v2_artifacts.py` | `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` | 7,127 |

Result checkpoint base:
`691bdda7689867ca57299f933d99b64d2dceeda2f22a91cd324308f9cd3c37de`
/ 3,189 bytes. Gate authority is `BASELINE_FROZEN / 0 / 1`; Task 7 remains
blocked. Task 2–5 and the 14-source/72-result frozen baseline are out of scope.

Fix round 1 must follow one grouped regression RED, the smallest complete
production correction, and one affected focused GREEN. It must not run a real
solve/preflight, create Gate 1/run config/cache/certificate, modify a scientific
parameter, weaken an assertion, or touch Task 2–5.
