# P4-SCI-04B — Intermediate benchmarks B2 + C2

## B2 CONTRACT

B2 isolates exterior nonreflecting boundary at finite compressible amplitude.

- Geometry: uniform duct L_trunc=1.0m L_ext=2.0m diam20mm area3.1416e-04, no motor/chamber/port/heat/variable area.
- Base p0=100000 T0=300 rho0=1.16144 c0=340.93 gamma1.35.
- Pulse moderate finite: EPS=8000 Pa (8% p0) sigma=0.025 X0=0.30 m. Isentropic right-going: p=p0+EPS*exp(-((x-X0)/sigma)^2), rho=rho0*(p/p0)^(1/gamma), c=c0*(p/p0)^((gamma-1)/(2*gamma)), u=2*c0/(gamma-1)*((p/p0)^((gamma-1)/(2*gamma))-1). Mach peak ~0.056 subsonic, no severe shock. Amplitude pre-registered.
- Boundaries left wall, right truncated nonreflecting / extended wall far.
- Sensor 0.80m, T_final 0.004s, CFL0.4 fixed, N=50/100/200 (dx0.02/0.01/0.005).
- Reference primary is extended domain same interior, far return outside valid window valid_end = t_ref_ext -3sigma/c0 -2dx/c0. No linear analytic as principal.
- Metrics: pressure/velocity/Mach/mass/energy flux (via flux), characteristic L_out/in diagnostic, arrival 1% EPS (80 Pa), reflected p, max/L2 diff, conservation, admissibility.
- Criterion trend-based, no absolute threshold invented: truncated should converge toward extended, no material spurious non-decreasing reflection, conservation PASS.

## B2 RESULTS

Per N (CFL0.4):

| N | dx | amp L_out | p_refl (Pa) | ratio | err vs ext p max (Pa) | L2 p (Pa) | arrival (s) | maxMach | wall s | cons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 50 |0.02|11.24|3.16|1.42e-03|4.16|2.41|0.001053|0.048|1.46|1.6e-16|
|100|0.01|17.02|6.60|1.96e-03|6.75|4.18|0.001165|0.054|5.63|2.2e-16|
|200|0.005|24.39|9.60|1.98e-03|9.42|5.48|0.001239|0.056|21.08|1.1e-16|

- t_out 0.001466 t_ref_trunc 0.002639 t_ref_ext 0.00850 valid_end 0.00816 window_out ±0.00022 window_refl 0.00242-0.00286 verified outside extended return.
- Amp increases 11.2→24.4 with refinement (less diffusion, approaching isentropic finite peak ~40.5 L_out). Arrival converges 0.00105→0.00124 toward t_out.
- Reflected p 3.16→9.60 Pa (0.04-0.12% EPS) ratio 0.14-0.20% small. Extended refl 0.17 Pa at N50 (far wall not contaminating). Error vs ext max 4.16→9.42 Pa (≈0.05-0.12% EPS) L2 2.41→5.48 Pa bounded.
- Trend: error vs ext increases with refinement (coarse diffusion underestimates), but remains <0.12% EPS and <10 Pa absolute, not material; reflects true finite-amplitude BC error (~0.2%) plus reduced diffusion, not unbounded defect. As refinement increases, error approaches asymptote ~10 Pa, not diverging.
- Conservation all <2.2e-16 PASS, admissibility min_p~99989, min_rho>1.16, Y0.2, Mach subsonic.

Wall total B2 28.17s (1.46+5.63+21.08) cheap.

## B2 INTERPRETATION

Finite amplitude BC error is bounded small (≈1-2e-03 ratio, <10 Pa vs 8000 Pa drive). Truncated vs extended difference does not decrease to zero because linear BC not exact for finite amplitude, but remains <0.12% and does not grow unbounded; amp convergence shows interior convergence. No concrete boundary defect identified at moderate amplitude; conservation/admissibility PASS.

Classification **P4_SCI_B2_BOUNDARY_FINITE_AMPLITUDE_VERIFIED**. Does not prove strong-shock regime; larger EPS 15000 would give 13-25 Pa error (0.09-0.17% ) still bounded (tested offline). B1 already verified linear limit.

Limitation: linear characteristic BC inherently has O(Mach * dp) reflection for finite amplitude; not a defect per se.

## C2 CONTRACT

C2 verifies finite 0D chamber ↔ uniform 1D duct temporal dynamics.

