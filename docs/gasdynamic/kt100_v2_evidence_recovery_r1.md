# KT100 V2 evidence recovery R1

Status: **preregistered; recovery campaign not yet executed**.

## Forensic decision on original R6

The one original `OPEN_END_PLENUM_V2` campaign is preserved at
`results/kt100-hybrid-model-fixture-v2-harness-20261002-r6-open-end-plenum-v2/`.
Each RPM directory contains only `manifest.json.gz`, `summary.json.gz`, and
`failure.json.gz`. The failures report `KeyError('transfer1')` at 390 degrees;
the summary has zero complete cycles. There is no cycle-primary JSON, trajectory,
accepted-step trace, or checkpoint. The manifest binds configuration and source
hashes but contains no physical state history. Therefore the decision result
cannot be reconstructed offline from primary data. The original campaign proves
neither periodicity nor a physical KT100 outcome.

The source binding comparison confirms a single product-code change since R6:
`motorsim/reference_harness/evidence.py` now maps output roles `transfer1` and
`transfer2` to P6 species-state keys `tr1` and `tr2`. This mapping is covered by
`test_cycle_evidence_maps_transfer_output_names_to_p6_species_names`. The
solver, gas/species equations, boundary equations, geometry, configuration,
operating points, CFL, convergence thresholds, maximum cycles, and synthetic
engine parameters are unchanged.

## Frozen recovery

`KT100_V2_EVIDENCE_RECOVERY_R1` authorizes exactly one campaign using the same
five RPM values (5000, 7000, 9000, 11000, 13000) and the exact per-RPM
configuration hashes from R6. It retains CFL 0.4, mesh target 0.03 m, 400-cycle
cap, binary64, `fastmath=false`, `parallel=false`,
`REFERENCE_PERIODIC_CONVERGENCE_V1`, and `OPEN_END_PLENUM_V2` with
`SYNTHETIC_ASSUMPTION`. The result goes to a new directory; R6 remains immutable.

The runner verifies the preregistration commit, its own frozen hash, the R6
input hashes, the one-file product source delta, and every per-RPM configuration
hash before running. It refuses a changed input or an existing output directory.
The preregistration and runner are committed before this one recovery campaign.
No tuning or second recovery attempt is allowed under R1. Whatever the fixed
contract produces is recorded without changing thresholds or model selection.

P4 dependency remains `CONDITIONAL_ON_P4`; this is synthetic engineering
evidence, not experimental validation, a calibrated carburetor result, or a
Commercial Core acceptance.
