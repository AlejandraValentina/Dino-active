## ADDED Requirements

### Requirement: Auditable single-cylinder two-stroke v1 gate

The product MUST NOT be classified `GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED`
unless two newly versioned, preregistered synthetic fixtures `FIXTURE_A_PRIME`
and `FIXTURE_B_PRIME` both pass this specification and their complete primary
evidence can independently regenerate each decision. Historical fixtures A,
B, and C MUST NOT be reinterpreted as prime evidence. P4–P9 contracts/evidence
and the P9 frozen spec hash MUST remain unchanged. A v1 candidate MUST be labelled
synthetic and `CONDITIONAL_ON_P4`; it MUST NOT imply experimental validation or
KT100 applicability.

#### Scenario: Preserve historical evidence and scope
- **WHEN** closure artifacts are generated
- **THEN** historical P4–P9 files, evidence, and thresholds remain byte-identical
  unless a separately authorized change requires otherwise, and deferred
  features are not represented as v1 gate capability.

### Requirement: Integrated network pressure reactions and equilibrium

The integrated solver MUST include pressure traction on blocked face area at
network/plenum endpoints and restrictions. Uniform stationary gas MUST remain
stationary for closed, partial, and full openings, plenum/network endpoints,
and mirrored face orientations. Equal/opposite internal reactions MUST cancel;
external reactions MUST be explicit in the momentum/force diagnostics.

#### Scenario: Uniform gas at rest
- **WHEN** uniform zero-velocity gas is integrated with any required interface
  class and valid orientation
- **THEN** no spurious acceleration occurs within the preregistered roundoff
  bound and every non-cancelling external pressure reaction is recorded.

### Requirement: Integrated atmospheric open-end capability

IntegratedEngine2T configuration and deserialization MUST support the existing
versioned `OPEN_END_PLENUM_V2` capability directly. `LEGACY_CHARACTERISTIC_V1`
and historical `nonreflecting` behavior MUST remain unchanged. Open-end inflow
uses the configured reservoir state and donor composition, while outflow and
choking use the approved capability equations. A short diagnostic MUST precede
the prime campaigns and MUST NOT be classified as campaign evidence.

#### Scenario: Initially equilibrated prime boundary
- **WHEN** a prime fixture begins from its frozen pressure/temperature state
  and advances a short diagnostic with the atmospheric boundary
- **THEN** pressure remains consistent with its reservoirs and integrated
  mass/energy fluxes, without artificial depressurization; only the subsequent
  preregistered fixed-horizon campaign may supply acceptance evidence.

### Requirement: Arbitrary positive transfer-route count

IntegratedEngine2T MUST accept at least one transfer route and MUST NOT rely on
fixture-specific transfer identifiers or a three-transfer minimum. Flow,
species, energy, restart, collectors, and topology accounting MUST include every
configured route exactly once.

#### Scenario: Two and three transfer topologies
- **WHEN** equivalent supported fixtures use two and three transfer routes
- **THEN** both construct, integrate, serialize, restore, and audit without
  special-case route identifiers or omitted ledgers.

### Requirement: Fuel-bounded chemical combustion V1

The new `FUEL_COUPLED_COMBUSTION_V1` MUST use a frozen, versioned
`SYNTHETIC_FUEL_SURROGATE_V1` snapshot/hash and explicitly synthetic
composition, stoichiometric AFR, LHV, efficiency, and provenance. It MUST NOT
change historical P7. Burned fuel MUST be limited to fuel and oxygen available
in the accepted cylinder state, update P6 pseudo-species consistently, and
release only `dm_fuel_burned * LHV * combustion_efficiency`; Wiebe progress may
distribute but MUST NOT increase this energy. Zero fuel or oxygen MUST yield
zero chemical heat. Unburned fuel MUST remain accounted for. Global mass,
species, and energy ledgers MUST close within frozen numerical bounds.
Stage chemistry MUST honor the integrated species-state roundoff admissibility
bound; tolerated tiny negative species values MUST provide zero reactant
availability and MUST NOT create fuel burn or heat.

#### Scenario: Zero fuel or insufficient oxygen
- **WHEN** available cylinder fuel is zero, or fresh-air oxygen cannot support
  the requested Wiebe burn
- **THEN** released heat is zero or oxygen-limited, burned species equal actual
  reactant mass converted, unburned fuel remains, and no prescribed excess heat
  is emitted.

### Requirement: Accepted-state fuel accounting

Delivered, trapped, burned, unburned, and short-circuited fuel MUST derive from
accepted stage fluxes and exact geometry-bound cylinder snapshots. Actual AFR
MUST use trapped fresh air divided by trapped fuel and remain distinct from the
V4 pseudo-species ratio. ISFC/BSFC MUST be undefined unless fuel provenance,
accepted periodic cycle, complete consumption ledger, and positive power
denominator are present.

#### Scenario: Missing event or nonperiodic result
- **WHEN** a required closure event, periodicity PASS, provenance, or positive
  power is absent
- **THEN** the affected outputs are `UNDEFINED` with reason/provenance and are
  never presented as measured or calibrated results.

### Requirement: Bounded perfect-mixing scavenging

V1 MUST declare `SINGLE_ZONE_PERFECT_MIXING_SCAVENGING_ASSUMPTION`. Metrics MUST
be derived from accepted net fluxes and geometry-bound inventories. Every
efficiency/fraction MUST be in [0,1]; undefined physical cases return
`UNDEFINED`, while inconsistent evidence is rejected. Gross crossings and net
inventory-derived quantities MUST be labelled separately. Advanced scavenging
models are outside this gate.

#### Scenario: Outside-domain metrics
- **WHEN** a computed efficiency or fraction would exceed its physical domain
- **THEN** the output is invalid/undefined with an explicit reason, never clipped
  into an apparently valid value.

