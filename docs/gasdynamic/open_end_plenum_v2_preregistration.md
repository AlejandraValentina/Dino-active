# `OPEN_END_PLENUM_V2` preregistration

Status: **IMPLEMENTED; the single preregistered KT100 campaign was executed, but its evidence writer failed before emitting cycle primaries**
Contract: `OPEN_END_PLENUM_V2 / OPEN_END_PLENUM_CONTRACT_V1`
Decision authority: user's scientific decision recorded 2026-10-05.

## Provenance decision

AUD-11 is classified by the user as **CASE B — CAPABILITY LIMITATION**. The
approved external interface is an ideal, lossless, stationary atmosphere/large
plenum. Its inflow is isentropic from specified stagnation pressure and
temperature. This is `SYNTHETIC_ASSUMPTION`; it is not a calibrated carburetor
and does not represent measured or calibrated Walbro WB40 data. No Cd, area,
pressure loss, fuel metering, AFR, or real-hardware behavior is inferred.

The frozen `Boundary` implementations are `LEGACY_CHARACTERISTIC_V1`. The
historical name `nonreflecting` is described as
`EXTERNAL_STATE_RIEMANN / FARFIELD`; this is semantic documentation only and
does not amend old source, fixtures, receipts, or interpretations. A future
`RESTRICTED_NOZZLE_V1` must require explicit documented Cd and effective area;
this preregistration defines no values or implementation for it. No
`MASS_FLOW_INLET` is included. Fixtures A/B keep their current endpoint kinds.

## Mathematical contract

Use a calorically perfect gas with the current EOS `R`, `gamma`, `cp`, and
outward unit normal `n`. Reservoir inputs are ambient static pressure `p_a`,
stagnation temperature `T_0`, and reservoir species composition `Y_0`; the
reservoir is at rest. The stationary reservoir also has stagnation pressure
`p_0=p_a`. For the interior primitive state `(rho_i,u_i,p_i,Y_i)`, define
`w_i=n*u_i`, `a_i=sqrt(gamma*p_i/rho_i)`,
`K_i=p_i/rho_i^gamma`, and outgoing invariant
`J_i=w_i+2*a_i/(gamma-1)`.

At a contact, pressure and normal velocity are common, but entropy/density and
species are side-specific. On the interior side at candidate pressure `p`,

```
rho_i*(p) = (p/K_i)^(1/gamma)
a_i*(p)   = sqrt(gamma*p/rho_i*(p))
w*(p)     = J_i - 2*a_i*(p)/(gamma-1)
```

For subsonic outflow, select `p*=p_a`, the interior entropy `K_i`, and
`w*=w*(p_a)`. If this state is sonic or supersonic, select the sonic limit
instead: `a*=w*=J_i*(gamma-1)/(gamma+1)` and
`rho*=(a*^2/(gamma*K_i))^(1/(gamma-1))`, `p*=K_i*rho*^gamma`. The external
pressure is a lower bound on pressure release; the choked face pressure is
computed from the sonic state and may exceed `p_a`.

For subsonic inflow, retain the outgoing invariant and interior entropy on the
interior side of the contact, while the plenum side has its own entropy
parameter `K_0=p_a/rho_0^gamma`, `rho_0=p_a/(R*T_0)`. Find the unique root on
the interval `w*(p)<0`, `0<p<=p_a`, of

```
F(p) = cp*T_0*(p/p_a)^((gamma-1)/gamma)
       + 0.5*w*(p)^2 - cp*T_0 = 0.
```

The subsonic root is unique because `dF/dp>0` for `w<0`. The common contact
pressure and velocity are `p*` and `w*(p*)`; use the reservoir-side donor
density `rho_0*=(p*/K_0)^(1/gamma)` in the incoming face state. Incoming
temperature is `T_0*(p*/p_a)^((gamma-1)/gamma)`, so
`cp*T* + (w*)^2/2 = cp*T_0`. If the requested inflow exceeds its isentropic
critical limit, use reservoir Mach `-1` and
`p*=p_a*(2/(gamma+1))^(gamma/(gamma-1))`; at this sonic limit all
characteristics are entering or tangent to the domain, so the interior
outgoing invariant is no longer imposed.

The sign of `w*` selects the mass donor: reservoir composition for inflow,
interior composition for outflow. Species flux is signed mass flux times that
donor composition. Energy flux is the same signed mass flux times donor total
enthalpy. Momentum flux contains `rho*w^2+p*`; its pressure reaction on the
domain is explicitly `-n*p*` per unit area (area is applied once by the
integrator). Reversing `n` mirrors velocity/mass-flux signs and leaves scalar
pressure, density, temperature, and donor choice invariant.

