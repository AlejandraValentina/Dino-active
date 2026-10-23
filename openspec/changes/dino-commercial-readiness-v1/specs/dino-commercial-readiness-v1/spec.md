# DINO Commercial Readiness V1 Specification

## ADDED Requirements

### Requirement: Start a design without a reference fixture
The Windows application SHALL let a user start a new project through a guided form for a supported single-cylinder, two-stroke engine using the existing integrated configuration adapter. The form MAY use a built-in structural starter template when it clearly identifies its default geometry and model choices as assumptions. A new project SHALL contain no historical run references. The UI SHALL distinguish measured, estimated and assumed inputs and SHALL NOT label assumptions as measurements.

#### Scenario: New project from the application
- **WHEN** the user selects `Nuevo proyecto`
- **THEN** the application opens the guided design form and identifies the starter values and topology as assumptions
- **AND** confirmation creates a fresh project with no historical run references, with a supported engine validated from visible UI controls and no file editing

### Requirement: Edit supported engine geometry and distribution
The engine editor SHALL expose the solver-supported bore, stroke, rod, chamber and crankcase volumes, operating conditions, port geometry and intake-control choices. It SHALL show calculated displacement, compression ratios and supported event/area quantities, validate impossible configurations through the existing backend, and identify input provenance. Controls that do not affect the selected physical configuration SHALL not be presented as editable physical inputs.

#### Scenario: Configure a coherent engine
- **WHEN** the user enters engine geometry, exhaust and transfer port dimensions, intake control and operating conditions
- **THEN** derived values update from the supported backend geometry
- **AND** invalid geometry is rejected before execution with an actionable UI message

### Requirement: Configure exhaust geometry through the existing solver binding
The exhaust editor SHALL expose supported sections and dimensions using the existing geometry adapter. A saved geometry change SHALL be present in the exact engine configuration passed to `IntegratedEngine2T`; unsupported sections SHALL not appear as active controls.

#### Scenario: Change one exhaust dimension
- **WHEN** a user changes a section dimension and saves a variant
- **THEN** the rendered geometry and dimension summary reflect the change
- **AND** the executable solver configuration contains that same geometry

### Requirement: Run and inspect an integrated exploratory point
The user SHALL be able to select a motor, a point RPM or supported RPM interval/resolution, a bounded execution budget, stop criteria and cancellation/recovery controls through the current coordinator. Results that do not meet existing periodicity criteria SHALL remain explicitly exploratory/transient. Only calculated, provenance-backed quantities SHALL be displayed.

#### Scenario: Run a brief point
- **WHEN** a user runs a bounded point from a new project
- **THEN** progress, cycles, pending work and available results remain visible and cancellation/recovery use the existing coordinator
- **AND** the result is not presented as periodic unless the existing contractual criteria are satisfied

### Requirement: Compare saved design variants
The analysis workspace SHALL compare two or more saved variants at matching RPM using available stored power, torque and pressure samples, identify changed geometry, and preserve the baseline configuration. Missing metrics and mismatched conditions SHALL be identified without interpolation or causal claims.

#### Scenario: Compare an exhaust modification
- **WHEN** the user duplicates a configured engine, changes an exhaust dimension and runs both variants
- **THEN** the application shows available same-RPM differences and the geometric changes while preserving the original baseline

### Requirement: Windows acceptance from a new project
Acceptance SHALL start from the packaged Windows executable and a new project, create and save a supported engine through the UI, run a bounded integrated exploratory point, duplicate the design, change exhaust geometry, run and compare the variant, then close and recover the saved project. The acceptance SHALL record screenshots, actual solver outputs, save/reopen results and observed runtime. The package SHALL be identified as TRIAL unless its source tree is clean. No manual JSON, script or database intervention is allowed in this workflow.

#### Scenario: Reopen the demonstrated comparison
- **WHEN** the user closes and reopens the saved project in the packaged executable
- **THEN** the project, variants, run references and available comparison are recovered with their identity checks intact
- **AND** all claims remain limited to functional trial evidence, with experimental validation pending
