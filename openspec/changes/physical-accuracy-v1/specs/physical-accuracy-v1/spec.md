## ADDED Requirements

### Requirement: Quantitative existing-result diagnosis
The assessment SHALL explain IMEP, BMEP, fresh delivery and trapped charge, burned residuals, oxygen-limited fuel, heat, work and mechanical losses from existing periodic evidence without modifying that evidence or the solver.

#### Scenario: Distinguish arithmetic from physical validation
- **WHEN** work and energy balances close
- **THEN** the report SHALL retain existing audit qualifications and SHALL NOT claim experimental accuracy, mesh independence or uniquely identified causal parameter effects

### Requirement: Reproducible experimental comparison
A reference run SHALL require sufficient original experimental inputs to represent the same engine and operating condition without inventing fundamental geometry or calibration data.

#### Scenario: Reference inputs inaccessible or incomplete
- **WHEN** the accessed sources do not support an exact experimental reproduction
- **THEN** the assessment SHALL state missing inputs, run no purported validation point and leave quantitative predictive accuracy undetermined

### Requirement: Bounded technical closure
The assessment SHALL end with a concrete technical conclusion and preserve functional Desktop, historical gates and evidence; it SHALL NOT initiate an open-ended campaign or tune coefficients to a target power.

#### Scenario: Complete assessment with unresolved accuracy
- **WHEN** balances and reference adequacy have been evaluated
- **THEN** assessment completion SHALL remain distinct from experimental validation and SHALL NOT authorize another campaign or a solver reconstruction
