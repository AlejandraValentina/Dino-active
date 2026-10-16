# DINO 2T Solver Diagnostic Recovery V1

## ADDED Requirements

### Requirement: Bounded diagnostics preserve scientific identity
Diagnostics MUST use bounded, explicitly identified fixtures or existing artifacts and MUST record measured scope, resource method, source identity and limitations. They MUST NOT resume the exhausted Stage 1 run, start RPM campaigns, or silently change historical preregistrations, physics, discretization, thresholds or numerical tolerances.

#### Scenario: Existing evidence is sufficient for a classification
- **WHEN** a historical receipt conclusively records a timeout, resource sample or hash mismatch
- **THEN** reuse that evidence and do not repeat the expensive numerical execution.

### Requirement: Performance claims identify measured boundaries
Profiling MUST distinguish solver work from evidence audit, serialization, checkpoint persistence and process overhead when the measurement supports that separation. Fixture or microbenchmark measurements MUST NOT be extrapolated as campaign runtime claims.

#### Scenario: A fixture is faster than production
- **WHEN** a reduced test configuration is profiled
- **THEN** label it as a fixture measurement and report its mesh, cycles and excluded costs.

### Requirement: Periodicity reports distinguish evaluation from acceptance
Reports MUST preserve the existing periodicity contract and thresholds. They MUST distinguish an executed comparison with no accepted period yet from a detector that was never run, using a versioned reporting layer if existing artifacts conflate those states.

#### Scenario: Execution stops before the horizon
- **WHEN** completed cycles were fed to the detector but a timeout occurs before a period is accepted
- **THEN** preserve the comparison metrics and classify the run as interrupted without claiming periodicity or rewriting the historical `NOT_EVALUATED` field.

### Requirement: Mesh independence requires a preregistered multi-resolution protocol
Any future mesh study MUST freeze configurations, resolution ratios, observables, uncertainty/tolerance rationale, temporal controls and budgets before execution. Similar plotted curves alone MUST NOT establish spatial independence.

#### Scenario: Refinement budget is unavailable
- **WHEN** the available budget does not support all preregistered resolutions
- **THEN** retain `NOT_ESTABLISHED` and do not launch a partial study that cannot answer the registered question.

### Requirement: Windows runner output cannot fail on console encoding
The logged child-process runner MUST capture Unicode output under legacy Windows console code pages without changing child exit codes or scientific artifacts.

#### Scenario: Child prints a non-CP1252 symbol
- **WHEN** a Python diagnostic writes a scientific symbol while its parent console is cp1252
- **THEN** the logged output is retained as UTF-8 and the child exit code is preserved.
