# Endpoint V2: SELF_REVIEW and bounded integration evidence

2026-10-26. This is a sequential review by the implementing agent, **not an
INDEPENDENT_REVIEW**, release gate or experimental validation.

## Defect, correction and causal evidence

The V1 MUSCL interior reconstruction leaves the two physical endpoint traces at
their cell means. An independent smooth isentropic frustum reference isolates
first-order boundary sampling, while its interior mass/energy residuals converge
at second order. Supplying the exact face state to the unchanged port equation
removes the boundary flux error. This identifies a spatial implementation
limitation; it does not invalidate HLLC or establish the cause of every engine
mesh difference.

The selectable `MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2` uses limited
one-sided endpoint traces consistently for boundary gas flux and signed species
donors. Conserved cell averages, physical equations, CFL, periodicity thresholds
and legacy/V1 selection are retained. Strict positivity and species simplex
bounds constrain slopes; no state floors or forced mass flow are introduced.

On the original frozen-reservoir reference the final global mass/momentum/energy
orders are 1.963/2.024/1.960. The independently mirrored right-reservoir case gives
2.042/2.041/2.044, versus approximately 1 for V1. These are zero-time-step
truncation diagnostics, not claims of second-order accuracy of an entire engine.

## Verification actually performed

- Integrated/default/V1/V2/port/thermal regression: **124 PASS**, 208.60 s.
- Frozen P4-P8 regression: **301 PASS, 3 SKIP**, 179.30 s; four existing NumPy
  deprecation warnings. No frozen expected values or tolerances changed.
- Final focused checks: **25 PASS**, 3.90 s, including additional legacy-port
  controls, near-vacuum endpoint extrapolation, strongly nonuniform cells,
  vanishing/absent species and nonconstant reconstructed network donors in both
  directions. This overlaps the 124-test suite; counts must not be added.
- Default and V1 controls match the actual pre-boundary implementation in gas
  states, species and cumulative ledger. CONFIG_V8 round trips; the previous
  reader rejects the unknown selector. Same-model checkpoint restoration and
  next accepted step are exact; a different reconstruction identity is rejected.
- One independent cold synthetic A9000, 44-cell, two-revolution run completed:
  **27.857 s compute**, 1444 accepted steps, zero rejected proposals. Maximum
  normalized mass/energy/species residuals are 2.52e-16/2.09e-16/4.21e-16.
  Cylinder work out is **28.810104 J** versus V1's 28.567634 J (+0.849%).
  Both are transient cumulative two-cycle quantities, not periodic power or
  evidence of an accuracy gain of that magnitude.
- Source-bound cycle-2 reconstruction/audit: **PASS**, 722 accepted steps,
  76.871 s. Native checkpoints bind configuration; this additional audit binds
  actual solver dependencies and the original primary stream. Native checkpoint
  source binding must not be claimed. Large original streams remain available
  locally with receipt hashes and are deliberately excluded from Git.

## Remaining limitations and decision

Keep V2 as a selectable numerical candidate, with legacy/default unchanged.
Only the stated analytic, conservation, restart and bounded integration tests
are closed. Limiter activation reduces local order at discontinuities; meshes
with fewer than three cells intentionally retain V1 endpoint behavior. Moving
reed force/volume mechanics still use cell pressure; their formal spatial order
is not established by the static-duct reference. There is no proof here of
engine mesh independence, temporal convergence, periodicity, real-port loss
identification or experimental predictive accuracy. The earlier 44/88/176 mesh
results used V1 and must not be relabelled V2 or rebound to current source hashes.

Next dependent work is a bounded separation of spatial and temporal error, then
stable same-simulation periodicity assessment. A public measured case must have
its own matched inputs and uncertainty assessment. No X30 assumptions, warm
start, Desktop changes, build or full RPM campaign were introduced.
