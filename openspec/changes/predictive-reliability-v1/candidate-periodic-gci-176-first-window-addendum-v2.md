# Independent 176-cell periodicity window — corrected addendum v2

This addendum supersedes the execution bounds in v1 before any complete cycle
was accepted. The first attempt failed in the runner while processing the cycle
observation tuple; it completed zero cycles and its partial artifacts remain
preserved under `DINO_ARTIFACT_ROOT/.../window-176-01`.

## Frozen identity and source

Reuse audited E2B A30 and the same 176-cell P0 conservative initialization,
source hashes, physics, solver, candidate, fresh detector and 9000 RPM identity
from v1. The runner correction only unpacks the existing observation and its
provenance separately. No solver or physical-model equation changes.

## Corrected window and cost

The failed attempt measured 120.23 s solver time before the observation bug,
without completing a cycle. The previous 108.73 s/cycle estimate is therefore
superseded for admission. The corrected first window is absolute cycles 31–37
(seven cycles maximum), solver budget 900 s, admission limit 1080 s. Projection
at the observed rate is 841.6 s, or 1009.9 s with 20% margin. This fits the
1200 s per-grid limit. The window remains within the 6 h cumulative E1.3 budget
and 1 GiB study artifact cap.

Stop on detector classification, conservation/admissibility failure, the
registered no-progress rule, or the budget. Preserve every complete cycle and
any partial recipe. Review before any 176 continuation or another mesh. No GCI
until all three grids are periodic and audited. No candidate promotion,
experimental validation, or predictive claim.
