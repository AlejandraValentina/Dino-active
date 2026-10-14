# DINO_DESKTOP_V1

## Why

Provide a usable Windows desktop application over the existing versioned
`ENGINE_CONFIGURATION_V1` services, while keeping scientific execution behind
the existing authorization and supervisor contracts.

## Scope

This change adds a native Qt Widgets application with motor/configuration and
escape editing, project/variant management, IMPL2 result comparison, and an
execution-status panel. It reuses existing backend services and never duplicates
physics. New configurations may be prepared and saved, but this change does not
authorize or run a scientific campaign.

## Non-goals

- Solver, hard-gate, R2, preregistration, or historical result changes.
- Campaign execution or experimental calibration.
- Claiming a newly edited configuration is scientifically validated.
- Silent interpolation or auto-approval of invalid result points.
