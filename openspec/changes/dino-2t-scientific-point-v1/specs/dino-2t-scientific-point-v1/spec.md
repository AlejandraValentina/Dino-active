# DINO 2T Scientific Point V1

## ADDED Requirements

### Requirement: Baseline and performance evidence are bounded and reproducible
Profiling MUST identify the selected configuration, implementation identity, instrumentation overhead, wall/CPU time, steps, cycle timing, and memory. Component attribution MUST distinguish temporal integration, ducts/waves, boundaries/flows, species, thermodynamics, audit/replay, and checkpoint/serialization where the instrumentation permits. Microbenchmark results MUST NOT be represented as end-to-end solver improvements.

#### Scenario: Existing 48-cell focal is used as reference
- **WHEN** its historical results are inspected
- **THEN** its four-cycle, 600-second-budget timeout and measured overrun remain immutable and are not resumed or treated as a new baseline.

### Requirement: Geometry identity is explicit and independently testable
The current solver identity MUST be hashed from actual source and configuration. Historical IMPL2 bindings MUST remain unchanged. Power-valve area semantics MUST be compared against an analytical geometry reference at opening, closing, interpolation boundaries, and map endpoints. Checkpoints with incompatible producer identity MUST be rejected.

#### Scenario: Historical implementation hash differs
- **WHEN** current source does not match the frozen IMPL2 hash
- **THEN** no hash override or historical checkpoint reuse is allowed; any derivative identity is recorded separately.

### Requirement: Periodicity reports observations separately from acceptance
New results MUST retain complete-cycle counts, lag-1/lag-2 residual evidence, thresholds, detector identity, accepted period if any, and termination reason. Evaluation, acceptance, observed non-periodicity over the available horizon, insufficient evidence, and budget termination MUST remain distinct. Existing thresholds and historical receipts MUST NOT be changed.

#### Scenario: Comparisons fail before timeout
- **WHEN** valid cycle comparisons exist but no period is accepted before termination
- **THEN** the result records the comparisons and classifies the observed outcome and timeout separately; it does not report an accepted steady state.

### Requirement: Mesh infrastructure does not imply mesh independence
Any refinement comparison MUST keep physical configuration fixed, record spatial and temporal resolution/CFL, compare quantitative pressure-wave amplitude, phase, propagation and conservation, and distinguish temporal and boundary errors. Independence MUST NOT be claimed without a preregistered study passing its criteria.

#### Scenario: Only infrastructure has been exercised
- **WHEN** no authorized refinement campaign has run
- **THEN** spatial independence remains NOT_EVALUATED or NOT_ESTABLISHED.

### Requirement: Integrated scientific point execution is explicitly authorized
The point preflight MUST bind solver identity, engine configuration, RPM, geometry/mesh, initial state, detector and thresholds, conservation gates, wall-time and memory budgets, maximum cycles, timeout/checkpoint policy, and terminal classifications. A real solver run MUST NOT start until a durable authorization explicitly binds this preflight and resource budget. No missing fuel, mechanical-loss model, or physical coefficient may be invented.

#### Scenario: Preflight is ready without run authorization
- **WHEN** the configuration passes preflight but there is no matching durable authorization
- **THEN** the run is rejected before solver advancement and the state remains implementation-ready or partial, not scientifically accepted.

### Requirement: Scientific metrics require accepted periodicity and valid inputs
IMEP, FMEP, BMEP, torque, power, and specific consumption MUST follow existing contracts. Undefined or unavailable inputs MUST remain undefined, and regime-dependent metrics MUST NOT be accepted without the required periodicity and valid explicit fuel/loss inputs.

#### Scenario: Periodicity or fuel/loss inputs are unavailable
- **WHEN** a run ends without accepted periodicity or explicit valid inputs
- **THEN** dependent performance metrics remain undefined and the result is classified with its actual evidence.

