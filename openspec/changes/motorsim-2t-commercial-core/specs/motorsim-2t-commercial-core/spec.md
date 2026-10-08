# Requirements

## ADDED Requirements

### Requirement: Preserve historical scientific contracts

The program MUST preserve historical P4–P8 records and the frozen P9 contract
byte-for-byte unless a later explicit scientific authorization creates a new
contract. New capabilities MUST use separate schemas and MUST NOT claim
experimental or predictive validation from synthetic cases.

#### Scenario: New capability uses a separate contract

- **WHEN** a new 2T component or metric is added
- **THEN** its behavior and evidence are versioned independently, with source
  provenance and no retroactive changes to P4–P9 results.

### Requirement: Traceable configurable two-stroke engine

The product MUST progressively support a configurable single-cylinder 2T engine
with gas exchange, four-species transport, scavenging, combustion, heat transfer,
crankcase dynamics, mechanical losses, fuel accounting, performance outputs,
checkpoint/restart/replay, and auditable primary evidence. Each material
parameter MUST identify its provenance. The program MUST NOT declare
`MOTORSIM_2T_COMMERCIAL_CORE_READY` until all required subsystems are integrated
and verified together.

#### Scenario: Incomplete capability cannot pass the product gate

- **WHEN** a subsystem has only unit or isolated fixture coverage
- **THEN** its phase may be recorded complete at its own scope but the overall
      commercial-core readiness remains not ready.

### Requirement: Deterministic integrated-engine configuration reconstruction

The integrated 2T engine MUST expose a versioned JSON-safe constructor
configuration and a factory that reconstructs supported existing engines
without caller geometry code. Configuration V1 is limited to setups whose
stage geometry is fully resolved by the existing slider-crank chamber model
and generic 2T port binding. It MUST preserve exact initial primitive states,
four-species inventories, meshes, boundary/EOS parameters, finite network
endpoint volumes, and configured existing reed, thermal, powervalve, and
prescribed-combustion inputs. Unsupported callback-dependent geometry MUST be
rejected rather than silently replaced or labeled reproducible. The factory
MUST produce the same canonical configuration identity and preserve existing
checkpoint restore/replay behavior.
Mutable live configuration that drifts after construction MUST be rejected
before a step, checkpoint operation, or configuration export can rely on its
stale identity.

#### Scenario: Supported configuration rebuilds deterministic engine state

- **WHEN** a supported engine configuration is encoded as canonical JSON and
  rebuilt without an external geometry callback
- **THEN** its configuration identity and initial physical/species snapshot
  MUST match exactly, and a restored checkpoint MUST replay the next accepted
  step exactly.

#### Scenario: Unsupported arbitrary geometry is not serialized as reproducible

- **WHEN** explicit slider-crank geometry or generic port binding is absent, or
  the configuration schema/geometry contract is malformed
- **THEN** configuration export or reconstruction MUST fail explicitly.

### Requirement: Generic engine topology uses one stage-coherent conservative state

The integrated 2T engine MUST keep cylinder, crankcase, intake, every named
transfer route, exhaust and their four extensive species masses in one
checkpointable state. A global SSPRK2 stage MUST resolve each face flux once
from that stage state and apply equal-and-opposite mass and energy increments
to its connected components. Species flux MUST use the actual donor selected
by the sign of that same mass flux; no independent legacy scalar may be
advanced as authoritative species state. Each accepted step MUST preserve
admissibility and record both stage states, interface fluxes, external
exchange, work and CFL. A checkpoint MUST bind mesh, topology, EOS, boundary,
geometry and initial-state identities, and restore atomically only when those
identities match. Internal ledgers MUST independently reconcile total mass,
energy and each species against external exchange and volume work. Readiness
remains unavailable until combustion, thermal, reed, scavenging, mechanics,
fuel and evidence collection are also verified on integrated fixtures.

When configured, an existing quasi-static reed model MUST resolve effective
intake area from the same stage's duct and crankcase pressures. A checkpoint
MUST reject wrapped/unwrapped angle disagreement and chamber volumes that do
not match the configured geometry at the restored angle. The explicit geometry
identity remains a caller-declared binding; the runtime volume check is an
additional state-consistency gate.

An existing `ExpansionChamber.mesh()` MAY be bound as the exhaust path mesh;
its section areas, face fluxes, four-species transport, and external boundary
exchange MUST then participate in both common SSPRK2 stages without modifying
the historical expansion-chamber or P5/P6 solvers.

The integrated geometry adapter MUST map each generic port duct to exactly one
named integrated path with a matching role, sum apertures on that route, and
resolve an existing powervalve roof at the current stage RPM before evaluating
main-exhaust area. Its binding and RPM policy MUST participate in restart
identity. The path map MUST be an immutable copy after construction so later
caller mutation cannot change stage routing under a stale configuration hash.
The current `MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V2` product topology supports
exactly one intake path, at least three transfer paths, and exactly one exhaust
path. Other role cardinalities MUST be rejected explicitly; changing these
limits requires a new configuration schema. Output collection MUST resolve
paths by their declared roles, not by literal path identifiers.
Internal duct species fluxes MUST receive adjacent cell states in geometric
left/right order and select the donor exactly once from the signed shared gas
mass flux; negative flux MUST use the right-cell composition.
When configured with the existing `CrankcaseGeometry` V2 and a cylinder
compression ratio, the integrated engine MUST derive crankcase and cylinder
volumes plus their opposite slider-crank volume rates at each SSPRK2 stage's
angle and RPM. The stage gas-energy RHS MUST include each chamber's `-p dV/dt`
work exactly once, and the geometry configuration MUST participate in restart
identity.

