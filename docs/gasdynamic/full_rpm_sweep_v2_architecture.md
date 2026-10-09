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

## 2026-10-09 bounded implementation diagnostic

The IMPL2 prototype `motorsim.full_rpm_evidence_impl2` transposes every
trajectory row field into columns with explicit row-presence masks, binds the
canonical V3 primary SHA-256, writes a gzip segment atomically, reads it back,
reconstructs the canonical primary, and invokes the existing independent
replay auditor. Across two A4000 and two B4000 repeats, the original and
reconstructed primaries were byte-canonically identical; all 24 independent
audits passed. Repeated runs at 1, 2, and 4 workers also produced identical
canonical hashes per engine configuration, with 808 accepted steps and 84/85
rejected trials respectively.

This representation reduced the compressed artifact from 2,624,076 bytes to
2,587,570 bytes on average (1.4%), while increasing measured end-to-end
evidence time from 15.22 seconds to 16.88 seconds per one-worker diagnostic
(10.9%). The additional transpose, gzip persistence/readback and canonical
reconstruction exceeded the small storage benefit. It is therefore retained
as an equivalence prototype, not adopted as the campaign writer. No evidence
fields or independent checks were removed.

The Windows `spawn` point executor was added behind an explicit
`--execute --workers N` path. Each process owns one engine and one point's
artifacts/checkpoint; only the coordinator writes the campaign manifest. A
512 MiB per-worker reservation caps workers against both the configured memory
budget and currently available memory. Workers return at a complete-cycle
checkpoint after timeout or cooperative interruption. The diagnostic-only
benchmark (four isolated one-cycle tasks per scale, both evidence paths) took
114.22 seconds with one worker, 55.10 seconds with two, and 30.56 seconds with
four, for 2.073x and 3.738x measured diagnostic speedups. Peak observed worker
RSS was 283 MiB; Python process startup and artifact I/O are included in wall
time, and task receipts rather than primary payloads cross the process
boundary. A full campaign has not tested checkpoint/restart under concurrent
workers and remains subject to independent review.

If the previous rough 12.50-hour serial sweep estimate scaled uniformly by the
diagnostic four-worker speedup, the arithmetic would be about 3.34 hours.
That is an unvalidated sensitivity illustration only: per-point periodic
convergence lengths and invocation/resume behavior are not represented by the
four one-cycle tasks, so it is not a campaign estimate or authorization.
