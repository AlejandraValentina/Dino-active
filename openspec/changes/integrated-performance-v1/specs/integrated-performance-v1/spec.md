## ADDED Requirements

### Requirement: Measured optimization
The implementation SHALL profile the real integrated execution before changing hot paths and SHALL compare unprofiled end-to-end runs on identical existing configurations. Instrumented profiling SHALL NOT supply the speedup denominator.

#### Scenario: Redundant thermal validation
- **WHEN** the integrated stage evaluates the surfaces of a validated thermal system
- **THEN** all surfaces SHALL remain validated in that stage, while redundant complete-system scans MAY be eliminated without changing floating-point heat evaluation or custom-system behavior

### Requirement: Preserved numerical behavior
The comparison SHALL preserve equations, mesh, boundaries, species transport, coefficients, tolerances, periodicity and conservation controls. It SHALL compare complete checkpoint states, ledgers and timing-independent diagnostics for both existing exhaust variants.

#### Scenario: New source identity
- **WHEN** optimized source differs from a checkpoint producer
- **THEN** incompatible historical checkpoints SHALL remain fail-closed, historical source and artifacts SHALL remain available, and same-identity restart SHALL be checked against uninterrupted execution

### Requirement: Bounded evidence and honest projection
Diagnostics SHALL use the declared sequential memory and wall limits, retain raw evidence outside Git, separate solver and processing costs, and label any full-curve time estimate as a projection rather than a measured campaign.

#### Scenario: Short benchmark
- **WHEN** three-cycle A/B diagnostics demonstrate equivalent numerical output and reduced wall time
- **THEN** the result SHALL describe that workload and SHALL NOT claim a newly measured periodic curve or experimental physical validation

### Requirement: Frozen experimental reconstruction
The X30 inventory, sources and unsent email SHALL remain preserved pending external precompression geometry. This change SHALL NOT simulate X30, send the email, search other engines or add unrelated infrastructure.

#### Scenario: Missing crankcase volume
- **WHEN** the external geometry remains unavailable
- **THEN** X30 SHALL remain blocked without an invented value
