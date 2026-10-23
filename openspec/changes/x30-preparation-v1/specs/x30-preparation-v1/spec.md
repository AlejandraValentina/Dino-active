## ADDED Requirements

### Requirement: Unsent focused author request
The preparation SHALL provide a concise professional email requesting only shareable X30 data sufficient for one operating condition, and SHALL NOT send it.

#### Scenario: Restricted original dataset
- **WHEN** original files cannot be shared
- **THEN** the draft SHALL accept a non-confidential subset without demanding new documentation

### Requirement: Qualified graphical experimental evidence
Any Figure10 extraction SHALL identify the published measured series, record axes and provenance, distinguish curve readouts from original samples and separate digitization bounds from experimental uncertainty.

#### Scenario: Continuous measured-series line without acquisition markers
- **WHEN** a value is read at a selected RPM
- **THEN** it SHALL NOT be presented as an independently recovered original measurement at that exact RPM

### Requirement: Traceable incomplete configuration
The X30 inventory SHALL separate documented, geometrically derived and unknown parameters under an identified manufacturer revision without filling missing values or fitting coefficients to power.

#### Scenario: Fundamental geometry absent
- **WHEN** operational volumes or connecting geometry remain unspecified
- **THEN** the inventory SHALL remain non-executable and SHALL identify finite missing inputs separately from possible preliminary assumptions

### Requirement: No execution or feature expansion
The preparation SHALL define one minimal future point and SHALL preserve solver, model coefficients and historical evidence without simulation, new audit campaigns or product features.

#### Scenario: Public trends available before exact reconstruction
- **WHEN** a published measured curve is readable
- **THEN** approximate trends SHALL remain usable with their limitations and SHALL NOT be promoted to predictive validation
