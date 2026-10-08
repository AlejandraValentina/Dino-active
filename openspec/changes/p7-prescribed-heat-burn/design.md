# Design

P7 uses `motorsim.p7_prescribed` as the single source-law implementation. The
event captures cylinder fresh-air and fuel at 350+360k degrees, splits steps at
350 and 390 degrees, and supplies species and internal-energy RHS contributions
at both SSPRK2 stages. P6 labels remain bookkeeping only. Ports are closed for
the event and energy includes only external exchange, `-p dV`, and heat.
P4 remains blocked and all results are conditional on P4.
