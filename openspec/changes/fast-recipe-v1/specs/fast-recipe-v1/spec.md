# FAST_RECIPE_V1

## ADDED Requirements

### Requirement: recipe captures the complete replay contract MUST

FAST_RECIPE_V1 MUST bind the implementation and solver hashes, immutable
configuration, full cycle-start state and ledgers, exact accepted timestep and
angle sequence, rejected-attempt sequence, cycle terminal state and ledgers,
combustion events, reed state, and canonical recipe digest. It MUST retain
enough information to reconstruct all canonical primary fields and periodicity
observables. Recipe capture MUST NOT alter solver equations or acceptance
decisions.

#### Scenario: complete recipe

- **WHEN** an integrated cycle is captured with FAST_RECIPE_V1
- **THEN** an offline consumer can reconstruct the complete V3 primary with
  all numeric fields equal to the reference path; the runner provenance field
  identifies the FAST producer, and periodicity observables are identical

### Requirement: audited results require canonical reconstruction and existing audit MUST

A FAST recipe MUST remain `UNAUDITED` until it reconstructs the complete
canonical V3 primary and `audit_integrated_cycle_primary` returns
`recomputed = true`. No engineering output, terminal PASS classification, or
campaign result may be emitted from a provisional recipe.

#### Scenario: provisional recipe

- **WHEN** a recipe has not completed canonical reconstruction and independent
  replay audit
- **THEN** its status remains `UNAUDITED` and it carries no definitive result

### Requirement: checkpoint and compatibility are fail closed MUST

Recipe checkpoints MUST be atomic, cycle scoped, and bound to FAST identity,
configuration, solver dependencies, and prior recipe hashes. Restore MUST reject
corruption, missing fields, cross-configuration recipes, incompatible solver
hashes, discontinuous step schedules, and terminal-state mismatches before
mutating the engine. A completed cycle boundary MUST resume identically to
uninterrupted advancement.

#### Scenario: incompatible recipe

- **WHEN** a recipe digest or binding differs from the requested engine
- **THEN** reconstruction rejects it and leaves the receiving engine unchanged

### Requirement: diagnostic benchmarks include deferred work MUST

Benchmarks MUST report physical advancement, capture, recipe I/O, primary
reconstruction, independent audit, total wall time, process CPU, memory, and
artifact bytes for conventional, provisional FAST, and fully audited FAST
scenarios. A provisional speedup MUST NOT be represented as an end-to-end
scientific speedup. Multiprocess comparisons MUST include worker startup,
coordination, capture, reconstruction, and audit.

#### Scenario: provisional-only gain

- **WHEN** FAST capture is faster but fully audited FAST is not
- **THEN** the report identifies the deferred costs and does not recommend FAST
  as the scientific pipeline

### Requirement: historical isolation MUST

FAST_RECIPE_V1 MUST use a distinct versioned identity and diagnostic artifact
root. It MUST NOT modify R2 evidence, the original FULL_RPM_SWEEP_V1
preregistration, historical primaries, checkpoints, receipts, or GUI files, and
MUST NOT start any RPM campaign point.

#### Scenario: diagnostic execution

- **WHEN** FAST_RECIPE_V1 benchmarks run
- **THEN** only isolated diagnostic artifacts are written and campaign point
  counts remain unchanged
