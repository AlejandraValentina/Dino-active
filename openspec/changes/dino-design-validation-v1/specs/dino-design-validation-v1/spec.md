# DINO_DESIGN_VALIDATION_V1 Specification

## ADDED Requirements

### Requirement: Editable design propagation is physically traceable
Every editable property declared solver-supported MUST be traced from the saved project and selected variant to the effective native IntegratedEngine2T configuration and actual solver state. A hash change alone is not evidence of physical influence. Unsupported, display-only, approximated, or ignored properties MUST be identified accurately. Fixes MUST be versioned and MUST NOT silently alter governing equations or physical acceptance criteria.

#### Scenario: Change a solver-supported exhaust parameter
- **WHEN** a user changes a supported section length or diameter
- **THEN** the effective section geometry, solver mesh/binding and relevant solver boundary data change and are inspectable.

### Requirement: Controlled exhaust sensitivity evidence
A bounded diagnostic comparison MUST use one engine, timing/distribution, combustion, fuel, operating conditions and boundary conditions with only a controlled exhaust geometry change. It MUST establish distinct geometry and numerical meshes, exercise the actual 1D solver, and report pressure/wave/flow response, primary evidence audit, conservation, reproducibility, resources and convergence. A performance improvement MUST NOT be assumed. Transient/non-periodic power MUST NOT be represented as steady performance.

#### Scenario: Compare base and modified exhaust
- **WHEN** both configurations run under the same bounded diagnostic setup
- **THEN** the recorded physical response differences and numerical variability are reported, or the model limitation preventing a physical conclusion is named.

### Requirement: Preserve versioned powervalve correction and history
The integrated constant-RPM powervalve MUST use the versioned configured-RPM endpoint resolution already present where appropriate, and tests MUST cover exact endpoints, near-boundary roundoff, genuinely out-of-range rejection and interior behavior. Historical FULL_RPM_SWEEP classifications and artifacts MUST remain unchanged.

#### Scenario: Evaluate an RPM map boundary
- **WHEN** configured RPM equals a map endpoint or is genuinely outside the domain
- **THEN** endpoint resolution succeeds while out-of-domain values still fail closed, and historical campaign results are not rewritten.

### Requirement: Result semantics remain explicit
Desktop results MUST distinguish EXPLORATORY from verified evidence, periodic from non-periodic, audited from unaudited, individual hard gates, experimental measurements and synthetic calculations, and invalid/missing points. Missing values MUST remain gaps with no interpolation or experimental claim.

#### Scenario: View diagnostic variant outputs
- **WHEN** results are plotted or compared
- **THEN** provenance, classification, periodicity, audit status and validity are visible and invalid/missing data remain absent.

### Requirement: Experimental data contract without validation claim
The application MUST define an import contract for measured RPM, torque, power, test conditions, units, uncertainty and provenance, and MUST keep those measurements separate from synthetic model outputs. Error metric definitions may be prepared, but experimental validation MUST remain unclaimed until suitable real data are supplied and evaluated under an authorized contract.

#### Scenario: Import a measured dataset
- **WHEN** a user imports an experimental table
- **THEN** schema, units, uncertainty and provenance are validated and the source values remain distinct from computed results; no validation status is created.