When configured with the existing prescribed P7 event and an ignition angle,
the integrated engine MUST capture the cylinder's actual four-species masses at
that angle and add P7 species conversion and prescribed heat to the same
cylinder RHS at both SSPRK2 stages. The source MUST use the existing fixed
40-degree P7 event and `Q_F` contract without adding chemistry or inferring fuel
properties. The global species ledger MUST distinguish this internal source
from external species flow, and the energy ledger MUST count P7 heat exactly
once. The checkpoint MUST preserve active/completed event ledgers and bind the
configured ignition angle. With P7 unconfigured, no combustion source may be
applied. A step that crosses an ignition or event-end boundary MUST be rejected
so callers can align accepted integration steps to the prescribed event.

#### Scenario: Three or more transfer routes share stage fluxes

- **WHEN** an engine topology has named primary, secondary and boost routes
- **THEN** each route participates in the same two SSPRK2 stages, each interface
  uses one shared Riemann flux, and every species follows the actual donor for
  forward or reverse flow.

#### Scenario: Reject inadmissible CFL or mismatched restart

- **WHEN** a proposed step exceeds its configured CFL bound or a checkpoint has
  a different mesh, topology, boundary, geometry or initial-state identity
- **THEN** the state remains unchanged and the step/checkpoint is rejected.

#### Scenario: Static reed and chamber limits are stage based

- **WHEN** the inlet reed is configured or a connected chamber has gross outward
  mass flux
- **THEN** reed area is resolved from that stage's pressure state, chamber
  depletion participates in the accepted CFL gate, and the same shared flux
  updates chamber, duct, species and global ledgers.

#### Scenario: Expansion chamber mesh participates in integrated exhaust

- **WHEN** an existing multi-section `ExpansionChamber` mesh is bound to the
  exhaust route
- **THEN** every section cell and face is advanced in both global SSPRK2
  stages, with species transport and external exchange in the integrated
  ledgers.

#### Scenario: Generic port and powervalve geometry participates in a stage

- **WHEN** every generic port duct is mapped to a matching integrated path and
  an exhaust port has an existing powervalve map
- **THEN** the stage resolves intake, each transfer route, and exhaust areas
  from the configured angle and RPM, and a mismatched geometry/RPM binding
  cannot restore a checkpoint.

#### Scenario: Reverse internal flow transports the right-cell composition

- **WHEN** the integrated finite-volume mass flux between adjacent duct cells
  is negative in either SSPRK2 stage
- **THEN** the four species flux MUST be the shared negative mass flux times
  the normalized right-cell species composition, without a second donor
  selection based on already reordered states.

#### Scenario: Existing slider-crank volumes drive both chamber stages

- **WHEN** an engine uses `CrankcaseGeometry` V2 and a finite cylinder
  compression ratio
- **THEN** both chamber volumes and volume rates are resolved from the same
  stage angle/RPM, the cylinder and crankcase swept-volume rates are opposite,
  and the resulting moving-volume step preserves the global mass/energy
      ledger with `-p dV/dt` included once per stage.

#### Scenario: Prescribed P7 conversion and heat share the integrated stages

- **WHEN** an integrated engine has P7 configured and an accepted step lies
  within one aligned prescribed event
- **THEN** each stage applies the existing captured-species P7 source to the
  cylinder species and energy RHS, and checkpoint/restart reproduces both
  source histories and their global ledgers without changing total gas mass.

#### Scenario: JSON checkpoint restores all accepted physical history

- **WHEN** the full engine checkpoint is serialized to JSON and restored under
  the same configuration
- **THEN** the conservative state, four species, angle/time/cycle, ledgers,
  accepted-step trace and replay trajectory continue identically.

### Requirement: Evidence and conservation for stateful components

New components that exchange mass, energy, or species MUST participate in
appropriate local and global ledgers, preserve admissibility, and provide
auditable evidence. Stateful capabilities MUST test serialization, restart, and
deterministic replay where applicable. Auditors MUST recompute claims from
primary evidence rather than trust stored PASS summaries.

#### Scenario: Invalid evidence is rejected

- **WHEN** evidence has missing fields, invalid numerics, identity mismatch, or
  inconsistent primary-to-summary values
- **THEN** audit returns a failure/invalid state without promoting a stored PASS.

### Requirement: Independent phases continue around local blockers

The program MUST classify blocked phases precisely and continue any later phase
whose inputs and acceptance do not depend on the blocker. A phase MUST stop only
for a real scientific decision or one of the global hard stops in the user
authorization.

#### Scenario: KT100 boundary blocker does not block an independent fixture

- **WHEN** a reference operating point fails at an existing boundary
- **THEN** the receipt remains unchanged while independent analytic fixtures and
  component work may proceed without changing that boundary or its contract.

### Requirement: Versioned open-end plenum boundary
The system SHALL preserve `LEGACY_CHARACTERISTIC_V1` exactly for historical
reproduction and SHALL expose `OPEN_END_PLENUM_V2` as a separately selected,
synthetic, stationary large-plenum capability. The new capability SHALL keep
interior and reservoir entropy distinct across the contact, preserve reversal
continuity, use ambient pressure for subsonic outflow, limit both flow
directions at their ideal isentropic choking conditions, use reservoir
stagnation enthalpy for incoming energy, and use the actual mass donor for
species. It SHALL make the pressure force at the external face explicit. It
SHALL NOT infer a calibrated carburetor/Walbro WB40, `Cd`, restriction area, or
loss. Existing fixtures SHALL retain their recorded boundary selections.

