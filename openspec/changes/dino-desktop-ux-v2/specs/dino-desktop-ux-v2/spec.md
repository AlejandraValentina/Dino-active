# DINO Desktop UX V2 Specification

## Purpose

Deliver a project and variant centered Windows desktop engineering workspace using the existing Qt application and existing backend APIs. This is a user interface capability only. Historical scientific results and their status remain unchanged.

## ADDED Requirements

### Requirement: Context-aware workspace
The application MUST show the current project, selected variant, save state, and scientific mode persistently. Variant selection MUST remain stable while changing pages. UI actions MUST modify only the explicitly selected variant. Resizable project, work, and inspector panels MUST persist their layout preferences.

#### Scenario: Change page with a selected variant
- **WHEN** the user selects a variant and changes between Motor, Escape, Simular, Results, or Compare
- **THEN** the same variant remains active and visible, and edits target only that variant.

### Requirement: Safe variant lifecycle
The application MUST support user-named creation, duplication, renaming, and deletion of variants with validation and reference protection. Existing variants MUST remain independent snapshots when the base engine changes. Deleting a project reference MUST NOT delete scientific artifacts.

#### Scenario: Delete a referenced variant
- **WHEN** a variant is referenced by runs or comparisons
- **THEN** deletion MUST explain the references and require an explicit safe resolution without removing artifacts.

### Requirement: Escape editor integrity
Escape geometry MUST be edited using shared stations and segment lengths so adjoining diameters remain continuous. The profile MUST show dimensions and scale, and comparisons may overlay another variant. Unsupported geometry MUST fail validation. Mesh resolution remains an advanced setting and MUST display that spatial independence has not been demonstrated by the historical exhaust diagnostics. No solver, physics, or mesh-adapter code may change under this objective.

#### Scenario: Edit a shared station
- **WHEN** a station diameter is changed
- **THEN** both adjoining segment endpoint diameters change from the same value and the backend configuration is validated before applying.

### Requirement: Explicit exploratory execution
The simulation workflow MUST show the selected project and variant, RPM, horizon, budget, exploratory mode, preflight outcomes, expected output availability, progress, checkpoint/restart, and cancellation. Every run requires an explicit individual confirmation. A one-cycle diagnostic MUST explain that accepted periodic power and torque are unavailable. VERIFIED MUST remain unavailable unless the existing backend provides matching authorization and contract support. No mass execution queue or campaign may be started.

#### Scenario: Prepare one cycle
- **WHEN** a one-cycle exploratory run is configured
- **THEN** the UI explains that it can provide transient traces but cannot provide accepted periodic performance metrics.

### Requirement: Run history and artifact isolation
The application MUST discover run entries through metadata and references without moving or rewriting primaries. The artifact root MUST be configurable and shared by execution and result browsing, while physical roots and identity bindings remain isolated. Incomplete history MUST retain its actual incomplete state.

#### Scenario: Browse runs from separate roots
- **WHEN** project history contains references to runs in different artifact roots
- **THEN** the user can open the referenced run without manually browsing for a result file, and no artifact is copied or relabeled.

### Requirement: Honest results and comparison
Results MUST identify project, variant, run, classification, periodicity, audit, conservation and experimental-validation status. Undefined values MUST show reasons. Negative values and invalid gaps MUST be preserved with no interpolation across invalid points. Historical IMPL2 evidence MUST be separate, explicitly historical synthetic evidence and MUST NOT load automatically as current project results. Users MUST be able to select two runs from history for comparison across directories.

#### Scenario: Open historical IMPL2 evidence
- **WHEN** the user opens Results without selecting a run
- **THEN** no historical aggregate is auto-loaded; the page explains that no run is selected and offers separate historical evidence navigation.

### Requirement: Responsive engineering pages
Motor, Escape, Simulation and Results pages MUST remain usable at 1360x900 and 980x680 without overlapping controls or hiding essential actions. Tables and forms MUST scroll or adapt. Text MUST use understandable Spanish for status while preserving raw technical codes in scientific details.

#### Scenario: Small window
- **WHEN** the window is 980x680
- **THEN** navigation, active context, primary fields, validation and essential actions remain accessible without overlap.

### Requirement: Preference and locale behavior
The application MUST persist the artifact root and panel/page preferences. Numeric entry MUST accept the configured locale and unambiguous comma or point decimal input. Displayed units MUST be explicit and consistent.

#### Scenario: Decimal input
- **WHEN** a user enters an unambiguous decimal with comma or point
- **THEN** the value is parsed as the same finite numeric magnitude and round-trips consistently in the UI.

### Requirement: Compatibility and preservation
Existing scientific contracts, hard gates, solver, physics, period criteria, preregistrations, historical results, artifacts, MotorSim.exe, and fail-closed behavior MUST remain unchanged. `EXHAUST_NUMERICAL_CONVERGENCE_V2_PARTIAL` remains terminal history and MUST NOT be promoted or reopened. No RPM campaign or diagnostic run may be initiated by this objective.

#### Scenario: Historical evidence remains immutable
- **WHEN** UX implementation is completed
- **THEN** historical exhaust reports, primary data, checkpoints, R2, IMPL2, and classification hashes remain unchanged.

### Requirement: Trial package verification
A Windows trial package MUST be rebuilt and checked for startup, project open, navigation, result selection and clean close. If built from a tree with unrelated local Ostacky changes, it MUST be labeled TRIAL and MUST NOT be represented as a clean release.

#### Scenario: Build with unrelated local changes
- **WHEN** packaging is performed while Ostacky files remain uncommitted
- **THEN** build provenance records the modified worktree and labels the package TRIAL.
