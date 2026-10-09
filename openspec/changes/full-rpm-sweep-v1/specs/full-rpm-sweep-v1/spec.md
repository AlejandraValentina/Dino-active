# FULL_RPM_SWEEP_V1

## ADDED Requirements

### Requirement: preregistered immutable configuration

The sweep MUST use only the hash-bound configurations and models in
`results/full-rpm-sweep-v1/preregistration.json`. The canonical source engine
configuration MUST remain immutable. Per-point configuration MUST differ only
in the declared RPM value. The fixture, engine configuration, fuel, solver and
periodicity contract identities MUST be recorded in each result.

#### Scenario: configuration identity

- **WHEN** a point is prepared
- **THEN** all source hashes match the preregistration and only `reference_rpm`
  differs from its immutable base configuration

### Requirement: explicit mechanical losses

Every configuration MUST resolve a valid, explicit
`MECHANICAL_LOSS_MODEL_V1` bound to its fixture and configuration hashes.
Missing, invalid, stale, incompatible or out-of-domain loss models MUST fail
closed before solver advancement. The sweep MUST NOT call or fall back to
`standard_fmep_model_v1()`.

#### Scenario: missing or implicit losses

- **WHEN** an explicit configuration-bound loss model is absent or invalid
- **THEN** preflight returns `FAIL_CLOSED` and zero solver cycles are run

### Requirement: fixed WOT RPM contract

The campaign MUST evaluate the preregistered inclusive RPM range and increment
for both configurations. WOT MUST mean the configured unthrottled intake and
exhaust open-end boundary condition, with the existing RPM-indexed power-valve
map applied unchanged. Fuel species and fuel-property snapshot MUST be
explicitly bound and hashed; the pseudo-species air/fuel ratio MUST be labeled
as such and MUST NOT be reported as a measured chemical AFR.

#### Scenario: RPM grid and WOT inputs

- **WHEN** preflight enumerates points
- **THEN** every RPM lies within the bound power-valve map, and boundary, fuel,
  mixture and loss inputs are explicit

### Requirement: existing periodicity and bounded horizon

The campaign MUST use `REFERENCE_PERIODIC_CONVERGENCE_V2` and its exact
versioned thresholds/streak without modification, with a maximum of 111
complete cycles per point. Nonconvergence at the horizon MUST be classified
`NO_CONVERGENCE_WITHIN_HORIZON`; failed or nonconverged points MUST NOT expose
valid periodic engineering outputs.

#### Scenario: periodicity result

- **WHEN** a point reaches its horizon without detector acceptance
- **THEN** it is classified nonconverged and no valid periodic output is emitted

### Requirement: no-solver preflight

Preflight MUST validate geometry, distribution/topology, ports, chambers,
thermal parameters, combustion, fuel, mechanical losses and boundary
conditions using the existing integrated configuration validators plus
sweep-specific contracts. Any invalid input MUST be reported before solver
advancement.

#### Scenario: invalid configuration

- **WHEN** a sweep configuration is malformed or incompatible
- **THEN** preflight reports the causal failure and records zero solver steps

### Requirement: outputs and provenance

Each converged result MUST record RPM, IMEP, FMEP, BMEP, brake torque, brake
power, brake torque, delivered AFR, lambda, phi, ISFC and BSFC with units,
dependency status and source provenance. AFR MUST be calculated from the same
accepted primary's delivered fresh-air and fuel ledgers; lambda MUST use the
bound fuel snapshot's stoichiometric AFR, and phi MUST be its reciprocal.
Missing ledgers or stoichiometry MUST produce causal `UNDEFINED` values. The
preregistered mixture pseudo-species ratio MUST NOT be substituted for a
delivered chemical AFR.
Mechanical outputs MUST be derived from the accepted integrated primary and
the explicitly bound mechanical model. Configuration, fixture, fuel, solver,
detector, preregistration and result hashes MUST be persisted.

#### Scenario: brake accounting

- **WHEN** a periodic primary and explicit loss model are evaluated
- **THEN** BMEP and brake power/torque satisfy the existing 2T accounting
  identities within numeric tolerance

### Requirement: budget and checkpoints

Every future campaign invocation MUST stop within 60 minutes, persist a
restartable checkpoint after each complete cycle and RPM point, and resume
only when all bound hashes match. The runner MUST check the deadline between
accepted solver steps; if it expires mid-cycle, it MUST roll back that partial
cycle and retain the previous complete-cycle checkpoint. The sweep MUST NOT reduce CFL, periodicity
thresholds or physical criteria to satisfy the budget.

#### Scenario: bounded interruption

- **WHEN** an invocation reaches its wall-clock cap
- **THEN** it stops at the latest durable checkpoint and records an
  `INTERRUPTED_CHECKPOINTED` status without fabricating a point result

### Requirement: readiness is not campaign execution

`FULL_RPM_SWEEP_V1_READINESS_PASS` MUST mean the preregistration, explicit
loss bindings, no-solver preflight and focused tests pass. It MUST record
`campaigns_started = 0` and `FULL_RPM_SWEEP_V1 = NOT_STARTED`.

#### Scenario: readiness close

- **WHEN** all readiness gates pass
- **THEN** explicit mechanical-loss precondition is resolved while the sweep
  remains not started