#### Scenario: Contact-aware reversal with unequal entropy
- **WHEN** an interior state approaches zero boundary flow at ambient pressure
  with a temperature different from the stationary reservoir temperature
- **THEN** face pressure and normal velocity approach the same reversal state
- **AND** each side retains its own entropy and the zero-flow species flux is
  zero

#### Scenario: Choked external flow
- **WHEN** the prescribed pressure difference requests subsonic flow beyond
  the isentropic critical ratio
- **THEN** `OPEN_END_PLENUM_V2` returns the corresponding sonic limiting state
- **AND** does not silently exceed the ideal choked mass flux

#### Scenario: Historical and future boundary identities remain separate
- **WHEN** a caller requests `LEGACY_CHARACTERISTIC_V1` or `nonreflecting`
- **THEN** historical equations and receipts remain unchanged
- **AND** `RESTRICTED_NOZZLE_V1` is only a documented future interface requiring
  explicit `Cd`, area, and provenance, with no invented defaults
- **AND** no mass-flow inlet capability is introduced

#### Scenario: Synthetic provenance is visible
- **WHEN** `OPEN_END_PLENUM_V2` is selected
- **THEN** its ideal, lossless stationary-plenum assumptions are labeled
  `SYNTHETIC_ASSUMPTION`
- **AND** the result is not described as calibrated Walbro WB40 data

### Requirement: Generic two-stroke port geometry

The engine configuration MUST represent any positive number of individually
identified transfer windows (including primary, secondary, and boost roles),
multiple exhaust apertures (including auxiliary or bridged segments), a piston
port intake, explicit duct association, and positive finite discharge
coefficients. Rectangular piston-controlled area MUST reuse the existing
kinematics and use `Cd*w*max(0,min(h,x(theta)-top))`; piston-port intake MUST
reuse its documented skirt-window geometry and MUST remain bidirectional at the
flow interface. Powervalve-ready roof travel MUST be geometry metadata and MUST
not create an actuator model in this phase. Arbitrary effective-area profiles
MUST use explicit periodic angle-area knots and deterministic piecewise-linear
interpolation. Configurations MUST persist primary geometry and derived
effective-area profiles bound to the exact primary configuration. Existing
project JSON versions and historical port interpretation MUST remain readable
unchanged.

#### Scenario: Multiple transfer and exhaust apertures

- **WHEN** a configuration has two or more transfer apertures and multiple
  exhaust apertures associated with named ducts
- **THEN** each aperture retains its own role, timing, geometry, coefficient,
  and duct association, and the compiled profile reports each duct's summed
  effective area by crank angle.

#### Scenario: Profile is periodic and bound to geometry

- **WHEN** an explicit area profile is loaded or geometry is edited
- **THEN** profile knots cover 0–360°, endpoint area agrees exactly, derived
  samples are recomputed, and stale or modified derived-profile evidence is
  rejected.

#### Scenario: Generic port geometry V1 rejects zero discharge coefficient

- **WHEN** a geometrically valid port has a finite discharge coefficient of
  zero
- **THEN** V1 rejects the configuration; accepting a zero-flow coefficient
  requires a new geometry schema.

#### Scenario: Reverse flow through piston-port intake

- **WHEN** the connected flow reverses through an open piston-port window
- **THEN** the geometry continues to expose its open area; donor selection stays
  with the existing conservative flow interface and is not suppressed by a
  one-way intake flag.

### Requirement: Auditable two-stroke scavenging metrics

The engine MUST derive cycle scavenging metrics from four-species inventories,
fresh-delivery ledger, and direction-aware fresh short-circuit ledger without
altering P6 transport. Let `F=fresh_air+fuel`, `R=residual`, `M=sum(four
species)`, `Fdel=fresh delivered through transfers`, `Flost=fresh short circuit
through outward exhaust`, and `Mref=rho_ambient*Vdisplacement`. The outputs MUST
include: delivery ratio `Fdel/Mref`; trapping efficiency `Fret/Fdel`; scavenging
efficiency `Fret/Mexhaust_close`; charging efficiency `Fret/Mref`; trapping
ratio `Fdel/Fret`; fresh retained `Fret`; fresh lost `Flost`; residual fraction
`Rexhaust_close/Mexhaust_close`; purity at transfer close `Ftransfer_close/
Mtransfer_close`; purity at exhaust close `Fexhaust_close/Mexhaust_close`; and
short-circuit fraction `Flost/Fdel`. `Fret` is `Fexhaust_close`. Reference
displacement volume is `pi*bore^2*stroke/4` with SI conversion. Each zero
denominator MUST produce an explicit undefined result and reason; invalid or
nonfinite inputs MUST be rejected, never clipped to a plausible efficiency.
These are model diagnostics, not experimental claims.

#### Scenario: Analytical species ledger

- **WHEN** reference mass is 0.01 kg, fresh delivery is 0.012 kg, short circuit
  is 0.002 kg, transfer-close species are `[0.003,0.001,0.006,0]` kg, and
  exhaust-close species are `[0.004,0.001,0.004,0.001]` kg
