# DINO 2T Professional Roadmap (proposed)

## ADDED Requirements

### Requirement: Stage gates preserve scientific claim boundaries
Any future stage under this roadmap MUST distinguish implementation, numerical verification, physical validation, experimental validation, and product/package acceptance. A stage MUST NOT be promoted from tests or UI completeness alone. Historical contracts, artifacts and classifications MUST retain their original identity.

#### Scenario: Review a stage result
- **WHEN** a stage proposes an engineering or scientific claim
- **THEN** its evidence, scope, limitations and applicable independent acceptance are recorded separately, and unsupported claims remain explicitly unvalidated.

### Requirement: RPM curves retain point provenance and failure states
Any future RPM curve MUST be assembled only from actual authorized simulations bound to one declared configuration and implementation identity. Periodicity, conservation, audit and scientific classification MUST be retained per point. Missing, invalid, nonconverged or undefined data MUST remain explicit and MUST NOT be interpolated into computed results.

#### Scenario: A sweep contains a failed point
- **WHEN** one authorized operating point fails or lacks an accepted performance metric
- **THEN** the curve preserves a gap and the point's actual classification and reason.

### Requirement: Design diagnostics trace to computed observables
Any future design diagnosis MUST link its statements to reproducible solver outputs under controlled configurations. Heuristic explanations MUST be identified as hypotheses and MUST NOT be represented as demonstrated physical causes.

#### Scenario: Compare two designs
- **WHEN** a diagnostic compares variants
- **THEN** it records changed inputs, common conditions, output provenance and numerical limitations, and does not infer causality beyond that evidence.

### Requirement: Calibration and optimization use independent evaluation
Any future calibration or optimization claim MUST record the objective, constraints, source runs, model identity and uncertainty. Acceptance MUST include evaluation data independent of data used to fit parameters; absence of such data MUST prevent an experimental-validation or commercial-accuracy claim.

#### Scenario: Evaluate a calibrated candidate
- **WHEN** fitted parameters are assessed
- **THEN** the fit and independent evaluation datasets are distinguished and results remain traceable to source measurements and simulations.
