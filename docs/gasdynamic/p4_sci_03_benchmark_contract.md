# P4-SCI-03 — reference qualification and benchmark contract

## LITERATURE / APPLICABILITY

Thompson (1987), Poinsot–Lele (1992), and Rudy–Strikwerda (1980) provide
characteristic/nonreflecting boundary formulations and discuss their
subsonic assumptions. Toro provides the exact Euler Riemann construction used
as an independent interface reference. Chung–Chen–Lu (SAE 950985) and
Zhang–Assanis (2003) motivate engine manifold/cylinder coupling, but are not
exact solutions for MotorSim fixtures. DOI metadata and applicability limits
are recorded in `reference_matrix.json`.

## BOUNDARY REFERENCE

For a uniform duct in the linear regime, outgoing and incoming acoustic
characteristics are measured at an interior sensor. The principal observable is
`R_in = |L_in|/max(|L_out|, epsilon)`, with `L_in` and `L_out` obtained from the
linearized Euler characteristic variables about the uniform base state. REF-B1-A
is the characteristic travelling-wave solution. REF-B1-B is an extended
domain run whose return wave is outside the measurement window. Acceptance is
trend-based: error to REF-B1-A decreases under refinement, the truncated result
approaches REF-B1-B, and `L_in` tends toward zero. No universal absolute
reflection threshold is invented.

## COUPLING REFERENCE

C1 compares the production interface flux against an independent exact ideal
gas Euler Riemann solver (Toro), including mass, momentum/interface pressure,
energy, passive species, wave ordering and flow direction. C2 is numerical
verification against a much smaller time step with exact global conservation;
it is not an analytic solution. C3 uses a rigid reflecting termination and
checks return arrival, reversal sign, chamber changes and conservation. C3
does not use the exterior nonreflecting boundary.

## BENCHMARK CONTRACTS

| Case | Isolates | Reference | Pre-registered criterion |
|---|---|---|---|
| B1 | linear nonreflecting boundary | characteristic + extended domain | refinement trend and incoming characteristic → 0 |
| B2 | finite-amplitude boundary | extended domain, same interior physics | truncated/extended agreement before external return |
| C1 | instantaneous interface | independent exact Riemann | pressure/flux errors and wave ordering recorded; tolerance requires prior fixture justification |
| C2 | finite chamber transient | C1 + temporal refinement | conservation and temporal convergence |
| C3 | controlled return coupling | rigid-wall reflection | arrival, reversal, chamber and conservation consistency |

## PRE-REGISTERED CRITERIA

No post-hoc absolute threshold is defined where literature does not supply one.
Each case is falsified by non-monotone refinement, disagreement with its
independent reference, wrong flow direction, or failed conservation/admissibility.

## LIMITATIONS

The repository has no ready exact variable-area nonlinear reference and no
published fixture matching the complete MotorSim coupling. C1–C3 therefore
remain design contracts until implemented in isolated test code. Engine papers
are context, not acceptance evidence.

## NEXT STEP

Implement the independent reference Riemann utility and B1/C1 fixtures in test
orchestrator scope only. Do not change product physics or the P4 contract.
