# KT100 Reference Case V1

## ADDED Requirements

### Requirement: provenance separation

Every parameter in `KT100_REFERENCE_CASE_V1` and `KT100_MODEL_FIXTURE_V1` MUST
carry one of `DOCUMENTED`, `DERIVED_FROM_DOCUMENTED`, `SYNTHETIC_ASSUMPTION`,
or `UNKNOWN`, plus value, units, source, source location and notes. A parameter
marked `UNKNOWN` MUST NOT be emitted as a real-engine specification. Every
synthetic assumption MUST state its value, units, reason, expected sensitivity,
result impact and conceptual origin. The documentary case MUST remain distinct
from the runnable fixture.

#### Scenario: unknown and synthetic values remain explicit

- **WHEN** a reader or fixture generator loads the case manifest
- **THEN** undocumented real-engine values remain `UNKNOWN`
- **AND** fixture completion values remain `SYNTHETIC_ASSUMPTION`
- **AND** no unknown or synthetic value is represented as a Yamaha specification

### Requirement: selected variant and independent geometry

The reference MUST identify one KT100 variant, year/context and source without
mixing specifications of other KT100 variants. Geometry MUST independently
derive displacement, piston area, swept volume, conditionally clearance volume,
crank radius, volume versus crank angle, mean piston speed by RPM, 2T cycle
frequency, and 2T indicated work-to-power conversion. Derived values MUST retain
their source inputs and assumptions.

#### Scenario: geometry is reproducible

- **WHEN** documented bore and stroke are evaluated
- **THEN** the computed displacement agrees with the documented rounded value
- **AND** geometry and unit-conversion tests reproduce the stored values

### Requirement: complete runnable fixture

`KT100_MODEL_FIXTURE_V1` MUST provide a complete, deterministic MotorSim
configuration for geometry, cylinder, crank-slider, crankcase, intake, transfer,
exhaust, prescribed combustion/source model, thermodynamics, boundaries and
solver. Each field MUST trace to its provenance entry. The fixture MUST be
separate from the reference record and MUST NOT modify solver physics to match
external output data.

#### Scenario: configuration is complete and deterministic

- **WHEN** the fixture is generated twice from the same manifest
- **THEN** both canonical configurations are byte-equivalent
- **AND** completeness, geometry, provenance and finite-value checks pass

### Requirement: exploratory numerical evidence

The bounded RPM study MUST state its selection rule and MUST NOT claim a Yamaha
operating range absent a variant-specific source. If the existing E13 periodic
qualification is technically executable, the study MUST use its unmodified
period-1/period-2 thresholds; otherwise the exact blocker and bounded evidence
MUST be recorded without substituting a transient result as periodic. Simulation
and sensitivity outputs MUST be identified as `KT100_REFERENCE_SIMULATION`,
synthetic and non-confirmatory. At least one small, preregistered sensitivity
must vary selected synthetic assumptions without calibration to outside data.

#### Scenario: no convergence or conservation result is hidden

- **WHEN** any study point fails or exhausts its fixed horizon
- **THEN** its status, cycles, balances, admissibility, CFL, restart and replay
  evidence are retained as failed or incomplete
- **AND** no threshold or input is adjusted after inspecting the output

### Requirement: P9 remains unchanged

This change MUST NOT edit the frozen P9 v1.0 specification, its preregistration
hash, P9 status, comparison pipeline, or P9 experimental/predictive claims. It
MUST NOT emit `P9_PASS`, `EXPERIMENTALLY_VALIDATED`, or
`PREDICTIVELY_VALIDATED`.

#### Scenario: reference work cannot advance P9

- **WHEN** the KT100 fixture or its campaign is generated
- **THEN** P9 remains `P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA`
- **AND** experimental validation remains `NOT_PERFORMED`
- **AND** predictive validation remains `NOT_CLAIMED`

## Hybrid fixture V2 continuation

### Requirement: V2 uses only contract-compatible existing capabilities

`KT100_HYBRID_MODEL_FIXTURE_V2` MUST remain distinct from V1 and preserve all
V1 documentation and artifacts. It MUST use the actual P5-C/P6/P7/P8/E13
implementations, identify every undocumented completion as
`SYNTHETIC_ASSUMPTION`, and MUST NOT change P4–P9 contracts or claim Yamaha
validation. If the frozen stack cannot provide the required topology, repeated
P7 event, E13 cycle convergence, restart/replay, and primary evidence together,
the work MUST stop before a campaign and record the precise blocker. A partial
configuration MUST NOT be called `KT100_HYBRID_MODEL_FIXTURE_V2_VERIFIED`.

#### Scenario: incompatible fixed P8/P7 behavior

- **WHEN** the existing P8 producer/auditor is fixed to another mechanical
  identity or cannot produce repeated P7 cycle evidence for E13
- **THEN** record the blocker and bounded preflight evidence
- **AND** do not alter P4–P9 contracts, calibrate assumptions, or claim V2
  verified, experimental, or predictive validity