For `K_i=K_0`, the subsonic states and flux must reduce to the corresponding
`LEGACY_CHARACTERISTIC_V1` reservoir state to floating-point solver tolerance.
This test does not change V1. A fixed-ambient-pressure subsonic outflow has
unit-magnitude, sign-reversing linear pressure reflection at the boundary; it
is a plenum opening, not the legacy farfield boundary.

## Frozen verification set

The implementation is not eligible for the campaign until these versioned
tests pass:

1. exact subsonic reduction to V1 for `K_i=K_0`, inflow and outflow;
2. reversal continuity at several reservoir/interior temperatures, with zero
   mass/species/energy flux at the analytic reversal state;
3. analytic fixed point at ambient pressure and zero velocity, including
   unequal temperatures and entropies;
4. inflow choking at the ideal critical ratio, sonic Mach, and stagnation-energy
   identity;
5. outflow choking at the ideal critical ratio, sonic Mach, and mass-flux cap;
6. linear acoustic pressure-reflection coefficient for the fixed-pressure
   outflow;
7. normal reversal symmetry for state, flux, species donor, and pressure force;
8. four-species donor selection on both sides of reversal;
9. `F_E/F_m = h_0` for incoming energy wherever mass flow is nonzero;
10. a fixed deterministic grid over pressure, temperature, velocity, and
    entropy ratios, checking finite/admissible states and no stale outputs;
11. frozen V1 tests and source/hash check demonstrating no change to
    `motorsim/gas1d/boundary.py` equations;
12. instrumented reproduction of each preserved KT100 r5 failure angle, logging
    actual boundary face state, normal, `J_i`, `K_i`, selected branch, and
    characteristic residual before any new campaign.

Focused suite names and numeric tolerances will be encoded in tests at the
implementation commit; the equations, comparison roles, and acceptance
relationships above may not be selected from the campaign outcome.

## One preregistered KT100 V2 campaign

After the capability tests and source/configuration binding pass, execute one
new five-point campaign using the new boundary ID. Use the current
`KT100_HYBRID_MODEL_FIXTURE_V2` producer/configuration as the base and change
only the explicit boundary capability identity/parameters. Keep geometry,
RPMs `[5000,7000,9000,11000,13000]`, CFL `0.4`, mesh target `0.03 m`, maximum
400 cycles, float64, `fastmath=false`, `parallel=false`, synthetic engine
parameters, and `REFERENCE_PERIODIC_CONVERGENCE_V1` thresholds unchanged. Write
to a new `...-r6-open-end-plenum-v2` result directory. Do not overwrite or
reinterpret r2–r5. Execute exactly once; preserve the outcome, including
nonconvergence or numerical failure. Boundary selection is based on this
preregistered physical model, never on convergence.

### Recorded campaign outcome (2026-10-05)

The one authorized command, `python scripts/run_kt100_open_end_plenum_v2.py`,
was executed once. Each of the five RPM points advanced to 390° and passed the
integrator's state, admissibility, and species-sum checks. Cycle-primary
construction then failed in `_duct_observables` with `KeyError('transfer1')`:
the evidence labels `transfer1`/`transfer2` did not match the P6 state keys
`tr1`/`tr2`. Consequently R6 contains zero durable cycle primaries and no
periodicity result. The offline audit's `PASS` means the explicit failure
receipt and source binding are internally consistent; it is not a simulation
acceptance. The mapping defect is fixed and tested, but R6 is immutable and the
single-campaign authorization does not permit a retry. The boundary capability
is therefore not qualified by a completed KT100 cycle campaign.

The user subsequently authorized a single separately preregistered recovery.
Offline recoverability, exact input bindings, and the recovery protocol are
recorded in `kt100_v2_evidence_recovery_r1.md` and
`results/2t-commercial-core-20261002/preregistration/KT100_V2_EVIDENCE_RECOVERY_R1.json`.
That distinct R1 campaign must not overwrite R6.

The campaign remains a synthetic engineering fixture. Its P4 dependency is
`CONDITIONAL_ON_P4`; it is not experimental validation, a calibrated
carburetor model, a Yamaha performance claim, or P9 evidence.

## Gates and completion states

- `AUD-11 = CASE B — CAPABILITY LIMITATION` is the human/scientific decision;
  the old forensic artifact remains historically unchanged.
- The contract preregistration must be present in a local commit before any V2
  code or campaign producer can run.
- Campaign requires all 12 frozen test groups above and strict OpenSpec PASS.
- After the single campaign, classify the observed result without parameter or
  boundary tuning. Close the AUD-11 queue item only after the contract,
  implementation, instrumentation, campaign artifact audit, regression checks,
  and documentation are complete.
- P3-R1 and its evidence remain historical and unchanged. Record its large
  volume-limit observation only as separate future scientific debt.
