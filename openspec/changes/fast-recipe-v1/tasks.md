## 1. Capture and reconstruction

- [x] 1.1 Add opt-in lightweight step capture without changing default trace behavior or solver results.
- [x] 1.2 Implement hash-bound FAST_RECIPE_V1 with terminal ledgers, rejection log, atomic cycle checkpoint, and fail-closed restore.
- [x] 1.3 Reconstruct canonical V3 primaries and invoke the existing independent replay auditor.
- [x] 1.4 Test exact state/primary equivalence, conservation, ledgers, periodicity inputs, corruption rejection, and cycle-boundary restart.

## 2. Benchmarks and multiprocessing

- [x] 2.1 Benchmark conventional, provisional FAST, and fully reconstructed/audited FAST on A4000/B4000.
- [x] 2.2 Measure 1/2/4-worker combined execution including coordination, storage, reconstruction, and audit.
- [x] 2.3 Record implementation identity, resource use, artifact sizes, speedups, and adoption recommendation.

## 3. Compatibility and closure

- [x] 3.1 Verify R2, v1 preregistration, historical primaries/checkpoints/receipts remain unchanged.
- [x] 3.2 Run focused tests, OpenSpec strict, artifact integrity, and program-status checks.
- [x] 3.3 Keep campaign authorization false and all historical unstarted points unstarted.