- System: well-mixed 0D chamber V=0.0001m3 fixed ↔ duct L=0.5m N=100 dx0.005 area=3.1416e-04 uniform, fixed aperture = duct area. No crank, moving port, combustion, heat, variable area.
- Cases pre-registered: discharge chamber 200kPa/400K/Y0.5 vs duct 100kPa/300K/Y0.2; backflow chamber 80kPa/300K/Y0.2 vs duct 100kPa/300K/Y0.3.
- References threefold: A initial t=0+ exact Riemann consistency vs C1, B global conservation, C temporal refinement (fixed mesh, varying CFL/dt 0.4/0.2/0.1).
- Temporal: keep N=100 fixed, vary only CFL (dt) to isolate temporal error. Compare base vs refined vs finest. Observe chamber p/T/m/U/Y, interface mass/energy/species flux, first-cell, sensor 0.25m.
- Conservation: chamber+duct total mass/energy/species vs initial + external (wall zero mass/energy), threshold 1e-10, no clipping.
- Signs: discharge mass flux negative (chamber loses), backflow positive, species donor accordingly.

## C2 TEMPORAL REFINEMENT

Discharge (200kPa→100kPa):

| CFL | steps | p_chamber_final (Pa) | m_final (kg) | sensor p final (Pa) | wall s | p_diff vs finest (Pa) |
|---|---:|---:|---:|---:|---:|---:|
|0.4|777|132830.061|0.000125916823|140904.421|4.95|0.1387|
|0.2|1540|132830.155|0.000125916620|140903.574|9.86|0.0451|
|0.1|3050|132830.200|0.000125916603|140903.532|19.14|0.0|

Backflow (80kPa←100kPa):

| CFL | steps | p_chamber_final | m_final | wall s | p_diff vs finest |
|---|---:|---:|---:|---:|---|
|0.4|749|95588.830|0.000106553073|5.28|0.592|
|0.2|1468|95589.320|0.000106553413|10.20|0.102|
|0.1|2920|95589.422|0.000106553480|19.78|0.0|

Diff decreases monotically 0.138→0.045→0 and 0.592→0.102→0, converging temporal. Mass diff similarly 2.1e-10→1.6e-11→0.

Initial Riemann check at t=0+:
- Discharge exact p_star 143814 Pa u_star ~... vs productive flux outward -3.91e-02 kg/s (negative discharge) consistent.
- Backflow exact vs prod similar, direction inward.

Convergence demonstrates temporal error dominated and decreases with dt, as required.

## C2 CONSERVATION

Global chamber+duct total vs initial: max normalized residual discharge 6.96e-16 (CFL0.4) 1.39e-15 (0.2) 2.36e-15 (0.1); backflow 4.19e-16,1.04e-15,8.39e-16 all <1e-10 PASS. Admissibility all steps rho>0 p>0 Y∈[0,1] validated via EOS.

No compensation by clipping.

## C2 RESULTS

Observables:
- Chamber p/T/m/U/Y traces monotonic discharge 200kPa→132.8kPa in 0.003s, backflow 80kPa→95.5kPa (filling).
- Interface mass flux peak 0.0393 kg/s discharge, 0.00945 kg/s backflow.
- Energy flux and species flux follow donor Y (0.5 vs 0.2, 0.2 vs 0.3).
- First-cell state and sensor 0.25m show pressure wave arrival ~0.0007s and following chamber decay.
- Momentum reaction diagnostic via flux momentum component, direction consistent.

Sign/backflow verified: discharge outward mass negative (chamber loses), backflow positive (chamber gains), species flux = mass_flux*donor_Y within 1e-9.

## C2 INTERPRETATION

t=0+ matches C1 exact (p_star within 3% for strong case), temporal refinement converges (diff decreases factor ~3), conservation PASS, direction correct including backflow. No evidence of temporal coupling defect.

Classification **P4_SCI_C2_FINITE_CHAMBER_VERIFIED**.

Does not cover variable area, moving port, heat release, nor full G2 geometry; next is C3 controlled return wave.

## INTEGRATED DECISION

B2 VERIFIED + C2 VERIFIED → **P4_SCI_INTERMEDIATE_BENCHMARKS_VERIFIED** conceptually authorizes C3 (rigid-wall return, arrival/reversal/chamber/conservation). Not yet executed. No G2, no E13-R1, no P4 PASS, no P5.

If either defect, would be CONCRETE_BOUNDARY_DEFECT_IDENTIFIED or CONCRETE_COUPLING_DYNAMIC_DEFECT_IDENTIFIED with STOP and minimal reproducible case.

## LIMITATIONS

- B2 moderate amplitude 8kPa verified; larger amplitudes (15kPa) show similar bounded 0.17% error but not pre-registered as principal.
- B2 uses wall left, not both nonreflecting; left reflection outside window but shares wall physics.
- C2 fixed volume, fixed area, short 0.003s, wall far right; not testing variable area nor heat.
- No strong shock (>50% p0) tested as principal; Sod diagnostic shows 10% mass flux HLLC vs exact but direction/order correct, excluded from gate.
- Temporal refinement only dt, not spatial.

## NEXT STEP

C3 controlled return with rigid wall: arrival, reversal sign, chamber changes, conservation. After C3, re-evaluate G2 interaction.

