# Spatial sensitivity diagnosis, 2026-10-27

SELF_REVIEW; no physics/solver change, no predictive or periodic claim.

The terminal .12265579 is relative density difference, exhaust parent cell4,
x=[.1208,.1586]m; rho=.606202 versus .531848 kg/m3 after conservative projection.
It is not a power error. Cylinder cumulative work28.8101 versus29.7602J differs
3.30%; exhaust mass differs0.752%, energy0.903% at720degrees. Work is cumulative
from independent initialization over two transient cycles, not periodic power.

Exact parent/child geometry reconstruction verifies every configuration field,
face, centroid, frustum volume and thermal-area split. Projection averages
conserved densities by exact volume and sums extensive species, then recovers
pressure/temperature. Eight checks PASS including shifted-face rejection,
all-component integral conservation, analytical boundary order in both directions.
Initial same-volume state differences <=1.01e-15. This excludes a changed geometry
or nonconservative projection as explanation; not discretization error of area
source terms on this nonsmooth, transient engine trajectory.

Two source-checkpoint-bound cycle2 probes sampled25 common phases at15degree
intervals. Each restored only its own original360degree checkpoint; no cross-RPM
or cross-mesh state transfer. Compute invocation elapsed15.46/40.07s, concurrent,
not speed benchmarks. Their terminal states/ledgers match original trajectories
exactly despite potential extra phase cuts. Stored recipes, frames, hashes,
FAST terminals and conservation reports are L1 evidence, not new L2 audits.

At360degrees the peak is residual-gas fraction in outletcell30, absolute.19612.
At630degrees peak is residual fraction in cell29, absolute.60901; maximum gas
metric .38217 is density at570degrees in cell29. The exit is x=1.079m.
At630degrees residual fractions coarse/fine projected for cells28/29/30 are
.977/.790, .882/.273, .563/.021. Native terminal outlet velocities are positive
105.41/58.70m/s at that phase. The largest differences track a steep compositional
front near the exit and its gas-state evolution. They are not uniform throughout
the engine and the720degree maximum alone understates transient field sensitivity.
CSV/JSON preserve every sampled phase. No claim of localization between samples.

V2 endpoint traces are demonstrably nonconstant at360/720degrees; both ends of
the exhaust reconstruct gas. Smooth analytical steady-duct order ~2 in both
orientations versus ~1 with V1 zero endpoint slopes, already preserved as controls.
Thus permanently first-order endpoint cells are not the current generic cause.
Local limiter flattening at extrema/discontinuities is admissible; no evidence
justifies removing the limiter. Smooth isolated tests do not exclude transient
outlet reflection, characteristic closure or local limiting effects.

A periodic constant-density passive top-hat experiment separates transport from
geometry/ports: u=1, p=1, rho=1, gamma1.4, t=.1, CFL-like dt=.2/[n*(1+sqrt1.4)],
initial species0 fraction1 on [.25,.5], species2 its complement; other species0.
Exact cell-averaged translated interval[.35,.6] is the reference. SSPRK2/HLLC with
MUSCL on32/64/128cells gives L1 .03554/.01875/.01445 versus first-order
.07402/.04989/.04138. Species integral remains.25 within6e-17; gasdensity error0.
This shows substantial mesh sensitivity of a front is possible without any port,
area or gas-energy change. It does not prove the engine's entire error is passive
transport, nor justify second-order claims across a discontinuity.

**Decision:** no demonstrated solver defect to correct yet. Dominant observed
feature is an underresolved near-exit compositional/gas front. Its diffusion,
phase displacement and outlet interaction remain coupled; they have not been
quantitatively separated. The local linearized-shift estimate in the JSON is
not a valid finite displacement fit for this steep nonlinear front. Do not use
it to align acceptance states or mask error. No fundamental architecture change
is justified by these data. Next bounded experiment should isolate the same
outlet/front regime on a uniform duct with and without the physical boundary,
using measured donor direction/trace and fixed mesh/time controls. Preserve all
engine models. Only then consider third-grid176 V2 and the finite periodicity
protocol, with no automatic extension/campaign. Resource bounds are preregistered
in mesh-periodicity-staged-protocol-v2.md. Experimental Cahoon remains externally
deferred; alternative institutional link retained without new request.
