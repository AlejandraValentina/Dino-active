# Engine Configuration V1

## Why

Add a reproducible, editable backend for 2T engine configurations and variants using only models already represented by `IntegratedEngine2T`. Preserve the existing sweep and historical scientific identities. Provide project persistence and an honest importer/comparator for the existing synthetic IMPL2 result set. This objective does not add the Windows UI, change solver physics, repair old results, or authorize new RPM campaigns.

## Scope

- Versioned engine configuration document with unit-bearing fields, provenance, validation, and deterministic identity.
- Exhaust section geometry that maps to the existing finite-volume duct mesh contract; unsupported physical shapes fail explicitly.
- Project persistence with base configuration, named variants, run-configuration references, result references, and validation state; primary artifacts remain external.
- Comparison service for imported curve datasets that preserves classifications, validity, gate results, undefined outputs, and gaps.
- A versioned proposal for the powervalve endpoint-roundoff defect without changing the solver or historical artifacts.

## Out of scope

- GUI/frontend, solver equations, numerical thresholds, hard gates, campaign execution, new scientific claims, automatic interpolation, automatic repair of invalid points, and unsupported physical components.
