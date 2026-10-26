## ADDED Requirements

### Requirement: Owner-approved request package
The work SHALL record the owner's authorization, recipients, subject, body, source hashes and delivery status. It SHALL prepare a send-ready package but SHALL NOT claim the message was delivered until the owner confirms delivery.

#### Scenario: Agent has no email channel
- **WHEN** the package is approved but the agent cannot send email
- **THEN** delivery status SHALL remain `APPROVED_NOT_SENT` and the next action SHALL be assigned to the owner

### Requirement: Boundary-explicit precompression volume
Any accepted crankcase free gas volume SHALL state the crank angle, the measurement or manufacturer definition, and whether inlet and transfer volumes are included. A value without that definition SHALL NOT be used.

#### Scenario: Partial public dimensions
- **WHEN** public drawings do not determine the connected free volume
- **THEN** the value SHALL remain unknown and no primary compression ratio SHALL be borrowed from another engine

### Requirement: Frozen configuration before execution
The work SHALL freeze one revision-coherent X30 configuration only after the volume and boundary definition are accepted. Every non-measured quantity SHALL be an explicit, dated assumption; no hidden defaults and no fitting to the published power curve.

#### Scenario: Missing secondary geometry
- **WHEN** transfer lengths/sections or installed intake/exhaust details remain unknown
- **THEN** they SHALL be declared assumptions or remain blocked, not silently replaced with STANDARD_V1 values

### Requirement: One bounded point
The work SHALL authorize at most one 9000 RPM WOT point using the existing integrated runner and current periodicity criteria. Time and cycle limits SHALL be fixed before execution. No new models, solver changes or RPM sweep are permitted.

#### Scenario: Non-periodic result
- **WHEN** the single point does not satisfy the periodicity criteria
- **THEN** it SHALL be classified as a transient estimate and SHALL NOT be presented as a periodic result

### Requirement: Exploratory comparison only
The calculated power/torque SHALL be compared with the published 15.1 +/- 0.3 kW graphical readout as an exploratory reference. The 0.3 kW digitization bound SHALL NOT be treated as experimental U95, and no 5% validation claim SHALL be made.

#### Scenario: Shaft versus indicated power
- **WHEN** the measured plane or mechanical losses are not confirmed
- **THEN** indicated work and shaft power SHALL remain separate and the discrepancy SHALL NOT be attributed to one component

### Requirement: Scope preservation
The work SHALL NOT modify the solver or coefficients, fabricate X30 geometry, search other engines, run a sweep, add product features, or push to a remote.

#### Scenario: Requested data does not arrive
- **WHEN** the external data remains unavailable
- **THEN** the objective SHALL remain blocked with the missing quantity and a local measurement procedure, without a synthetic X30 substitute
