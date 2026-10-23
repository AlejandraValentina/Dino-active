## ADDED Requirements

### Requirement: Public nominal data reconciliation
The review SHALL incorporate verified MAN089, article and254V nominal values with source revision and measurement conventions, while distinguishing nominal values, regulatory limits and measured experimental specimen data.

#### Scenario: Different timing tolerances
- **WHEN** an earlier manual timing tolerance exceeds a later homologation maximum
- **THEN** the source roles and revisions SHALL remain explicit without silently merging their allowable ranges

### Requirement: Mandatory bounded reconstruction decision
The work SHALL conclude either A with a statically checked executable nominal configuration and explicit assumptions or B with exactly identified essential geometric data that cannot reasonably be derived from the accessed drawings.

#### Scenario: Unidentified precompression free volume
- **WHEN** available projections and partial dimensions do not determine the connected gas volume
- **THEN** the review SHALL preserve that input as unknown and SHALL NOT borrow a primary compression ratio from another engine

### Requirement: Preserve scientific scope
The work SHALL preserve existing inventories and historical evidence, SHALL NOT modify solver or coefficients, and SHALL NOT simulate, fit power, add features or search other engines.

#### Scenario: Decision B data request
- **WHEN** an essential geometric input remains missing
- **THEN** the existing email draft SHALL be refined to request the minimal shareable quantity without sending it or launching another research campaign
