# exhaust-numerical-convergence-v2 Specification

## ADDED Requirements

### Requirement: Current implementation identity
The diagnostic evidence MUST bind to the final adapter and solver source hashes actually used. Earlier EXHAUST_MESH_V1 evidence MUST remain attributed to its original adapter hash and MUST NOT be relabeled as current-hash evidence. Geometry, conservative remapping, variable-area source, interfaces, boundaries, and checkpoint compatibility MUST be verified.

#### Scenario: Final adapter verification
- **WHEN** the final adapter is compared with the prior diagnostic implementation
- **THEN** source-level changes and focal regression results are recorded under the actual current hash
- **AND** historical results retain their original identity.

### Requirement: Controlled duct verification
Before engine comparisons, exercise a constant-area duct, small pressure-pulse propagation, a known reflecting boundary, and a section-area transition. Compare analytic solutions where applicable and otherwise a justified refined numerical reference. Measure propagation speed/time, amplitude, reflection/transmission, conservation, diffusion/dispersion, CFL, and timestep sensitivity. Spatial and temporal errors MUST be separated.

#### Scenario: Wave and reflection tests
- **WHEN** a small pulse is propagated through a constant-area duct and toward a known boundary
- **THEN** arrival time, amplitude, reflected wave, and conservation are compared to analytic expectations or a justified reference.

### Requirement: Variable-area verification
Area-transition tests MUST evaluate transmission/reflection and geometric conservation using the solver's existing variable-area formulation. The test MUST state whether the transition is a sharp discontinuity or a resolved smooth profile and MUST not claim a discontinuity solution for a smooth geometry.

#### Scenario: Section transition
- **WHEN** the pulse crosses a declared section-area transition
- **THEN** measured incident, reflected, and transmitted signals are compared against a matching analytical model or refined reference.

### Requirement: Separated refinement
Spatial mesh refinement and temporal timestep refinement MUST be evaluated separately. Resolutions 1/2/4/8 cells per section are allowed; finer references require justification. Richardson extrapolation or GCI MUST NOT be used without justified asymptotic conditions.

#### Scenario: Space and time sensitivity
- **WHEN** spatial and temporal resolution are varied independently
- **THEN** the resulting error trends and any unresolved interaction are reported without treating a single decreasing difference as proof of convergence.

### Requirement: Bounded A/B refinement
If controlled duct tests are interpretable and budget remains, the diagnostic MUST compare both exhaust designs at 3000 RPM on 1/2/4/8 meshes with all non-mesh engine inputs and initial states physically equivalent. Compare common physical coordinates using an explicit interpolation rule. Report differences within each design separately from A/B differences, along with conservation, CFL/rejections, costs, hashes, and provenance. No periodicity may be inferred from short transients.

#### Scenario: Conditional A/B diagnostic
- **WHEN** controlled tests are interpretable and the aggregate time budget permits the matrix
- **THEN** the bounded A/B cases run with equivalent conditions and explicit spatial interpolation
- **AND** otherwise the matrix is skipped with remaining budget and the blocker recorded.

### Requirement: Diagnostic budget and classification
New solver diagnostic wall time MUST remain within 1800 seconds aggregate and stop at the cap. Controlled tests take priority; a blocking defect stops the A/B matrix. Findings MUST distinguish implementation defect, method limitation, transient, insufficient resolution, and inconclusive evidence.

#### Scenario: Budget cap
- **WHEN** accumulated new solver diagnostic wall time reaches 1800 seconds
- **THEN** no additional solver diagnostic is launched and the evidence records consumed time.

### Requirement: Historical and claim protection
Historical R2, IMPL2, and EXHAUST_MESH_V1 evidence, contracts, hashes, and classifications MUST remain immutable. This objective MUST NOT run a full RPM campaign or KT100, fabricate periodicity, claim spatial independence without sufficient evidence, or claim experimental validation. Scientific fixes require a separately versioned implementation with regression tests and no relaxed physics or hard gates.

#### Scenario: Historical evidence protection
- **WHEN** new convergence evidence is produced or a solver defect is encountered
- **THEN** historical artifacts remain unchanged and any scientific fix receives a new versioned identity.

### Requirement: Reproducibility and final checks
Tests MUST cover wave propagation/reflection, variable area, refinement, timestep sensitivity, conservation, scientific identity, checkpoint/restart, reproducibility, and Desktop integration at a scope appropriate to the change. OpenSpec strict and program-status checks MUST pass before final classification. Ostacky files MUST remain unstaged, and no push is permitted.

#### Scenario: Diagnostic closure
- **WHEN** implementation and bounded diagnostics are complete or blocked
- **THEN** tests, source/configuration hashes, timing, classifications and limitations are persisted, strict checks pass, and no Ostacky file is staged.
