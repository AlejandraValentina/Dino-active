## ADDED Requirements

### Requirement: Current integrated Windows runtime
The package SHALL execute the current integrated solver and existing Desktop workflow, including optimized thermal evaluation, species, gas exchange, combustion, power, restart and RPM comparison. It SHALL preserve all physics and hash checks.

#### Scenario: Frozen producer sources
- **WHEN** the packaged runner executes or resumes
- **THEN** source dependencies and psutil SHALL be bundled and same-identity checkpoints SHALL restore without developer Python

### Requirement: Portable historical examples
The package SHALL include a project with six real existing periodic A/B points and their unchanged evidence. Project-local ./ references SHALL resolve relative to the project; legacy references SHALL retain their existing meaning.

#### Scenario: Relocated distribution
- **WHEN** the distribution is extracted outside the repository and opened with a different working directory
- **THEN** its history, pressure traces, power, torque, comparison and exports SHALL remain available without historical machine paths

### Requirement: Real executable acceptance
Acceptance SHALL exercise Dino2T.exe, load and compare historical data, export, execute and recover a bounded integrated point. Package/source wall time SHALL be measured under equivalent conditions. Historical producer mismatch SHALL remain fail-closed.

#### Scenario: Short exploratory execution
- **WHEN** the brief run is cancelled after complete cycles and resumed
- **THEN** valid checkpoints SHALL be preserved and the restored result SHALL match the source reference, without claiming periodicity or full-curve speedup

### Requirement: Preserved scope
The delivery SHALL remain TRIAL if the build tree is dirty, preserve X30 and all historical evidence, and SHALL NOT change physical models, launch full campaigns or push.

#### Scenario: Pending X30 geometry
- **WHEN** experimental validation is unavailable
- **THEN** the product delivery SHALL retain that limitation without inventing inputs
