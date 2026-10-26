# Bounded stability/periodicity protocol — preparation, not execution

The two-revolution endpoint V2 run is transient; its cycle-2 source-bound replay
passes. Solver computation was 27.86 s for two revolutions; full replay/audit of
cycle 2 took 76.87 s. Do not infer a periodic power prediction from that timing.

## Scope and provenance

One fixed A9000 synthetic reference, 44 cells, unchanged endpoint V2/nozzle V2
configuration. Continue from the **native cycle-2 checkpoint of this same run**,
whose original initialization was independent/cold. This is same-simulation
continuation, not transfer from a different RPM, warm start, X30, or SPV1 recovery.
Keep the original run and all hashes; give the additional invocation its own
identity/provenance linking the original checkpoint, configuration and actual
solver dependency hashes. Reject any source/configuration mismatch rather than
rebinding it. V3 remains frozen.

## Proposed finite resource budget

- At most 10 additional complete cycles (through cycle 12), 240 s total wall
  budget, with an internal 150 s numerical-work admission limit and 16 MiB
  estimated output plus the existing 2 GiB storage reserve.
- Native checkpoint, cumulative ledgers, detector state and per-cycle comparison
  at every complete revolution. Exact accepted/rejected-step recipe throughout.
  Preserve a mid-cycle FAST terminal state plus recipe without labelling it native.
- Original time step/event schedule, CFL, admissibility, physics, geometry and
  detector thresholds. No automatic enlargement or restart from zero.
- Initial detector history must be reconstructed from the same source-bound
  prefix, explicitly distinguishing checkpoint-derived L1 from audited primary
  evidence. Compare all states/species/inventories/work; retain every cycle's
  failed metrics and maximum normalized discrepancy.

## Decision limits and technical prerequisite

This proposal can test stable continuation and progress of the transient.
If no period is detected, report `TRANSIENT_AT_BUDGET`; do not predict how many
more cycles would suffice from two initial cycles. If the unchanged detector
identifies a candidate period, stop and checkpoint it. **A checkpoint-only period
is not an admitted audited periodic result**: its requisite cycle primaries must
still be regenerated from the exact recipes and verified, with their own finite
budget. One replay fits the reserved time approximately; a complete streak may
require more. Do not promise complete L2 periodicity acceptance inside this pilot.

Before implementing/executing this pilot, close the endpoint candidate regression
and assess its spatial/time error with a bounded plan. The measured inlet
component candidate is not an engine convergence reference. Numerical convergence
of the synthetic point and real-engine predictive validation remain distinct.
This document does not launch a run, alter a gate or authorize an RPM campaign.
