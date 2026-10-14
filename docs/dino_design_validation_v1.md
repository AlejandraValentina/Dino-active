# Dino design sensitivity and imported measurements

## Solver-backed exhaust scope

The Desktop exhaust editor changes a named section's conical length/diameters,
the effective finite-volume mesh, and the mapped exhaust state. The current
starter comparison varies only diffuser length (180 mm to 200 mm); engine,
ports, timing, fuel, combustion, losses and operating conditions are held fixed.
See the diagnostic receipt and the external artifact report referenced there.

The comparison has one finite-volume cell per named exhaust section. This is a
coarse quasi-one-dimensional conical-frustum representation. It does not resolve
within-section gradients, radial or three-dimensional modes, boundary-layer
separation, or the internal reflecting surfaces and wave interactions of a
physical expansion chamber. A section's name/kind does not add a separate
physical model. The one-cycle tests establish solver sensitivity and repeatable
response, not mesh convergence, periodic performance, or that the change improves
an engine. Both exhaust variants remained `PERIODICITY_NOT_IDENTIFIED`; transient
brake power is therefore not a performance comparison. The missing component
for a stronger expansion-chamber claim is a versioned section-to-mesh adapter
that creates multiple axial finite-volume cells inside each cone/chamber
section while preserving section interfaces, followed by a controlled
1/2/4-cell-per-section refinement comparison. Until that exists, the observed
pressure/flow differences cannot be separated from spatial discretization
error.

## Measurement import contract

`motorsim.measurement_data` accepts bounded UTF-8 CSV plus an explicit
`metadata.json` declaration. It supports `pressure_trace`, `dyno_torque`, and
`dyno_power`, with supported source units converted into Pa, N*m, or W. Dyno
tables use RPM; pressure traces declare 360 or 720 degree cycles and use
crank-angle degrees. Every row carries an uncertainty in the declared source
unit. Metadata records engine/configuration, test conditions, source, notes and
provenance (`MEASURED`, `DOCUMENTED`, `SYNTHETIC`, or `UNKNOWN`). Original CSV
bytes are preserved and hash-bound by the manifest.

Imported measurements stay in the measurement dataset format, separate from
synthetic simulation reports. The optional comparison pairs exact RPM or
cycle/angle coordinates only; it never interpolates. It reports signed bias,
MAE, RMSE, uncertainty-normalized RMSE when uncertainties are positive, and
matched rows. Zero measured values have no relative-error value. A comparison
always reports `EXPLORATORY_COMPARISON`, with validation and P9 eligibility
false. No measurement dataset is supplied by this objective, so no experimental
validation or calibration claim is made.

## Result display and audit semantics

Exploratory result import verifies run/configuration/result/checkpoint bindings,
reconstructs and independently re-audits each completed cycle primary, then
rebuilds output summaries and crank-angle channels. Classification, periodicity,
primary audit/recomputed state, conservation and hard-gate state remain separate
fields. Runs without a complete cycle appear as missing-value gaps; no values
are interpolated. These results remain provisional and do not claim scientific
or experimental validation.
