# DINO_PREDICTIVE_RELIABILITY_V1

Owner authorization: 2026-10-26, progressive physical correction and verification
in the order proposed by the engineering audit. This supersedes V3 as current
work; V3 remains frozen and its results and queue history remain intact.

## Baselines and evidence

- Functional packaged baseline: CRV1 rc7, source fc27542155840cdadbcc2b591ae5cd8e99031899,
  ZIP SHA-256 2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a.
- Development reference before this objective: e3be7e2. No modification of its
  results or checkpoints; new model capabilities have explicit new identities.
- Existing P0-P9 contracts, thresholds and evidence remain frozen. Synthetic
  engineering verification is never relabelled experimental validation.
- Preserve unrelated dirty files and the owner's untracked Opus audit.
- Existing eight BLOCKED_LOCAL items reexamined: historical RPM and CRV1 work
  remain deferred; X30 still lacks measured crankcase geometry; interrupted SPV1
  recovery remains unrelated. No historical item is taken or changed here.

## Ordered work and gates

1. **Restriction and connection.** Implement an isolated, versioned ideal-gas
   quasi-steady restriction reference. Distinguish geometric throat, discharge
   coefficient, effective throat and duct section. Verify dimensions, equilibrium,
   reverse flow, forward/reverse Cd, choking continuity, donor total enthalpy and
   species. Then construct the complete 0D-1D connection, including characteristic
   compatibility, throat/duct state, pressure force and energy. A mass-only nozzle
   replacement is not an accepted connection. Preserve the old model as reference.
2. **Spatial accuracy.** Only after the connection gate, version an improved
   reconstruction; retain HLLC/HLLE, SSPRK2 and positivity checks. Verify uniform
   equilibrium, smooth-wave convergence, shocks, reflection, species and mass/
   energy. Compare actual errors, not only number of cells or nominal order.
3. **Integrated diagnostics.** Preregister bounded engine cases and budgets before
   calculation. Check conservation, independent initialization, admissibility,
   work including crankcase pumping, species, restart and mesh/time sensitivity.
   No full RPM campaign by default; do not require a particular power increase.
4. **Identify closures.** Assess scavenging, reed dynamics, heat, gas properties,
   combustion and mechanical losses against suitable subsystem data. Fix the
   demonstrated moving-cell heat denominator defect before using that combination.
   Keep simple models that meet identified-domain accuracy; avoid simultaneous
   parameter changes or tuning to a reserved power datum.
5. **Predictive validation.** Use a complete measured motor and preregister a blind
   comparison. If essential inputs are missing, preserve the missing-input blocker;
   do not synthesize measurements or claim EngMod2T-equivalent accuracy.

Each gate requires numerical evidence and a documented review before dependent
work. Major model changes need reference receipts with hashes and conservation.
No product/release claim without the corresponding independent review.

## Initial restriction acceptance (fixed before implementation)

- Ideal calorically-perfect gas: gamma=1.2, 1.35, 1.4; R=287 J/kg/K.
- p0=1e5, 2e5, 5e5 Pa; T0=300, 900 K; geometric areas 1e-6, 1e-4 m2;
  Cd=0, 0.5, 0.8, 1. Equilibrium and both flow directions are explicit tests.
- Compare to independently computed isentropic Mach-parametrized mass flux at
  M=0, 0.001, 0.01, 0.1, 0.3, 0.8, 1 (relative error <=1e-10 for nonzero flow,
  exact zero at equilibrium). Choked flow must not depend on lower backpressure.
- Area/Cd linearity, total-pressure linearity and T0^(-1/2) scaling: relative
  tolerance 1e-12. Temperature and total enthalpy must use the actual donor.
- No pressure-ratio deadband. Reject nonfinite/nonpositive states and invalid Cd;
  no clipping of inadmissible physical inputs. Use cancellation-safe formula near
  equilibrium and test its small-difference limit.
- The reference restriction alone does not authorize replacing integrated fluxes.
  Its momentum cannot be inferred as duct momentum from throat mass flux alone.

## Operational limits

Respect storage preflight before generating run artifacts. First subsystem tests
<=60 s each, diagnostic processes <=240 s, estimated artifacts <=0.1 GiB. Logs
and compact receipts are durable; do not duplicate historical result trees.
No push, cleanup, automatic continuation of V3, Desktop rebuild or X30 assumptions.
On a fundamental inconsistency stop that branch and present its reproducer and
strategy consequences before proceeding with dependent implementation.

## Sources

- NASA Glenn, mass flow/choking and total-state relations:
  https://www.grc.nasa.gov/www/k-12/BGP/mflchk.html
- Thompson & Yoon (2020), Gas Dynamics Modeling, DOI 10.1155/2020/6787408:
  distinguishes duct compatibility, throat and receiving volume states.
- Blair et al. (1995), DOI 10.4271/952138: discharge-coefficient definitions and
  duct-end geometry matter; a coefficient must be tied to its reference model.

These support the formulation; they do not validate a Dino motor or supply its Cd.
