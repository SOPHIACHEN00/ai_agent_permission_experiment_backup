# Task 0 Brief — Increment 0 Contracts and Canonical Fixtures

## Role in the project

This task creates the executable contract that every later authority, environment, and policy module must obey. Do not implement ledger transitions, tool execution, environment stepping, learning algorithms, or live S-QSTN integration.

## Required deliverables

1. Create an independent Python 3.12 project using `pyproject.toml` and a `src/pa_rl` package. Runtime code in this task must use only the Python standard library.
2. Define exactly these six high-level controller actions:
   - `REQUEST_AUTHORIZATION`
   - `REQUEST_REFRESH`
   - `DISABLE_LOCAL_AUTHORIZATION`
   - `EXECUTE_WITH_AUTHORIZATION`
   - `DENY_WITH_REASON`
   - `ESCALATE`
3. `CLARIFY` and `PROPOSE_NARROW_SCOPE` must not exist as enum members, aliases, candidate slots, or hidden transitions.
4. Define frozen public contracts for:
   - controller action groups and action candidates;
   - permission choices `{deny_persist, deny_reask, allow_once, allow_reuse}`;
   - request/operation scope;
   - authorization status and grant type;
   - public events;
   - scenario manifest and terminal outcome specification;
   - public observation shape;
   - field visibility `{public, private, oracle}`;
   - S0 terminal binary reward result.
5. Define a `PermissionUserAdapter` protocol with:
   - `reset(public_scenario, seed)`;
   - `observe_event(verified_public_event)`;
   - `answer_permission(public_permission_request, public_history)`.
6. Implement canonical JSON serialization and SHA-256 hashing for contract artifacts. Candidate ID/order must be deterministic and independent of dict insertion order.
7. Add versioned configuration with these v0 defaults:
   - environment version `pa_env_v0.10`;
   - contract version `contracts_v0.1`;
   - authorization policy `authorization_policy_v0`;
   - candidate limit `16`;
   - public event history length `4`;
   - response-rate smoothing alpha `1.0`;
   - episode horizon comes from each scenario and must be in `[3, 8]`.
8. Add ten canonical scenario JSON fixtures spanning:
   - one-time grant success;
   - reusable grant used for two protected steps;
   - attempted execution without grant;
   - explicit local authorization disable/revocation;
   - consumed one-time grant requiring refresh;
   - broader scope requiring a new/refresh request;
   - persistent denial/do-not-reask;
   - safe-impossibility denial success;
   - safe-impossibility escalation success;
   - timeout/truncation.
9. Every scenario must explicitly declare:
   - public request/task context;
   - hidden evaluator postconditions;
   - scripted permission responses;
   - horizon;
   - legal terminal success kinds;
   - expected legal and prohibited path descriptions.
10. Add tests using standard-library `unittest` only. Tests must exercise observable behavior rather than inspect source text.

## TDD requirements

- Write tests before production code.
- Run them and capture the expected failure caused by missing modules/behavior.
- Implement the minimum code needed to pass.
- Run the task test suite and then the project suite.
- Record both RED and GREEN commands/output summaries in the report.

## Required tests

- the action enum has exactly the six specified members;
- deferred actions cannot be parsed;
- only authorization request/refresh actions require a permission answer;
- all four permission choices round-trip through JSON;
- invalid/empty scope fields and horizons outside `[3, 8]` are rejected;
- canonical hash is stable under input dict key reordering;
- candidate ordering and IDs are stable under input list reordering;
- visibility registry rejects duplicate paths or mixed visibility;
- all ten fixtures load and validate;
- no oracle/private fixture field appears in the public observation projection;
- scenario and configuration hashes are reproducible.

## Binding research decisions

- User choice, not controller request, determines one-time versus reusable grant type.
- Refresh will later create a new record; this task must not encode in-place authority expansion.
- Deny/escalate is successful only if the scenario manifest pre-registers the corresponding safe-impossibility terminal outcome.
- v0 resets authority and interaction history at episode boundaries.
- Raw S-QSTN private state, rule IDs, future response, minimal-scope truth, necessity labels, and evaluator labels are non-public.

## Out of scope

- No Gymnasium, Torch, Tianshou, RLlib, or other new dependency.
- No authorization state transitions beyond enum/contracts.
- No real API calls, external tools, or sensitive data.
- No test that merely greps source code or compares a helper's output to itself.

## Required report

Write `docs/implementation_reports/task-0-report.md` containing:

- status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`);
- files created/changed;
- RED evidence;
- GREEN evidence with exact command and test count;
- decisions and deviations;
- self-review and remaining concerns.

