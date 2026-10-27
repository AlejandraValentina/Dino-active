# Frozen-state mesh/time diagnostic from native25, 2026-10-27
No periodic campaign. One physical cycle9000->9360degrees per case, outputs every
30degrees. First3cases:44cells cap.5deg,44cap.25,88cap.25. Fourth88cap.5 only if
spatial/temporal interaction needs resolution. At most4cases/480s total admitted
compute wall budgets,120s and16MiB each,2GiB reserve. No extension on timeout.
Same V2/MUSCL/boundary/CFL/closures/detector thresholds. Do not run detector across
meshes. Original native25/source hashes must match recorded manifest.
Remap is new diagnostic initialization, not a native cross-mesh resume. Exact
frustum bisection, constant conserved densities per parent, extensive species
split by child volume. Constructor computes the actual new config identity and
initial inventory; original checkpoint and guards remain intact. Physical gas
state, chamber states, clock and active combustion history transferred explicitly.
Validate positivity, exact primitive equivalence, global mass/energy/species,
back restriction and native cross-mesh rejection before running. Three tests PASS.
P0 mapped field has no invented subcell slopes: initial fine-grid reconstruction
adjustment remains confounded with spatial error, even with zero restricted error.
Control transient-vs-discretization using same starting state, same phases and
same physical parent volumes. Actual SSPRK2 signed interface fluxes aggregated,
including cylinder/exhaust reversal. Preserve checkpoints, profiles, recipe and
source/configuration hashes. No stage dictionary mutation. Compare work/IMEP,
inventories, pressure/density/species normalized L1/L2/Linf with physical weights;
contrast time and space differences with actual one-cycle change, no exact-state
claim. Additional cases require measured need within stated4case budget.
