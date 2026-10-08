# Dynamic reed / gas coupling V1 — preregistration

**Status:** preregistered, not yet implemented or numerically evaluated.  
**Configuration class:** `SYNTHETIC_ASSUMPTION`; not a KT100 geometry or a
measured reed.  2026-10-06.

## Scope and preserved behavior

This capability couples one moving petal between two well-mixed ideal-gas
control volumes. It is a bounded component foundation for later intake-network
binding, not a complete-engine campaign. `DYNAMIC_REED_V1`, static reed flow,
P5-C, P6 and P7 remain unchanged. No engine-specific reed dimensions or
performance claims are inferred.

The literature treats reed motion and intake gas flow as coupled phenomena and
uses reduced reed models in engine simulations (Cunningham, Kee and Kenny,
1999, [Reed valve modelling in a computational fluid dynamics simulation of
the two-stroke engine](https://journals.sagepub.com/doi/10.1243/0954407991526658);
Turner et al., 2000, [Development of a Reed Valve Model for Engine Simulations
for Two-Stroke Engines](https://trid.trb.org/View/1799668)). Conservative
moving-interface schemes require fluid pressure work and solid work to use the
same interface motion; the general numerical issue is described by
[Baumann et al., 2015](https://epubs.siam.org/doi/10.1137/140962930). These
sources motivate coupling and conservation, but do not prescribe MotorSim's
synthetic geometry or numerical contract below.

## Versioned synthetic geometry

`DYNAMIC_REED_HINGED_FLAP_GEOMETRY_V1` defines a rectangular flap of width
`W`, length `L`, and generalized coordinate `x` equal to free-edge lift. Its
synthetic deflection shape is linear along the length:

`y(s) = x s/L`, `0 <= s <= L`.

Consequently the open curtain area and swept-volume coefficient are fixed by
geometry:

`A_flow(x) = Cd W x`,  
`A_sweep = dV_left/dx = W integral_0^L (s/L) ds = W L/2`,  
`V_left(x) = V_left,0 + A_sweep x`,  
`V_right(x) = V_right,0 - A_sweep x`.

The face normal is left-to-right and positive lift increases the left control
volume. The right volume must remain positive throughout `[0, x_stop]`. The
pressure force coefficient is not independent:
`A_pressure = A_sweep`, so virtual work gives
`(p_left-p_right) A_sweep dx = (p_left-p_right) dV_left`.
The flow curtain width and the swept-volume coefficient remain distinct
quantities. `effective_width * lift` is never used as a swept volume.

The geometry object records id, version, `SYNTHETIC_ASSUMPTION` provenance,
`W`, `L`, closed reference volumes, and stop lift. It validates
`pressure_area_m2 = W L/2` against the existing petal record and its
`effective_width_m = W`; mismatches are configuration errors. This V1 does not
represent nonlinear beam modes, leakage, distributed petal fluid loading,
thermal coupling, or a real-engine fit.

## Coupled equations and integration contract

Let `mdot` be the signed mass flow left-to-right from the existing reed
restriction relation, `h0_donor` its donor stagnation enthalpy, `x` lift,
`v=dx/dt`, `m_r` the effective petal mass, `k` stiffness, and `c` damping.
Positive flow uses left gas composition; negative flow uses right gas
composition. The four species are transferred using the same signed `mdot`
and actual donor fractions, not the legacy fresh scalar.

`dM_left/dt = -mdot`, `dM_right/dt = +mdot`.  
`dE_left/dt = -mdot h0_donor - p_left A_sweep v`.  
`dE_right/dt = +mdot h0_donor + p_right A_sweep v`.  
`dx/dt = v`,  
`m_r dv/dt = (p_left-p_right) A_sweep - c v - k x`.

The reed mechanical energy is
`E_reed = 0.5 m_r v^2 + 0.5 k x^2`.
Thus gas plus reed energy changes only by `-c v^2`; the global ledger adds the
same nonnegative `reed_dissipation = integral(c v^2 dt)` as an explicit
outgoing conversion to the synthetic reed/ambient thermal sink. It is not
silently lost or added to gas. The mass flux's enthalpy is applied with exactly
opposite signs. There is no heat release, chemistry, or species source.

The state RHS is evaluated at both SSPRK2 stages from that stage's gas
pressures, petal state, lift-dependent curtain area and donor composition.
Gas, four species, petal coordinates, spring energy accounting and cumulative
dissipation are advanced by the same SSPRK2 update. The implementation must be
transactional on failed admissibility. V1's initial coupled fixture excludes
stop contact; a trial stage outside the validated lift/volume domain is
rejected without state mutation and requires caller timestep reduction. No
clipping, post-step petal advance or operator splitting is permitted. A future
contact-enabled coupling requires a separate versioned event/restitution
contract.

## Preregistered verification

Before integration or a fixture run, implement tests for:

1. geometry identity, units, derived `W L/2`, matching pressure-force area,
   positive swept volumes over the full lift interval, and mismatch rejection;
2. exact closed-lift zero flow, curtain-area proportionality, and area bounded
   by the declared flap geometry;
3. equal-pressure fixed point and forward/reverse flow with the correct four-
   species donor;
4. pressure-force virtual work equal and opposite to the two gas volume-work
   terms at every RHS stage;
5. stage-coherent SSPRK2 gas/reed/species advancement, with no independent
   post-step state change;
6. global mass and each species conservation, species sum equals gas mass,
   and energy closure after adding reed stored energy and dissipated-energy
   ledger;
7. admissibility failure leaves all gas, species, reed, and ledger values
   unchanged; out-of-domain stop/volume states reject rather than clip;
8. deterministic replay/checkpoint including geometry identity, petal state,
   and cumulative dissipation; configuration mismatch rejects restore;
9. regression that the existing standalone `DYNAMIC_REED_V1` and static
   integrated reed tests remain unchanged.

Only after this preregistration is committed may the bounded synthetic fixture
tests be implemented and run. No full engine campaign, Fixture A/C rerun,
KT100 run, P4-P8 campaign or performance tuning is included here.

## Scientific dependency and limits

The synthetic linear flap shape is an explicit geometry assumption, not a
derived property of an undocumented production petal. If a future real reed
configuration has measured shape, pressure area, or swept displacement, it
must use a separately versioned documented geometry. Coupling into the full
1D integrated engine remains subsequent work and must bind explicit adjacent
cells/volumes before it can claim end-to-end dynamic-reed verification.
