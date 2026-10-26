# Spatial endpoint capability V2 — before implementation

The read-only steady-nozzle residual experiment demonstrates first-order endpoint
sampling, while interior mass/energy errors approach second order. Correct the
numerical trace, not the physical coupling law. Keep all earlier versions intact.

Implement `MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2`, opt-in, using V1
interior slopes and a three-cell one-sided derivative at physical endpoints.
Limit with adjacent secants, positivity for rho/p and the species simplex.
An extrapolated outer face can lie outside the range of cell means in a smooth
monotone profile; do not force its slope to zero by incorrectly bounding it to
that interval. The inner face remains within the adjacent means. No floors or
modification of conserved cell means. Gas and species limits remain independent.
Meshes with fewer than three cells explicitly fall back to V1 reconstruction.

Feed the reconstructed boundary gas state to the same port/external/network
equations and the reconstructed donor composition to the same signed mass flux.
Use actual stage volumes for all conserved means and inventories. Closed walls
still impose zero mass/energy flux; conservation ledgers still share each face
flux. No flow cap, new physical Cd, smoothing of geometry or relaxation of CFL,
periodicity or species criteria.

Capability identity must be immutable and serialized in existing CONFIG_V8.
Earlier readers must reject the unknown spatial-model value. Checkpoints from
different spatial models must reject one another. Legacy/default/V1 paths remain
unchanged, including physical state and ledgers in control tests.

L0: endpoint linear consistency, positivity/simplex on steep profiles, two-cell
fallback, both-stage integrated conservation, closed walls, signed species donor,
same-model restart and cross-model rejection. L1: steady-nozzle residual
20/40/80/160 must reduce whole-duct mass/energy residual with observed order >1.8
on the last pair; endpoint flux errors should be second order. Reference mass/
energy flux invariants remain within 1e-12; exact-face coupling error <=1e-10.
Do not change these limits after the result. Test source/method/area quadrature
independently so an oracle error cannot be mistaken for a solver defect.

After verification, preregister any bounded integrated calculation separately.
No automatic new engine mesh or periodicity campaign is included in this contract.
No new-model release/predictive claim without its necessary evidence and review.
