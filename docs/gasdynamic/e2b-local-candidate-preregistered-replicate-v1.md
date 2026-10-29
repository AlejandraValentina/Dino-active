# E2 candidate — preregistered independent timing replicate v1

**Frozen before replicate execution.** This addendum does not replace or edit
the post-hoc confirmation record in `e2b-local-candidate-equivalence-v1.md`.
It resolves the specific prospective-replication path identified there.

## Frozen run matrix

- Exactly two new benchmarks: the existing opt-in Brent candidate on A44 and
  B44, five complete cycles each. No new baseline run and no exploratory
  tuning.
- Frozen implementation: the E2 candidate at commit `d532239`; assert the
  runner's normalized source hashes match the prior five-cycle candidate
  receipts before interpreting the result.
- Frozen input files: `results/e2-spatial-waves-v1/preparation/A44.json` and
  `B44.json`; their SHA-256 identities are recorded in the prior baseline and
  candidate receipts. The bisection baseline files remain unchanged and are
  reused for numeric comparison.
- New outputs go under
  `results/predictive-reliability-v1/e2b-local-candidate-v1/preregistered-replicate-v1/`.
- No source edit between A44 and B44. No solver, physics, CFL, tolerance,
  clipping or default change. Brent remains opt-in.

## Acceptance frozen before timing

For each new candidate snapshot, compare to its existing five-cycle bisection
baseline with the existing canonical comparator and tolerance:

```
abs(a-b) <= 1e-10 + 1e-10*max(abs(a),abs(b))
```

All compared values must be finite; fields, branches and accepted-step totals
must match. Mass residual `<=1e-15 kg`, energy residual `<=1e-10 J`, each
species residual `<=1e-15 kg`, no unrecovered retry failures, peak RSS
`<=200 MiB`, and restore, Brent replay, and bisection replay must pass exactly.
Performance must be at least 2x and no more than 4x against the audited
13.8755 s/cycle (A44) and 14.3571 s/cycle (B44) references. Report local
bisection ablation separately; it is not the binding denominator.

If both cases pass, classify the bounded E2 candidate `PASS` for these frozen
cases only, subject to the measured scope and no predictive-accuracy claim. Any
failed comparison or acceptance bound is `FAIL`; performance below 2x is
`PARTIAL`. Do not rerun or replace a failed output.

This is a preregistered replication of the already selected candidate, not a
claim that the original candidate selection was prospective. The two new
measurements consume the remaining two slots of the original maximum of ten;
no further benchmark is authorized under that cap.
