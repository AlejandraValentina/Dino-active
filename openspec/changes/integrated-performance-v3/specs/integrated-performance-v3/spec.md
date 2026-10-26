## Purpose

Determine whether a periodic solution at one RPM can initialize a new nearby-RPM operating point and materially reduce cycles to periodicity, while preserving the physical state and existing solver/periodicity contracts.

## Scope

- Inspect A9000 and A10000 periodic source configurations, run manifests, results and complete-cycle checkpoints.
- Permit only same-variant, same-engine transfers whose geometry, topology, discretization, EOS, species, boundaries and solver controls match; RPM and its explicitly configured RPM-dependent valve control may differ.
- Construct a new execution identity from the target operating point and transferred conservative state. Bind the source run/result/checkpoint hashes and provenance.
- Transfer gas conserved state (chamber mass/internal energy/species; duct conservative variables/species; network-volume mass/energy/species). Preserve any supported dynamic component state only when its structural identity is compatible.
- Reset simulation clocks, cumulative run ledgers, temporal combustion-event history, trace and periodicity detector. Start a new run at the compatible cycle phase; never present this as a continuation/restart.
- Run at most one A10000 pilot from periodic A9000, at most 40 new cycles and 240 seconds, with complete-cycle checkpointing and no automatic extension.
- If periodicity is reached, compare physical outputs and conservation to the historical A10000 periodic result using existing contracts and justified tolerances; adopt/integrate only after a substantial measured gain.

## Exclusions

No solver equations, geometry, mesh, combustion, scavenging, CFL, periodicity thresholds, Desktop changes, full campaign, X30 work, new calibration or experimental-validation claim. Historical source artifacts remain unchanged.

## Acceptance

1. Source and target identities and hashes are verified; incompatibilities fail closed.
2. Transferred mass, energy and each species inventory are preserved within conversion roundoff; state is admissible under the target operating-point model.
3. The run has a new identity and source provenance; clocks, ledgers/events and detector are correctly reinitialized.
4. A single pilot respects both hard budgets and writes a complete-cycle checkpoint. It is never automatically extended.
5. A periodic pilot shows substantial cycle/time reduction and target-output equivalence within justified tolerances before coordinator integration; otherwise the approach is rejected or left explicitly inconclusive.