- **THEN** delivery ratio is 1.2, trapping efficiency is 5/12, scavenging and
  charging efficiency are 0.5, trapping ratio is 2.4, residual fraction 0.4,
  transfer purity 0.4, exhaust purity 0.5, and short-circuit fraction 1/6.

#### Scenario: Zero denominator and reverse exhaust

- **WHEN** a ratio denominator is zero or an exhaust exchange is inward
- **THEN** the ratio is explicitly undefined when appropriate, and inward
  exhaust species do not increment fresh-short-circuit mass.

### Requirement: Configurable multi-petal reed intake

The engine MUST expose separate `STATIC_REED_V1` and `DYNAMIC_REED_V1` modes.
Every petal MUST identify its mass, effective pressure area, effective flow
width, spring stiffness, damping, lift stop, discharge coefficient, restitution,
and parameter provenance. Static mode MUST compute bounded equilibrium lift
from signed pressure differential and MUST block reverse flow. Dynamic mode MUST
advance petal position and velocity using the damped lumped-mass/spring equation
under the supplied pressure differential, enforce closed/open lift stops with
the configured restitution, and expose bidirectional transient flow through
the current open area; reverse pressure MUST drive closure but MUST NOT erase
area before the petal physically closes. Multiple petals MUST have independent
state and contribute summed area. Flow MUST reuse the existing gas-flow function
and MUST NOT alter global ledgers itself.

#### Scenario: Static reed opening and reverse protection

- **WHEN** forward differential is positive
- **THEN** static lift is the spring equilibrium clipped to `[0,lift_stop]` and
  effective area is coefficient × width × lift; reverse differential returns
  zero area/flow.

#### Scenario: Dynamic petal response

- **WHEN** the differential changes while a petal has nonzero velocity
- **THEN** the petal state advances deterministically from its previous
  position/velocity, respects the stops, and permits transient reverse flow only
  while its area remains open.

#### Scenario: Multi-petal and invalid configuration

- **WHEN** a reed bank contains multiple valid petals or any mass/stiffness/
  damping/area/provenance value is invalid
- **THEN** valid petal areas/states remain individually inspectable and malformed
  or nonfinite inputs are rejected without silently clipping parameters.

### Requirement: Expansion chamber reuses the quasi-1D solver

The engine MUST represent an expansion system as connected, provenance-bearing
conical sections for header, diffuser, belly, baffle cone, stinger, silencer,
tailpipe, or generic cones. Geometry MUST reuse the existing quasi-1D mesh and
MUST NOT add a parallel gas solver. The result adapter MUST derive pressure,
temperature, Mach, mass flow and characteristic speeds from actual solver
primitive states. A travelling-wave decomposition MUST identify its linear
small-perturbation base state and MUST NOT be represented as a nonlinear wave
solution. Reflection timing MUST be reported as a characteristic travel-time
estimate; amplitudes remain outputs of the gasdynamic solver.

#### Scenario: Build a continuous expansion assembly

- **WHEN** adjacent sections have matching endpoint diameters
- **THEN** they form a mesh using the existing frustum geometry; disconnected,
  nonfinite, or nonpositive sections are rejected.

#### Scenario: Map an actual 1D solution

- **WHEN** admissible primitive cells from the quasi-1D solver are provided
- **THEN** the adapter reports pressure, temperature, signed Mach, mass flow,
  and left/right characteristic speeds for every cell.

#### Scenario: Report travel-time limits

- **WHEN** a characteristic cannot travel toward a requested station because
  the base flow is supersonic in that direction
- **THEN** its travel-time estimate is explicitly unavailable and no reflected
  wave amplitude is fabricated.

### Requirement: Configurable prescribed-wall thermal ledger

Thermal configuration MUST represent cylinder wall, head, piston crown,
crankcase, transfer walls and exhaust walls as separately addressable surfaces.
Each configured surface MUST carry explicit area, heat-transfer coefficient,
provenance and either a fixed positive wall temperature or a bounded RPM/load
temperature map. `CONSTANT_H_V1` MUST calculate signed gas-to-wall heat as
`h*A*(Tgas-Twall)`. The cycle ledger MUST integrate complete, strictly ordered
crank-angle samples with the declared RPM and return signed energy per surface
and total. Map extrapolation, incomplete cycles, missing surfaces, and malformed
or nonfinite values MUST be rejected. The model MUST not silently select/fill
coefficients or alter the gas solver.

#### Scenario: Analytical fixed-wall cycle

- **WHEN** a fixed gas-wall temperature difference and explicit area, `h`, RPM,
  and complete cycle samples are supplied
- **THEN** the per-surface ledger equals the trapezoidal integral of
  `h*A*(Tgas-Twall)` over crank-angle time.

#### Scenario: Mapped prescribed wall temperature

- **WHEN** an RPM/load point lies inside an explicit map
- **THEN** bilinear interpolation supplies its temperature, while an out-of-map
  point is rejected rather than extrapolated.

### Requirement: Prescribed combustion progress V2

`COMBUSTION_MODEL_V2` MUST support one or two weighted Wiebe components with
explicit ignition timing, duration, shape parameters, component delay and
provenance. The model MUST expose normalized progress, derivative per crank
degree, configured combustion efficiency and CA10/CA50/CA90. Efficiency MUST
be an explicit scalar or bounded RPM/load map. The progress capability MUST
remain separate from P7 historical code. It MUST NOT infer fuel chemistry,
species conversion, stoichiometry, LHV or heat release.

