# Design

- Reuse V3.1 Analysis, the existing run history, the existing independent
  exploratory importer, and `CurvePlot`-adjacent Qt components.
- Compute brake power and torque only from status-bearing imported metrics.
  Convert power from the importer's declared kW unit to HP, kW, or CV.
- Draw power and torque on separate vertical axes. Preserve failed, missing,
  nonperiodic, and undefined points as gaps; never interpolate or extrapolate.
- A sweep uses the configured integrated engine and existing no-solver
  preflight at every RPM. Each RPM gets a distinct run ID, its own primary
  artifacts and checkpoint. One coordinator atomically updates the sweep
  manifest after each point.
- Execution remains exploratory and requires a fresh user confirmation with
  explicit point count, horizon, memory cap, per-point budget, and total budget.
- Existing V1/IMPL2 reports remain read-only and retain their own identities.
  This feature does not promote any campaign result to scientific acceptance.
