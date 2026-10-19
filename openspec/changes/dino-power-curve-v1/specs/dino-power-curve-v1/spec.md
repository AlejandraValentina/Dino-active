# DINO_POWER_CURVE_V1 Specification

## ADDED Requirements

### Requirement: audited RPM results in Analysis

The application MUST reuse existing RPM run artifacts and aggregate reports
through their supported importers. It MUST preserve result provenance, source
hashes, classifications, periodicity, audit and conservation status. Opening
history MUST NOT copy historical results into the active project or relabel
them as current-project runs.

#### Scenario: open existing RPM results

- **WHEN** a user selects RPM runs from the existing history
- **THEN** each primary is verified through the existing independent importer
  and its original variant, RPM, identity, status, and provenance remain visible

### Requirement: brake performance curves

Analysis MUST show brake power and brake torque against RPM together, with
independent vertical axes, explicit units, selectable power units HP, kW, and
CV, per-series visibility controls, data point selection, maxima and their RPM,
and CSV export. Power conversion MUST use the declared source unit. Only
`DEFINED`, finite metrics from import-validated rows may appear as numeric
points.

#### Scenario: unavailable or invalid point

- **WHEN** a point is missing, failed, nonperiodic, or its metric status is not
  `DEFINED`
- **THEN** its numeric value is omitted and the curve breaks at that RPM; no
  interpolation, extrapolation, or zero substitution occurs

### Requirement: exact compatible comparison

The application MUST compare configurations only at exact shared RPM values
whose scientific identity and reported operating conditions are compatible.
Configuration/geometry differences are allowed and MUST remain visible.
Unmatched RPM values MUST remain unpaired. Missing compatibility metadata MUST
be reported as unknown and MUST NOT be treated as equal.

#### Scenario: unequal RPM grids

- **WHEN** two series have different RPM grids
- **THEN** only exact RPM intersections are compared and the application MUST
  state that no interpolation was used

### Requirement: bounded integrated sweep

The sweep MUST execute each selected RPM as an independent run through the
existing integrated solver and conventional evidence/audit path. Before the
first solver step, it MUST validate the full requested grid, the engine
configuration, explicit mechanical-loss model, fuel, conditions, maximum
cycles, per-point budget, total budget, memory cap, and external artifact root.
Invalid configuration MUST fail closed with zero solver steps.

#### Scenario: preflight rejection

- **WHEN** any RPM or run input fails validation
- **THEN** the sweep is rejected before starting any point and records the
  causal reason

### Requirement: partial persistence and safe resume

Each RPM MUST have its own run ID, configuration identity, primary artifacts,
checkpoint, audit, and scientific classification. A single coordinator MUST
atomically update the sweep manifest after each point. Cancellation or budget
exhaustion MUST preserve completed points and the latest valid per-point
checkpoint. Resume MUST verify all sweep, engine, solver, periodicity, and point
identities and MUST reuse only completed or compatible checkpointed points.

#### Scenario: interrupted sweep

- **WHEN** the user cancels or the total budget expires
- **THEN** completed points remain available in history, remaining points stay
  explicitly unstarted, and no failed point becomes a numeric curve value

### Requirement: exploratory execution and scientific claims

A user MUST explicitly confirm the selected point grid and budgets before a
sweep starts. Sweep results MUST remain classified as exploratory unless an
existing scientific contract independently accepts each point. This change
MUST NOT authorize a campaign, modify periodicity or physical gates, or alter
historical result identities.

#### Scenario: sweep execution confirmation

- **WHEN** a user starts a configured sweep
- **THEN** the application shows the exact RPM points, horizon, memory, per-
  point and aggregate wall budgets, artifact root, and exploratory status
  before starting the integrated solver

#### Scenario: report result

- **WHEN** a sweep contains nonconverged or unstarted points
- **THEN** the curve is labeled partial, retains the failed/missing gaps, and
  makes no scientific validation claim