#### Scenario: Single or double prescribed burn

- **WHEN** one or two valid Wiebe components and a supported operating point
  are evaluated
- **THEN** weighted progress is monotonic and bounded by configured efficiency,
  the three CA points are ordered, and the final progress equals efficiency.

#### Scenario: Zero efficiency and invalid operating point

- **WHEN** efficiency is zero or RPM/load lies outside its configured map
- **THEN** the burned fraction remains zero with undefined CA points, or the
  out-of-map request is rejected; no heat or chemistry output is fabricated.

### Requirement: Explicit two-stroke mechanical losses and brake metrics

Mechanical losses MUST be explicit nonnegative MEP terms with source class and
provenance; each term MUST use either a fixed value or bounded RPM/load map.
For the declared 2T 360-degree cycle, the model MUST derive indicated/brake
MEP, work, power and torque from the stated displacement, RPM and indicated
work. It MUST preserve negative brake output without clipping and MUST NOT fit
loss terms to desired performance.

#### Scenario: Convert indicated cycle work to brake output

- **WHEN** indicated work, total 2T displacement, RPM and explicit mechanical
  loss terms are supplied
- **THEN** loss work is `FMEP*Vd`, brake work is indicated work minus loss work,
  and power/torque follow the declared 360-degree cycle convention.

#### Scenario: Loss exceeds indicated work

- **WHEN** configured losses exceed indicated cycle work
- **THEN** negative brake work/power/torque remain visible and are flagged, not
  clipped to zero.

### Requirement: Explicit fuel, AFR and 2T SFC accounting

Fuel accounting MUST use explicit stoichiometric AFR, LHV and provenance. The
cycle input MUST distinguish delivered and trapped fresh-air/fuel masses,
explicit P6 species-ledger short circuit, and a bounded prescribed burned
fraction. Outputs MUST include delivered
and trapped AFR, equivalence ratio, fuel trapped/burned/unburned/short-circuited,
fuel flow, released-energy potential, indicated SFC and brake SFC when brake
power is positive. Fuel flow MUST use the declared 2T 360-degree cycle rate.
Zero denominators and nonpositive brake power MUST have explicit undefined
statuses. The energy potential MUST NOT be passed to the gas solver without a
separately verified energy coupling.

#### Scenario: Complete fuel ledger

- **WHEN** explicit fuel properties, P6 delivered/trapped and short-circuited
  species masses, burned fraction, RPM and indicated/brake work are supplied
- **THEN** AFR, equivalence, species-derived fuel masses, flow, energy potential
  and SFC are returned with the 2T cycle convention.

#### Scenario: Missing fuel or nonpositive brake power

- **WHEN** no fuel is present or brake power is zero/negative
- **THEN** AFR or brake SFC is explicitly undefined; masses and energy remain
  zero or signed according to the supplied ledger, without invented values.

### Requirement: RPM-mapped exhaust powervalve geometry

Powervalve V1 MUST map RPM continuously to an explicit `[0,1]` exhaust roof
position with provenance. Position zero MUST mean raised/open and position one
MUST lower the roof by the configured travel distance. The model MUST target
only its declared movable main exhaust window and MUST reuse generic port area
and event calculations. RPM outside the configured map MUST be rejected. No
actuator dynamics or unprovided RPM calibration may be inferred.

#### Scenario: Interpolate roof position

- **WHEN** an RPM lies between configured map points
- **THEN** linear interpolation changes the main exhaust port's area profile and
  event angles through the existing port geometry.

#### Scenario: Invalid target or map range

- **WHEN** the target port is not the configured movable main exhaust or RPM
  lies outside the map
- **THEN** the request is rejected without changing other ports.

### Requirement: Slider-crank crankcase V2 geometry and donor-aware links

Crankcase V2 MUST accept explicit bore, stroke, rod length, BDC volume and
provenance. It MUST use the established slider-crank position to calculate
volume throughout 360 degrees, analytic volume rate at RPM, and the ratio of
maximum to minimum crankcase volume. A standalone 0D intake/leak link MUST reuse
the existing bidirectional restriction relation and its actual donor state;
it MUST NOT clamp reverse flow. The helper MUST NOT claim production P5-C/P6
integration or modify their stage ledger.

#### Scenario: Crankcase volume and compression

- **WHEN** valid slider-crank dimensions and BDC volume are supplied
- **THEN** TDC/BDC volumes, crankcase compression ratio and volume-rate sign
  follow the existing kinematics and preserve its endpoint behavior.

#### Scenario: Reversible intake/leak flow

- **WHEN** pressure ordering changes across a configured link
- **THEN** the existing restriction resolves the direction, enthalpy and fresh
  fraction from the actual upstream donor; closed area gives exact zero flux.

### Requirement: Reusable intake volumes and junction interfaces

Network V1 MUST represent plenum, airbox and boost-bottle volumes and explicit
connections with area, effective length and provenance. Atmosphere MUST default
to four-species fresh air only, with pressure and temperature explicit. A
0D-volume/1D-duct exchange MUST reuse the existing P3 Riemann flux and P6
four-species donor semantics; adjacent volume and duct MUST receive equal and
opposite mass, energy and each species increment. A lumped Helmholtz estimate
MUST use explicit effective neck length and MUST be labeled as an estimate.
Network components MUST NOT be claimed integrated into P5-C until their states
share its SSPRK stages and global ledgers.

