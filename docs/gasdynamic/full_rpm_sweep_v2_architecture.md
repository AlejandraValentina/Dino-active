# FULL_RPM_SWEEP_V1_IMPL2 evidence performance diagnosis

## Measured boundary

The bounded A4000/B4000 runs measured about 15 seconds per first-cycle
diagnostic in memory. Direct stage clocks attribute approximately 54% to
independent primary replay audit, 23% to primary construction, and 14% to
numerical advancement. Low-rate samples show recursive JSON conversion,
`deepcopy`, EOS/species validation and HLLC inside the numerical path. Rejected
CFL trials consume roughly 0.10 seconds per cycle (84–85 trials), about 0.6% of
total measured time. Historical campaign metrics add roughly 0.8–1.2 seconds
for primary file writes per cycle, depending on mesh.

Geometry memoization produced 1.0529x combined end-to-end speedup with exact
primary/terminal-state equality and unchanged rejection counts. Even removing
the entire numerical advance gives an Amdahl ceiling near 1.16x. A 5x result
requires changing the evidence construction/audit architecture while
preserving its content and independent recomputation.

## Proposed versioned boundary

1. Store each accepted step in a deterministic columnar segment: clock and RPM;
   three SSPRK states; two stage geometries; stage fluxes, species and work;
   thermal, combustion and port ledgers; and the exact admissibility/rejection
   classifications. Keep the field registry and units versioned.
2. Let the solver append primitive numeric values to typed buffers. Avoid
   rebuilding nested dictionaries and deep-copying the complete trace at each
   snapshot. A cycle checkpoint stores the current state and cumulative ledger
   baselines plus the hash of the completed evidence segment.
3. Implement the independent auditor as a separate reader over those segments.
   Recompute the same SSPRK stages in bounded chunks and compare every stored
   field, conservation ledger and terminal state. Use Numba only for contiguous
   arithmetic kernels after profiling demonstrates those kernels dominate.
4. Produce the existing JSON primary as a streaming export from the columnar
   segments. Keep canonical units, sorting, finite-number rules, provenance and
   stable hashes for the new schema. Do not alter the v1 JSON or its hashes.
5. Benchmark stage-by-stage on A4000 and B4000 and enforce exact acceptance,
   rejection, admissibility and checkpoint continuation. If converting back to
   the existing evidence schema consumes the saved time, keep a new primary
   schema under IMPL2 rather than claiming a runner speedup.

## Release boundary

This document is an architecture proposal, not a campaign authorization. Any
implementation must use `FULL_RPM_SWEEP_V1_IMPL2`, a distinct output root and a
separately reviewed preregistration. The v1 pilots, checkpoints, manifest and
scientific thresholds remain read-only.
