# Bounded integrated mesh sensitivity V1

Before calculation, 2026-10-26. Connection and isolated/integrated spatial
verification passed; see source-bound receipts. Do not equate these numerical
gates with engine predictive validation.

One additional A9000 diagnostic only: start independently from the same original
initial conditions, double every duct cell by exact frustum bisection (44->88
cells), retain end areas, total volumes and volume centroids to relative 1e-12.
Conservatively prolong initial species inventories and unchanged gas primitives.
Keep nozzle V2, MUSCL V1, geometry, CFL, periodic criteria, physical parameters
and two revolutions. Maximum step 0.5 degree, with original admissibility retries.

Budget: 240 s, 10000 accepted steps, 5 MiB outputs, storage preflight with existing
reserve. Use the existing trace-free SSPRK2 path, not another integrator. Keep
every actual accepted dt/angle and rejected proposal in a recipe; preserve native
checkpoints at complete revolutions and the initial checkpoint. On a mid-cycle
stop preserve the exact terminal FAST state plus recipe, explicitly not a native
checkpoint until the recorded recipe is replayed. No bindings bypass or extra
simulations on an automatic budget extension.

First verify trace-free/full-trace state and ledger equality in a small integrated
test. Existing coarse full-stage evidence and offline audit remain available;
this mesh sensitivity case is L1, not a substitute for its L2 audit. Check exact
same-mesh native checkpoint restoration and rejection of cross-mesh restoration.

Acceptance of execution: positive/admissible original criteria, conservation
normalized mass/species <=1e-9 and energy <=1e-8, initial integral differences
<=1e-12, complete 720-degree phase and successful checkpoint restoration.
Report mesh differences in chamber states/work, species and duct fields projected
conservatively to original control volumes. No fixed target power and no clipping.
One refinement pair **cannot demonstrate mesh independence**; quantify its error
indicator and retain that limitation. If material sensitivity remains, document
it before calibration or a predictive claim; do not silently add refinements or
declare the 44-cell curve validated. Independent closure conservation corrections
may proceed without fitting to these unvalidated engine outputs.
