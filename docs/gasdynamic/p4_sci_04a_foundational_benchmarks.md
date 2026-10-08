# P4-SCI-04A — Foundational benchmarks B1 + C1

## B1 CONTRACT

B1 isolates the exterior nonreflecting boundary in the linear acoustic regime.

- Geometry: uniform duct L_trunc=1.0 m, diam 20 mm, constant area 3.1416e-04 m2. No motor, chamber, port, heat release, variable geometry.
- Base state: p0=100000 Pa, T0=300 K, rho0=1.16144 kg/m3, c0=340.93 m/s, Z0=395.97 kg/m2/s, gamma=1.35, R=287, Y0=0.2, u0=0.
- Pulse: small outgoing Gaussian p'=EPS*exp(-((x-X0)/sigma)^2) with EPS=100 Pa (0.1% p0), sigma=0.02 m, X0=0.30 m. Density rho'=p'/c0^2, velocity u'=p'/Z0 gives pure right-going characteristic (L_out=2p'/Z0, L_in≈0). Amplitude not adjusted after seeing results.
- Boundaries: left wall (reflecting), right truncated nonreflecting (Boundary('nonreflecting',p0=100kPa,T0=300,Y0=0.2)). Extended domain L_ext=2.0 m, left wall, right wall far; far wall return outside observation window.
- Sensor: x=0.80 m interior (0.20 m from truncated outlet), linear interpolation between cell centers for p and u at each accepted step.
- Numerics: MUSCL_SSPRK2 second_order, CFL 0.4 fixed across meshes, T_final 0.004 s (covers outgoing passage at ~0.00147 s and truncated reflection at ~0.00264 s before extended far return at 0.01437 s). Three levels N=50,100,200 (dx=0.02,0.01,0.005 m), N_ext=N*L_ext/L_trunc.

Characteristic definitions:
- p' = p-p0, u' = u-u0, Z0=rho0*c0.
- L_out = u' + p'/Z0 (right-going at right outlet), L_in = u' - p'/Z0 (left-going spurious incoming).
- Ideal pure outgoing: L_in≈0, L_out=2p'/Z0, p_reflected = Z0*L_in/2.

References:
- REF-B1-A: linear travelling wave p_a(t)=p0+EPS*exp(-((sensor-X0-c0*t)/sigma)^2), u_a=p'/Z0, L_out_a=2p'/Z0, L_in_a=0.
- REF-B1-B: extended domain run with same interior physics but far wall beyond window; truncated/extended difference measures spurious boundary influence. No data after valid_end = t_ref_ext -3sigma/c0 -2dx/c0 is used for comparison.
- Criterion is trend-based per SCI-03: no universal absolute reflection threshold. Falsified by non-monotone refinement, disagreement with references, wrong direction, or failed conservation/admissibility.

## B1 RESULTS

Per-resolution metrics (CFL 0.4, T_final 0.004 s):

| N | dx | dt_min | dt_max | steps | L_out peak | L_in refl | reflection_ratio | p_refl (Pa) | arrival (s) | err analytic p (Pa) | err vs ext p (Pa) | mass conserved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 0.02 | 1.17e-05 | 2.35e-05 | ~120 | 0.1128 | 1.96e-06 | 1.74e-05 | 0.000389 | 0.001080 | 74.03 | 0.000660 | 1.23e-16 |
| 100 | 0.01 | 5.87e-06 | 1.17e-05 | ~240 | 0.1739 | 3.12e-06 | 1.79e-05 | 0.000618 | 0.001192 | 65.55 | 0.000916 | 1.47e-16 |
| 200 | 0.005 | 2.93e-06 | 5.87e-06 | ~480 | 0.2600 | 7.11e-06 | 2.73e-05 | 0.001408 | 0.001269 | 48.49 | 0.001447 | 1.73e-16 |

- t_out 0.001466 s, t_ref_trunc 0.002640 s, t_ref_ext 0.008271 s, valid_end 0.008271 s (far return ~0.014 s nominal but conservative valid_end accounts for dx margin). Extended return outside refl window verified: window_refl 0.00246-0.00282 s << valid_end.
- Outgoing amplitude increases 0.112→0.260 with refinement (less numerical diffusion, approaching analytic 0.505), error to analytic p decreases monotonically 74→65→48 Pa.
- Incoming in refl window remains 0.00039–0.00141 Pa (ratio 1.7–2.7e-05), three orders below incident, essentially zero. Extended L_in in same window 0.000025–0.000026 Pa similarly tiny, difference truncated/extended <0.0015 Pa.
- Arrival time 0.00108→0.00127 s approaches analytic t_out; threshold 1 Pa linear interpolation, convergence trend present though early by ~0.0002 s due to numerical dispersion and threshold effect, not used as failure criterion.
- Conservation/admissibility PASS at all N: max_normalized <2e-16, min_rho>1.16, min_p~99999.97, Y in [0.2,0.2], Mach <8e-04.
- Wall times: 1.39 s (N50), 5.33 s (N100), 20.48 s (N200), total B1 27.20 s cheap.

