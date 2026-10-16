# DINO Stage 1 Scientific Readiness

## ADDED Requirements

### Requirement: Scientific diagnostics preserve numerical error categories
Any future bounded diagnostic MUST separate spatial discretization, temporal discretization, boundary-condition effects, implementation defects, physical-model limits, and insufficient/inconclusive evidence. It MUST record the tested configuration, implementation identity, observables, budget and provenance. Historical evidence MUST retain its original hashes and classifications.

#### Scenario: Refinement does not establish convergence
- **WHEN** measured changes across resolutions are nonmonotonic or larger than the design response
- **THEN** classify spatial independence as NOT_ESTABLISHED or PARTIAL and do not infer a physical design effect independent of mesh error.

### Requirement: Periodicity is an explicit prerequisite for cycle metrics
Every performance result that requires a periodic cycle MUST bind to a periodicity evaluation over consecutive cycles using declared state and integral observables and tolerances. Not evaluated, not identified, budget-limited, and nonconverged states MUST remain distinct and MUST NOT be represented as periodic.

#### Scenario: Horizon ends before periodicity
- **WHEN** an authorized bounded run reaches its horizon without meeting the periodicity detector
- **THEN** preserve its valid transient evidence and classify periodicity as not converged/budget-limited; do not promote cycle metrics that require periodic operation.

### Requirement: Conservation and performance consistency remain independently auditable
Verification MUST check mass, energy and species ledgers at relevant coupled interfaces and replay persisted evidence independently. IMEP, FMEP, BMEP, torque, power, and consumption MUST retain their physical definitions, units, source data, and undefined reasons. Passing conservation alone MUST NOT be treated as validation of physical accuracy.

#### Scenario: A performance metric is undefined
- **WHEN** required periodicity, input model, sign condition or source magnitude is absent or invalid
- **THEN** persist an explicit undefined/invalid state and reason; do not synthesize a numeric value.

### Requirement: RPM readiness is separate from campaign authorization
The RPM sweep contract and preflight MUST identify solver/configuration/model hashes, RPM grid, WOT and boundary conditions, fuel/AFR, explicit mechanical-loss model, periodicity, conservation, output units, workers/resources, checkpoints, artifact root, per-invocation and global budgets, and failure classifications. Completing readiness MUST NOT authorize or start a campaign.

#### Scenario: Contract is ready but campaign is not authorized
- **WHEN** all configuration preflight checks pass but no matching campaign authorization exists
- **THEN** report readiness separately and keep all campaign points NOT_STARTED.
