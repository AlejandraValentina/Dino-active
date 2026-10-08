## ADDED Requirements

### Requirement: isolated duct geometry
The foundation SHALL represent ordered intake and transfer geometries with exact frustum volumes and shared mesh faces.

#### Scenario: build mesh
- **WHEN** a valid segment list and target spacing are supplied
- **THEN** the shared mesh contains positive volumes and shared faces

### Requirement: bidirectional interfaces
The foundation SHALL expose forward flow, zero crossing and backflow through existing Riemann coupling without direction clamps.

#### Scenario: closed port
- **WHEN** interface area is zero
- **THEN** mass, energy and species fluxes are exactly zero

### Requirement: governance
Integrated periodic engine evidence SHALL remain CONDITIONAL_ON_P4.

#### Scenario: isolated verification
- **WHEN** P5-A fixtures run without the integrated engine
- **THEN** their result is independent of P4 and no P4 PASS is inferred

## ADDED Requirements

### Requirement: integrated conditional topology
P5-B SHALL compose atmosphere, intake, crankcase, two transfer ducts and cylinder without connecting exhaust.

#### Scenario: isolated integrated fixture
- **WHEN** the short fixture is executed
- **THEN** interface traces and stage timing are recorded without inferring P4 acceptance

### Requirement: closed-volume work fixture
P5-B SHALL provide a closed-volume fixture that uses the contractual chamber
volume-rate mechanism with every physical port closed and without heat or
combustion sources.

#### Scenario: closed-volume compression and expansion
- **WHEN** the fixture advances with moving crankcase and cylinder volumes
- **THEN** mass and passive-species inventories remain constant, external
  mass/species/energy fluxes are zero, and system energy changes only by the
  stage-consistent integrated `-p*dV/dt` work; compression work is positive,
  expansion work is negative, and chamber states remain admissible

### Requirement: finite single chamber-to-duct fixture

P5-B SHALL provide an externally closed finite fixture composed of one fixed-volume
0-D chamber and a finite 1-D duct using the existing gas1d Riemann interface and
SSPRK2 stage convention. The shared interface flux SHALL update the chamber and
the adjacent duct cell with opposite signs; no exhaust, heat release, or external
boundary is part of this fixture.

#### Scenario: closed single 0D↔1D transfer

- **WHEN** the finite fixture advances through both SSPRK2 stages
- **THEN** global mass, total energy, and passive-species inventories are conserved,
  all chamber and duct states remain admissible, and the fixed chamber volume is unchanged

### Requirement: one-transfer closed subsystem

P5-B SHALL provide an isolated subsystem consisting of one crankcase 0-D chamber,
one finite constant-area transfer duct, and one cylinder 0-D chamber. Each of the
two physical chamber/duct interfaces SHALL be solved exactly once per SSPRK2 stage,
with the same extensive flux reused with opposite signs in the connected duct cell
and chamber. Both chambers SHALL use the contractual volume-rate mechanism; no
intake, exhaust, heat release, combustion, or P6 species semantics are part of this
fixture.

#### Scenario: isolated crankcase-to-cylinder transfer

- **WHEN** the two-stage fixture advances with open or closed transfer interfaces
- **THEN** global mass and passive-species inventories conserve with no external
  boundary, energy changes only by the two integrated `-p*dV/dt` chamber work terms,
  closed interfaces have exact zero flux, and every stage state is admissible.
  The fixture SHALL expose both the SSPRK2 stage-quadrature (applied) inventory
  deltas and final-stored-state deltas; the strict energy conservation gate SHALL
  apply to the applied delta, while stored-state roundoff SHALL be reported and
  checked against a documented machine-roundoff bound.

### Requirement: two-transfer closed subsystem

P5-B SHALL provide an isolated subsystem composed of one crankcase 0-D chamber,
one cylinder 0-D chamber, and two independent finite transfer ducts. Each of the
four chamber/duct interfaces SHALL be solved exactly once per SSPRK2 stage, and
the same extensive flux SHALL be reused with opposite signs in the adjacent duct
cell and chamber. Chamber RHS contributions from both ducts SHALL be summed before
each chamber stage update. No intake, atmosphere, exhaust, heat, combustion,
periodicity, or P6 semantics are part of this fixture.

#### Scenario: symmetric and asymmetric two-transfer verification

- **WHEN** the two-stage fixture advances with identical, then intentionally
  different, transfer initial states/geometries
- **THEN** symmetric per-transfer traces match within deterministic tolerance;
  asymmetric traces remain distinct without state/array/history/ledger aliasing;
  global mass and passive-species inventories conserve; energy changes only by
  crankcase and cylinder `-p*dV/dt` work; individually closed interfaces have
  exact zero flux; duct interiors evolve; every stage is admissible and
  stage-consistent. The strict energy gate SHALL use applied SSPRK2 quadrature,
  with final stored-state roundoff independently reported and bounded.

### Requirement: complete finite P5-B topology

P5-B SHALL provide one global conservative SSPRK2 fixture composed of an
atmosphere boundary, a finite intake duct, one crankcase chamber, two
independent finite transfer ducts, and one cylinder chamber. Every stage SHALL
reevaluate the port laws, chamber states, interface Riemann solves, duct
interior fluxes, chamber RHSs, and contractual volume work from the same stage
state. The atmosphere/intake far boundary SHALL be the only external boundary;
all other interface fluxes SHALL be reused with opposite signs on connected
stored components.

#### Scenario: complete finite topology

- **WHEN** the fixture advances through closed and open intake/transfer angles
- **THEN** all three duct families evolve as stored finite-volume states,
  closed physical ports have exact zero mass/energy/species flux, the five
  physical interfaces are solved once per stage, global mass/species balance
  equals the stage-consistent atmospheric integral, and energy balance equals
  atmospheric energy plus both integrated `-p*dV/dt` work terms. Stored-state
  subtraction roundoff SHALL be reported separately from the strict applied
  SSPRK2 quadrature gate; no periodicity or P4 acceptance is inferred.
