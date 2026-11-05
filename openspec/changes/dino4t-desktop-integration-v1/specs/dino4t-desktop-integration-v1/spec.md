# Dino Desktop 2T/4T integration

## Objective

Integrate the native single-cylinder 4T foundation into the existing Windows
Dino Desktop application while preserving the independent numerical and
scientific contracts of 2T and 4T.

## Requirements

- Desktop identifies projects by engine family and dispatches configuration,
  execution, results and reports through family-specific contracts.
- 2T projects/results and their existing workflow remain readable and unchanged.
- 4T uses `DINO4T_API_V1`, `DINO_DESKTOP_ENGINE_PROJECT_4T_V1`, and
  `DINO4T_OPERATING_POINT_RESULT_V1`. Desktop does not call internal solver
  routines or reshape 4T results into 2T schemas.
- The 4T editor exposes only known API configuration fields. It preserves
  configuration provenance, rejects unknown fields, and supports variants.
- Runs retain API summary, resolved configuration, final-cycle trace, hashes,
  run identity and build/source provenance. Imports verify hashes and leave the
  source artifacts unchanged.
- Performance curves and A/B comparisons require periodic 4T results and an
  exact compatible operating context. Transient outputs are labeled and are
  not shown as definitive performance curves.
- Periodicity is not experimental validation. The interface and reports retain
  `NOT_PERFORMED` experimental validation and `NOT_CLAIMED` predictive status.
- The Windows bundle includes the pinned NumPy/SciPy runtime used by 4T and
  preserves the existing single-executable Desktop entry point.
- No solver equations, numerical methods, protected scientific contracts or
  historical evidence are changed by this integration.

## Acceptance

- Focused automated integration and existing 2T Desktop regressions pass.
- The source GUI and one packaged Windows candidate exercise 2T project/result
  compatibility, 4T project editing/variants, bounded execution, persistence,
  history/import, report/CSV and truthful transient/periodic presentation.
- Packaged build provenance and SHA-256 are recorded. No release promotion or
  public distribution is implied.
