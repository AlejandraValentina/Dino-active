# DINO Tuning Workbench V1 Specification

## Purpose

Provide an engineering workbench for existing MotorSim 2T configurations while preserving backend and scientific evidence contracts.

## ADDED Requirements

### Requirement: Component-oriented editable build
The application MUST organize supported cylinder, distribution/ports, exhaust and combustion inputs by component. Derived displacement and port angles MUST come only from existing backend geometry APIs. Escape edits MUST preserve shared station continuity and the existing solver mapping. Each changed component and section MUST be visibly identified. The UI MUST label synthetic/unvalidated configurations honestly.

#### Scenario: Edit the diffuser length
- **WHEN** a named variant changes the diffuser from 180 mm to 200 mm
- **THEN** the diffuser is highlighted, its before/after dimensions are named, shared stations remain continuous, and no physical-validation claim is added.

### Requirement: Explicit baseline and consistent variant identity
The project, active variant, selected baseline, scientific mode, and saved/dirty state MUST remain visible. One user-facing variant name MUST be used in all workspace regions; technical display metadata may appear in Evidence. Baseline selection MUST be explicit and persisted as a per-project user preference across sessions; it MUST NOT modify the project file or propagate edits.

#### Scenario: Select another variant
- **WHEN** a variant is selected
- **THEN** build, simulation, run history, result and comparison context show that same variant without opening a separate project page.

### Requirement: Honest single-run preparation
Execution MUST remain one explicitly confirmed EXPLORATORY run at a time. Horizon estimates MUST use comparable existing per-cycle timing or a 30-second fallback. An insufficient budget MUST show expected cycles and a bounded suggestion; changing horizon MUST NOT raise budget automatically. The 600-second ceiling and all backend preflight checks MUST remain. VERIFIED, periodic power, torque or BMEP MUST NOT be implied when unavailable.

#### Scenario: Choose a long horizon
- **WHEN** the requested horizon estimate exceeds the selected budget
- **THEN** the UI warns before confirmation, leaves the budget unchanged, shows the capped suggested budget, and explains when the cap still cannot cover the horizon.

### Requirement: Results and run comparison in the workspace
Existing run history for the active project/variant MUST remain directly available. A selected run MUST show classification, periodicity, independent-audit status, conservation, provenance, hashes, and undefined-metric reasons. A baseline run may be compared without file browsing. Different RPM, fuel, mesh or configuration MUST trigger a scope warning. Curves MUST preserve gaps and invalid points.

#### Scenario: Compare an existing run with baseline
- **WHEN** baseline and variant runs exist
- **THEN** their audited data can be compared without browsing for individual JSON files; only exact corresponding angles may have deltas; conditions that differ are named; no missing values are interpolated or fabricated.

### Requirement: Discrete pressure and wave views
Pressure axes MUST scale to finite data with readable tick values and units; absolute and relative pressure MUST be distinguishable. Spatial-by-angle maps MUST use actual cell observables with one discrete band per cell and MUST NOT spatially interpolate. An unavailable trace MUST explain why.

#### Scenario: Show a pressure wave map
- **WHEN** an audited primary contains pressure by angle and cell
- **THEN** the map uses those samples and exact cell positions, marks known port events from existing profiles, and identifies missing samples rather than interpolating them.

### Requirement: Safe preferences and artifact isolation
The default artifact root MUST be outside a Git repository. An existing preference that points inside a repository MUST be disclosed and retained until the user explicitly chooses a new root. Artifacts MUST NOT be silently moved, renamed or deleted. All Windows application tests MUST use temporary QSettings locations and MUST NOT write test keys to the user's real configuration.

#### Scenario: Existing root points inside the checkout
- **WHEN** the configured root is inside a Git worktree
- **THEN** existing data remains available read-only, new execution is guarded until the user explicitly corrects the root, and no artifact is moved or removed.

### Requirement: Responsive and testable packaged workspace
The workbench MUST remain operable at 1360x900 and 980x680. Results and evidence MUST remain accessible beside or below the build area without hiding safety confirmations. The Windows TRIAL executable MUST be smoke-tested without starting a solver; package provenance and hashes MUST be persisted. A dirty-tree package MUST remain TRIAL.

#### Scenario: Open the trial package
- **WHEN** the packaged application opens the example and a referenced existing run
- **THEN** the variant and baseline are explicit, the run is readable, and missing/undefined values are honestly explained without launching a simulation.

## Constraints

No solver, physical model, mesh adapter, periodicity contract, hard gate, result artifact, or historical classification may change. No campaign, batch execution, series of RPM, one-confirmation multi-run feature, empirical tuning recommendation, or scientific/experimental validation claim is in scope.
