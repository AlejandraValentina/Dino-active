# Scavenging partition conservation v1

## Scope

This is an additive post-processing/accounting capability after the immutable
`ENGINE_PHYSICS_V1` terminal gate at `1ceaa86`. It does not reopen or
reclassify that gate and does not change `IntegratedEngine2T` physics.

## ADDED Requirements

### Requirement: Distinguish gross crossings from inventories

The capability MUST distinguish fresh air, fuel, residual and burned species.
`fresh_delivery_kg` and `fresh_short_circuit_kg` MUST retain their documented
gross positive crossing semantics; they MUST NOT be treated as unique-parcel
mass partitions. Exact transfer/exhaust closure snapshots MUST remain bound to
their event instants and species order.

#### Scenario: Gross crossings exceed a snapshot-based partition

- **WHEN** gross delivered or short-circuit ledgers cannot form a unique-mass
  partition with a closure inventory
- **THEN** the gross partition identity is marked not applicable, bounded
  derived metrics are `UNDEFINED` with a reason when outside their domain, and
  no clipping, normalization or residual absorption occurs.

### Requirement: Audit full-cycle species conservation

The corrected conservation identity MUST be evaluated per species as terminal
inventory minus initial inventory minus external species exchange minus internal
species sources. The result MUST be compared to the versioned tolerance and
MUST include burned species and fuel separately.

#### Scenario: Existing periodic primary is replayed

- **WHEN** a primary contains exact inventories, ledgers and closure snapshots
- **THEN** the full-cycle species residual is reported, the sampling instants
  are explicit, and the corrected partition record is auditable without a
  solver rerun.

### Requirement: Historical evidence remains immutable

The capability MUST write corrected offline records under a new versioned
evidence path and MUST preserve all `ENGINE_PHYSICS_V1` primaries, campaigns,
reviews and terminal status unchanged.

#### Scenario: Gate impact is evaluated

- **WHEN** corrected offline metrics are generated
- **THEN** they are evaluated only by `SCAVENGING_PARTITION_CONSERVATION_V1`
  and MUST NOT be relabeled as an `ENGINE_PHYSICS_V1` PASS.
