# E2B local-candidate equivalence protocol v1

**Status:** `POST_HOC_PROTOCOL_FROZEN_FOR_CONFIRMATION`.

This document freezes the equivalence and performance criterion used for the
bounded `PRED-E2-LOCAL-CANDIDATE-V1` work. It is **not** a clean prospective
preregistration: an initial 2-cycle exploratory run was executed before this
document existed. The 5-cycle confirmation defined here is prospective relative
to this document, but the candidate was already selected after the exploratory
run. E2 is therefore not declared `PASS` by this document alone.

## 1. Scope

- Candidate: explicit opt-in `root_solver='brent'` in
  `motorsim/port_connection_v2.py`, plus the exact EOS/pressure-wave
  validation reductions in the same candidate task.
- Default production path remains deterministic bisection. The candidate is
  enabled only by setting `IntegratedEngine2T.port_root_solver = 'brent'`.
- Frozen configurations: `results/e2-spatial-waves-v1/preparation/A44.json`
  and `B44.json`.
- Harness: `scripts/diagnostics/e2b_local_candidate_v1.py`.
- No change to equations, branches, CFL, tolerances, clipping, conservation,
  rc7, P0–P9, or historical evidence.

## 2. Observables

The full canonical snapshot and run ledger are compared, including:

- `snapshot.state.chambers`, `snapshot.state.ducts`,
  `snapshot.state.network_volumes`, and `snapshot.state.species`;
- `snapshot.angle_deg`, `crank_angle_unwrapped_deg`, `time_s`, `cycle`,
  `accepted_steps`, `rejected_steps`, `ledger`, `p7`, and fuel-combustion
  state;
- top-level `ledger`, `initial_inventory`, and `conservation`;
- branch/string fields must be identical; no missing or extra fields.

`recorded_at_utc`, source hashes, timing fields, peak RSS, configuration hash,
and the derived `snapshot_sha256` are excluded from numeric comparison.
`snapshot_sha256` is reported separately: exact equality is stronger evidence
but is not required when the numeric criterion passes.

## 3. Numeric tolerance

For every compared numeric field `a` (baseline) and `b` (candidate):

```
abs(a - b) <= 1e-10 + 1e-10 * max(abs(a), abs(b))
```

This is a combined absolute/relative criterion. Numeric fields must also be
finite on both sides. A candidate with any branch change, non-finite value,
missing field, or array-length change fails.

The 0-cell and 44-cell paths are not part of this tolerance; they are covered
by the existing regression suite and the frozen E2B campaign.

## 4. Conservation and replay

- Mass residual absolute value must be `<= 1e-15 kg`.
- Total-energy residual absolute value must be `<= 1e-10 J`.
- Every species residual absolute value must be `<= 1e-15 kg`.
- The candidate must have the same accepted-step count as the baseline for the
  same cycle count, with zero unrecovered retry failures.
- A restored candidate snapshot must replay one step with the same
  `root_solver='brent'` setting and preserve the default-path replay contract.
  Any replay divergence is a failure, not a tolerance exception.

## 5. Performance criterion

- Reference audited E2B cost: `13.8755 s/cycle` (A44) and
  `14.3571 s/cycle` (B44).
- Required speedup for an E2 PASS: **2–4×** against that reference.
- Report both the absolute candidate time and the ratio against the reference;
  also report the local bisection baseline as an ablation, but do not use the
  local ablation to replace the audited reference.
- Peak RSS must remain `<= 200 MiB`.
- A benchmark is at most 10 minutes; total bounded-candidate benchmarking is at
  most 100 minutes and at most 10 benchmarks.

## 6. Sample and execution

- Exploratory sample: 2 cycles per variant (already executed).
- Frozen confirmation sample: 5 cycles per variant, A44 and B44.
- The confirmation must be run with the source hashes recorded in the result
  JSON and must not change code between A and B.
- A confirmation PASS requires tolerance equivalence, conservation bounds,
  replay, zero unrecovered retries, and at least `2×` against the audited
  reference for both variants.
- If the confirmation is below `2×`, the candidate is `PARTIAL`; if it changes
  physics or cannot demonstrate equivalence/replay, it is `FAIL`.

## 7. Known limitation

The first 2-cycle measurement was not prospectively preregistered. The
5-cycle confirmation can establish a reproducible candidate result, but it
cannot retroactively make the initial selection a preregistered experiment.
Any E2 `PASS` claim remains subject to owner/reviewer acceptance of this
protocol deviation or a new independent preregistered replicate.
