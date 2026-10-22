## ADDED Requirements

### Requirement: Reproducible length-only exhaust variant
The system SHALL reuse existing projects and variants and preserve non-exhaust parameters, primitive initial conditions and cell counts while editing one exhaust section length.

#### Scenario: Existing partitioned exhaust
- **GIVEN** the delivery1 engine with31 exhaust cells and7 sections
- **WHEN** its header length changes from83 to103mm
- **THEN** the saved variant SHALL retain31 cells and all other engine parameters, with extensive initial inventories scaled only by changed volume

### Requirement: Real bounded Desktop comparison
The system SHALL execute both variants from identical initial primitives at9000RPM with the unchanged periodicity detector and equal caps of30cycles,300seconds and512MiB each.

#### Scenario: Nonperiodic A/B
- **WHEN** either point finishes without contractual periodicity
- **THEN** pressure and transient cycle diagnostics SHALL remain visible while definitive power and torque curves retain gaps and no RPM grid SHALL start

### Requirement: Recoverable comparison in existing workflow
The system SHALL save comparison references with hashes in the existing project and reopen them through the existing verified importer.

#### Scenario: Saved result changes
- **WHEN** a referenced result hash changes
- **THEN** recovery SHALL reject the comparison without silently loading the changed data

### Requirement: Existing coordinator compatibility
The system SHALL use the existing RPM coordinator for both supported point schemas without claiming independent audit for engineering runs.

#### Scenario: Completed engineering point reuse
- **WHEN** a completed engineering point is resumed through its existing sweep manifest
- **THEN** its result, samples and isolated checkpoint SHALL be verified before reuse, without repeating completed cycles
