# Three-level bounded mesh diagnosis V1

Owner reauthorized continuation on 2026-10-26. Registered before calculating the
third solution. Earlier two-level artifacts remain immutable, with their actual
source/runner hashes. This is numerical solution verification, not validation.

## One additional engine execution

Reference levels: `spatial-muscl-coarse` (44 cells) and `mesh-refined-v1`
(88 cells). Add 176 cells by conservative exact frustum bisection of the original
88-cell **initial configuration**, not its terminal checkpoint. Same A9000,
720 degrees, equivalent-nozzle V2, MUSCL V1, CFL, physical geometry, wall h/T,
combustion, species and independent initialization. Record each accepted time
step, rejection and native complete-revolution checkpoint. No warm start.

Budget 240 seconds, 10000 steps, 5 MiB output, original storage preflight/reserve.
Projection from 88-cell case is about 180 seconds; stop rather than extend if the
actual budget is exhausted. Solver and detector unchanged. No full RPM campaign.
The nominal maximum step remains 0.5 degree; existing CFL/admissibility rejection
determines actual steps. Therefore differences combine spatial and residual
temporal error: no pure spatial uncertainty or mesh-independence claim.

Input checks before stepping: hash-bound successful parent configuration and
terminal state, exact 720-degree reference phase, native terminal checkpoint,
reference RPM 9000, static reed. Parent and child initial mass/energy/species
integrals agree within 1e-12 relative; frustum volume moments and wall partitions
preserved. Native static checkpoints do not bind source. Prior producers precede
the moving-cell heat correction; their static cells use the identical mesh volume
so that correction is inactive here. No historical bindings are rewritten.
The new receipt records actual solver dependency hashes, runner/helper hashes,
parent receipt hash and actual independent initial checkpoint identity.

## Comparison fixed before calculation

Use three levels with exact factor-two nested meshes. Verify the two child
configurations equal the conservative transformation of their respective parent
(including original physical inputs and wall mapping) before accepting a family.
Compare terminal states at exactly 720 degrees in SI units; sum extensive species
and volume-integrate Euler states to their original coarse volumes.

For cylinder/net indicated work, crankcase pumping, heat, fresh delivery and
trapping/species inventories: report signed successive differences, ratios and
classify monotonic decreasing, oscillatory decreasing, nondecreasing, or
indeterminate/roundoff. A shrinking difference in power alone is insufficient.
For monotonic nonzero decreasing differences, p = log2(|(f44-f88)/(f88-f176)|)
is a **conditional fitted order**. Richardson extrapolation assumes one leading
error term: do not call it an established continuum solution or a measured
uncertainty. Three points fit that ansatz; no self-derived asymptotic-ratio check
constitutes independent proof. No clipping of oscillatory or negative orders.

Do not compute/claim a certified GCI band where time error is unseparated or
asymptotic behavior unestablished. Sources: NASA Glenn/NPARC, *Examining Spatial
(Grid) Convergence*, https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html
(three-grid/order/extrapolation discussion; conditional nature retained here).

Execution acceptance retains mass/species normalized residual <=1e-9, energy
<=1e-8, full phase, checkpoint equality and cross-mesh rejection. This gate does
not impose a desired power or manufacture predictive validation. If incomplete,
compare only complete shared phases and do not fit terminal three-grid order.
The one execution ends this diagnosis; any additional calculation needs a
separate technical rationale and explicit budget, not automatic refinement.
