# Design

## Historical boundary

`ENGINE_PHYSICS_V1 = FAIL_TERMINAL` remains immutable. Its original failure
was caused by the then-active gross-crossing partition identity, not by a new
trajectory. R2 records the V1 result and the later offline semantic correction
separately.

## Offline derivation

The R2 producer loads only the four compressed primary files and never calls a
solver step. It regenerates all engineering outputs from the accepted primary
cycle and exact port-closure snapshots. Full-cycle species conservation is the
hard conservation identity:

`terminal inventory = initial inventory + external species exchange + internal species sources + residual`.

Gross positive transfer/exhaust crossings remain gross ledgers and are not
treated as mutually exclusive unique parcels. A bounded metric outside its
gross-crossing domain is `UNDEFINED` with a reason; no clipping or placeholder
is permitted. In the four R2 points, `TE` is undefined for this reason.

## Gate

Each point must be `PERIODIC_ENGINEERING_RESULT`, have a finite positive
thermodynamic state, pass mass/energy/species/partition conservation, pass fuel
availability and chemical-heat identity checks, and contain provenance-bearing
defined or explicitly undefined outputs. Plausibility warnings are retained
and do not override the hard gate.
