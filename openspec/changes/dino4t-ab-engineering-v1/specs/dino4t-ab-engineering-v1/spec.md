# Dino 4T Desktop A/B engineering workflow v1

## Objective

Allow an engineer to configure two distinct 4T designs in one Desktop project,
run them through `DINO4T_API_V1`, and compare/export only when the existing
scientific and numerical compatibility conditions are met.

## Requirements

1. Keep 2T and 4T model APIs, result contracts, and scientific evidence
   independent.
2. A/B endpoints must be distinct runs with individually verified result,
   configuration, and project references. Design changes must be explicit and
   confined to identified physical configuration fields.
3. A performance comparison is available only for completed,
   `PERIODIC_CONVERGED` results with exact RPM, identical selected models,
   numerical settings, operating conditions, code commit/clean state, and
   thermochemistry source hashes. Incompatible inputs display reasons and no
   performance delta.
4. Show A, B, absolute delta (B − A), and relative delta to A only when A is
   finite and non-zero. Preserve full numeric precision in exported JSON/CSV.
5. Comparison exports retain both run IDs, result/config hashes, exact resolved
   configurations, model identifiers, periodicity tolerances, provenance, code
   identity, and explicit validation/predictivity limitations. Do not
   interpolate, synthesize, or label calculated differences as experimentally
   proven improvements.
6. Execution runs outside the GUI thread, has a bounded wall/cycle budget,
   reports progress and failures, and preserves available complete results.
   Any cancellation/recovery capability must stop at safe completed-cycle
   boundaries and must not change solver equations or numerical acceptance
   criteria.
7. Regression checks cover project/variant persistence, strict comparison
   eligibility, differences/exports, non-periodic and failed results, and
   compatibility with existing 2T projects/results.
8. Packaged Windows verification exercises the A/B Desktop workflow and
   consumes actual results created by the 4T API. Synthetic provenance remains
   explicit; periodicity alone is not experimental validation.

## Bounded engineering pair for integration acceptance

- Source config: `configs/dino4t/example_single_cylinder_500cc.json` at the
  recorded source commit. It is labelled `SYNTHETIC_ASSUMPTION` for engine
  geometry/valves/ducts and is a software/model sensitivity fixture, not a
  representation of a measured engine.
- A: the unchanged base configuration.
- B: a duplicate design with intake-valve harmonic `max_lift_mm` changed from
  10.0 mm to 8.0 mm. All other physical and numerical values remain identical.
  The parameter is selected because the existing S4 local sensitivity record
  identifies intake maximum lift as model-active; this is not a prediction of
  the finite-difference or full-run A/B difference. The actual difference is
  determined only from the two runs below.
- Operating point: 6000 RPM, equivalence ratio 1.0.
- Models/numerics: explicitly recorded from the source config; `dx=10 mm`,
  `CFL=0.8`, `max_dtheta=0.5 deg`, second order, `minmod`, restriction `V2`,
  two-zone-equilibrium combustion, and the existing periodicity settings.
- Maximum: 20 cycles per design and 300 seconds solver wall time per design.
  The total pair budget is 720 seconds, including API/configuration/artifact
  overhead; stop after that budget, with no extension or tolerance changes.
- Cost basis: the existing same-config 6000 RPM reference completed 6 cycles
  in 76.219 s. The pair budget is more than nine times that observed run time,
  with a hard cap to accommodate slower convergence without opening an
  unbounded campaign.
- Eligibility and analysis rules are frozen by this spec before either new
  result is observed. If either result is not completed and periodic, record
  the status and do not calculate performance differences.

The integration gate is not a predictive-validation gate. Experimental
validation remains `NOT_PERFORMED`; predictive capability remains
`NOT_CLAIMED`.
