# Design — Integrated Performance V3

1. Use the existing periodic A9000 and A10000 artifacts as immutable source/reference evidence. Verify run/result/checkpoint hashes and the source periodicity classification.
2. Keep exact checkpoint restore semantics unchanged. A warm initialization is a distinct new run: transfer only validated physical state at the same phase, use the target RPM's already-defined controls, and bind the source hashes to the target run identity.
3. Reject differences in solver schema, topology, meshes, geometry, EOS, species, boundaries, CFL, combustion model, or other physical configuration. Permit only explicitly whitelisted operating RPM and its existing RPM-dependent power-valve map differences.
4. Reconstruct target native initial conditions from source conserved values. Verify target admissibility and before/after mass, energy and four-species inventories before taking a solver step. Start a clean periodicity detector and new ledger/time/combustion history.
5. Execute only A9000 → A10000 with a 40-cycle/240-second hard cap. Record performance against the historical 104-cycle/715.63-second A10000 cumulative reference. Do not extend a nonperiodic pilot.
6. Integrate into `power_curve_sweep` only if the pilot reaches the existing periodicity gate, matches the historical physical result within existing justified numerical tolerances, and demonstrates a substantial reduction. Otherwise close with a measured rejection/inconclusive result.
