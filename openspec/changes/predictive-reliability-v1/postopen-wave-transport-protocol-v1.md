# Recorded39 post-opening wave/marker diagnosis — preparation v1

Status: **prepared, not activated for solver execution**. This document binds a
bounded follow-up to the existing recorded39 diagnostic. It does not authorize
new solver steps, periodic extension, candidate adoption, or changes to rc7.

## Question and fixed scope

The existing 0–60° diagnosis found burned-marker growth concentrated after
opening, especially 90–150°. This run would compare the same recorded39 initial
field through 150° at 88/176/352 cells and use the existing 176-cell half-step
case as the temporal control. It can localize numerical sensitivity in this
transient arc; it cannot establish a periodic mesh error, engine accuracy, or
predictive capability.

## Exact source recovery

The 0–60° outputs are `FAST_RECIPE_V1_TERMINAL_STATE`, not restorable native
checkpoints. For each case, a future activated runner must:

1. Verify every required file hash against the completed-run manifest and bind
   the original runner and solver dependency hashes.
2. Construct a fresh engine from the recorded configuration and restore the
   recorded native initial checkpoint at 13680°.
3. Replay every saved accepted step and rejected proposal in order, comparing
   recomputed step records exactly and recomputing the terminal FAST state.
4. Continue only after exact agreement at 13740°; otherwise fail closed.
5. Advance to 13830° while recording common phases 90°, 120°, and 150°.

This recovery repeats the recorded prefix as verification work. It does not
reinterpret or modify that historical result.

## Cases and controls

| Case | Grid | Angular cap | Purpose |
|---|---:|---:|---|
| P0-88 | 88 cells | 0.0625° | Coarse spatial comparison |
| P0-176 | 176 cells | 0.0625° | Common spatial reference |
| P0-352 | 352 cells | 0.0625° | Fine spatial comparison |
| P0-176-timehalf | 176 cells | 0.03125° | Temporal sensitivity control |

All physics, initial fields, 9000 RPM, coupling, HLLC/MUSCL choices, CFL,
boundary behavior, and source criteria remain bound to the original cases. No
P1 representation case is included because the existing pre-opening report
found it did not explain the spatial signal. Compare pressure, density, species
markers, and integrated face fluxes at common phases. Report local and integral
norms; do not force monotonicity or Richardson/GCI through nonmonotone contacts.

## Cost and acceptance to admit a run

Replaying the existing 60° recipe and extending another 90° projects at 2.5×
each measured source-case time. The four source cases total about 166.5 s, giving
416.2 s projected; a 30% margin gives 541.0 s. Proposed admission caps are 600 s
total and 210 s per case. These are projections, not benchmarks. An activated
runner must re-estimate after the first case and stop before admitting any case
whose projected cost with margin exceeds either cap. It must preserve progress,
all partial outputs, and the source result.

The execution acceptance is provenance and conservation integrity plus complete
phase coverage and source replay agreement. The result is diagnostic only. No
threshold converts a transient norm into predictive accuracy or a mesh GCI.

## Activation boundary

The preparation artifact verifies source hashes and projected costs with zero
solver steps. Solver execution remains a separate activation decision. If the
actual replay differs, a source hash fails, a case exceeds its cap, or a physical
admissibility/conservation check fails, retain the partial result and stop the
case set; do not alter physics, timestep limits, or acceptance thresholds to
continue.
