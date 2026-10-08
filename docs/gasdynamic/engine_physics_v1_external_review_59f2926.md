# Independent external review receipt — ENGINE_PHYSICS_V1

Review source: independent review supplied by the scientific owner, auditing
HEAD `59f2926` on 2026-10-07. This receipt is a durable provenance artifact;
it does not alter the historical campaign, outputs, solver, fixtures, or
review conclusions.

## Verdict

`ENGINE_PHYSICS_V1_FAIL`

`FULL_RPM_SWEEP_V1_CAN_START = NO`

The four historical points remain `NO_CONVERGENCE_WITHIN_HORIZON @ 12 cycles`.
The prior PASS is reclassified as recoverable review. Recovery is limited to
the ENGINE_PHYSICS_V1 output adapter, plausibility gates, and operating-point
workflow. No new physics, campaign expansion, FULL_RPM_SWEEP_V1, KT100, P9,
or rerun of the original 12-cycle campaign is authorized.

## Findings preserved from the external review

- The adapter must use primary `fresh_delivery_kg`; absent dependencies must
  remain `UNDEFINED` and must never receive a physical zero fallback.
- AFR, phi, and lambda require explicit undefined semantics when fuel or air is
  unavailable.
- Scavenging must use exact `port_closure_snapshots`, with species order
  `fresh_air/fuel/residual/burned`, explicit DR/TE/SE/CE/residual/short-circuit
  definitions, and a hard partition-conservation gate without clipping.
- Fuel burned must come from primary `fuel_burned_kg`; heat/LHV reconstruction
  is only a cross-check. Chemistry, energy, species, partition, and dependency
  inconsistencies require hard invalid classification.
- Engineering outputs are usable only after `PERIOD_1` or `PERIOD_2`.
  Earlier values are `TRANSIENT_DIAGNOSTIC` and must not be presented as a
  regime operating point.
- A recovery horizon must be preregistered from physical residence time before
  execution, with detector thresholds and convergence streak unchanged. A
  compatible warm start may be investigated without changing physics.
- Only one versioned recovery campaign may follow the repair. If any point
  fails to converge, that result is accepted and no PASS-seeking rerun follows.

## Required recovery evidence

Implement and test the versioned output/gate contract; regenerate the existing
four points offline under a new evidence path while retaining the historical
outputs; preregister the operating-point contract and physical horizon before
the recovery campaign; then evaluate only the recovery gate. The historical
review and all historical evidence remain immutable.

This durable receipt is linked to the recovery work by the status log and the
subsequent recovery preregistration commit. The full user-supplied review text
remains the source record associated with this receipt.