#### Scenario: Reverse volume/duct flow

- **WHEN** pressure order reverses across a network interface
- **THEN** the resolved P6 flux uses the actual new donor composition and all
  extensive increments remain equal and opposite.

#### Scenario: Atmosphere and boost-bottle estimate

- **WHEN** an atmosphere boundary and explicit bottle/neck geometry are given
- **THEN** atmosphere contains only the default fresh-air species and the
  Helmholtz estimate uses caller-provided effective length without hidden
  corrections.

### Requirement: Versioned engineering output schema

The existing fixed-channel `MOTORSIM_ENGINEERING_OUTPUTS_V1` MUST retain its
strict 360-degree 2T convention, RPM/cycle identity, explicit P4 dependency
status, crank-angle trace and cycle metrics. The integrated V2 schema binds
the engine configuration SHA-256 and supports path-addressed duct-cell and
duct-face channels alongside the supported fixed channels; its builder remains
available for existing records. Every channel and metric MUST declare units
and source. Undefined values MUST carry null, status and
reason. Nonfinite/bool values, unknown V2 channel forms, mismatched sample
counts, incomplete cycles, invalid configuration identity or altered units
MUST be rejected. All schemas MUST keep periodicity `NOT_EVALUATED`,
experimental validation `NOT_PERFORMED`, and predictive validation
`NOT_CLAIMED`.

The integrated collector MUST emit `MOTORSIM_ENGINEERING_OUTPUTS_V3` for
cycle-derived metrics whose semantics were corrected by AUD-14, while V1 and
V2 builders remain available with their original meanings. V3 MUST identify
gross fresh-charge transfer delivery and gross outward short-circuit crossings
by name; these positive-crossing integrals may count recrossings and MUST NOT
be described as unique net mass. `gross_intake_air_fuel_ratio` MUST mean only
the gross fresh-air/fuel species ratio crossing the engine intake boundary;
`afr` MUST be undefined unless a trapped or burned AFR is directly available.
ISFC and BSFC MUST use the P7 prescribed fuel-species sink, and MUST be
undefined when that sink or the corresponding power is nonpositive. The output
MUST state that P7 consumption is prescribed bookkeeping, not measured or
experimentally validated fuel burn.

The additive `MOTORSIM_ENGINEERING_OUTPUTS_V4` MUST preserve V3 unchanged and
may report cylinder `fresh_air` and `fuel` pseudo-species masses at the later
of the exact aggregate transfer-closure and exhaust-closure events. This is the
last exact cylinder gas-exchange-port closure state; it MUST be sourced from
the accepted SSPRK2 endpoint and MUST remain UNDEFINED without both exact
snapshots. The associated fresh-air/fuel pseudo-species mass ratio MUST be
named as a species ratio, MUST be UNDEFINED for zero fuel, and MUST NOT be
called AFR or equivalence ratio. V4 MUST keep AFR/equivalence ratio UNDEFINED
without explicit stoichiometric properties and MUST NOT infer LHV from P7 heat.

#### Scenario: Build a trace with unavailable metric

- **WHEN** a complete crank-angle trace and supported cycle metrics are supplied
- **THEN** units, sources and undefined reasons are serialized, with no claim of
  periodicity or validation.

#### Scenario: Reject stale or unsupported channels

- **WHEN** channel units, sample counts or cycle span disagree with the schema
- **THEN** construction or offline validation rejects the artifact.

#### Scenario: Build integrated output with duct topology identity

- **WHEN** one complete integrated primary cycle supplies its configuration
  identity, duct meshes, accepted cell states and face fluxes
- **THEN** V2 emits path-addressed pressure, temperature, Mach, four species
  masses, signed face mass flow, port areas and port flows with source/unit
  provenance, while retaining all non-claim controls.

#### Scenario: Reject forged integrated summaries

- **WHEN** a cycle summary disagrees with the accepted SSPRK2 trajectory or
  global conservation reconstructed from that trajectory
- **THEN** V2 output construction rejects it and does not serialize the summary.

#### Scenario: Label gross delivery and short-circuit outputs

- **WHEN** a complete integrated cycle is converted to engineering output
- **THEN** V3 labels gross fresh-air-plus-fuel crossings explicitly, records
  that recrossings are not deduplicated, excludes reverse exhaust from
  short-circuit mass, and does not claim a net or unique-mass interpretation.

#### Scenario: Report fuel consumption without conflating intake with burn

- **WHEN** an integrated cycle has intake fuel delivery but no positive P7
  fuel-species sink
- **THEN** the gross intake ratio may be reported, AFR stays undefined, and
  ISFC/BSFC stay undefined rather than reporting zero consumption.

#### Scenario: Rebuild fuel mass accounting from the integrated cycle

- **WHEN** a complete primary cycle contains signed intake-face species flux,
  P6 fuel delivery/short-circuit rates, accepted P7 species sources, and start
  and terminal four-species inventories
- **THEN** the V2 collector independently reports intake air/fuel per cycle,
  P7 fuel-species consumption, short-circuited fuel, terminal system fuel
  inventory and the global fuel-species residual from those accepted records;
  gross intake AFR is defined only for positive fuel delivery, while
  equivalence ratio remains UNDEFINED unless a stoichiometric AFR is explicitly
  configured. ISFC/BSFC require positive corresponding power and use the
  integrated fuel-species flow without inferring fuel LHV.

