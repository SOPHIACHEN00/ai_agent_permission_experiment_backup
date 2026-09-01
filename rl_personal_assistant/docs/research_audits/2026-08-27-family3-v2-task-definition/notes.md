# Notes: Family-3 v2 task-definition design

## Starting evidence

- v1 fixed formula leaves `s3_v3=13/25<3/5`; the limiting mechanism is
  prompt/one-time stochastic feasibility, not a required lifecycle decision.
- Terminal-cache bypass certifies `s3_v4=1`; its prior missing value was a
  computational representation problem, not graph difficulty.
- Strategic Family 3 currently uses mixed-value recurrence and the generic
  `scope_sensitive_offer` objective. It has no explicit disable/refresh
  directive; mandatory graphs separately test disable→refresh compliance.
- A valid v2 construct must not merely relabel a carrier or lower a target. It
  needs an action-level causal contrast that is visible to the policy and
  checkable by the exact oracle.

## Working assumptions to validate

- The desired scientific claim is about adaptive authorization lifecycle
  planning under delayed, scope-dependent future utility—not rote compliance
  with a directive.
- The primary exact gate remains per-graph oracle success at least `3/5`.
- Oracle feasibility should be established from a construction invariant and
  then verified, not discovered by sweeping budgets or targets.

## Evidence / alternatives

### Current ten-graph audit

The fixed v1 values are `1,1,1,13/25,1,1,121/125,9/10,1,7953/10000`,
where v4's value `1` comes from the separate valid terminal-cache-bypass
certificate. Only v3 violates `3/5`. Its public initial vector is the unique
combination of sensitivity 3, utility 1, target 5, and prompt budget 3; exact
analysis shows the failure is prompt-funded one-time recurrence.

The reusable foundations are the six actions, authority/monitor/tool path,
scope lattice, typed public authorizations and budgets, ordinary binary outcome
conjunction, Markov/firewall checks, exact DP, carrier/purpose rotation, and
mandatory directive FSM as a separate compliance gate.

### Alternative A — stale-authorization retirement

Create a public state with one disjoint reusable stale grant. Algebraically set
remaining exposure so `DISABLE(stale) -> REQUEST -> EXECUTE` succeeds while
requesting first fails. This is the smallest change and uses ordinary exposure
semantics, but the causal consequence is almost immediate and a simple
threshold Rule can solve it. It is useful as a focused unit test, not the best
definition for the whole long-horizon family.

### Alternative B — relation-continuity handoffs

After each workload change, require retain for EXACT, refresh for BROADER, and
new request for DISJOINT. A structural witness can make every graph value 1.
However, making every alternative a contract violation turns the family into
scope-relation compliance and resembles the mandatory FSM more than strategic
planning.

### Alternative C — forecast-conditioned scope reservation (recommended)

At reset, a single public permission window offers two legal candidates with
the same action enum: request the current narrow scope or its frozen broader
scope. This is a new v2 request grammar: the selected candidate scope is what
the adapter shows the user and what the ledger records. The public response
profile deterministically grants reusable authority for either offered scope;
the policy cannot choose the grant type. The window is consumed after one
verified grant. After the first committed effect, a public
forecasted workload draw selects an exact-tail program or a broader-tail
program. The early scope choice cannot be repaired later.

Let `n=sensitivity*|narrow attributes|`, `b=sensitivity*|broader attributes|`,
and let exact/broader tail lengths be `e>d>=1` with `e-d<=2`. Set

```text
utility_target = e + 1
prompt_budget = 1
exposure_budget E = max((e+2)n, (d+2)b)
horizon = max(8, e+4)
```

Because `n<b` and `d<e`, `E < (e+2)b`. Therefore:

- narrow + exact program succeeds;
- narrow cannot cover the final broader task after the window closes;
- broader + broader program succeeds;
- broader + exact program exceeds exposure before completion.

With public `P(exact)=4/5` or `1/5`, the correct initial request has exact
value `4/5`, the opposite request has `1/5`, and the action gap is `3/5`.
Thus every graph passes the frozen feasibility floor by theorem, while a
single-variable forecast intervention must switch the unique optimal action.

### Construct-validity conclusion

Alternative C best isolates the intended claim: use public future-demand
information now to choose a least-privilege or future-proof authorization whose
consequence appears only after committed work. It retains ordinary binary task
success and six actions, is distinct from directive compliance, and makes
oracle feasibility an input invariant rather than an output-tuned parameter.

It does not, by itself, imply DDQN superiority over a strong forecast-aware
Rule. Family-3 v2 is first a construct/credit-assignment gate; learner advantage
remains a later empirical question across the full suite.

### Proposal review corrections

Independent review found that v1 sensitivity-3 offers are one-time and that
v1 dispatch always requests the current task scope. The proposal now states
both necessary v2 exceptions explicitly: deterministic public reusable terms
for both scope offers, and candidate-scope-to-user/ledger binding. It also
formalizes offer-window closure/no-repair behavior, distinguishes `V*` from
the swapped request Q-values, and adds executable label/permutation controls.

### Formal-spec reader testing

The approved design was written as synchronized English/Chinese specs under
`docs/superpowers/specs/2026-08-27-increment8-family3-v2-design*.md`. Three
read-only reader tests initially found executable ambiguities rather than a
construct change: reusable-grant lifetime, deterministic committed tool
outcomes, transaction-safe scope binding, irreversible-failure ordering,
policy/raw-scope separation, exact denominator-five sampling, candidate-row
shape, evidence allowlists, and reachable-state coverage in the no-repair and
Markov gates. The specs were amended with explicit contracts.

Final independent verdicts are all PASS with zero Critical or Important
findings: fresh implementation-reader, exact algebra/RNG/FSM audit, and
bilingual semantic-equivalence audit. The exact ten-row table and theorem are
unchanged. No implementation, DP run, all-forty run, or learner work occurred.
