# Transonic connection V2: equivalent ideal nozzle candidate

2026-10-26. Owner authorized resolving the transonic domain and selectable
integration only after verification. V1 and its failed domain receipt remain
unchanged. This contract precedes the V2 implementation and decision runs.

## Explicit change of closure

V1's separated subsonic expansion does not specify the underexpanded jet or its
interaction with the surrounding annulus. Simply extending its acoustic equation
past sonic conditions overdetermines an inlet with no outgoing characteristic.

V2 uses a STANDARD_V1 **equivalent ideal converging-diverging nozzle**, with
effective throat At=Cd*Ageometric, pipe section Ap, inviscid isentropic segments
and at most one entropy-producing normal shock. This is an explicit physical
model assumption, not a derivation that real ports have a smooth divergent
profile, and not a claim that Cd calibrated for another model transfers unchanged.
At and Ap alone specify a quasi-steady nozzle's state and shock area; they do not
specify its axial shock position. No invented nozzle length or pressure recovery
calibration is permitted. V2 cannot be relabelled the verified V1 expansion.

Chamber-to-pipe: conserve Q and H0=cp*Tc. Unchoked flow is isentropic, matched to
the exact interior acoustic curve. Choking fixes Q=At*Gcritical(pc,Tc); its pipe
state is either subsonic downstream of an internal normal shock, sonic at At=Ap,
or the supersonic area-Mach exit. The subsonic choked branch is bounded by the
isentropic subsonic exit and the downstream state of a normal shock at the exit.
Infer the normal-shock area from its total-pressure loss and require At<=As<=Ap.

Supersonic inlet selection uses the exact Euler Riemann problem between pipe
interior (left, outward coordinate) and prescribed nozzle exit (right). All its
waves must enter the pipe or be stationary. Otherwise this exit is not a valid
boundary state. In particular do not keep an outgoing subsonic characteristic
constraint while prescribing supersonic inflow. At a stationary exit shock the
upstream and downstream Euler fluxes agree, providing flux continuity.

Pipe-to-chamber: use interior donor entropy through the incoming acoustic wave,
then isentropic contraction into a receiver without pressure recovery. Supersonic
pipe outflow is unchanged when no upstream-moving shock is required. If contraction
capacity or chamber backpressure requires unstart, require a compression shock
with nonpositive propagation speed; do not apply downstream data upstream through
an outward-moving wave. An absent admissible branch is a typed domain error with
the inputs preserved, not clipped flow or silent legacy fallback.

Closed apertures solve the reflected wall wave (zero mass/energy/species; correct
dynamic wall pressure). Vacuum-generating data are outside positive-state scope
and reported explicitly. Closed-port wall momentum must not be counted twice.
Full face Euler flux, donor species and shared chamber/duct mass and energy are
retained. The stationary geometry supports axial reaction without wall work.

## Verification fixed before numerical decision

1. Independent exact Euler reference: Sod pressure/velocity, shock RH and entropy,
   contacts, reflection, rarefaction fan samples, vacuum rejection and symmetry.
2. Manufactured nozzle states for gamma 1.2/1.35/1.4, At/Ap .01/.1/.5/1,
   300/900 K, both normals. Subsonic, sonic, supersonic and internal/exit shocks.
   Full flux and mass/energy closure relative <=1e-9; shock RH <=1e-10.
3. Match characteristic directions, positive rho/p/T, donor H0 and species;
   total pressure cannot increase along the nozzle. No Mach cap.
4. Sweep both choking transitions and exit-shock transition; physical flux must
   converge continuously under nearby matched data, <=1e-6 at relative 1e-8 input
   perturbations. Preserve rest exactly and verify a positive-area limit to wall.
5. Reevaluate all 1008 V1 grid inputs and all 37 old counterexamples with full
   branch metadata, conservation and causal-wave checks. Explicit domain failures
   remain failures, never counted as successful states.
6. Only after all gates: selectable integrated model with distinct identity and
   checkpoint bindings; legacy route remains the default. Bounded diagnostics
   preserve actual endpoint primitives and both stage fluxes; check conservation,
   restart, admissibility and time refinement. No power target or claim of
   experimental predictive validation. Spatial work waits for this gate.

Primary references: ideal-gas nozzle and normal-shock conservation relations,
[NASA CDV reference](https://www.grc.nasa.gov/www/wind/valid/cdv/cdv.html);
[Clawpack exact Euler Riemann theory](https://www.clawpack.org/riemann_book/html/Euler.html).
The new implementation is independently derived; the reference solver is kept
separate from the frozen production HLLC and must not alter P0-P9 contracts.
