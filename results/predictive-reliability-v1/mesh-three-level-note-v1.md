# Three-grid verification and transient diagnosis — SELF_REVIEW

2026-10-26. No physical equation, CFL, combustion, geometry, port model or
periodicity threshold was changed. One extra engine execution, independent
initialization, 176 cells, two revolutions. It completed in 184.42 seconds of
solver time (185.38 seconds process wall time), within the 240-second budget.
3,869 accepted steps; normalized mass/energy/species residuals below 1.33e-15.
Native checkpoints restore; cross-mesh checkpoint restoration is rejected.

| Two-revolution transient quantity | 44 cells | 88 cells | 176 cells |
|---|---:|---:|---:|
| Cylinder work delivered, J | 28.567634 | 29.458065 | 30.202562 |
| Net indicated work delivered, J | 23.004993 | 23.861521 | 24.588441 |
| Combustion heat, J | 151.235911 | 149.703783 | 148.844792 |
| Global stored mass, kg | 0.003111376 | 0.003128997 | 0.003142615 |
| Global stored energy, J | 1410.48459 | 1419.26698 | 1426.30400 |

The last refinement changes cylinder work by +0.744497 J (+2.53% relative to
88 cells) and net work by +0.726920 J (+3.05%). Successive cylinder-work
differences have ratio 0.8361, conditional fitted order 0.2582; net-work order
0.2367. Neither is a demonstrated asymptotic order. The formal smooth periodic
subsystem order above two does not carry over automatically to this engine
transient with fronts, limiter activation and first-order boundary cells.

Of 27 scalar quantities, 20 have shrinking monotonic differences, four shrinking
oscillations, two nonshrinking monotonic differences, one nonshrinking
oscillation. Global fresh-air/fuel inventory increments do not shrink; heat to
walls oscillates. On the same original control volumes, only 245/366 normalized
field differences shrink. Exhaust pressure at original cell 27 differs about
15.0% between the last two projected solutions; cell-4 burned fraction differs
by 0.1041 **absolute fraction**, not relative percent. Do not judge equivalence
from work or count alone. Indicators mix residual time error and spatial error;
the earlier 44-cell time test does not bound time error on every finer mesh.

Decision: **mesh independence NOT demonstrated**. No certified GCI/uncertainty,
no extrapolated power prediction, no additional automatic refinement. The
conditional Richardson fit in the machine-readable analysis is a one-leading-
error-term fit, not established truth. Three fitted points cannot independently
prove their own asymptotic assumption. See [NASA/NPARC guidance](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html).

## Periodicity: separate question, zero new solver steps

Bound native states at 360 and 720 degrees and cumulative ledger differences
feed the **unchanged** V2 comparator and streak detector. The reconstruction is
explicitly L1 checkpoint-derived evidence, not a fabricated audited primary.

| Cells | Failed cycle-1/2 comparisons | Checks | Exhaust failures |
|---|---:|---:|---:|
| 44 | 280 | 413 | 191 |
| 88 | 540 | 809 | 379 |
| 176 | 1007 | 1601 | 723 |

The checks grow with cell count: these raw counts do not rank mesh quality.
All cases are still transient. With two cycles, neither the required streak nor
period-2 convergence can be established, even if one comparison were to pass.
No inference of different periodic attractors, numerical instability, or a warm
start defect follows. These are independently initialized new-model transients;
historical periodic curves of the older model are not new-model validation.

## Consequences for the next technical step

Conservation/restart and manufactured smooth/shock verification remain valid.
The slow/nonmonotonic engine sensitivity is an unresolved accuracy limitation,
not evidence to tune power or replace equations. Before another expensive engine
calculation, isolate boundary/area/initial-front truncation on cheap analytic
problems; only a demonstrated defect warrants an implementation correction.
A future periodic result needs its own state/whole-domain detector acceptance
and numerical uncertainty; two initial revolutions cannot replace it.

Forty-one focused reference/loader/phase/conservation-indicator tests pass. The
loader checks native configuration compatibility in addition to file hashes,
including a negative case with a rehashed but incompatible checkpoint. Frozen
P4–P8 regression: 301 PASS, 3 SKIP, four existing NumPy warnings, 176.98 s.
rc7, P0–P9 evidence and the unrelated
SPV1 checkpoint task remain untouched. Large historical primary streams remain
local with their original hashes; no duplication or cleanup was performed.
