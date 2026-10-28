# Recorded39 post-opening wave/transport execution — activation v1

Status: activated 2026-10-28 by the user's instruction to continue the unified
Dino 2T roadmap. This activates only the prepared, bounded transient diagnostic
described in `postopen-wave-transport-protocol-v1.md`.

## Frozen source and work

- Revalidate the completed `preopen-wave-transport-run-v1` manifest, four P0
  case receipts, initial native checkpoints, accepted/rejected recipes, FAST
  terminals, configurations, solver source hashes, and the preparation receipt.
- Reconstruct each of the four engines from its native initial checkpoint;
  replay its recorded 0–60 degree recipe exactly, including each rejected
  proposal, then continue the same state through 90, 120 and 150 degrees.
- Cases: 88, 176, 352 cells at 0.0625 degree cap and 176 cells at 0.03125
  degree cap. No P1 case or periodic extension.
- Record common-phase pressure/density/species fields and integrated face
  transport over 60–90, 90–120 and 120–150 degrees. Keep spatial and temporal
  comparisons separate; report nonmonotone results as observed.

## Admission and stop rules

- Source-bound linear projection including 30% margin: 541.002 s total;
  total admission cap 600 s; per-case cap 210 s; study artifact cap 1 GiB;
  retain the configured free-space reserve.
- Before each case, re-estimate from measured case time. Do not start a case
  unless its projection with margin fits its per-case cap and the remaining
  global cap. Stop before exceeding either limit.
- Preserve completed cases and partial receipts. Exact replay, 30-degree
  target coverage, global normalized conservation <=1e-12 and complete
  phase-window flux accounting are required for a COMPLETE result.
- No parameter, closure, detector, CFL, precision, or acceptance-threshold
  changes. No periodic mesh/GCI, experimental validation, predictive claim,
  candidate adoption, rc7 modification, or claim of causality from this
  transient comparison.

Preflight and execution outputs are append-only under `DINO_ARTIFACT_ROOT`;
execution is launched with `scripts/agents/run_logged.py`.
