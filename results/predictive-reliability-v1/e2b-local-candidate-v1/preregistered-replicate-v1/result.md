# E2 preregistered replicate result

Protocol: `docs/gasdynamic/e2b-local-candidate-preregistered-replicate-v1.md`, frozen at commit `6ddd952` before measurement.

| Case | Candidate s/cycle | Audited reference s/cycle | Speedup | Accepted steps | Rejected proposals | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|
| A44 | 6.25507996 | 13.8755 | 2.21828× | 3611 | 0 | 28.2539 MiB |
| B44 | 6.26933408 | 14.3571 | 2.29005× | 3615 | 5 | 28.2188 MiB |

**Decision: PASS for the frozen A44/B44 opt-in candidate cases.** Both snapshot comparisons pass the frozen numeric tolerance; source hashes match the solver files at the frozen implementation commit. Mass, energy and species residuals are within preregistered limits. Restore, repeated Brent replay and default bisection replay are exact for both cases. Both speedups fall inside the 2–4× target and RSS is below 200 MiB.

The A run wrote all evidence but the CLI returned an error while formatting a relative output path after the run; the JSON evidence was validated directly. B used an absolute output path and completed with exit status 0. No rerun was made. This is a runner reporting issue and did not alter solver execution or captured results.

This is an engineering performance result for these two frozen configurations. It does not validate predictive accuracy, change defaults, promote V2/MUSCL, or establish performance on the 176-cell periodic/GCI branch.
