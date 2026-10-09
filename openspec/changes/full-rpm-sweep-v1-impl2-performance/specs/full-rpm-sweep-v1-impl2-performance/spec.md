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
