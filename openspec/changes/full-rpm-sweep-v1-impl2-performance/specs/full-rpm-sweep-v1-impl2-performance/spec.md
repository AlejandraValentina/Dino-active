# FULL_RPM_SWEEP_V1_IMPL2 performance and restart contract

## ADDED Requirements

### Requirement: implementation identity isolation MUST

The implementation MUST be identified as `FULL_RPM_SWEEP_V1_IMPL2`. Any
change to solver, restore, campaign producer, or evidence code used by a
future RPM point binds its
producer and dependency hashes, and write to a distinct artifact root. It MUST
NOT reuse v1 checkpoints or mix v1 and IMPL2 outputs.

#### Scenario: incompatible checkpoint

- **WHEN** a checkpoint lacks the IMPL2 identity or required cycle-local trace
  baseline
- **THEN** restore MUST reject it before mutating the live engine

### Requirement: explicit cycle-local trace baseline MUST

The checkpoint MUST identify its trace scope and trace-origin state when a
completed cycle trace is compacted, and it MUST preserve the cumulative
fuel-combustion ledger baseline. The campaign runner MUST verify the checkpoint
file hash against the campaign manifest before deserializing it. Restore MUST
validate the present trace against the ledger delta from that baseline. The
checkpoint's outer artifact hash MUST bind history removed by compaction.

#### Scenario: compacted-cycle restart

- **WHEN** a hash-bound cycle-local checkpoint is restored and advanced
- **THEN** state, cumulative ledgers, conservation, admissibility, and the next
  cycle's accepted trace MUST agree with uninterrupted advancement

### Requirement: performance accounting without scientific relaxation MUST

Benchmarks MUST separately measure numerical advancement, accepted and
rejected steps, evidence construction and audit, serialization, filesystem
writes, compilation warm-up, hot execution, and memory. No optimization may
change equations, SSPRK2 ordering, CFL, mesh, thresholds, periodicity, or gates.

#### Scenario: optimization equivalence

- **WHEN** an IMPL2 optimization is benchmarked against the retained reference
- **THEN** both use the same initial state and their conservation, species,
  energy, pressure, temperature, fluxes, work, periodicity, admissibility,
  accept/reject classifications, and checkpoint continuation are compared

### Requirement: campaign remains unauthorized MUST

This change MUST NOT start RPM points. FULL_RPM_SWEEP_V1 remains PARTIAL until
the v1 campaign is independently completed under its original implementation
or a later IMPL2 preregistration and explicit authorization are provided.

#### Scenario: readiness report

- **WHEN** the performance recovery work completes
- **THEN** it reports measured speedup, projection uncertainty, compatibility
  identities, and `campaign_started = false`

### Requirement: segmented evidence must preserve independent replay audit MUST

Any IMPL2 segmented or columnar primary representation MUST have a versioned
field layout, explicit row and field-presence semantics, atomic persistence,
and a canonical primary hash. A reader MUST reconstruct the complete canonical
V3 primary and pass it to the existing independent replay auditor. It MUST NOT
replace that auditor with producer-side checks. Comparisons MUST include every
canonical field and all conservation and inventory magnitudes; v1 evidence is
read-only.

#### Scenario: lossless segmented round trip

- **WHEN** a segmented primary is read for scientific audit
- **THEN** the reconstructed canonical hash equals the source primary hash and
  the existing independent auditor passes on the reconstructed object

### Requirement: parallel point execution has isolated workers and one coordinator MUST

The versioned IMPL2 point executor MUST use Windows `spawn` processes with
independent engine/configuration state and point-owned artifacts/checkpoints.
Only the coordinator may write the global campaign manifest. Worker count MUST
be limited by both the requested count and an explicit memory budget. Completed
points may be reused only after configuration, solver, producer and artifact
hashes validate. Checkpoint writes MUST be atomic and point scoped. Timeout or
interruption MUST stop scheduling pending work and allow active workers to
return at a completed-cycle checkpoint; worker failures MUST reach the
coordinator. The diagnostic benchmark MUST NOT start campaign points.

#### Scenario: interruption during parallel work

- **WHEN** the coordinator receives a timeout or interruption
- **THEN** it cancels unscheduled work, records worker-owned completed-cycle
  checkpoints, and atomically persists the global manifest after workers stop

### Requirement: evidence and multiprocessing performance claims are end to end MUST

Benchmarks MUST report evidence construction, canonical reconstruction,
independent audit, compression and write time, and compare sequential and
spawn-process execution at each feasible worker count. They MUST record actual
per-process CPU time, aggregate per-core utilization, wall time, memory,
artifact bytes, and exact numerical/evidence hashes. A serialization-only or
microbenchmark speedup MUST NOT be presented as a campaign projection.

#### Scenario: insufficient end-to-end improvement

- **WHEN** the combined diagnostic does not materially reduce total runtime
- **THEN** the report identifies the measured limiting stages and does not
  promote IMPL2 or authorize campaign execution
