# FULL_RPM_SWEEP_V1_IMPL2 performance recovery

## What Changes

Introduce a separate restart format with explicit cycle-local trace and ledger
baseline metadata, add bounded phase-level performance accounting, and define
compatibility isolation for any future IMPL2 campaign.

## Why

The v1 campaign is PARTIAL and its preregistration, two accepted points,
primaries, checkpoints, and manifest are immutable. The measured 5.3% geometry
cache improvement is insufficient for the remaining 28 points. A separate
implementation identity is needed for checkpoint compatibility and any later
optimization work.

## Scope

- Add explicit cycle-local trace compaction and ledger baselines for restart.
- Measure solver advancement, primary construction, independent audit,
  serialization, filesystem writes, and accepted/rejected step time separately.
- Evaluate compiled kernels against measured end-to-end cost before adopting
  them. Preserve the reference implementation and all existing numerical
  criteria.
- Bind implementation, producer, solver dependencies, benchmark outputs, and
  artifacts to `FULL_RPM_SWEEP_V1_IMPL2` and a distinct artifact root.

## Non-goals

- No RPM campaign point may start under this proposal.
- No equation, integration sequence, CFL rule, detector threshold, hard gate,
  tolerance, or v1 artifact may change.
- No reuse of v1 checkpoints across implementation identities.

## Compatibility decision

Legacy v1 checkpoints with a cleared trace and cumulative fuel ledger remain
unchanged and are rejected as ambiguous by the revised restore path. New
checkpoints must explicitly declare `trace_scope = CYCLE_LOCAL` and carry the
fuel ledger baseline and trace-origin state captured when the preceding full
cycle trace was compacted. Their outer artifact hash binds the discarded
historical trace.
This is a restart-format change and requires a new implementation hash set.

## Acceptance

- Full-trace and cycle-local restore continuation, ledger integrity, conservation
  and incompatible-checkpoint rejection tests pass.
- End-to-end A4000/B4000 benchmarks report hot and compilation costs, separate
  numerical and evidence stages, accepted/rejected step costs, and memory.
- Baseline and candidate satisfy all existing scientific comparisons.
- If measured end-to-end speedup after the three dominant stages remains below
  3x, stop micro-optimization and record an architecture-level diagnosis.
- FULL_RPM_SWEEP_V1 stays PARTIAL and no campaign is authorized by this change.
