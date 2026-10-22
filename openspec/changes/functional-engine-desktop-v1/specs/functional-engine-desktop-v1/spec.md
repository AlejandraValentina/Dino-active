## ADDED Requirements

### Requirement: Explicit physical gas-exchange configuration
The system SHALL activate corrected connections only under a versioned explicit
contract, preserving legacy interpretation when the contract is absent.

#### Scenario: Reed intake and asymmetric transfer connections
- **GIVEN** a GAS_EXCHANGE_V2 engine with declared reed intake
- **WHEN** piston position closes the legacy inlet or cylinder transfer window
- **THEN** reed intake SHALL depend on pressure and reed area, and the transfer
  crankcase endpoint SHALL remain connected through its duct section

### Requirement: Conservative coupled scavenging
The system SHALL apply its documented partial-mixing law during SSPRK species
transport and SHALL keep outlet rates bounded by available donor inventories.

#### Scenario: Preferential spent-gas outflow
- **GIVEN** fresh and spent species and an explicit mixing fraction
- **WHEN** gas exits the cylinder during transfer and exhaust overlap
- **THEN** the closure SHALL modify emitted composition while preserving total
  mass flux and paired receiver increments without artificial species sources

### Requirement: Existing desktop execution path
The system SHALL reuse project, execution, checkpoint, history and results
components for engineering runs, without mandatory replay or independent audit.

#### Scenario: Open engine, simulate and inspect
- **GIVEN** an executable saved reed-engine project
- **WHEN** the user starts and then selects its completed run from history
- **THEN** Desktop SHALL display calculated signals and physical estimates with
  explicit periodicity and audit states

### Requirement: Honest nonconverged results
The system SHALL keep nonconverged power out of definitive curve series.

#### Scenario: Horizon completed without periodicity
- **WHEN** the engine reaches its configured horizon without periodicity
- **THEN** results SHALL label estimates as transient and nonconverged and SHALL
  NOT claim predictive or experimental validation