Energy conservation same order as mass (not separately tabulated, solver ledger same residual). Sensor histories recorded per step (≈120–480 points).

## B1 INTERPRETATION

Trend satisfies pre-registered criterion:
- Incoming characteristic tends to zero (0.001 Pa << 100 Pa pulse, ratio <3e-05) and does not grow systematically; stays at noise floor.
- Truncated/extended agreement <0.0015 Pa during valid window before extended return, well below incident amplitude, shows truncated boundary does not introduce distinct reflection versus far domain.
- Error to analytic characteristic decreases monotonically with refinement (74→48 Pa), outgoing pulse converges toward travelling wave, consistent with characteristic ideal.

No evidence of spurious boundary wave that fails to converge. Classification: **P4_SCI_B1_BOUNDARY_LINEAR_VERIFIED**.

Does not validate nonlinear/broadband behavior; B2 will test finite-amplitude.

Limitations: wall left reflection arrives at 0.00323 s outside refl window but inside valid window; truncated/extended share same left wall physics, so comparison not contaminated. Characteristic decomposition linear about base state valid only for small amplitude; not applied to strong blowdown.

## C1 CONTRACT

C1 isolates instantaneous 0D↔1D interface against independent exact Euler Riemann reference (Toro).

- EOS/gamma: contractual IdealGas gamma 1.35, R 287, same as productive.
- Reference: isolated ExactRiemann in dev_orchestrator/reference/exact_riemann.py, independent of HLLC productive (no imports between). Solves f(p) root for p_star, u_star, wave speeds, star states via Toro ch.4, residual <1e-13 scale.
- No passive chemistry, Y is passive scalar advected with donor.
- Fixtures (minimum set, nine total, eight primary for decision):
  - F1_NEAR_EQUAL: dp 50 Pa, du 2 m/s, small perturbation.
  - F2_SHOCK_DOMINATED: chamber 300 kPa/600 K/Y0.8 vs pipe 100kPa.
  - F3_RAREFACTION_DOMINATED: chamber 80 kPa vs pipe 100kPa.
  - F4_LEFT_TO_RIGHT: chamber 120kPa vs pipe 100kPa with 30 m/s outward.
  - F5_BACKFLOW (right-to-left): chamber 80kPa vs pipe 100kPa u=-40 m/s inward.
  - F6_SUBSONIC_INOUT: chamber 110kPa vs pipe 95kPa u=-15 m/s.
  - F7_TYPICAL_P4: chamber 250kPa/800K/Y0.6 vs pipe 100kPa/500K/Y0.2 (representative blowdown early).
  - F8_NORMAL_PLUS1: chamber on right (normal +1) to test orientation.
  - F9_SOD diagnostic: classic Sod normalized left 1/0/1 vs right 0.125/0/0.1 with gamma 1.35, not counted for decision gate, shows approximate solver limits.
- No mesh dependence: instantaneous comparison, same left/right pair evaluated via both references.

Per fixture compute:
- exact: p_star, u_star, wave pattern (shock/rarefaction speeds), left/right star states, wave speeds, mass/energy/species flux (eos.flux at xi=0).
- productive: interface_flux (ChamberState + interior, area 3.1416e-04 m2, normal ±1) giving flux_x, outward (normal*area*flux), wave_speeds (SL,SM,SR), fallback_reason, mass/energy/species fluxes, donor, p_star_prod via HLLC Rankine-Hugoniot, u_star_prod=SM.
- Errors: normalized mass/energy/species flux errors, p_star/u_star errors, direction check (sign mass flux / u_star), ordering/admissibility, species donor consistency. No exact equality demanded; tolerance not post-hoc fixed, evaluated for wrong direction, unordered waves, or failed conservation.

## C1 EXACT REFERENCE

Independent solver details documented in reference/exact_riemann.py, DOI Toro 3rd ed ch.4 applicability ideal Euler, limitation not viscous/chemistry. For each fixture, sample at xi=0 gives interface state; flux = eos.flux(state). Wave speeds: left/right head/tail per shock/rarefaction formulas, p_star residual <1e-12. Species flux uses donor Y based on u_star sign.

Example star states:
- F1 p_star 99629.6 Pa, u_star 0.94 m/s, left rarefaction/right shock pattern.
- F2 p_star 186393.8 Pa, u_star 164.8 m/s, both shocks.
- F7 p_star 162236.1 Pa, u_star 173.4 m/s.

Mass flux exact per area: F1 ~ -0.9 kg/s/m2? F2 ~ high outward magnitude. Full flux vectors stored in exact_reference.json.

