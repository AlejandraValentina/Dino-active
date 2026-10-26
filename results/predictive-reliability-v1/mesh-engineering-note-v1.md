# Bounded mesh sensitivity — SELF_REVIEW, 2026-10-26

One independent-initialization, two-revolution A9000 transient diagnostic,
equivalent-nozzle V2 + MUSCL V1. Neither case is a periodic power prediction.
Protocol and thermal remapping addendum were committed before execution.

| Quantity | 44 cells | 88 cells |
|---|---:|---:|
| Cylinder work delivered over two revolutions, J | 28.5676343 | 29.4580651 |
| Crankcase work absorbed, J | 5.56264147 | 5.59654386 |
| Combustion heat, J | 151.235911 | 149.703783 |
| Heat to walls, J | 19.9551819 | 19.9687478 |
| Solver compute, s | 25.6231 | 66.5121 |

Fine-case initial inventory discrepancy is 1.59e-15 relative. Final normalized
mass/energy/species conservation residuals are respectively 9.79e-16,
3.65e-16, 6.06e-16. Native checkpoints at 360/720 degrees restore exactly;
the incompatible coarse checkpoint is rejected. 2,396 accepted fine-grid steps.
Exact frustum bisection preserves geometry, volume moments and total wall area,
h and wall temperatures; initial species are prolonged conservatively.

Cylinder work changes +3.12%. Conservative projection at the same 720-degree
phase finds exhaust cell 4 density difference 10.94%, temperature 9.66%; cell 24
pressure 5.82%; cell 30 velocity difference normalized by sound speed 0.1104
(this last value is not an 11.04% relative velocity error). These transients
remain sensitive to spatial resolution, materially more than the earlier
0.0893% time-step difference. One pair cannot establish a convergence order or
an asymptotic error bound. No mesh independence or predictive accuracy claimed.

Decision: diagnostic execution/conservation gate satisfied; preserve candidate
status. Do not tune closure parameters or judge real-engine accuracy from this
coarse transient. Further convergence evidence is required before a quantitative
engine prediction, alongside measured input and validation data. No automatic
additional mesh campaign is authorized by this receipt.

The first preparation attempt stopped before any steps because JSON lists had
been converted to tuples. Exact native roundtrip regression now detects this;
no physical values or comparison criteria were changed. Seven preparer tests
pass. Primary bound evidence: `mesh-refined-v1/receipt.json`, native checkpoints,
configuration and accepted-step recipe. Earlier full-stage diagnostics and
source-bound replay audits remain preserved under their original source hashes.
