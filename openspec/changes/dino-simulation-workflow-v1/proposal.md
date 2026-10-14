# DINO_SIMULATION_WORKFLOW_V1

## Why

Connect editable ENGINE_CONFIGURATION_V1 projects to the existing IntegratedEngine2T solver through a versioned local exploratory workflow. Keep verified execution behind independent preregistration, explicit authorization and the existing scientific gates.

## Scope

This change adds a fail-closed preflight, a bounded single-configuration exploratory runner, durable isolated artifacts with checkpoint/restart and cancellation, engine-backed exhaust geometry, result comparison, and Qt workflow integration. Exploratory outputs are provisional and cannot be represented as verified. The existing campaign runners and their authorization contracts remain unchanged.

An authorized numerical correction resolves the configured constant operating RPM for the powervalve map rather than a stage RPM reconstructed from floating-point time/angle arithmetic. It preserves exact map-domain checks for genuinely out-of-range RPMs and changes solver identity. Historical campaigns, hashes and classifications remain immutable.

## Non-goals

- Full RPM campaigns, KT100 experiments, calibration or verified runs.
- Changing hard gates, periodicity thresholds, CFL limits or solver equations beyond the versioned powervalve endpoint semantic correction.
- Reclassifying historical IMPL2 points or reusing IMPL2 authorization for new configurations.
- Claiming exploratory output as scientific validation.
