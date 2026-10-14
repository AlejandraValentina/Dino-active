# EXHAUST_MESH_V1

## Why

The existing exhaust represents each named geometric section with one finite-volume cell. That cannot quantify spatial discretization sensitivity for the modeled pressure waves.

## Scope

Add an explicitly versioned 1/2/4-cell-per-section axial mesh. Preserve each section length, endpoint diameters, interfaces, exact frustum volume and existing quasi-1D solver equations unless verification demonstrates the minimum versioned correction is needed. Bind mesh identity to engine configuration and checkpoints; integrate Desktop/project workflow; run six bounded one-cycle A/B diagnostics within an aggregate 1800-second budget.

## Non-goals

No complete RPM campaign, KT100, experimental validation, claim of spatial independence from only 1/2/4 refinement, or modification of historical DINO_DESIGN_VALIDATION_V1, R2 or IMPL2 evidence.
