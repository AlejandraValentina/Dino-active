# DINO 2T Solver Recovery V2

## Why

The prior bounded diagnostic classified performance and memory as limited, found that the exploratory runner supplied V1 identity to a V2 periodicity detector, and documented a power-valve endpoint behavior tied to floating-point RPM reconstruction. It also left mesh-refinement setup as a protocol rather than reusable infrastructure.

## What changes

- Correct new-run periodicity contract binding and persist detector evaluation separately from termination, including comparison counts, residual locations, thresholds, accepted period, and compatible checkpoint bindings.
- Remove a redundant full-primary JSON roundtrip from output metadata preparation after the canonical primary has already been persisted.
- Verify the power-valve lookup against the configured constant operating RPM at map boundaries without changing the solver equations or map.
- Provide reproducible 1/2/4/8 mesh setup, conservative remap checks, per-resolution receipt support, and offline comparison utilities that do not assert acceptance without registered tolerances.
- Keep operational changes separate from any physical result changes; preserve V1 receipts and checkpoints.

## Out of scope

No campaign RPM points, exhausted focal-run resume, full mesh study, Stage 2, experimental validation, periodicity threshold changes, or mesh-independence claim.
