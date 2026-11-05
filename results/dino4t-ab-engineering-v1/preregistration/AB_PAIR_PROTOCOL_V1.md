# Preregistered Dino 4T A/B Desktop integration pair

- Protocol: `DINO4T_DESKTOP_AB_PAIR_V1`
- Protocol source/base commit: `5e4ba4d27a8156d2cf3b07d633ae92c6dea213c5`
- Acceptance spec: `openspec/changes/dino4t-ab-engineering-v1/specs/dino4t-ab-engineering-v1/spec.md`
- Pair: unchanged example design A vs. duplicate B with intake-valve maximum
  harmonic lift 10.0 → 8.0 mm, at exactly 6000 RPM and equivalence ratio 1.0.
- Configuration/data status: synthetic assumptions; not a measured real motor.
- Identical across A/B: all other resolved inputs, model selections, numerics,
  initial conditions, fuel, ambient, loss models, code commit, and thermo data.
- Existing criteria only: max 20 cycles; current periodicity monitor thresholds
  remain exactly those recorded in each resolved configuration.
- Cost ceiling: 300 s solver wall time each, 720 s total for both calls,
  initialization and artifacts. No top-up or repeat of either point.
- Expected-cost reference: existing 6000 RPM result used 6 cycles / 76.219 s.
- Stop: stop a point at the API wall cap or 20 cycles, stop the pair at 720 s,
  preserve its actual classification and do not relax criteria.
- Analysis: differences only if both results report completed and
  `PERIODIC_CONVERGED`, with identical model IDs, numerical context, exact RPM,
  clean same-code identity, and thermo source hashes.
- Scientific claim: calculated model sensitivity only. No experimental
  validation or predictive claim.

This preregistration is committed before either A/B run.
