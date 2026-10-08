# Design

## Production boundary

`motorsim.integrated_2t.IntegratedEngine2T` is the sole production simulation
path for this phase. Reference-harness and P0–P8 paths are regression-only.
Every result records the configuration, fixture, fuel, detector, solver and
auditor identities and their SHA-256 values.

## Versioned models

- `STANDARD_V1` port discharge coefficients are explicit per port and sense.
- `SCAVENGING_MODEL_V1` is a bounded two-zone/profile model with mass, energy
  and species closure; DR, TE, SE and CE are undefined when their denominators
  or validity conditions are not met.
- `SYNTHETIC_GASOLINE_V1` is a frozen synthetic surrogate with explicit LHV,
  stoichiometric AFR, composition, density where needed, provenance, version
  and content hash. It is not a commercial gasoline identification.
- `IDEAL_FUEL_METERING` uses target AFR/equivalence ratio and reports its
  assumptions. Combustion is fuel-coupled and oxygen-limited: zero fuel gives
  zero heat, unburned fuel remains in the ledger, and state-derived AFR/phi are
  never replaced by placeholders.
- Cylinder, duct and wall heat transfer are explicit `STANDARD_V1` models.
  Mechanical losses use a documented FMEP model with no crankcase double count.

## Classification

`HARD_PHYSICAL_INVALID` is terminal for a point. Plausibility deviations are
`PLAUSIBILITY_WARNING` only when the physical state and conservation contract
remain valid and the explanation is recorded. Undefined quantities are
serialized as undefined with reason, never as fabricated zeroes.

## Evidence

The phase preregistration freezes the four operating points and model hashes
before execution. A final artifact contains convergence, runtime, state
outputs, performance outputs, conservation, gate/warning classifications and
all provenance. No next phase is implied by this change.

