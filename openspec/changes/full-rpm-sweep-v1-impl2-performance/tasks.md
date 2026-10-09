## 1. Restart compatibility

- [x] 1.1 Add explicit cycle-local trace compaction and cumulative fuel-ledger baseline.
- [x] 1.2 Test round-trip continuation, ledger integrity, conservation, rejection of ambiguous legacy compact snapshots, and checkpoint file hash mismatch.
- [x] 1.3 Update the implementation runner to use the explicit compaction API.

## 2. Performance evidence

- [x] 2.1 Add stage timings and accepted/rejected step accounting to bounded benchmarks.
- [x] 2.2 Benchmark baseline and geometry-cache candidate on A4000 and B4000.
- [x] 2.3 Separate historical filesystem-write metrics from in-memory measurements and record sampled peak process RSS.
- [x] 2.4 Assess Numba feasibility from measured stage shares; reject a kernel prototype because its maximum end-to-end Amdahl impact is below 1.16x.

## 3. Compatibility and release gate

- [x] 3.1 Record dependency, producer, artifact-root, and benchmark identities for IMPL2.
- [ ] 3.2 Run relevant regressions, strict OpenSpec, artifact integrity, and program-status checks.
- [x] 3.3 Preserve FULL_RPM_SWEEP_V1 = PARTIAL; do not run campaign points.
