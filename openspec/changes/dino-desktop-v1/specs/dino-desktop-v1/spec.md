# DINO_DESKTOP_V1 Specification

## ADDED Requirements

### Requirement: Native desktop shell and safe backend integration
The system MUST provide a Windows Qt Widgets application with distinct Motor,
Escape, Projects, Simulation, and Results areas. UI code MUST use existing
`ENGINE_CONFIGURATION_V1` services and MUST NOT duplicate solver physics.
Long-running reads/builds MUST not block the event loop, and expected file,
validation, and service failures MUST be shown as recoverable UI messages.

#### Scenario: Open and edit an engine project
- **WHEN** the user opens the desktop app and selects a supported project
- **THEN** the project is loaded through the backend, fields show units and
  validation state, and unsupported/inconsistent edits cannot be saved as valid.

### Requirement: Supported engine and exhaust editor
The editor MUST expose supported engine geometry, ports, intake/transfers,
combustion/fuel, explicit losses, and operating conditions through visual
controls. Escape editing MUST use the backend linear-diameter section model,
show dimensions and a live profile, and distinguish editable unsupported
geometry from solver-supported configurations. Variants MUST preserve unedited
base fields.

#### Scenario: Edit an exhaust variant
- **WHEN** a user duplicates the base engine and changes exhaust section
  dimensions
- **THEN** the application shows the updated profile and exact configuration
  diff, while the base remains unchanged and backend validation decides
  simulability.

### Requirement: Project lifecycle and identity
The UI MUST support new/open/save/save-as/import/export, variant duplication and
comparison, dirty-state indicators, and atomic persistence through the project
backend. It MUST display stable identities and MUST NOT store cycle primaries or
checkpoints inside editable projects.

#### Scenario: Save a modified project
- **WHEN** valid edits are saved
- **THEN** the backend atomically persists the project identity and references,
  and the UI clears the dirty indicator only after successful replacement.

### Requirement: Result visualization preserves evidence
The application MUST load the real IMPL2 aggregate JSON and CSV companion via
the result service, display interactive power, torque, IMEP/FMEP/BMEP and BSFC
curves and point details, and export tables/plots. Invalid or missing values
MUST remain gaps; units, hashes, classifications, periodicity, hard gates, and
synthetic provenance MUST remain visible. PERIOD_1 MUST NOT be labeled as
scientific PASS.

#### Scenario: View an invalid RPM point
- **WHEN** the user selects one of the three existing `NUMERICAL_INVALID` RPMs
- **THEN** no numerical value is drawn for that point and its failure
  classification and provenance remain inspectable.

### Requirement: Execution panel fails closed
The execution panel MUST display configuration identity, authorization/preflight
state, registered points, worker and budget state, checkpoints, and recovery
classification. It MUST invoke the existing supervisor only when that exact
configuration is preregistered and an explicit valid authorization is present.
It MUST NOT synthesize authorization or bypass the runner. New/unregistered
configurations may only produce a saved execution request. This development
change MUST NOT launch a campaign.

#### Scenario: Request execution for an unregistered variant
- **WHEN** a user selects an edited configuration without a matching
  preregistration and authorization
- **THEN** execution is disabled, the precise missing prerequisites are shown,
  and a request document may be saved without starting workers.

### Requirement: Windows launch and testable lifecycle
The system MUST provide a reproducible Windows launch/package recipe, persistent
local UI preferences, and tests covering startup, project lifecycle, validation,
escape geometry, real result import/display/export, authorization fail-closed
behavior, file errors, and asynchronous responsiveness. No new campaign is run.

#### Scenario: Close during an asynchronous operation
- **WHEN** a background operation is active and the user requests cancellation
- **THEN** the operation is cooperatively cancelled or safely awaited, UI state
  remains consistent, and no result artifact or project is partially replaced.
