## ADDED Requirements

### Requirement: Single verified reference selection
The assessment SHALL select one real single-cylinder two-stroke engine and distinguish manufacturer nominal dimensions, homologation limits, measured test inputs, estimates and unknowns using accessible primary sources.

#### Scenario: Published nominal dimensions
- **WHEN** a manufacturer drawing is available
- **THEN** it SHALL NOT be presented as measurements of a different experimental specimen without a documented identity link

### Requirement: Independent comparison eligibility
A future validation SHALL use the same hardware, operating condition and power measurement plane, with declared uncertainty and a held-out result that was not used to tune the prediction.

#### Scenario: Incomplete experiment package
- **WHEN** fundamental specimen or measurement data remain unavailable
- **THEN** selection SHALL remain distinct from validation readiness and the report SHALL state a finite acquisition or measurement package

### Requirement: No scientific execution in selection
This work SHALL preserve solver, model coefficients, historical evidence and Desktop and SHALL NOT execute simulations, add features or reopen STANDARD_V1.

#### Scenario: Finish bounded search
- **WHEN** sources, selection and comparison criteria are documented
- **THEN** the assessment SHALL close without starting another campaign or contacting third parties