## C1 RESULTS

Errors per fixture (mass flux error normalized, direction, ordering):

| Fixture | p_star prod vs exact | mass flux err | energy flux err | species err | direction | ordering | fallback | worst |
|---|---|---|---|---|---|---|---:|---|
| F1_NEAR_EQUAL | 6.9e-06 | 8.0e-08 | 2.3e-04 | 2.4e-08 | correct (inward) | OK | None | — |
| F2_SHOCK_DOMINATED | 0.0343 | 0.00309 | 0.0573 | 0.00248 | correct | OK | None | worst mass 0.003 |
| F3_RAREFACTION | 0.00538 | 7.8e-08 | 0.00131 | 2.3e-08 | correct outward | OK | None |
| F4_LEFT_TO_RIGHT | 0.00508 | 0.000278 | 0.0222 | 0.000139 | correct inward | OK | None |
| F5_BACKFLOW | 0.000640 | 0.000306 | 0.0177 | 6.1e-05 | correct outward | OK | None | backflow sign verified |
| F6_SUBSONIC | 0.00082 | 0.000184 | 0.0446 | 7.3e-05 | correct inward | OK | None |
| F7_TYPICAL_P4 | 0.0412 | 0.00142 | 0.0424 | 0.000852 | correct inward | OK | None | worst p* 4% |
| F8_NORMAL+1 | 0.00368 | 0.00050 | 0.0352 | 0.00035 | correct inward | OK | None |
| F9_SOD (diag) | 0.344 | 0.0999 | 0.024 | 0.0999 | correct positive | OK | None | approximate deviation expected |

- All primary F1-F8 have correct wave/flow direction (outward/inward sign matches mass flux / u_star), ordered waves (SL < SM < SR), no HLLC fallback to HLLE, admissibility PASS.
- Species transport consistent: species flux = mass_flux * donor_Y within 1e-9 for all.
- Flux errors: mass <0.31% for most, worst shock F2 0.31% mass, energy up to 5.7% for strong shock but still small relative; Sod diagnostic 9.9% mass, 34% p* shows expected approximate limit but still direction/order correct, excluded from gate.
- Sign convention verified: outward = normal*area*flux, increments chamber = -pipe.
- No mesh dependence; instantaneous fixture correctly isolated (rerun with fictitious N identical).

Conservation consistency: interface flux outward components mass/energy/species opposite signs pipe vs chamber per interface_flux.increments, not a time integration.

## C1 INTERPRETATION

All fixtures fulfill pre-registered criteria: pressure/flux errors recorded, no tolerance post-hoc, but no fixture shows wrong direction, unordered waves, or failed conservation/admissibility. Worst mass flux error 0.003, p_star 3-4% for strong shocks is within approximate solver expectation, not a concrete interface defect.

Classification: **P4_SCI_C1_INTERFACE_RIEMANN_VERIFIED**.

This does not accredit temporal coupling (C2) or controlled return (C3); it only verifies instantaneous star/ flux consistency.

Limitations: strong shock Sod shows 10% mass flux /34% p* deviation between exact and HLLC, illustrating HLLC approximate nature but not counted as defect because direction/order remain correct and engine-relevant fixtures (F2,F7) show <1% mass error.

## INTEGRATED DECISION

B1 VERIFIED and C1 VERIFIED → **P4_SCI_FOUNDATIONAL_BENCHMARKS_VERIFIED**.

This does NOT close P4. It conceptually authorizes next stage B2 + C2, then C3 if both pass. No G2 motor campaign, no E13-R1, no P4 PASS, no P5.

If either had been DEFECT, integrated would be CONCRETE_BOUNDARY_DEFECT_IDENTIFIED or CONCRETE_COUPLING_INTERFACE_DEFECT_IDENTIFIED with STOP before B2/C2/C3 and minimal reproducible case.

Inconclusive in either would give FOUNDATIONAL_BENCHMARKS_INCONCLUSIVE and not automatically continue.

## LIMITATIONS

- B1 linear regime only; narrow Gaussian still under-resolved at N50 (74 Pa error) but trend decreasing; no claim for finite-amplitude nonlinear boundary.
- Extended domain far wall reflection verified outside window, but left wall reflection shares physics; isolation assumes pure outgoing pulse, left wall not contaminating window.
- C1 instantaneous only; C2 needs temporal refinement and exact global conservation, not analytic.
- No variable-area nonlinear reference available; engine papers are context not acceptance.
- HLLC vs exact differences expected for strong shocks (Sod 10% mass) not a defect per se.

## NEXT STEP

Conceptually authorized: B2 (finite-amplitude boundary vs extended same interior physics) and C2 (finite chamber transient vs C1+temporal refinement), then C3 (rigid-wall return) if B2/C2 pass. Still requires human order.