### Requirement: Work and performance semantics

The engine MUST report `W_cyl=integral(p_cyl dV_cyl)`,
`W_cc=integral(p_cc dV_cc)`, and `W_piston,net=W_cyl+W_cc` with each physical
volume's own signed p-dV work. Brake work MUST be net piston gas work minus
provenance-bearing mechanical losses, with no duplicate crankcase pumping in
FMEP. IMEP/BMEP MUST use frozen geometry-derived displacement, never a caller
override. Power/torque MUST use the 2T 360-degree cycle convention.

#### Scenario: Mechanical work conversion
- **WHEN** a complete accepted cycle and a valid explicit loss model exist
- **THEN** all indicated/net/brake work, MEP, power, torque, loss, and SFC terms
  are derived consistently from their declared inputs and signs.

### Requirement: Strict output validity and provenance

Versioned output records MUST contain status, provenance, definition/version,
and periodicity dependency. `DEFINED` values MUST be finite and satisfy the
physical domain of their metric. Required provenance/configuration absent or
invalid periodicity MUST prevent definition of dependent outputs. Invalid values
MUST be rejected, not silently clipped or sanitized.

#### Scenario: Invalid output domain
- **WHEN** an output would encode nonpositive AFR, negative BSFC, an efficiency
  outside [0,1], or performance requiring absent periodicity/provenance
- **THEN** serialization rejects it or emits a reasoned `UNDEFINED` record.

#### Scenario: Period-two cycle metrics require an aggregate definition
- **WHEN** the detector identifies `PERIOD_2` but a V5 metric describes one
  360-degree cycle and no two-cycle aggregate is bound
- **THEN** a periodic-dependent metric MUST remain `UNDEFINED`; V5 MUST NOT
  treat the period-two label alone as an accepted single-cycle metric.

### Requirement: Recomputable primary evidence and exact replay

Primary cycle evidence MUST bind producer, detector, configuration, fixture,
fuel snapshot, accepted trajectory, terminal state, and restart/replay identities
by hashes. The offline auditor MUST reconstruct relevant RHS/fluxes, sources,
ledgers and outputs from persisted accepted state data. Every rejected
admissibility trial MUST be persisted and re-executed from its preceding
accepted state by the offline auditor; the failure reason and exact half-step
retry sequence MUST match. For every accepted start, the auditor MUST also
reconstruct the runner's nominal 0.5-degree/event proposal and reject an
accepted shortened step without a matching rejected-trial chain. Retry/halving
MUST NOT be silent. During replay the accepted step increment MUST be taken
from the validated nominal proposal or final rejected-step halving record,
not reconstructed by subtracting accumulated angle coordinates. The persisted
end angle MUST agree with that increment within four float64 ULPs of the angle
coordinate; this permits coordinate-subtraction roundoff without relaxing the
step sequence or solver replay.
Continuous, checkpoint/restart, and independent replay MUST compare full
physical state, species, ledgers and relevant outputs, not only digest strings.

Integrated single-cycle primary records use V3. Offline audit MUST replay every
accepted SSPRK2 step from the bound start checkpoint and compare all saved stage
states and flux/source records. Caller retries MUST be included in an ordered
per-cycle rejection log whose CFL count agrees with the checkpoint rejection
counter delta; the campaign runner source is bound by hash. The primary builder,
the complete set of Python modules used by the integrated RHS, and the campaign
periodicity detector source are bound separately. Conservation residual limits
use the documented float64 accumulation bound
`gamma_n = n*u/(1-n*u)`, `n = 16 * accepted_steps`, with `u` equal to float64
unit roundoff and each residual scale equal to the sum of absolute primary
terms in its ledger equation. The auditor recomputes these limits and enforces
them before accepting a primary record.

#### Scenario: Summary or evidence tampering
- **WHEN** a summary conflicts with primary states or a trial rejection is
  missing from the evidence stream
- **THEN** the audit fails and cannot issue a successful gate classification.

### Requirement: Pre-registered mesh and prime-fixture campaigns

The integrated mesh study MUST be preregistered in a separate commit with its meshes, observables, sufficiency criterion, and tolerance. A separate commit MUST freeze both prime fixtures, physics/configuration hashes, mesh, RPM, horizon, detector V2, thresholds, evidence schema, restart and acceptance criteria before either campaign. Mesh sufficiency and campaign horizons MUST NOT be changed after
observing results. Each prime campaign MUST run exactly its preregistered
20-complete-cycle horizon, record explicit nonconvergence/failure, and never be
extended post hoc. At least two distinct RPMs MUST be exercised across the two
primes. Full acceptance requires complete audited campaigns for both fixtures.

#### Scenario: No period within the fixed horizon
- **WHEN** the frozen 20-cycle horizon ends without the preregistered period
  detector passing
- **THEN** the result is `NO_CONVERGENCE_WITHIN_HORIZON` and the fixture fails
  the v1 gate; the horizon and thresholds are not relaxed.

### Requirement: Versioned v1 definition of done and freeze classification

The v1 Definition of Done is this OpenSpec contract. All new findings MUST be
classified `BLOCKS_2T_V1` or `POST_2T_V1_BACKLOG` before implementation. The
terminal verified classification requires both audited prime fixtures, all
regressions and internal adversarial review. Only then may
`GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED` be proposed, followed by
`MOTORSIM_2T_V1_DEVELOPMENT_FREEZE_CANDIDATE`. P4–P9 states and external
validation claims remain separate.

#### Scenario: Candidate classification
- **WHEN** any required fixture, evidence, numerical, restart, performance,
  review, or regression gate is incomplete or failed
- **THEN** the candidate is not produced and the exact gate remains open or
  failed without implying scientific acceptance.
