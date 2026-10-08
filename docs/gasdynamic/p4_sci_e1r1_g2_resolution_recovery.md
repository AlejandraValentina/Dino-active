# P4-SCI-E1-R1 — recovery of the N=375 experiment

## Why E1 was inconclusive

The original N=375 physical run reached cycle 30, but its final aggregator
looked for the nonexistent `segment.result.counts.steps` field. Its periodicity
streaks were also reconstructed only after the loop. The scientific run was
therefore preserved as historical evidence but classified inconclusive.

## Corrections

E1-R1 writes atomic summaries and periodicity traces after every cycle, keeps
optional telemetry nullable, and updates the canonical `motorsim.periodicity`
detector live. Detector state is included in restart metadata. The campaign
started from canonical initial conditions and changed only `dx_target`.

## Configuration and result

G2 used `dx_target=0.002 m`, N=375, NUMBA_FUSED, CFL 0.4, float64, 3000 RPM,
and the unchanged E13-R1 thresholds. Cycles 1–30 completed with conservation
and admissibility passing. There was no early stop. Final detector state:
lag-1 streak 0, branch A streak 0, branch B streak 8, no detected period.

Branch B's lag-2 sensor metric falls from early values above 0.02 to
`0.0001501, 0.0000812, 0.0000715, 0.0000414` near the end, while the baseline
N≈251 last three values were `0.0897298, 0.0683317, 0.0290580`. This is a
clear sustained sensitivity signal, but branch A does not close and no
spatial convergence claim is made from one refinement.

## Reproducibility limitation

The recovery runner wrote physical restart state before assigning the terminal
state of the just-completed cycle. Consequently the checkpoint comparison with
the original attempt is invalidated by an off-by-one instrumentation defect.
The per-cycle scientific summaries and E13 trace are durable and valid for
the stated comparison; no rerun is performed in this order.

## Interpretation and next decision

`P4_SCI_E1_RESOLUTION_HYPOTHESIS_SUPPORTED`: branch B improves materially,
without E13 convergence. This is sensitivity evidence, not proof of spatial
convergence and not P4 acceptance. A future run would first need the checkpoint
write-order fix and explicit authorization. P4 remains blocked and P5 has not
started.
