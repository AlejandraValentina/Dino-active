# AUD-11 — reservoir boundary forensic result

Date: 2026-10-05. Scope: the frozen `Boundary('reservoir')` branch and the
Commercial Core audit finding B4. This is a diagnostic and decision package;
it does not modify the gasdynamic solver, boundary equations, KT100 evidence,
or P4–P9.

## Protocol and roles

The protocol was performed sequentially because no separate reviewer was
assigned. The role labels below describe distinct passes by the same author;
they are **self-review**, not independent review.

1. **Forensics:** reproduce the known rejected state through both the direct
   boundary and the existing P3 preflight test; inspect the exact V1 equation
   and preserve the five KT100 R5 receipts read-only.
2. **Domain analysis:** derive the admissible subsonic-inflow interval from the
   implemented isentropic reservoir model and check monotonicity and endpoints.
3. **Skeptic pass:** check normal orientation, use of static versus stagnation
   quantities, and whether a full-state Riemann boundary can return a flux for
   the same data. No evidence supports changing the recorded failure into a
   solver defect.
4. **Discriminating tests:** `tests/test_reservoir_forensic_diagnostic.py`
   checks the bounded branch, the orientation-symmetric rejection, and the
   material difference between V1 rejection and a full-exterior-state HLLC
   flux. The existing `test_frozen_boundary_gap_is_not_hidden` remains intact.
5. **Synthesis:** apply A/B/C under the repository protocol. No candidate is
   selected by whichever one returns a convenient result.

## V1 branch derivation and reproduction

For a reservoir at rest with stagnation enthalpy `h0 = cp*T0`, the current
subsonic inflow branch solves

`J+(w) = w + 2*a(w)/(gamma - 1)`,

where `w` is velocity along the outward normal,
`a(w) = sqrt((gamma - 1)*(h0 - w^2/2))`, and
`-a_sonic <= w <= 0`. Its derivative is
`dJ+/dw = 1 - w/a > 0`; therefore its image is exactly the bounded interval
`[J_choke, J_rest]`, where
`J_choke = -a_sonic + 2*a_sonic/(gamma - 1)` and
`J_rest = 2*sqrt((gamma - 1)*h0)/(gamma - 1)`.

For the existing `R=287`, `gamma=1.35`, `p0=100000 Pa`, `T0=300 K`
preflight, the rejected interior is
`(rho=100000/(287*301), u=-0.001 m/s, p=100000 Pa, Y=0.2)` at normal `+1`.
Its `J+ = 1951.42924471796`, while `J_rest = 1948.1859694157974`; the excess
is `3.2432753021626`. Thus this state has no root in V1's declared subsonic
inflow domain. Mirroring velocity and normal preserves the rejection, ruling
out the simple orientation-sign error.

The diagnostic compares a different, conventional full exterior primitive
state used as an HLLC ghost state. For the same interior, V1 raises
`No consistent reservoir inflow branch`; the full-state HLLC evaluation
returns finite flux with mass flux `-5.797538393432691e-4 kg/(m² s)`. This is
evidence that the choice of boundary contract has a material consequence, not
evidence that the full-state result is the correct MotorSim answer.

## Hypotheses, evidence, and contradictions

- **H1 — ordinary implementation bug in V1:** not supported for this case.
  The exact V1 equation has no admissible root; monotonicity, endpoints, and
  mirrored orientation are tested. The existing rejection test still passes.
- **H2 — V1 is a valid, bounded stagnation-reservoir capability:** supported.
  It requests an isentropic subsonic inflow branch and rejects states outside
  that branch. This is a local capability limit for that operating-state
  pairing, not evidence of a KT100 physical failure.
- **H3 — another boundary model should be selected for the target physical
  interface:** unresolved by repository evidence. Plausible contracts include
  (a) preserve V1 and reject/require a different consistent operating state;
  (b) prescribe a full exterior primitive state and solve an interface Riemann
  problem; or (c) prescribe a mass-flow/nozzle relation with its own geometry
  and choking contract. They impose different information and can change mass,
  energy, species donor, and reflection. The engine configuration and frozen
  fixtures do not specify which physical apparatus the boundary represents.

NASA's Cart3D documentation describes stagnation-pressure/temperature subsonic
inflow and separately documents a mass-flow/total-temperature option; its
boundary-condition paper explains that supersonic inflow requires a different
full-state treatment and that different boundary conditions produce different
flow contours. NASA's choking reference also makes the flow limit depend on
total conditions, area, gas properties, and Mach number. These references show
that multiple established formulations exist. **Inference:** they do not
determine which apparatus or control mode MotorSim intends to represent, so
they cannot select a V2 contract here.

References:

- NASA Cart3D boundary tutorial: <https://www.nas.nasa.gov/publications/software/docs/cart3d/pages/howto/samples_power/README.html>
- NASA Ames Cart3D boundary-condition paper: <https://www.nas.nasa.gov/publications/software/docs/cart3d/pages/publications/AIAA_2018-0334.pdf>
- NASA Glenn mass-flow choking: <https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html>

## Classification and decision package

**Outcome: C — `RESERVOIR_BOUNDARY_V2_SCIENTIFIC_DECISION_REQUIRED`.** The
failure is explained by V1's bounded characteristic branch, but at least two
physically legitimate boundary contracts remain and produce materially
different flow. Existing contracts, equations, fixtures, and tests do not
identify the intended external apparatus. The decision cannot be made by
numerical convenience without inventing physical boundary conditions.

Decision options if/when this boundary is required:

1. **Retain V1 semantics and reject the state.** Require an operating point
   compatible with the isentropic stagnation reservoir. This preserves the
   current contract and avoids defining new external hardware behavior.
2. **Add a separately versioned full-state Riemann boundary.** Require the
   user/configuration to supply the complete exterior primitive state and
   define supersonic, reversal, composition donor, and admissibility behavior.
   It yields a different interface flux and can reflect waves differently.
3. **Add a separately versioned flow/nozzle-controlled boundary.** Require
   the controlling mass-flow/total-state data and effective area/discharge
   model, plus explicit choked and reversal behavior. It represents a different
   physical setup and changes the flow constraint.

No option is implemented or recommended as the target MotorSim model because
the configuration carries no evidence identifying that setup. No KT100
campaign, solver modification, P4 change, or threshold change was made.

Verification: `python -m pytest tests/test_reservoir_forensic_diagnostic.py
tests/test_coupling_preflight.py -q` — 7 passed. This is focused automated
diagnostic evidence; it is not an independent review or physical validation.