#### Scenario: Read older V2 fuel traces without fabricating intake composition

- **WHEN** a V2 primary trace lacks the newer gross-intake-air rate but retains
  its signed species flux at the intake face
- **THEN** the collector reconstructs gross inlet fresh_air from that accepted
  signed face flux; if it is absent or malformed, output construction fails.

### Requirement: Integrated cycle closure evidence and scavenging outputs

Integrated full-cycle evidence MUST use a versioned primary-cycle schema that
stores exact accepted-stage cylinder species snapshots at the last aggregate
transfer and exhaust closure events derived from the bound generic port
geometry. A powervalve MUST be resolved at the cycle RPM before its exhaust
closure is derived. Closure states MUST be exact trajectory endpoints; nearest
samples and interpolation MUST NOT be used. If a closure is absent, the exact
endpoint is missing/ambiguous, or RPM varies in a way that prevents an exact
powervalve event, the record MUST mark closure evidence unavailable and
scavenging outputs MUST remain null/UNDEFINED. Scavenging ratios MUST only be
defined when an explicit positive reference-charge mass is supplied, and MUST
be computed from the same cycle's P6 fresh-delivery/outward-short-circuit
integrals and closure species inventories. Missing evidence MUST NOT retain a
previous cycle's values.

#### Scenario: Emit exact closure-bound scavenging metrics

- **WHEN** a constant-RPM integrated cycle reaches unique exact transfer and
  exhaust closure endpoints and receives an explicit reference-charge mass
- **THEN** the versioned primary evidence binds both four-species snapshots and
  the V2 collector emits scavenging metrics from those snapshots and that
  cycle's P6 ledgers.

#### Scenario: Keep scavenging undefined without exact closure evidence

- **WHEN** the port geometry has no aggregate closure or the accepted trajectory
  lacks an exact closure endpoint
- **THEN** no interpolation is performed and scavenging values remain null and
  UNDEFINED even if another cycle previously had valid closure data.

#### Scenario: Report unburned fuel species at exact exhaust closure

- **WHEN** a primary cycle contains a validated exact exhaust-closure snapshot
  of the cylinder's four species
- **THEN** engineering output MUST report the `fuel` pseudo-species mass from
  that snapshot as `cylinder_fuel_species_at_exhaust_close_kg`; without the
  snapshot it MUST be UNDEFINED, and the value MUST NOT be labeled as total
  trapped fuel or reconstructed from the terminal global inventory.

#### Scenario: Report pseudo-species at the last exact cylinder port closure

- **WHEN** a V4 primary cycle contains validated exact transfer and exhaust
  closure snapshots from accepted SSPRK2 terminal stages
- **THEN** V4 reports the cylinder `fresh_air` and `fuel` pseudo-species masses
  from whichever aggregate closure occurs later and their species-mass ratio
  when fuel mass is positive; the ratio is not AFR, missing/zero-denominator
  values are UNDEFINED, and V3 remains byte-semantically unchanged.

#### Scenario: Verify a second integrated synthetic configuration

- **WHEN** a second internally defined engine configuration changes the
  expansion-chamber section lengths while retaining the shared integrated
  solver, transfer topology, four-species state, prescribed combustion,
  thermal boundary and explicit synthetic loss model
- **THEN** it MUST independently complete cycles, satisfy the same preregistered
  periodicity contract, close its global ledgers, and build validated V2
  engineering outputs. The result remains synthetic and CONDITIONAL_ON_P4 and
  MUST NOT be presented as experimental or commercial readiness.

Engineering trace channels MUST pair each accepted state with an RHS evaluation
made from that same state. The terminal point MUST be a read-only evaluation of
the accepted terminal state; a requested prescribed P7 endpoint rate MUST be
identified as pre-limiter and MUST NOT enter cycle ledgers or conservation.

### Requirement: Preserve V1 periodicity and add a signed-work V2 detector

`REFERENCE_PERIODIC_CONVERGENCE_V1` MUST remain unchanged. The separately
versioned `REFERENCE_PERIODIC_CONVERGENCE_V2` MUST accept finite signed
indicated work while retaining the existing 1 J denominator floor and 0.005
relative threshold:
`abs(work_a-work_b) / max(1 J, abs(work_a), abs(work_b))`.
All other V1 observables, thresholds, period-1 precedence, period-2 A/B branch
identity, three-comparison streaks, and restart replay rules MUST remain the
same. V2 detector snapshots MUST identify V2 and MUST NOT restore as V1 or
rewrite historical V1 results. This detector version does not change the cycle
primary record schema or constitute convergence evidence by itself.

#### Scenario: Compare negative work without changing V1

- **WHEN** two compatible cycle-primary records contain finite negative
  indicated work
- **THEN** V1 retains its prior INVALID behavior while V2 compares signed work
  with the specified magnitude denominator and unchanged threshold.

#### Scenario: Restore signed-work period detection

- **WHEN** a V2 detector snapshot contains complete history and streak state
- **THEN** restore replays that history under V2, preserves independent A/B
  streaks and period-1 precedence, and rejects a V1 snapshot.

### Requirement: Exploratory experimental-data import remains separate from P9

