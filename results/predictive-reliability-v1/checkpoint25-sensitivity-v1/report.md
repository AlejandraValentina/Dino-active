# Checkpoint25: finite temporal/spatial attribution
2026-10-27. **Spatial sensitivity dominates full-duct fields and outlet throughput;
tail composition primarily continues its transient evolution over this one cycle.
No solver defect demonstrated.** No periodicity/mesh-independence/experimental claim.

## Domain, initialization and resource limits

Same source-bound native25, same EOS/combustion/ports/CFL/closures, one cycle
9000->9360degrees, same30degree output phases.44/88total cells across5ducts.
MUSCL V2, transonic V2 and OPEN_END_PLENUM_V2 unchanged. Original history untouched.
Coarse cases are exact same-simulation resumes. Fine cases are explicitly new
conservative diagnostic initializations with constructor-generated configuration
identity and real initial inventory, not native cross-mesh resume or invented hashes.
Native restore of the original checkpoint on the other mesh remains rejected.
The diagnostic maps physical state, clock, ongoing combustion event/history and
volume-weighted trace origin. No detector history is transplanted to claim a
period on the refined mesh. Five focused initialization/norm tests PASS.

Exact frustum volumes/centroids and thermal-area split; conserved densities
constant inside each parent; extensive species split by volume. Initial relative
inventory errors<=9.22e-16, inverse restriction errors<=1.16e-15; primitive state
of each child equals its parent. Checkpoint source remains unmodified. The actual
constructor initial-inventory values are retained for the new configuration;
no restore guard is relaxed. Unknown subcell slopes are not fabricated.
**P0 remap adjustment cannot be separated from subsequent spatial error in one
cycle, even though the initial common-volume comparison is exact.**

Initially3cases, then fourth for interaction. CFL collapsed finecap.5 to mostly
actual.25degree steps, so its agreement with finecap.25 was not a temporal test.
A preregistered amendment added exactly one finecap.125 case (2882accepted steps)
versus about1440withfinecap.25. No more cases. All5completed within120s each,
aggregate measured case wall~211s, below480s total admission. Max16MiB per case,
preflight passed. Actual stages, signed interface fluxes, profiles, recipes and
native terminal checkpoints persisted. All terminal checkpoints restore.

## Quantitative differences (not exact errors)

Volume-weighted L1/L2; maxima normalized symmetrically for positive gas states,
velocity by sound speed, species as absolute fraction. Conservative projection
recovers gas primitives only after restricting conserved quantities; species
sum extensively, not by arithmetic fraction averaging.

|Contrast, final phase|Burned fraction L1|L2|Linf|Pressure relative L1|
|---|---:|---:|---:|---:|
|44cells .5->.25deg|2.696e-5|1.130e-4|7.749e-4|.0004143|
|88cells .25->.125deg|1.247e-5|4.002e-5|2.546e-4|.0001809|
|44->88 at common.25deg|.012505|.034261|.169482|.020491|
|44cells same-phase cycle25->26 at.25deg|.001344|.001901|.005481|.0004386|

Full spatial burned difference is9.3times the one-cycle change in L1; temporal
44difference is about2%ofthatcomposition change. But pressure time difference
is comparable to the tiny pressure evolution between cycles; **not all temporal
contributions are negligible for drift or work near convergence**. Work changes
.02775%with44time refinement,.007889%with88time refinement; space at matched.25
changes.02313%. Neither work nor its near-zero cycle increment certifies field
accuracy. IMEP/work for each case in cases-final.csv; fine0125 work131.053516J.

The spatial density maximum.16953 and burned maximum.16948 occur at parent
exhaustcell5. Temporal effects and physical domains are compared at equal phase,
not by shifting waves to improve agreement. Sampled wave-peak positions and all
half-fraction crossings are preserved; multiple crossings do not identify one
unique front.30degree sampling does not resolve every acoustic arrival/peak.
No analytic transient motor reference or asymptotic order is available.
A separate pressure projection check gives relative L1 .020498 using volume-mean
fine pressure versus .020491 using pressure from restricted conserved state;
the unresolved-velocity-variance projection term is only8.73e-6 in L1. Thus
that thermodynamic averaging distinction does not explain the pressure gap.

## Region of original failed composition metrics

For parentcells16–30, burned L1 time44=4.868e-7, space=.00014194,
cycle evolution=.00191128; spatial difference is7.43%ofcycle evolution, temporal
is.0255%. Fine actual time halving yields tail L1=1.153e-7. Thus the local
composition plateau is most compatible with continuing discrete-model relaxation,
not a dominant time-step difference on this observation interval. However tail
pressure spatial L1=.02591 versus cycle change.0003624: gas dynamics and composition
have very different sensitivities. A single ratio cannot describe the solver.
This does not exclude later propagation of upstream spatial differences into
that tail or distinguish physical relaxation from numerical diffusion completely.

## Cylinder/exhaust reversal and inventories

At common.25deg cylinder->exhaust gross mass225.051mg versus229.486mg onfine,
reverse43.568mg versus44.164mg, outgoing atmosphere180.969mg versus203.473mg.
Space changes forward exchange1.97%, reverse1.37%, exit throughput12.44%.
Time44changes forward.034%,reverse.024%,exit.00058%. No outlet inflow in these
cases. All species gross/net integrals for every interface are persisted;
subsystem actual species balance residuals are in subsystem-checks.json.
Allclose<2e-17kg, not inferred from inventory alone. Global conservation also
closes (energy residuals order1e-11J over cumulative ledger); no clipping/defect.
Refinement changes spatial inventory/transport adjustment while work barely moves:
small work differences do not bound caudal or species errors.

## Decision

Do not launch another periodic campaign now. The original25 checkpoint remains
the accepted origin for any future same-model continuation; diagnostic fine
states do not become product warm starts. Tail composition supports relaxation,
but full-field spatial/initialization sensitivity and throughput are too large
to assert numerical sensitivity is globally small relative to transient change.
Only two meshes and two time steps each do not establish mesh independence or
exact truncation error; formal interaction remains mixed with nonlinear fields
and unknown subcell initialization. Neither transient solution is exact.

A staged three-grid44/88/176 study with validated initialization-representation
controls is prepared in post-checkpoint25-convergence-design-v1.md, before costly
periodic convergence. It separates P0/P1 remap effects from evolving wave/front
structure using short fixed-duration tests and matched **actual** steps.
A conditional original-checkpoint25 continuation(max4cycles/90s) is prepared but
not executed; it requires bounding spatial/initialization sensitivity for the
observables of interest first. No production equation, limiter, coupling,
threshold or rc7 baseline changed. SELF_REVIEW, L1 only.
