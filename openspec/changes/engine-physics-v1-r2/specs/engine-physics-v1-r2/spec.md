# ENGINE_PHYSICS_V1_R2 Specification

This specification defines the superseding offline evaluation of the historical
`ENGINE_PHYSICS_V1` gate. It does not reopen or pass the historical gate.

## ADDED Requirements

### Requirement: historical result is preserved

The R2 evidence MUST state `ENGINE_PHYSICS_V1 = FAIL_TERMINAL` and MUST retain
the original evidence and exact gate semantics. It MUST identify R2 as a
superseding gate rather than a retroactive interpretation of V1.

#### Scenario: historical V1 remains terminal

- **WHEN** the R2 manifest is evaluated
- **THEN** it records V1 as `FAIL_TERMINAL` and does not modify V1 evidence

### Requirement: fixed primary inputs

The evaluation MUST consume exactly these existing periodic primary cycles:

| point | cycle |
|---|---:|
| A′3000 | 73 |
| A′4000 | 88 |
| B′3000 | 34 |
| B′4000 | 38 |

No solver execution, campaign, R3, KT100 campaign or full RPM sweep is allowed.

#### Scenario: replay uses existing primaries

- **WHEN** the R2 producer runs
- **THEN** it reads the four listed primary files and performs zero solver steps

### Requirement: corrected conservation semantics

The hard partition check MUST use the corrected four-species conservation
identity. Gross crossing ledgers MUST remain explicit and MUST NOT be forced
into a unique retained/short-circuit parcel identity. Out-of-domain bounded
metrics MUST be represented as `UNDEFINED` with an explicit reason.

#### Scenario: gross crossing is not a unique partition

- **WHEN** gross ledgers contain recrossings
- **THEN** partition is `NOT_APPLICABLE` and species closure is the hard identity

### Requirement: periodic engineering outputs

Every result MUST be derived from its accepted periodic cycle and MUST include
the complete contracted output set: trapped/delivered air and fuel, AFR,
lambda, phi, fuel burned/unburned, chemical heat, exhaust temperature, DR, TE,
SE, CE, residual/burned purity, work, IMEP, FMEP, BMEP, power, torque, ISFC
and BSFC. Every output MUST contain status, units, definition/version and
source provenance.

#### Scenario: periodic output provenance

- **WHEN** an output is persisted
- **THEN** its cycle, status, units, definition/version and source are present

### Requirement: hard physical gate

Each point MUST persist `HARD_PHYSICAL_GATE = PASS` or `FAIL` and check finite
positive thermodynamic state, mass/energy/species/partition conservation, no
fuel creation, fuel availability, chemical heat consistency, valid defined
efficiencies, absent-dependency semantics and absence of placeholders.

#### Scenario: hard gate result

- **WHEN** a point is evaluated
- **THEN** it has an explicit `HARD_PHYSICAL_GATE` result and detailed checks

### Requirement: review state

The administrative gate MUST remain under review.
Even when all four technical point gates pass, the R2 administrative result
MUST remain `REVIEW` until the independent task `EP-R2-EXTERNAL-REVIEW` is closed.
The implementation SHALL keep this review state durable.

#### Scenario: external review remains required

- **WHEN** all four offline technical checks pass
- **THEN** the administrative R2 result remains `REVIEW`
