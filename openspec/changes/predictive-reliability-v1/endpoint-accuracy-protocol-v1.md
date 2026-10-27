# Endpoint V2 bounded mesh/time assessment, 2026-10-27

Preregister before execution. Same independently initialized synthetic A9000
configuration as spatial-boundary-v2-engine, same gas physics, CFL, port law,
reconstruction V2, thresholds and terminal phase 720 degrees. No periodic claim.

1. Fixed 44-cell mesh, reduce maximum angular proposal from 0.5 to 0.25 degrees
using existing diagnose_integrated_port_v2.py. This is a time-sensitivity check,
not a change to production defaults. Existing CFL/events may shorten steps.
240 seconds/100 MiB maximum with original storage reserve, separate output.
2. Conservatively bisect the original V2 configuration from 44 to 88 cells using
existing diagnose_integrated_mesh_v1.py; same independent initialization, never
transfer a terminal state between meshes. 240 seconds/5 MiB maximum. Check
initial mass, energy and each species within 1e-12 and conservation gates
mass/species <=1e-9, energy <=1e-8. Preserve checkpoints and actual source hashes.

Compare original V2, time-refined V2 and mesh-refined V2 at identical phase using
all terminal states and cumulative ledger, not power alone. Mesh refinement also
changes CFL-limited steps, so two meshes cannot establish formal order or GCI.
If time changes are substantial, separate temporal error before a mesh claim.
Both two-cycle trajectories remain transient. Any periodicity continuation
requires this assessment first and its separate finite protocol; no automatic
extension, full RPM campaign or experimental validation follows from a PASS.
