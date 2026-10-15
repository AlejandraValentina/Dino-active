# DINO Commercial Desktop V3 Specification

## Purpose

Deliver one Windows Qt application with a component-centered DISEÑO mode and a data-centered ANÁLISIS mode. This is a presentation and navigation capability using existing backends. It must preserve all scientific and historical contracts.

## ADDED Requirements

### Requirement: Two persistent workspace modes
The main window MUST offer DISEÑO and ANÁLISIS modes. DISEÑO MUST use the available width for motor components and MUST NOT reserve a large blank results panel. ANÁLISIS MUST prioritize run state, available traces, waves, valid metrics and comparisons. Project, active variant, baseline and selected run MUST survive mode changes.

#### Scenario: Switching workspace modes
- **WHEN** the user switches between DISEÑO and ANÁLISIS
- **THEN** the active project, variant, baseline and selected run remain available
- **AND** DISEÑO shows component work without a blank results panel

### Requirement: Legible native Windows controls
Tabs, table rows, headers, dialogs, numeric controls and navigation MUST meet readable contrast and fit supported layouts. At 1360×900 and 980×680 essential controls MUST remain reachable without accidental horizontal scrolling or clipped labels. Qt 125%/150% simulation MUST be distinguished from Windows display scaling.

#### Scenario: Compact supported window
- **WHEN** the app is displayed at 980×680 or 1360×900
- **THEN** essential navigation, inputs and actions remain reachable and legible

### Requirement: Component rail and geometry-derived views
The component rail MUST show complete, modified, pending and invalid states. Existing engine APIs MUST supply cylinder displacement, port events, and area-angle data. Intake timing MUST use actual nonzero area transitions across TDC. Escape geometry MUST retain the existing backend representation, shared station continuity, visible dimensions, calculated volume and explicit baseline overlay/differences. No inverse timing editor or new physical estimate is permitted.

#### Scenario: Editing represented exhaust geometry
- **WHEN** the user edits an exhaust segment or shared station
- **THEN** the existing geometry adapter validates and displays the resulting dimensions
- **AND** the interface does not infer performance or add inverse timing controls

### Requirement: Single execution state and visible progress
RPM, horizon and budget MUST have one authoritative state shared throughout the app. Existing one-run confirmation, preflight, fail-closed behavior, checkpoint/restart and cancellation MUST remain. Execution progress, elapsed/remaining budget, angle/cycle and checkpoint state MUST be visible while running. No campaign or automatic queue may be introduced.

#### Scenario: Starting one run
- **WHEN** the user confirms a single preflighted run
- **THEN** the shared execution state displays progress and checkpoint information
- **AND** no campaign or automatic queue is created

### Requirement: Honest analysis and comparisons
Only existing sampled values may be displayed. Pressure axes MUST use the correct absolute/relative units and finite data range; absolute pressure MUST not receive artificial negative ticks. Spatial-angle maps MUST render existing cell samples discretely without interpolation. Defined metrics, undefined reasons, classification, periodicity, audit and conservation MUST remain explicit. Comparison MUST identify incompatible conditions and avoid causal attribution when factors differ. No result may be fabricated or promoted.

#### Scenario: Comparing existing runs
- **WHEN** the user selects compatible or incompatible existing runs for comparison
- **THEN** only stored samples and defined metrics are shown
- **AND** incompatible conditions are identified without causal attribution

### Requirement: Evidence and scientific detail remain accessible
Hashes, provenance, audit, conservation and raw technical reason codes MUST remain accessible under an organized evidence/detail surface. User-facing status MAY be translated to Spanish while preserving original codes in evidence and tooltips.

#### Scenario: Inspecting evidence
- **WHEN** the user opens the evidence surface for a selected run
- **THEN** provenance, hashes, audit, conservation and original technical status remain accessible

### Requirement: Historical and backend preservation
The solver, physical models, mesh adapter, hard gates, periodicity, historical runs, R2, IMPL2, FAST classification, convergence receipts and all scientific artifacts MUST remain byte-identical. The objective MUST NOT start simulations or campaigns.

#### Scenario: Preserving scientific artifacts
- **WHEN** the desktop redesign is implemented or packaged
- **THEN** solver, physical models, hard gates, historical runs and scientific artifacts remain unchanged
- **AND** no simulation is started

### Requirement: Verification and trial distribution
Automated P0/P1 regressions MUST exercise real widget state and isolated QSettings. Real Windows interaction and a TRIAL package MUST be checked when the interactive desktop is available. Screenshots alone or offscreen rendering alone MUST NOT establish packaged acceptance. Dirty-tree packages MUST remain labeled TRIAL.

#### Scenario: Building a dirty-tree package
- **WHEN** the Windows package is built from a modified working tree
- **THEN** it is labeled TRIAL and is checked for startup, project, history and result workflows when desktop interaction is available
