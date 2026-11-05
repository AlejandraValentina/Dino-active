# Platform integration audit and scientific replan v1

## ADDED Requirements

### Requirement: revision-bound audit before replanning
The system SHALL retain the frozen audit scope and evidence distinctions in `results/platform-integration-audit-v1/protocol.md`.

#### Scenario: an A/B-only capability is inspected
- **WHEN** a capability is absent from main and present on the A/B branch
- **THEN** the report SHALL attribute it to the A/B revision and SHALL NOT upgrade main.

### Requirement: prospective unified scientific plan
The plan SHALL preserve frozen 2T evidence and define independent 4T numerical and measured-validation obligations, without launching product changes or campaigns.

#### Scenario: audit findings remain open
- **WHEN** the audit/replan deliverable is completed with confirmed defects
- **THEN** its delivery gate MAY pass but the product/scientific verdict SHALL retain those defects.
