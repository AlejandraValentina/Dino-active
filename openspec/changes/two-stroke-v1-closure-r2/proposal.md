# Superseding R2 gate for the synthetic 2T closure

## Status and legitimacy

This change is written after observing the R2 campaigns and therefore does not
claim that its requirements governed the original v1.0 campaign. The original
gate remains historical and terminal:

`MOTORSIM_2T_V1_CLOSURE_V1_0 = FAIL_TERMINAL`

R1 did not converge within the original exact 20-cycle horizon. Offline
`PeriodicDetectorV2` evaluation gives P1 streak 0, P2 branches A=0/B=0, and
`detected_period=None` for both primes.

The R2 gate is legitimate only as a separately versioned superseding evaluation
of the owner-authorized decision recorded before R2. Its pre-execution basis is:

- owner decision `OWNER_DECISION_C14_C15_R2` (`OPTION_B_FIX_RUNNER_SINGLE_R2`);
- R2 preregistration commit `9b73a1e` and its SHA-256
  `37e0e6855d7acac7164ddb006d51bf505e10453e417baa78fde351632dd9ab98`;
- fixed horizon rule `ceil(4 * exhaust_residence_cycles) + required_streak`,
  with required streak 3, giving A′ 111 and B′ 47;
- frozen solver, physics, fixtures, mesh, fuel, combustion, thermal,
  mechanical losses, RPMs, detector, thresholds, and convergence streak.

The R2 preregistration was operationally amended after B′ completed and the
first A′ attempt stopped: commit `dddf243`, preregistration SHA
`7a712f7811ab883a753075b7531f4f8c6ddd404605ef4e68c7767ed13d84c3ee`.
That amendment changed only restart/trace operation and producer binding:
restart A′/B′ 56/24 → 10/10. It did not change the horizon, physical rule,
solver, physics, fixtures, mesh, fuel, combustion, thermal, losses, RPM,
detector, thresholds, or streak. The two A′ attempts are preserved; their 56
common cycles are bit-identical in trajectories and observables.

## Result

The computational R2 evidence is retained as:

- A′ `PERIOD_1 @ cycle 73/111`;
- B′ `PERIOD_1 @ cycle 38/47`;
- real `PeriodicDetectorV2`, with existing SHA-bound result artifacts.

This change is currently `REVIEW`, not `PASS`. Its B1–B3 repair is a
`SELF_REVIEW`; a new external review is required before any R2 PASS or
development-freeze candidate is declared.

