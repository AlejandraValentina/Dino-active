# FAST_RECIPE_V1 benchmark decision

## Diagnostic method

On Windows, the benchmark ran one complete diagnostic cycle for A4000 and
B4000 in three scenarios: conventional trace/build/audit; trace-free recipe
capture without audit; and trace-free capture followed by recipe read,
canonical primary reconstruction, the existing independent replay audit, and
primary persistence. Spawned process counts were 1, 2, and 4. Each worker had
an isolated output directory; one coordinator wrote the aggregate receipt.
The resource planner reserved 512 MiB per worker. Process startup and
coordination are included in scale wall time. Artifacts and logs are outside
Git under `DINO_ARTIFACT_ROOT`.

## Results

| Workers | Matrix wall time | Speedup vs 1 | Worker CPU sum | Peak individual RSS | Conservative summed RSS |
|---:|---:|---:|---:|---:|---:|
| 1 | 82.09 s | 1.00x | 77.81 s | 253 MiB | 253 MiB |
| 2 | 50.56 s | 1.62x | 79.41 s | 251 MiB | 477 MiB |
| 4 | 28.54 s | 2.88x | 80.88 s | 251 MiB | 870 MiB |

Across A4000/B4000, mean conventional job time was 16.30 s at one worker;
provisional recipe capture/write was 3.17 s (5.14x), while complete recipe
reconstruction plus independent audit and output persistence was 20.80 s
(0.78x). The provisional mode defers work and emits no primary/result. It is
not an end-to-end scientific speedup. Physical advancement remained about
2.1–2.2 s per cycle. Recipe reconstruction averaged 6.28–6.78 s and the
existing independent audit 8.24–8.68 s.

Conventional and reconstructed/audited canonical primary SHA-256 values were
identical for both points at every worker scale. A4000 SHA-256:
`65acda4fd1cc4c84a70ad44cfe86b004cfa218f232fb7abdbb434b413e2a0a34`; B4000
SHA-256: `2e5163e4cb38b30223a74b9da895a417100909948c4866923c79497b350f82ba`.
The receipt also binds configuration, solver, recipe and cycle checkpoint
hashes. The read-only verifier checked all 18 worker receipts, recipes,
checkpoints and primaries. Per-worker restore and one-step continuation
matched. Unit tests verify ledger/state equality, checkpoint continuation,
corruption rejection and independent audit with `recomputed=true`.

## Decision and limits

Classification: `FAST_RECIPE_V1_PARTIAL`; exploratory/provisional use only.
Do not adopt FAST as the scientific sweep evidence pipeline: complete
reconstruction and audit cost about 22% more wall time per tested cycle and
roughly double persisted bytes versus the conventional primary. Four-worker
spawn improved throughput of this six-job diagnostic matrix by 2.88x, but that
does not change the per-job FAST result and is not a campaign projection.

This diagnostic did not invoke the campaign runner, change campaign points,
or test recovery from abrupt process death inside a future sweep. Its
cycle-boundary checkpoint was restored and continued independently inside
each worker. Campaign authorization remains false. No projection to 30 points
is made because one cycle does not measure periodicity/convergence horizon.

Durable machine-readable details: `results/full-rpm-sweep-v1/fast-recipe-v1-identity.json`
and `results/full-rpm-sweep-v1/fast-recipe-v1-benchmark-receipt.json`; external
worker artifacts are rooted at the path recorded in the receipt.
