# Engine physics v1 specification

## Scope

This is a new capability after the frozen R2 closure. It must not modify the
original v1.0 gate, the superseding R2 gate, their results, or their claims.

## ADDED Requirements

### Requirement: Single production core and versioned provenance

All phase points MUST execute through `IntegratedEngine2T` and MUST record
version/hash provenance for solver, detector, auditor, producer, configuration,
fixture, fuel, thresholds and each newly introduced model.

#### Scenario: Production path is identifiable

- **WHEN** a phase result is audited
- **THEN** it names the integrated production core and every bound version/hash
  and does not present reference-harness output as new production evidence.

### Requirement: Explicit fuel and combustion closure

The phase MUST use a frozen `SYNTHETIC_GASOLINE_V1` snapshot and ideal metering
with explicit target AFR/phi. Combustion MUST conserve the fuel/species/energy
ledger, limit burning by available oxygen, retain unburned fuel, and produce
zero heat when fuel is zero.

#### Scenario: Fuel state is insufficient or oxygen limited

- **WHEN** fuel or oxygen is unavailable
- **THEN** heat and burned fuel are limited by the actual state, unburned fuel
  remains reported, and AFR/phi are undefined with a reason when a denominator
  is zero.

### Requirement: Scavenging and engineering models are bounded

`SCAVENGING_MODEL_V1`, port coefficients, heat transfer and FMEP MUST be
explicitly versioned with provenance and domain checks. DR, TE, SE and CE MUST
be undefined rather than fabricated when invalid. Mechanical losses MUST be
applied once and expose IMEP, FMEP, BMEP, torque, power and SFC definitions.

#### Scenario: A model leaves its validity domain

- **WHEN** a denominator, state, coefficient or domain condition is invalid
- **THEN** the point is classified according to the hard physical gate and the
  affected derived quantity is explicitly undefined; no placeholder value is
  emitted.

### Requirement: Four-point phase evidence

Two materially distinct synthetic configurations MUST each run at two distinct
RPM points through the same production core. Each point MUST have periodicity
classification, runtime, conservation receipt, hard-gate result, warnings and
engineering outputs with units and provenance.

#### Scenario: Phase run completes

- **WHEN** all four points are evaluated
- **THEN** a durable manifest binds the four results to the preregistration,
  model hashes and evidence files, and the phase gate is evaluated only from
  those results.

### Requirement: Historical closure remains immutable

This change MUST NOT alter or reinterpret R2 closure artifacts, P0–P8 frozen
contracts, KT100 evidence, or experimental/P9 status.

#### Scenario: Baseline is compared

- **WHEN** the phase is reviewed against `1a58b2a`
- **THEN** the baseline remains the frozen R2 reference and any new capability
  is identified as ENGINE_PHYSICS_V1 evidence only.

### Requirement: Contract-correct engineering output adapter

The V2 adapter MUST consume primary `fresh_delivery_kg`, primary
`fuel_burned_kg`, and exact `port_closure_snapshots` with species order
`fresh_air`, `fuel`, `residual`, `burned`. Missing or invalid dependencies MUST
remain explicitly undefined and MUST produce a hard physical gate failure when
the dependent output is required. Partition conservation and the fuel heat
identity MUST be independently checked; derived heat MUST NOT replace the
primary burned-fuel ledger.

#### Scenario: Historical transient primary is regenerated offline

- **WHEN** a 12-cycle primary is evaluated with `NO_CONVERGENCE_WITHIN_HORIZON`
- **THEN** corrected outputs are written under a new versioned evidence path,
  retain `TRANSIENT_DIAGNOSTIC` status, and are not usable as a periodic
  engineering operating point.

### Requirement: Periodic operating-point eligibility

Engineering regime outputs MUST be marked usable only after the real
`PeriodicDetectorV2` returns `PERIOD_1` or `PERIOD_2`. `NOT_EVALUATED`,
`NO_CONVERGENCE_WITHIN_HORIZON`, and numerical or physical failures MUST
produce diagnostics only and MUST NOT be promoted to a regime result.

#### Scenario: Detector has not accepted an operating point

- **WHEN** an adapter receives any non-periodic status
- **THEN** every engineering output carries `NOT_USABLE_UNTIL_PERIODIC` and
  the operating point carries `TRANSIENT_DIAGNOSTIC`.
