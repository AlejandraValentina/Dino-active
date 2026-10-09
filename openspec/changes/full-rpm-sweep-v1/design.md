# Design

## Inputs and bindings

`results/full-rpm-sweep-v1/preregistration.json` records the source fixture
file SHA-256, canonical engine-configuration SHA-256, canonical
`MECHANICAL_LOSS_MODEL_V1` SHA-256, fuel snapshot identity, RPM grid, WOT
boundary condition, existing `PeriodicDetectorV2` contract and solver
dependency hashes. Configuration inputs are read-only. Each RPM point is
constructed as a detached copy with only `reference_rpm` set to that grid
point; its derived point hash is recorded.

The loss resolver accepts only an explicitly present model bound to the exact
fixture and configuration hashes. It rejects absence, malformed terms, stale
hashes, invalid model versions, and unsupported RPM/load domains. It never
calls `standard_fmep_model_v1()`.

## Preflight

Preflight reconstructs `IntegratedEngine2T` through its existing
`from_configuration_dict` contract at every RPM. That existing constructor
validates geometry, slider-crank chambers, port geometry and power-valve maps,
duct topology/meshes, thermal bindings, combustion and boundary states. Sweep
specific checks additionally require a complete RPM range, fixed WOT boundary
semantics, explicit premixed fuel species and fuel snapshot, and the
hash-bound mechanical model. Preflight never advances the solver.

## Engineering outputs

Post-processing uses the resolved explicit loss model with the existing
two-stroke net-piston-work accounting. It preserves `BMEP = net_piston_work /
displacement - FMEP`, `brake_power = brake_work * RPM / 60`, and torque from
work per 360-degree cycle. Nonconverged points receive a classification and no
valid periodic engineering outputs.

## Checkpoint and budget

The preregistered horizon is 111 complete cycles per point. A future runner
must checkpoint after every accepted cycle and completed RPM point, bind each
checkpoint to configuration/solver/detector hashes, and resume only on exact
hash match. Each invocation has a 60-minute wall-clock cap and stops at the
last durable checkpoint. Any runtime projection beyond the campaign budget
requires a separate performance task; convergence thresholds or CFL may not
be relaxed.
