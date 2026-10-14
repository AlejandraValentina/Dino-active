# DINO_SIMULATION_WORKFLOW_V1 Specification

## ADDED Requirements

### Requirement: Project to executable engine configuration
The desktop workflow MUST derive solver configuration from the selected project base or variant using ENGINE_CONFIGURATION_V1 and IntegratedEngine2T adapters. Canonical engine, variant, effective configuration and solver dependency identities MUST be recorded. Backend preflight MUST reject unsupported or invalid geometry, boundary, combustion, thermal, mechanical-loss and power-valve inputs before integration.

#### Scenario: Select a supported variant
- **WHEN** the user selects a validated engine variant
- **THEN** the adapter produces the corresponding native solver configuration and a stable identity without duplicating physics in Qt.

### Requirement: Safe exploratory execution
The system MUST provide a versioned `EXPLORATORY` route for a user-confirmed local run of one configuration at one operating RPM. It MUST use a project/run-isolated artifact root, exact solver/model/configuration hashes, independent evidence audit, conservation records, explicit provisional classification, bounded worker/time/memory policy, cancellation and compatible checkpoint/restart. It MUST NOT call or bypass a historical campaign runner. The `VERIFIED` mode MUST remain unavailable unless a matching contract, preregistration and external explicit authorization are present.

#### Scenario: Run a local configuration
- **WHEN** preflight succeeds and the user confirms the displayed RPM, mode and budget
- **THEN** an isolated exploratory run begins and writes its own identity, checkpoints, cycles, audit and provisional result; no verified PASS is created.

### Requirement: Explicit execution confirmation and recovery
The Qt panel MUST show selected motor/variant, RPM and boundary conditions, mode, preflight findings, resource/time bounds, progress, cycles, periodicity status, errors, checkpoint and recovery state. Cancellation MUST preserve recoverable artifacts; resume MUST reject any identity mismatch.

#### Scenario: Cancel and resume
- **WHEN** the user cancels an exploratory run and later resumes it
- **THEN** the run stops at a complete checkpoint boundary, retains completed cycles and only resumes if configuration, solver and model hashes match exactly.

### Requirement: Exhaust geometry uses the solver model
The exhaust editor MUST edit the backend's actual supported 1D section parameters and produce a distinct executable solver configuration when supported. Unsupported geometry MUST fail preflight with a clear reason. The UI MUST make no acoustic or power-gain claim absent from the solver.

#### Scenario: Compare original and modified exhaust
- **WHEN** a user changes supported exhaust lengths or diameters
- **THEN** the derived solver configuration changes and separately run exploratory results can be compared without interpolation or validation claims.

### Requirement: Bounded powervalve endpoint resolution
For the constant-RPM integrated engine, the powervalve MUST resolve against the configured operating RPM rather than an RPM reconstructed from each floating-point step. Exact endpoints and representable in-domain values MUST interpolate normally; any genuinely out-of-domain RPM MUST still fail closed. This implementation MUST carry a new solver identity. Historical artifacts and classifications MUST remain unchanged.

#### Scenario: Integrate at a configured map endpoint
- **WHEN** a constant-RPM integrated engine runs at an RPM equal to a map endpoint
- **THEN** roundoff in `delta_angle / dt` cannot turn the configured endpoint into an out-of-map rejection, while an RPM outside the configured domain remains rejected.

### Requirement: Compare computed variants
When valid run results exist, the application MUST compare supported power, torque, IMEP, FMEP, BMEP, defined BSFC, periodicity and hard-gate outputs. Invalid or absent values MUST remain gaps. Exploratory and verified provenance/classifications MUST remain distinct.

#### Scenario: Compare exhaust variants
- **WHEN** both variants have results at a requested metric and RPM
- **THEN** the UI shows side-by-side values with units and run identities; missing or invalid values are not interpolated.

### Requirement: Workflow verification and historical isolation
Tests MUST exercise project-to-solver conversion, configuration changes, fail-closed preflight, identity binding, real bounded engine execution, cancellation/restart, artifact isolation, independent audit and Qt workflow. Historical R2/IMPL2 evidence MUST remain byte-for-byte untouched and no full RPM campaign or KT100 experiment may run as part of this change.

#### Scenario: Inspect historical campaign after local development
- **WHEN** the new workflow is used for an exploratory motor configuration
- **THEN** historical campaign manifests, primaries, checkpoints and classifications remain unchanged and separately addressable.
