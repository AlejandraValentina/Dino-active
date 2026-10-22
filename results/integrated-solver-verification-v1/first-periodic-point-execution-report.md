# First periodic point: terminal result

**PARTIAL_RESOURCE_OR_TIME.** Five physical cycles completed at 3000 RPM, 48 cells, CFL 0.4. No periodic point accepted. Cycles 6-10 were not started.

## Physical evolution (transient)

| Cycle | New-cycle wall s | Indicated work J | Cylinder end bar | End K | End mass mg | Failed lag-1 metrics |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 109.72 | -40.705 | 21.064 | 1029.72 | 125.393 | insufficient history |
| 2 | 134.52 | 16.353 | 14.148 | 892.02 | 97.224 | 212 |
| 3 | 138.06 | 0.607 | 13.804 | 863.48 | 97.998 | 199 |
| 4 | 134.75 | -0.214 | 13.932 | 866.89 | 98.513 | 140 |
| 5 | 133.03 | -0.076 | 14.134 | 885.64 | 97.830 | 117 |

All five primary audits PASS with recomputed=True. No accepted lag-1 streak or period-2 branch streak. End-state pressure/temperature are not peak values. IMEP, BMEP, torque and power remain UNDEFINED under the existing periodicity requirement.

## Operational stop

Full launcher wall: 1588.672 s. Conservative ledger: 1628.296/3000 s. Four invocation walls: 384.469, 363.859, 451.843, 388.125 s.
New-cycle work accounts for 650.078 s; the other 938.218 s includes full-history revalidation, startup and closure. The last invocation revalidated the five-cycle history but admitted no new cycle. Its approximately 195.64 s remaining worker window was below the frozen 237.09 s admission estimate.

The global budget and memory limits were not exhausted. This is a conservative scheduling/resource termination, not a demonstrated impossibility to complete cycle 6 and not a physical or numerical terminal failure.

Peak worker RSS: 398.49 MiB; supervisor+worker peak: 424.36 MiB. Sampling is not an OS hard memory ceiling.

## Closure

Primary hashes, selected checkpoint and result integrity verified. Checkpoint restores canonically, next_cycle=6; no orphan or partial primaries, all workers stopped. Definition and scientific/operational sources remain exact. A3b and all historical evidence remain unchanged. No retry or code change.

One next decision: review the measured revalidation/admission cost before another authorization. Do not infer a physics change or extend this attempt.

Full compact evidence: [first-periodic-point-execution-receipt.json](first-periodic-point-execution-receipt.json). Heavy primaries remain outside Git.
