# A3b T1-B..E execution plan (v3 lineage)

- Status: `PLAN_ONLY_NOT_AUTHORIZED`
- Authorization request: `DRAFT_NOT_AUTHORIZED` (no owner authorization requested or granted)
- Classification: `RESUME_READY_FOR_AUTHORIZATION`
- Scope: T1-A is COMPLETE; T1-B..E are a forward execution, not a T1-A resume.
- Solver steps: `0`

## T1-A result

- 3 cycles COMPLETE; `next_cycle=4`; cycle 3 primary `a7eaf55bffc8855117f01c2419201533425e1b9bdf21ddac6e6bf7b37c4d4f2f`; audit PASS.
- Cumulative `530.469/600 s`; global `530.469/4320 s`; global available `3789.531 s`.
- V2→V3 lineage: PASS; scientific fields equal; cycles 1-2 preserved with matching primary hashes; cycle 3 is the only new state.

## Budget

- Remaining config caps: `3670 s`; nominal headroom `119.531 s`.
- Central projected global total: `3417.819-3651.489 s` (includes T1-A spent); +5 pp `4050.869 s`; +10 pp `4450.269 s`.
- The +10 pp stress exceeds 4,320 s; the affected config would be PARTIAL under the frozen cap, with no extension.

## Configurations

| Config | Cells | CFL | Cap (s) | Plan | Linear 3 cycles (s) | Per-invocation nominal (s) | Observed-adjusted upper (s) | Status |
|---|---:|---:|---:|---|---:|---:|---:|---|
| T1-B | 48 | 0.2 | 1050 | [2, 1] | 867.300 | 582.027, 292.927 | 596.144, 299.985 | MARGINAL |
| T1-C | 48 | 0.1 | 2100 | [1, 1, 1] | 1734.600 | 582.027, 582.027, 582.027 | 596.144, 596.144, 596.144 | MARGINAL |
| T1-D | 28 | 0.4 | 310 | [3] | 252.960 | 256.787 | 262.963 | READY |
| T1-E | 18 | 0.4 | 210 | [3] | 162.620 | 166.457 | 170.427 | READY |

## Marginal invocation risk

- T1-B invocation 1 (2 cycles) and T1-C (1 cycle each) share the 578.2 s nominal envelope.
- Observed-adjusted upper invocation: `596.144 s` vs `595 s` internal deadline and `600 s` cap.
- Verdict: `MARGINAL`. If interrupted, do not retry beyond the affected config's cap; classify PARTIAL.
- Recommended order: T1-B invocation 1 (canary) → T1-D → T1-E → T1-B invocation 2 → T1-C. The owner must accept the residual risk.

## Required before execution

- A new **v4 forward protocol/addendum** that carries forward the v3 ledger and authorizes T1-B..E only.
- A new **v4 matrix-completion driver** with the same audit/replay/checkpoint/fail-closed contracts.
- A new **owner execution authorization** quoting the v4 hashes, caps, plans and the T1-B/T1-C marginal-invocation risk decision.
- v4 lineage and zero-step preflights, including a budget preflight; zero solver steps.

## Stop rules

- Any hash, identity, configuration, lineage or ledger mismatch.
- Any attempted T1-A re-run or any attempted edit to v2/v3 artifacts.
- Global charged time would exceed 4,320 s, or a configuration would exceed its cap.
- An invocation reaches 600 s or the 595 s internal deadline without completing its cycle.
- NaN/Inf, conservation mismatch, or a checkpoint/audit failure.
- T1-B invocation 1 or T1-C interruption at the marginal envelope: do not retry beyond the affected config's cap; classify PARTIAL.
- Any tolerance change or any use of later results to alter the frozen atol table.
- The +10 pp stress projection would exceed 4,320 s; stop the affected configuration and classify PARTIAL; no extension.

## Non-claims

- A3b T1 is a first numerical sensitivity evaluation, not a definitive convergence closure.
- No steady-state convergence and no periodicity identification.
- No power or torque curve is produced by this protocol.
- No experimental validation.
- No claim outside the studied mesh/CFL domain.
- No supported resolution domain from T1-A alone.

