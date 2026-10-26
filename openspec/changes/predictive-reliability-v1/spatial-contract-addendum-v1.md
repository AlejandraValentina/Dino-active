# Preimplementation clarification: passive-species independence

2026-10-26, before the first spatial implementation or decision calculation.
Acceptance thresholds and analytic test cases in spatial-contract-v1 remain
unchanged. Two corrections to the preliminary reconstruction design are needed:

1. Use separate common bounds for the gas primitive vector and the species
   fraction vector. Limiting passive fractions must not modify the gas flux.
   Otherwise changing a passive composition at fixed rho/u/p would change the
   reconstruction of gas dynamics despite the species-independent ideal EOS.
2. Select the most abundant species as the dependent slope (negative sum of the
   other three), instead of always making species 4 dependent. This preserves
   identically absent species: a fixed absent dependent species could acquire a
   spurious slope from independent nonlinear limiters, forcing every slope to
   zero. The dependent choice changes neither cell inventories nor the simplex.

All gas faces use the same shared HLLC flux. All species use that signed mass
flux and donor fractions. Cell means remain untouched; no positivity floor or
flow clipping. One-ULP inward bounds may prevent cancellation from constructing
a negative face fraction; this is a reconstruction roundoff guard, not a change
to acceptance tolerances, time integration, state validation or conserved means.

Primary numerical-method reference: piecewise-linear Riemann-state reconstruction,
[Clawpack](https://www.clawpack.org/riemann_book/html/Approximate_solvers.html).
Generalized minmod theta=1.5 is the stated limiter; it is not labelled the
theta=2 MC limiter. Sources support the method, not a predictive engine claim.
