# DINO 2T Solver Recovery V2

## ADDED Requirements

### Requirement: New results report periodicity evaluation separately from termination
New exploratory results MUST report whether the versioned periodicity detector ran, whether it accepted a period, how many complete cycles and comparisons were evaluated, and why execution ended. Historical receipts MUST remain unchanged.

#### Scenario: Timeout after valid comparisons without accepted period
- **WHEN** a run times out after detector comparisons were computed
- **THEN** its new result records a partial evaluation with no accepted period, retains comparison metrics and thresholds, and classifies the timeout separately.

### Requirement: Periodicity identity matches the selected detector contract
Cycle records passed to `PeriodicDetectorV2` MUST declare `REFERENCE_PERIODIC_CONVERGENCE_V2`. A mismatch MUST remain invalid and MUST NOT be reported as successful evaluation.

#### Scenario: A checkpoint is bound to V2 detector records
- **WHEN** a run resumes from a checkpoint carrying a different periodicity contract
- **THEN** the runner rejects the checkpoint before advancing the solver.

### Requirement: Geometry changes require bounded physical evidence
Power-valve area queries MUST use the configured physical RPM map input while preserving the solver's reconstructed kinematic RPM. Boundary behavior MUST be tested at map endpoints and immediately adjacent floating-point values. Historical preregistrations and artifacts MUST remain immutable.

#### Scenario: A reconstructed RPM drifts by one floating-point unit at a map endpoint
- **WHEN** the configured engine RPM equals a power-valve map endpoint
- **THEN** geometry uses the configured RPM for the power-valve area and remains defined at the exact endpoint.

### Requirement: Solver performance changes preserve canonical audits
Optimizations MUST retain independent canonical replay, all species and numeric precision. Performance claims MUST state the fixture, instrumentation overhead, wall time, memory, and numerical/audit equivalence scope. No campaign or exhausted-run resume is authorized by this change.

#### Scenario: Output-only metadata follows primary persistence
- **WHEN** an already serialized canonical primary is enriched for engineering-output calculation
- **THEN** the workflow avoids another full primary JSON copy while the stored primary bytes and audited physical values remain unchanged.

### Requirement: Mesh study infrastructure is reproducible but non-claiming
Mesh configurations, observables, comparisons, conservation checks, and per-resolution receipts MUST be reproducible and tied to the existing protocol. Infrastructure or fixtures MUST NOT imply mesh independence without the registered study passing.

#### Scenario: Refinement setup is requested without a study authorization
- **WHEN** the 1/2/4/8 setup helper is invoked
- **THEN** it verifies geometry and remap conservation, performs zero solver steps, and reports spatial independence as not evaluated.

### Requirement: Partial execution classifications are explicit
New execution results MUST distinguish successful completion, timeout, cancellation, operational/resource failure, audit failure, and numerical failure. A partial result MUST NOT be represented as complete.

#### Scenario: Execution ends before enough periodic comparisons exist
- **WHEN** no period is accepted and fewer than two complete cycles were evaluated
- **THEN** the result reports insufficient evidence separately from timeout, cancellation, or numerical failure.

#### Scenario: A comparison record violates periodicity identity
- **WHEN** the detector emits an invalid comparison because a cycle identity or contract is incompatible
- **THEN** the result classifies invalid comparison evidence and does not treat it as an executed non-periodic result.
