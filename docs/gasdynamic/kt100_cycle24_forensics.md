# KT100 V2 cycle-24 forensic result

The R1 campaign was not rerun. Its accepted cycle-20 checkpoint was replayed
through cycles 21–23, each matching its persisted primary exactly, then stopped
at the original cycle-24 failure. The replay reproduced the exact angle
`142.19487248520613°`, accepted-step count `21925`, and
`InvalidState: Conserved rho/species inadmissible`.

The failed primitive conversion was an intake-duct cell with
`rho=0.7952109571685706 kg/m³` and legacy `rhoY=0.7952109571685707 kg/m³`:
the scalar exceeded density by exactly one float64 ULP (`1.1102230246251565e-16
kg/m³`). Pressure, temperature, velocity, Mach, both SSPRK2 stage inputs/RHS,
the candidate state, species inventory, boundary traces, port areas, and
pre-failure ledgers are stored in
`results/2t-commercial-core-20261002/kt100_cycle24_forensics.json`.

The cause is a general conservative-to-primitive roundoff rejection for the
legacy `rhoY` passive scalar near `Y=1`, which P5 still accumulates while P6's
four-species mass inventory is authoritative. The minimal P5 cell reproducer
passes through a dedicated bounded 8-ULP view adapter; a 32-ULP violation still
fails, and the general `IdealGas.primitive()` check remains strict. This changes
no thermodynamic equation or flux. It does not prove a whole-cycle continuation:
the R1 allowance is consumed, four requested RPM points were never started,
and no KT100 R2 is authorized by this finding.

Review status is author forensic analysis and targeted self-review. No
independent review artifact exists for this delta.
