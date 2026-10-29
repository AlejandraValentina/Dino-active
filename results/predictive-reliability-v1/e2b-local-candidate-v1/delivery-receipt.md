# E2 local performance candidate — delivery receipt

## Result

The bounded A44/B44 run measured the explicit opt-in bracketed Brent root path against deterministic bisection. It retained the same accepted-step totals (A: 3611; B: 3615), rejected-proposal counts (A: 0; B: 5), passed the frozen numeric comparison, and passed restore/replay checks. No equations, CFL limits, tolerances, clipping or production defaults changed. The audited E2B reference remains the comparison basis.

| Case | Audited reference (s/cycle) | Local bisection (s/cycle) | Brent candidate (s/cycle) | Speedup vs audited | Speedup vs local |
|---|---:|---:|---:|---:|---:|
| A44 | 13.8755 | 12.04767 | 6.39572 | 2.169× | 1.884× |
| B44 | 14.3571 | 12.25459 | 6.43568 | 2.231× | 1.904× |

Peak RSS was 27.86 MiB (A) and 29.04 MiB (B), below the 200 MiB cap. The baseline peaks were 27.95 and 29.44 MiB. All snapshots passed the frozen per-numeric-field tolerance `abs(a-b) <= 1e-10 + 1e-10*max(|a|,|b|)`. Maximum absolute differences were 1.223e-9 (A) and 7.567e-10 (B); maximum normalized relative differences were 6.963e-13 and 7.532e-13. Accepted-step totals match. Mass residuals remained below 4.5e-18 kg, energy below 9.4e-13 J, and individual species residuals below 4.2e-18 kg. Restore, repeated opt-in replay and default-bisection replay were exact for both variants.

The practical 2× lower bound is met against the audited reference for both variants. The local bisection ablation is below 2×; it does not replace the owner-selected audited-reference denominator.

## Qualification

**PASS for the frozen A44/B44 candidate cases after a preregistered timing replication; original selection limitation remains disclosed.** The first exploratory measurement preceded the original protocol. The independent five-cycle candidate-only replication was preregistered in `docs/gasdynamic/e2b-local-candidate-preregistered-replicate-v1.md` before either new timing run. It passed the acceptance bounds for both variants. This supports the bounded candidate result, not a claim that the original candidate selection itself was prospective.

The candidate remains opt-in (`port_root_solver='brent'`); default behavior is still deterministic bisection. This does not promote V2/MUSCL or make a predictive-accuracy claim.

## Evidence

- Runs: `baseline-A.json`, `candidate-A.json`, `baseline-B.json`, `candidate-B.json`.
- Tolerance receipts: `comparison-A.json`, `comparison-B.json`.
- Restore/replay receipts: `replay-A.json`, `replay-B.json`.
- Prospective replication outputs and result: `preregistered-replicate-v1/A/`, `preregistered-replicate-v1/B/`, and `preregistered-replicate-v1/result.md`.
- Frozen protocol and its limitation: `docs/gasdynamic/e2b-local-candidate-equivalence-v1.md`.
- Focal tests: 363 passed across `test_e2b_local_candidate_v1.py`, integrated V2 port tests, transonic V2 tests and EOS tests.

## Preregistered replication

| Case | Replicate (s/cycle) | Speedup vs audited | Steps / rejected | Peak RSS |
|---|---:|---:|---:|---:|
| A44 | 6.25508 | 2.218× | 3611 / 0 | 28.25 MiB |
| B44 | 6.26933 | 2.290× | 3615 / 5 | 28.22 MiB |

Both snapshots pass the frozen tolerance against the existing baseline; all
solver source hashes match the frozen commit. Conservation and three replay
checks pass for each. The A command's final console summary hit a Windows
relative-path formatting exception after writing the candidate, comparison,
and replay artifacts. Those artifacts were read and validated directly. B
used an absolute output path and exited successfully. No benchmark was
repeated to recover from the reporting exception.

## E1.3 viability re-evaluation

Do not resume the 176 periodic/GCI branch from this result alone. Its current runner uses the default bisection path; the 2.17–2.29× result above is measured only on A44/B44 and cannot be projected to a 176-cell case or a different root-solver identity. Existing 176 budget is 230.1685 s, while the recorded best-case minimum continuation estimate remains 364.115 s. Reusing the opt-in candidate there would require a versioned activation and case-specific bounded recost before execution. Therefore E1.3 remains blocked and no periodic run was launched.
