# P4-CONTRACT-REVIEW-01

## ORIGINAL CONTRACT

The original P4C document fixes G1 and G2 as the two exhaust geometries and
states: “continuar hasta periodicidad/límite” and “Sin resultado periódico,
E13 no PASS.” It also states that E14 requires G1/G2 and causal
`blowdown→geometría→puerto`. The OpenSpec requirement says E12–E15 require
“conservación, convergencia periódica, comparación y admisibilidad.” These
texts do not scope E13 to G1 alone.

## DOCUMENTED INTENT

G1 is the straight reference configuration and G2 is the chain geometry used
for the required wave/reflection comparison. The historical contract treats
both as P4C configurations subject to the same periodicity gate; G2 is not
documented as diagnostic-only.

## OBSERVED G2 RESULT

Cycles 1–30 completed with conservation and admissibility PASS. Branch A
lag-2 reached streak 5; branch B had 14 FAIL comparisons and streak 0. Lag-1
and lag-4 did not close. The detector audit found no pairing, identity, or
reset defect. This demonstrates nonclosure under E13-R1 through max30, not
chaos, instability, experimental realism, or asymptotic behavior.

## INTERPRETATION

The evidence supports `P4_CONTRACT_CONFIRMED_G2_PERIODICITY_REQUIRED`.
G2 periodicity is an explicit contractual gate, even though G2 also provides
geometry/reflection evidence. No post-hoc relaxation is justified by the
failed result. A counterfactual in which G2 E13 were diagnostic would leave
the other recorded gates passing, but that is not the current contract.

## POST-HOC RISK

Changing E13 to make the observed G2 result pass would be a post-hoc acceptance
change. The same wording could not honestly have been written before observing
the result without additional prior design evidence; therefore no contract
revision is applied here.

## CONCLUSION

P4 remains blocked. The next route is `SCIENTIFIC_CHANGE_REQUIRED`: a human
scientific decision is needed about the model/geometry behavior before any new
campaign. E13-R1, thresholds, and detector semantics remain unchanged. P5 and
experimental validation P9 have not started.
