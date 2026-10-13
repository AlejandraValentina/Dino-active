# FAST_RECIPE_V1 diagnostic capture and reconstruction

## Purpose

Measure whether a compact, hash-bound record of accepted solver steps can
reduce the cost of integrated 2T evidence capture while preserving the
existing canonical primary and independent replay audit.

## Scope

- Add an opt-in, versioned capture path. The default `IntegratedEngine2T.step`
  path and every historical writer remain unchanged.
- A recipe binds the complete cycle-start checkpoint, configuration and solver
  identities, accepted `(dt_s, delta_angle_deg)` sequence, rejected-attempt log,
  cycle terminal state/ledgers, and its own canonical digest.
- Reconstruct the complete existing V3 primary by deterministic replay, then
  pass it to the existing independent auditor. Scientific primary fields must
  match the conventional path; the runner provenance hash identifies the FAST
  producer and therefore differs by design.
- Benchmark conventional evidence, provisional recipe capture, and recipe
  capture plus complete reconstruction/audit on bounded A4000/B4000 diagnostic
  cycles. Include process coordination and write costs in end-to-end timings.

## Non-goals

- No solver equations, SSPRK2 ordering, CFL, meshes, thresholds, periodicity,
  hard gates, fuel/mechanical models, or historical evidence may change.
- No campaign point, FAST result, or point classification is authorized by
  this change. Unreconstructed or unaudited recipes remain `UNAUDITED`.
- No GUI work or sweep execution is included.

## Decision rule

Report provisional and fully audited speedups separately. If only provisional
capture is faster, classify that as an exploratory mode. Do not adopt FAST as a
scientific pipeline unless reconstruction, existing independent audit,
checkpoint/restart, and measured end-to-end comparisons pass.
