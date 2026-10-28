# Candidate periodic mesh study — preregistration v1

Status: frozen for the first bounded 88-cell window. This authorizes no
candidate promotion and no predictive claim. The broader 176-cell window is
conditional on reviewing the 88-cell result first.

## Frozen physical and numerical identity

- Reference: E2B A, independently initialized at 9000 RPM, 44 total cells,
  31 exhaust cells, MUSCL V2, V2 port law, `OPEN_END_PLENUM_V2`, SSPRK2/HLLC,
  CFL 0.4. Preserve the complete E2B A configuration and candidate hashes.
- Reference state: audited A cycle 30 from the durable E2B artifact root. Reuse
  its native checkpoint and audited periodic classification; do not rerun A.
- Fine grids: construct 88 and 176 cells from that same A30 state using the
  existing conservative P0 prolongation, each with a fresh periodic detector.
  No state transfer from 88 to 176 and no parameter, closure, or geometry
  changes beyond the declared nested mesh identity.
- The cross-grid `physics_identity_sha256` is the frozen E2B A44 source
  configuration SHA-256
  (`a1428f8eba4e5d24d6778624c5e5a70b61cf21587581096338836ab7faeabe67`). Each
  remapped mesh also records its distinct mesh/configuration identity. This
  prevents mesh refinement metadata from being mistaken for a physical-model
  change.
- First window: 88 cells, cycles 31–36 at most, solver budget 260 s and
  admission limit 290 s. Preserve a native checkpoint and detector after each
  cycle. Stop on detector classification, failed conservation/admissibility,
  or budget. Reevaluate the trend before another window or any 176-cell run.

## Frozen source binding

The protocol binds:

- `results/e2b-periodic-ab-v1/manifest.json` and `artifact-index.json`;
- `results/e2-spatial-waves-v1/preparation/A44.json`;
- external `A/checkpoint-030.json`, `A/recipe-030.json`, and `A/audit-030.json`
  under `DINO_ARTIFACT_ROOT/e2b-periodic-ab-v1-20261028`;
- current solver dependency hashes, which must equal the E2B frozen map.

All external files must match `artifact-index.json`. The checkpoint must restore
to A30 exactly, and the audit must report exact replay and lag1 periodic
classification PASS. Refuse execution if any source hash differs.

## Acceptance and interpretation

The first-window receipt must report exact source hashes, mesh identity,
conservative remap residuals, all accepted/rejected recipes, native cycle
checkpoints, detector outcome, global conservation, runtime and storage
preflight. Conservation residuals must remain at or below 1e-12 and no invalid
state or clipping is permitted. Periodicity on 88 requires the existing
`PeriodicDetectorV2` contract on a fresh history; periodicity on 44 does not
transfer automatically.

No GCI can be calculated from an incomplete or nonperiodic mesh. If 88 reaches
an audited periodic state, assess whether the frozen budget and trend support
the separately preregistered 176-cell window. The final 44/88/176 comparison
requires audited same-period primaries, monotone convergence, observed order
declared within [0.5, 2.5] or explicitly qualified, and GCI ≤2% for IMEP and
modeled power. Otherwise classify PARTIAL/FAIL as defined by the staged plan.

## Budget and preservation

First 88-cell window: ≤290 s, ≤1 GiB aggregate study storage, 2 GiB free-space
reserve, and source/output roots selected through `DINO_ARTIFACT_ROOT`. Never
remove or overwrite prior artifacts. The existing plan allows ≤600 s for an
88-cell window, ≤1200 s for a 176-cell window, ≤6 h cumulative, and ≤1 GiB for
the entire study; any continuation must be checkpointed and separately
admitted after reviewing actual cost. No reduction of CFL, precision, detector
criteria, or conservation thresholds to fit a budget.

## Scope limits

This is numerical verification of an experimental solver candidate. MUSCL V2
and port-law V2 remain opt-in/experimental. Legacy remains default; rc7 and
P0–P9 evidence remain untouched. This study does not validate measurements,
exhaust-change predictions, the physical closures, or performance-product
readiness.
