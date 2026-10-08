# Design: REFERENCE_ENGINE_HYBRID_HARNESS_V1

## Preregistration — frozen before any KT100 V2 run

The machine-readable contract is
[`reference_periodic_convergence_v1.json`](../../../docs/gasdynamic/reference_periodic_convergence_v1.json).
Its SHA-256 is frozen by the commit that records this document, before KT100
campaign execution. It defines `REFERENCE_PERIODIC_CONVERGENCE_V1`, not P8 and
not contractual E13.

### Convergence decision

Reuse the numeric limits already used by the accepted E13-R1 implementation:
0.5% for work, pressure, temperature and velocity-type observables, and 0.2%
for stored inventories and explicitly listed cycle-integrated quantities. This is a pre-campaign
engineering reproducibility criterion, not a new accuracy claim. Unlike E13,
the harness has no mesh-bound pressure sensors: its observable vector uses
physical terminal quantities for both chambers and each duct cell, four global
species inventories, cylinder work, per-cycle fresh delivery, short-circuit
and P7 heat. Each comparison reports every component and every applicable
threshold; all must pass. The raw conservative state vectors are always
persisted and compared exactly for restart/replay, but are not an ambiguous
convergence metric.

For positive scalar states, `d(a,b)=abs(a-b)/max(abs(a),abs(b))`. Chamber mass
and total energy, and each duct-cell mass and total energy use 0.002 relative.
Chamber and duct-cell pressure and temperature use 0.005 relative. Each duct
cell species mass is divided by that cell's total mass and compared with a
0.002 absolute fraction difference. Duct velocity is divided by local sound
speed and compared with a 0.005 absolute difference. Global species inventory
and P7 burned-species increment use the total system mass at the start of the
later-indexed compared cycle as denominator (0.002). Fresh delivery and
short-circuit increments use that same cycle-start total gas mass (0.002), and
P7 heat increments use total gas energy at the start of the later-indexed
cycle (0.002).
The only P7 species-ledger convergence observable is the per-cycle
`burned_produced` increment, normalized by cycle-start total gas mass (0.002);
remaining P7 ledger fields are audit-only. Work uses
`max(1 J, abs(a), abs(b))`, matching the
existing E13 work floor (0.005). A zero/zero pair gives zero; non-finite,
negative, missing, shape-mismatched or identity-mismatched inputs are INVALID,
never PASS. No epsilon is introduced.

Period-1 compares adjacent complete cycles and takes precedence. Period-2
compares cycles two apart, with separate A/B streaks anchored to the first
cycle; either branch FAIL/INVALID resets only its own streak. Both branch
streaks and the lag-1 streak require three consecutive valid PASS comparisons.
The fixed maximum is 400 complete cycles. It cannot be raised after observing a
case.

### Physics/event orchestration

The current product stack supports one 2T cylinder, one intake, two transfer
paths/ports and one exhaust path. Configuration outside that topology is
rejected. Its atmospheric P5-C boundary is fixed at 101325 Pa / 300 K; P6
assigns fresh-air-only donor composition. The P4 ideal-port flux API accepts
effective geometry but no configurable discharge coefficient. The harness
does not silently consume legacy 0D coefficients: V2 records this product-model
limitation as a `MODEL_FORM_DIFFERENCE` from V1. A future case requiring a
different atmospheric boundary or active discharge coefficients cannot run
under this harness without an independently authorized product capability.

The harness constructs `Model` geometry and the existing `IntegratedP5C`,
`P6IntegratedSystem`, EOS, Riemann fluxes, CFL step and P7 source. It supplies
finite meshes/states from a validated JSON config. Cycles use one normalized
360-degree phase interval. P6/P7 internally recognize their existing event
window at scheduler angles 350–390 degrees. Configured physical event phase
`phi` is limited to 30–350° so the fixed 40° event fits wholly inside the
physical cycle window 30–390°. The harness adds offset `350 - phi` to all
scheduler angles, cycle boundaries and checkpoints, and wraps the geometry
callback with the inverse offset. After each full physical revolution, it
rebases the scheduler to [30+offset,390+offset] without changing gas/species
state; elapsed time remains a separate monotone counter. Thus the product source sees its
unchanged 350–390 window while port geometry continues to see the configured
physical crank angle. This adapter changes no physical geometry or P7 equations
and is not the historical P7 absolute 350–390° campaign gate. The existing P7
duration (40 degrees) and heat per burned mass remain fixed product
capabilities; the harness rejects configs requesting different values. Only
`burned_produced` and heat increments enter P7 convergence; all other P7
event/ledger fields are primary audit evidence.

The harness does not import P8 anchors/windows/auditor, does not claim E13
conformance, and does not change existing P4–P9 contracts. Any required
capability absent from the product modules is a hard stop rather than a new
physical equation.

### Evidence and binding

Primary evidence is a deterministic gzip JSON stream by campaign/run and cycle.
Every accepted endpoint binds angle/time/cycle identity, gas conservative
state, species by component/cell, component totals, boundary exchanges, P7
event/source ledger, fresh delivery, short-circuit, work, CFL and admissibility.
The manifest binds configuration bytes and SHA-256 of product component source
files (P4 exhaust port, P5-C/P5-B, P6, P7, gas1d EOS/solver/Riemann/boundary,
checkpoint, and the source of reused E13 numeric thresholds). P8 is explicitly
excluded.

An offline auditor independently validates finite numeric types and hashes,
rebuilds cycle ledgers and convergence from primary records, checks each
trajectory's last endpoint against its cycle terminal, then checks restart and
replay state/ledger equality before summaries. Stored PASS fields and digest
equality alone are insufficient.

## First client

KT100 V2 derives documented values only from the preserved V1 source manifest.
Missing transfer duct, discretization and state fields remain individually
`SYNTHETIC_ASSUMPTION` with reason and sensitivity. RPM points remain
`EXPLORATORY_SYNTHETIC_OPERATING_POINTS`; V1 outputs are comparison context
only (`MODEL_FORM_DIFFERENCE`). Sensitivity runs begin only after the base
campaign is complete. Experimental and predictive claims remain prohibited.
