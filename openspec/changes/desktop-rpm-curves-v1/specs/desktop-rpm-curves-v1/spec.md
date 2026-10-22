## ADDED Requirements

### Requirement: Explicit verified completed point reuse
The existing coordinator SHALL reuse only explicitly selected results with compatible project, variant, RPM, configuration, implementation and horizon identities, verifying artifacts before any solver step.

#### Scenario: Reuse9000RPM
- **GIVEN** the delivery2 A/B9000 results
- **WHEN** the grid8000/9000/10000 is executed
- **THEN** only8000 and10000 SHALL execute from initial state for each variant and9000 artifacts SHALL remain unchanged

### Requirement: Honest exploratory display
The existing power and torque plot SHALL display transient estimates only under an explicit exploratory display mode with hollow markers and dotted segments, separate from periodic points.

#### Scenario: Missing or nonperiodic points
- **WHEN** a point is missing, invalid or nonperiodic
- **THEN** missing and invalid points SHALL remain gaps and nonperiodic estimates SHALL retain original scientific statuses and SHALL NOT be relabeled converged

### Requirement: Bounded recoverable integrated execution
The system SHALL reuse existing Desktop, projects, histories, checkpoints and the RPM coordinator with30cycles/300s per new point,650s cumulative per variant and512MiB sequential for this demonstration.

#### Scenario: Cancel and resume
- **WHEN** a sweep is interrupted
- **THEN** completed points SHALL be verified and reused, incomplete compatible checkpoints SHALL resume and elapsed budgets SHALL remain cumulative

### Requirement: Scientific status and equal-RPM comparison
The system SHALL report global periodicity separately from observed work, power and trapped-charge variation, exact equal-RPM deltas, pressures and execution times.

#### Scenario: Unresolved periodicity
- **WHEN** the grid remains nonperiodic
- **THEN** exploratory results SHALL remain visible without a predictive claim and the report SHALL name the unresolved variables and discretization limitations without extending the campaign

### Requirement: Explicit control map coverage
The system SHALL reject out-of-map RPM unless an explicit POWERVALVE_OPEN_ENDPOINT_HOLD_V1 policy extends an already fully open upper endpoint to the selected maximum RPM. Existing in-range point configurations SHALL remain unchanged.

#### Scenario:10000RPM upper map limit
- **GIVEN** the synthetic valve is fully open at9500RPM
- **WHEN** the declared endpoint-hold policy authorizes10000RPM
- **THEN** the effective10000RPM configuration SHALL explicitly include that open endpoint with synthetic provenance while9000RPM retains its original identity
