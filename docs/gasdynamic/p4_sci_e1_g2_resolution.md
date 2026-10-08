# P4-SCI-E1 — G2 resolution experiment

## PRE-REGISTERED HYPOTHESIS

`H_NUM_RESOLUTION`: changing only `dx_target` from 0.003 m to 0.002 m
would materially reduce branch-B lag-2 sensor error.

## EXPERIMENT

The frozen G2 geometry and canonical initial conditions were used with
`NUMBA_FUSED`, CFL 0.4, float64, 3000 RPM, and N=375. No baseline restart or
interpolation was used. The physical campaign ran sequentially from cycle 1
through cycle 30, with checkpoints at 5, 10, 15, 20, 25 and 30 and FULL_DEBUG
at 20, 25 and 30.

## BASELINE

The baseline remains the prior N≈251 campaign. Its last three branch-B
lag-2 sensor metrics are 0.0897298, 0.0683317 and 0.0290580.

## RESULTS

Cycles 20, 25 and 30 are complete and have conservation residuals at roughly
10^-14. The runner failed while aggregating the final report because it
expected `steps` inside `segment.result.counts`; that key is not present in
the existing schema. Per-cycle summaries for the remaining cycles were not
persisted, so the required equivalent lag-2 sequence cannot be reconstructed
without rerunning the campaign.

## BASELINE VS REFINED / E13-R1

The primary branch-B comparison is **INCONCLUSIVE**. No PASS/FAIL or streak
claim is made for the refined run, and no convergence period is declared.

## CONSERVATION

The retained FULL_DEBUG cycles 20, 25 and 30 are complete and conserve the
combined ledger. No numerical regression was observed in retained evidence.

## INTERPRETATION / FALSIFICATION ASSESSMENT

`P4_SCI_E1_INCONCLUSIVE`: the physical run completed, but the artifact
aggregation defect prevents the pre-registered comparison. This result neither
supports nor weakens the resolution hypothesis.

## LIMITATIONS

The campaign is not repeated in this order. A future action would first need a
tooling fix and explicit authorization for a new single-variable run; the
existing physical evidence is preserved.

## NEXT DECISION

Human/scientific decision required. P4 remains blocked, E13-R1 is unchanged,
and P5 has not started.
