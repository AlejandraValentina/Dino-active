# Tasks — reference-engine-hybrid-harness

- [x] Freeze harness scope, observables, thresholds, streak rules and cycle cap
      in the machine-readable preregistration; commit before KT100 execution.
- [x] Implement configuration validation and reusable geometry/topology setup.
- [x] Implement cycle-relative event orchestration over existing P5-C/P6/P7.
- [x] Implement `REFERENCE_PERIODIC_CONVERGENCE_V1` and restartable detector.
- [x] Implement primary trajectory/cycle evidence, source bindings and JSON-safe
      checkpoint/restore.
- [x] Implement offline audit, conservation recomputation, replay comparison
      and malformed-evidence rejection.
- [x] Self-test period-1, period-2, detector persistence, initial-state and
      accepted-SSPRK2-step checkpoint/restore, malformed evidence and
      conservation recomputation; P5/P6/P7/CFL product regression paths pass.
- [x] Create KT100 V2 configuration with complete provenance and run preflight.
- [x] Run the affected P5-B/P5-C/P6/harness tests (76 passed), then the
      P4-P8 regression set plus harness/P5-B tests (346 passed; 4 existing
      NumPy deprecation warnings); strict OpenSpec validation,
      `git diff --check`, `git lfs fsck`, and the frozen P9 SHA-256 all pass.
- [x] Execute the fixed five-point campaign under the frozen contract and
      classify failures without tuning. Preserve earlier receipts; r5 uses the
      corrected effective-face CFL and records all five outcomes audited offline.
- [ ] Verify independent restart/replay and audit for campaign anchors.
- [ ] Compare V1/V2 as `MODEL_FORM_DIFFERENCE`; perform only preregistered local
      sensitivities after base campaign completion.
- [x] Run relevant P4–P8 regressions, OpenSpec strict, `git diff --check`,
      `git lfs fsck`, and verify the frozen P9 hash.
- [x] Independent punctual review of opt-in boundary orientation and exact
      effective-face CFL wiring: no material defect found; local commits only,
      no push/archive.

Initial status: preregistration approved by punctual independent review and
strictly validated before the first KT100 V2 execution.

## Current execution evidence

The fixed campaign is blocked before the first complete 360-degree cycle at
every preregistered RPM. The r5 failure receipts are auditable and source-bound:

| RPM | Result | Accepted steps | Stop angle | Product boundary result |
| ---: | --- | ---: | ---: | --- |
| 5000 | `NUMERICAL_FAILURE` | 129 | 88.025837° | `No consistent reservoir inflow branch` |
| 7000 | `NUMERICAL_FAILURE` | 95 | 90.309320° | `No consistent reservoir inflow branch` |
| 9000 | `NUMERICAL_FAILURE` | 75 | 91.961725° | `No consistent reservoir inflow branch` |
| 11000 | `NUMERICAL_FAILURE` | 63 | 94.486988° | `No consistent reservoir inflow branch` |
| 13000 | `NUMERICAL_FAILURE` | 54 | 95.512819° | `No consistent reservoir inflow branch` |

The precise existing `Boundary('reservoir')` state rejects an inlet branch at
these accepted-state trajectories. Changing the boundary model or P5-C
operating state would be a physical/model change, so no campaign retry policy,
CFL value, mesh, boundary state, or synthetic parameter was tuned to bypass it.
A non-evidentiary 5000-RPM diagnosis restored the complete SSPRK2/P6 snapshot
and tried each rejected step through eight successive halvings; after 134
accepted diagnostic steps and 23 rejected attempts (the deepest accepted retry
used seven halvings), the next boundary branch still had no solution even at
the eighth halving, at 87.856764°. This diagnosis was not stored as
campaign evidence and does not change the r5 classification. Because no cycle
completed, there is no periodic classification, performance comparison,
checkpoint continuation, or campaign replay evidence. The r5 offline evidence
auditor reports `PASS` for the failure receipts and current source/configuration
binding; that validates the record, not the hybrid run. r5 also corrects the
harness CFL calculation to use the actual geometry-resolved P5 interface areas
and HLLC interface wave speeds. The five failures persist under that bound.

An additional regression isolated a left-face orientation defect in the old
P5-B atmospheric-boundary adapter: its global +x `Boundary.flux` tuple was
treated as outward-oriented. The new harness explicitly selects
`external_boundary_flux_convention="global_x"`; historical fixtures retain
their prior default. A uniform stationary-state test and the focused P5-B,
P5-C, P6, and harness suite pass after that correction. This correction did not
resolve the separate unsupported reservoir branch recorded above.

Artifacts:
`results/kt100-hybrid-model-fixture-v2-harness-20261002-r5/` is the current
fixed-campaign evidence. Earlier partial/rejected attempts remain preserved in
the sibling base, r2, r3, and r4 directories and are not used as current results.

Closeout audit: all five r5 receipts were re-audited offline in this turn; each
failure record agrees with its summary, configuration and product source
bindings (`evidence_audit=PASS`), while retaining `NUMERICAL_FAILURE` and zero
complete cycles. `tests/test_reference_harness.py` passes 11 tests after adding
an accepted-step P5-C/P6 checkpoint/restore continuation comparison against an
uninterrupted path. This verifies harness serialization and continuation at an
accepted step; it does not substitute for a KT100 campaign anchor.

KT100 campaign restart/replay, V1/V2 numerical comparison, and sensitivity are
still pending because no complete V2 cycle exists. Do not infer V2 performance
from V1 or run sensitivities against absent cycle outputs. The fixture remains
`KT100_HYBRID_MODEL_FIXTURE_V2_BLOCKED_BEFORE_FIRST_CYCLE`, not VERIFIED. No
solver, boundary, physical parameter, threshold, cycle horizon, P4–P9 contract,
or P9 preregistration was changed. P9's frozen hash remains unchanged and P9
still awaits experimental data.