The reusable importer MUST support pressure trace, dyno torque and dyno power
with strict headers, declared units, uncertainty, metadata and provenance. Raw
bytes MUST be preserved and hash-bound. Overlay MUST join exact coordinates
only and report descriptive errors without claiming equivalent conditions.
Every result MUST be marked `EXPLORATORY_COMPARISON`, not eligible for validation
or P9 decisions. The importer MUST NOT modify or invoke the frozen P9 contract
or pipeline.

#### Scenario: Import and compare a trace

- **WHEN** a declared pressure/dyno dataset and simulation values with matching
  canonical units are supplied
- **THEN** raw data remains bound, exact matches and descriptive errors are
  returned, and unmatched/interpolated points are not invented.

#### Scenario: Keep P9 authority separate

- **WHEN** an exploratory overlay is produced
- **THEN** it cannot emit P9 PASS/validation status and remains explicitly
  ineligible for preregistered decisions.

### Requirement: Versioned fuel library and simulation snapshots

`FUEL_LIBRARY_V1` MUST store immutable, versioned `FuelDefinition` records with
identity, display name, family/category, provenance, source records, optional
RON, density and reference temperature, LHV, explicit stoichiometric AFR or
complete elemental mass fractions, optional oxygen and ethanol fractions with
their basis, and built-in/user-defined identity. Missing properties MUST remain
unknown; a profile is not eligible for derived combustion outputs unless its
required properties are explicit or derivable by the versioned elemental
stoichiometry method. User definitions MUST be versioned when edited. A
simulation selection MUST freeze fuel id, version, canonical content hash and
the full definition snapshot so later library changes cannot alter historical
simulation provenance. Built-ins may be disabled but MUST NOT be physically
deleted or edited; user profiles support create, duplicate, versioned edit,
enable/disable, delete, import and export. Restore defaults MUST restore built-in
profiles without deleting user profiles. Lubricant definitions and premix ratio
are separate future interfaces and MUST NOT be embedded in fuel properties.
This library does not define fuel delivery, trapped fuel, combustion or
heat-release physics.

#### Scenario: Preserve incomplete documented fuel identities

- **WHEN** an official fuel source gives product identity/RON and only bounds
  or maxima for composition while density, elemental composition, stoichiometry
  or LHV are unavailable
- **THEN** the profile MUST preserve the known claims and source provenance,
  leave unknown fields null, and keep property-dependent combustion outputs
  unavailable; bounds MUST NOT be converted into point values.

#### Scenario: Freeze the selected fuel definition

- **WHEN** a simulation selects an enabled, versioned fuel definition
- **THEN** its id, version, full canonical definition and matching SHA-256 MUST
  be captured, and editing or restoring the library MUST NOT change that frozen
  snapshot.

#### Scenario: Manage built-in and user-defined profiles

- **WHEN** a user creates, duplicates, edits, imports, exports, disables,
  deletes or restores fuel definitions
- **THEN** user operations MUST preserve built-in immutability, require a new
  version on edits, reject identity collisions, and keep deleted/disabled
  profiles unavailable for simulation selection without altering prior
snapshots.

### Requirement: Explicit dynamic-reed geometry and stage-coherent coupling

The integrated dynamic reed capability MUST use a versioned geometry record
`DYNAMIC_REED_HINGED_FLAP_GEOMETRY_V1`. The record MUST distinguish flow
curtain width from swept-volume area and MUST define a provenance-bearing
lift shape and adjacent gas control volumes. For the preregistered linear
hinged-flap shape, `A_flow = Cd W x`,
`A_sweep = dV_left/dx = W L/2`,
`V_left = V_left,0 + A_sweep x`, and
`V_right = V_right,0 - A_sweep x`. The generalized pressure-force area MUST
equal `A_sweep`; a configuration mismatch MUST be rejected. It MUST NOT infer
geometry from an undocumented real engine or use `effective_width * lift` as
swept volume.

The first coupled capability MUST advance gas, the four P6 species, reed
position/velocity and its energy ledger in the same SSPRK2 stages, using each
stage's pressure, lift-dependent flow area and actual signed donor composition.
Mass and donor enthalpy transfers MUST be applied with opposite signs to the
two adjacent control volumes. The gas volume-work terms and pressure-force work
on the petal MUST be equal and opposite. Damping loss MUST appear explicitly
in an energy sink ledger; no clipping, post-step reed update or operator
splitting is allowed. Unsupported contact/out-of-domain stages MUST reject
transactionally. The standalone `DYNAMIC_REED_V1` and static path remain
unchanged; this synthetic component is not real-motor validation.

#### Scenario: Reject invented or inconsistent reed geometry

- **WHEN** a coupled reed definition has missing provenance, nonpositive
  adjacent volume, out-of-range lift, or a pressure-area mismatch with the
  declared flap geometry
- **THEN** configuration MUST be rejected before state advancement and no
  geometry may be inferred from a real reference engine.

#### Scenario: Preserve mass and energy through dynamic reed stages

- **WHEN** an admissible two-volume synthetic state advances through SSPRK2
  with forward or reverse reed flow
- **THEN** gas and four-species mass MUST exchange using the current donor at
  each stage, the interface fluxes MUST cancel globally, and total gas plus
  reed stored energy plus the explicit reed-dissipation ledger MUST close.

#### Scenario: Reject out-of-domain coupled stages atomically

- **WHEN** a proposed SSPRK2 stage crosses the declared lift or positive-volume
  domain
- **THEN** the step MUST reject without modifying gas, species, reed state or
  ledgers; the solver MUST NOT clip the state.
