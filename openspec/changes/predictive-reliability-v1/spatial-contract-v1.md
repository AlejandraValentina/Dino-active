# Spatial reconstruction candidate V1 — acceptance before implementation

Preparation only. Implementation waits for the verified connection gate. Preserve
the first-order legacy path and every P0-P9 threshold. No CFL, EOS, combustion,
geometry or periodicity change. Use existing HLLC/HLLE and the integrated SSPRK2.

Piecewise-linear primitive reconstruction on actual cell-center distances;
limited slopes with theta=1.5 monotonized central/minmod. A common cell limiter
bounds reconstructed density/pressure to neighboring positive cell means. No
pressure floor or modification of conservative averages. Endpoint slopes are zero
until a separately verified boundary reconstruction exists: these boundary cells
remain first order. Internal numerical fluxes use shared left/right face states.

Reconstruct extensive-species-derived fractions consistently with the gas mass
flux. Three independent slopes and a fourth equal to their negative sum preserve
the simplex. Apply one common bound for all four fractions and gas primitives.
No independent species flux can manufacture mass; donor selection follows signed
gas mass flux. Cell means remain authoritative. Stationary geometry sources keep
the existing pressure balance; do not claim an isentropic nozzle well-balanced
scheme or second order at discontinuities.

Numerical selection must be explicit, serialized, hashed, immutable during a run,
and rejected by readers that do not implement the capability. Default remains
legacy. Integrated diagnostics use the verified new coupling only after its gate.

## Fixed tests and isolated diagnostics

- Positive and invalid inputs, nonuniform mesh, orientation, constant-state and
  stationary contact preservation; no new extrema or negative rho/p/fractions.
  Reconstructed fractions sum to one within 32 machine epsilons.
- Periodic smooth entropy wave: rho=1+0.2 sin(2*pi*(x-t)), u=1, p=1,
  gamma=1.4, with smooth four-species fractions. Initialize exact cell averages,
  not point samples. SSPRK2, CFL=0.2, t=0.1; N=40/80/160. Independent analytic
  cell-average L1 errors; observed gas/species order >=1.7 for final refinement.
  Compare error against the first-order path at equal mesh and timestep.
- Small-amplitude right-going acoustic sine, amplitude 1e-6, same meshes,
  time and CFL. Compare pressure error to linearized analytic propagation with
  nonlinear truncation stated; final observed order >=1.6.
- Sod shock tube gamma=1.4, exact Euler reference: positive states, shock speed,
  contact/species transport and conservation; do not demand second order at shock.
  Closed or periodic domains must conserve mass/total energy/species to 1e-11 of
  natural inventory/throughput scales, allowing declared accumulation roundoff.
- Stage-coherent integrated execution, configuration/restart rejection for wrong
  reconstruction model and exact same-model replay. Source/time and legacy
  regression checks before dependent model identification. Report any extra
  positivity rejections; never lower numerical accuracy to meet runtime budgets.

First subsystem diagnostics <=60 s, engine diagnostics <=240 s, outputs <=0.1 GiB
per run with preflight. No RPM curve or periodicity campaign. No predictive claim
from manufactured smooth waves. Any material model failure leaves its gate open.
