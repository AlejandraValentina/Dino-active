## ADDED Requirements

### Requirement: Versioned supported-engine configuration
The system MUST represent a 2T `IntegratedEngine2T` configuration using a versioned document with explicit SI units, provenance, native configuration identity, fuel/combustion, mechanical-loss model, operating conditions, and validation state. It MUST validate by adapting the native configuration through `IntegratedEngine2T.from_configuration_dict` without advancing the solver. It MUST reject unknown schema fields, unsupported solver capabilities, inconsistent geometry/topology, non-finite values, and missing or implicit mechanical-loss models. The configuration hash MUST be deterministic over canonical semantic content and independent of display names.

#### Scenario: Round-trip a supported fixture
- **WHEN** a supported integrated engine fixture is loaded as an editable configuration and exported
- **THEN** the native configuration round-trips through `IntegratedEngine2T` exactly, with stable hash and no solver steps.

#### Scenario: Unsupported capability
- **WHEN** a project requests an unimplemented component or model
- **THEN** validation fails with the capability and field identified; no surrogate component is inserted.

### Requirement: Escape sections and solver adaptation
The system MUST model a 1D circular exhaust route as ordered positive-length linear-diameter sections with explicit SI dimensions and provenance, and MUST convert supported sections to the existing finite-volume variable-area duct mesh using documented cell-volume integration. It MUST preserve required topology and initial-state compatibility. It MUST report finite-volume resolution and MUST reject shapes, junctions, or boundary components not represented by the current solver contract.

#### Scenario: Modify an existing supported expansion profile
- **WHEN** a variant changes lengths or endpoint diameters of supported sections while preserving valid duct topology
- **THEN** the generated solver configuration has a matching mesh, volume, centers, stable identity, and passes native configuration validation without integrating a cycle.

#### Scenario: Unsupported geometry
- **WHEN** geometry requires a multi-dimensional flow field, non-axisymmetric port, branch junction, or unsupported wall/component model
- **THEN** the project remains editable as a draft where appropriate, but solver adaptation reports NOT_SUPPORTED and does not approximate it silently.

### Requirement: Variants and configuration projects
A project MUST persist a base engine, simulation recipes, named variants, provenance, identities, external result references, and scientific validation status. Duplicating a variant MUST apply an explicit patch and preserve all unmodified parameters. Project JSON MUST NOT embed cycle primaries/checkpoints. Save MUST be atomic; load MUST strictly validate schema and hashes. Comparison MUST report changed paths with units and before/after values.

#### Scenario: Duplicate and edit exhaust only
- **WHEN** a variant is created from a base and only exhaust sections are changed
- **THEN** all other semantic configuration fields and hashes of their projections remain equal, while the variant receives a distinct configuration hash.

#### Scenario: Persist external results
- **WHEN** a project saves result references
- **THEN** it stores path/identity/hash/classification metadata only and does not copy primary evidence into the editable document.

### Requirement: Curve result import and comparison
The comparison service MUST import the versioned IMPL2 CSV/JSON report and validate schema, units, point IDs, and result identities. It MUST retain periodicity, numerical validity, hard gates, statuses, and reasons. Invalid/missing/undefined points MUST remain gaps; the service MUST NOT interpolate, smooth, or present `PERIOD_1` as universal gate acceptance. Dataset provenance MUST remain SYNTHETIC and nonexperimental.

#### Scenario: Compare synthetic IMPL2 variants
- **WHEN** the existing IMPL2 report is loaded
- **THEN** power, torque, BMEP/IMEP/FMEP, and defined consumption series are queryable by variant and RPM, with the three `NUMERICAL_INVALID` points represented as absent values and retained classifications.

### Requirement: Powervalve endpoint-roundoff proposal
The system MUST preserve a versioned proposal containing the reproduced cause, a bounded ULP-only endpoint correction recommendation, exact-boundary and genuinely-out-of-domain tests, solver-identity impact, and revalidation plan. It MUST NOT modify the solver, campaign producer, preregistration, or historical IMPL2 evidence.

#### Scenario: Review correction proposal
- **WHEN** the proposal is exported
- **THEN** the proposed tolerance is distinguished from a solver change, and historical results remain unchanged pending a separately authorized/versioned implementation and rerun.

### Requirement: Verification and limits
The implementation MUST provide focused tests for units, geometry, serialization, deterministic hashes, native-engine adaptation, variants, project persistence, curve comparison, invalid inputs, and unsupported capabilities. Documentation MUST identify solver limits and future Windows UI API boundaries. No RPM campaign or GUI frontend is run or added under this change.

#### Scenario: Validate implementation boundary
- **WHEN** the focused verification suite, strict OpenSpec validation, and program-status check are run
- **THEN** every supported adapter round-trip passes, unsupported inputs fail closed, and no GUI or campaign is launched.
